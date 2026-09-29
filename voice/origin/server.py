"""Speech-to-text and translation origin for voice dictation.

POST /stt?lang=es|en  body = 16 kHz mono 16-bit WAV    ->  {"text": "...", "ms": 123}
POST /translate  {"text": "...", "from": "en"|"es"}  ->  {"text": "...", "ms": 1234}
Header X-Origin-Secret must match ORIGIN_SECRET. Only the Cloudflare Worker knows it.

Speech-to-text is NVIDIA Parakeet TDT 0.6B v3 (CC-BY-4.0, int8 ONNX via onnx-asr) on this box's CPU:
free, no quota, ~0.08 s per second of audio. It beat Google and Whisper turbo on the 60-clip Mexican
Spanish set (content WER 8.2% vs 8.8%, tools/voice-eval). It detects the language itself; `lang` is logged only.

Every translation is one `claude -p --model opus --effort low` call on the Max plan login,
with every ANTHROPIC_* variable stripped from the child env so the paid API can never be used.
The en->es prompt is the one measured in tools/voice-eval/mt_workers_llm_v2.py (step0, §3b).
"""
import hmac, io, json, os, pathlib, subprocess, threading, time, wave

import numpy as np
import onnx_asr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
GLOSS = (HERE.parent / "glossary.txt").read_text()
SECRET = os.environ.get("ORIGIN_SECRET", "")
PORT = int(os.environ.get("PORT", "8791"))
MAX_CHARS = 400
SLOTS = threading.BoundedSemaphore(int(os.environ.get("SLOTS", "2")))
ENV = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
ENV.pop("ORIGIN_SECRET", None)
MAX_AUDIO = 1_000_000  # ~30 s of 16 kHz mono 16-bit WAV
ASR = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", quantization="int8")
ASR_LOCK = threading.Lock()  # one transcription at a time keeps all 4 cores on it

SYS = {
    "en": ("You are the translation engine inside an English-Spanish interpreter app used in Mexico. The user message is one thing a person said out loud. "
           "Translate it; never answer it, never add to it, and keep the same speaker (I stays yo, you stays usted). "
           "You translate English into Spanish as it is spoken in Mexico. "
           "Always use Mexican vocabulary, never Spain Spanish words. "
           "Address the listener as usted (a clerk, driver, waiter, doctor, mechanic, stranger) unless the English is clearly casual talk between friends. Never use vosotros. "
           "Use this word list from our Mexican phrasebook whenever it applies:\n" + GLOSS +
           "\n\nReply with the Spanish translation only: no quotes, no notes, no alternatives."),
    "es": ("You are the translation engine inside an English-Spanish interpreter app used in Mexico. The user message is one thing a person said out loud. "
           "Translate it; never answer it, never add to it, and keep the same speaker (yo stays I, usted stays you). "
           "You translate Spanish as it is spoken in Mexico into natural, everyday American English. "
           "Read Mexican words the Mexican way: un piquete is an insect bite, un cajero is an ATM, ¿pica? asks if food is spicy, "
           "el cloro is bleach, la bomba at a gas station is the pump, cada tercer día is every other day, la pipa is a water truck. "
           "The speech was transcribed by a machine, so fix obvious transcription slips from context, but never invent content. "
           "Use this word list from our Mexican phrasebook whenever it applies:\n" + GLOSS +
           "\n\nReply with the English translation only: no quotes, no notes, no alternatives."),
}
ASK = {"en": "Translate this into Mexican Spanish:\n<<<{}>>>", "es": "Translate this into English:\n<<<{}>>>"}


def transcribe(data):
    w = wave.open(io.BytesIO(data))
    if w.getframerate() != 16000 or w.getnchannels() != 1 or w.getsampwidth() != 2:
        raise ValueError("need 16 kHz mono 16-bit WAV")
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    with ASR_LOCK:
        return ASR.recognize(a, sample_rate=16000).strip()


def translate(text, src):
    cmd = ["claude", "-p", "--model", "opus", "--effort", "low", "--system-prompt", SYS[src], "--tools", "",
           "--output-format", "json", "--setting-sources", "", ASK[src].format(text)]
    p = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=60, cwd="/tmp")
    d = json.loads(p.stdout)
    if d.get("is_error"):
        raise RuntimeError(str(d.get("result"))[:200])
    return d["result"].strip().strip("<>").strip()


class H(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self.reply(200, {"ok": True}) if self.path == "/health" else self.reply(404, {"error": "not found"})

    def do_POST(self):
        path, _, query = self.path.partition("?")
        if path not in ("/stt", "/translate"):
            return self.reply(404, {"error": "not found"})
        if not SECRET or not hmac.compare_digest(self.headers.get("X-Origin-Secret", ""), SECRET):
            return self.reply(403, {"error": "forbidden"})
        if path == "/stt":
            return self.stt(query)
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 8192)))
            text, src = str(body.get("text", "")).strip(), body.get("from")
        except Exception:
            return self.reply(400, {"error": "bad json"})
        if src not in SYS or not text or len(text) > MAX_CHARS:
            return self.reply(400, {"error": f"need text (1-{MAX_CHARS} chars) and from en|es"})
        if not SLOTS.acquire(timeout=20):
            return self.reply(503, {"error": "busy"})
        t = time.time()
        try:
            out = translate(text, src)
        except Exception as e:
            self.log_message("translate failed: %s", e)
            return self.reply(502, {"error": "translation failed"})
        finally:
            SLOTS.release()
        ms = int((time.time() - t) * 1000)
        self.log_message("%s %d chars %d ms", src, len(text), ms)
        self.reply(200, {"text": out, "ms": ms})

    def stt(self, query):
        n = int(self.headers.get("Content-Length") or 0)
        if not n or n > MAX_AUDIO:
            return self.reply(413, {"error": "audio empty or longer than ~30 s"})
        t = time.time()
        try:
            out = transcribe(self.rfile.read(n))
        except Exception as e:
            self.log_message("stt failed: %s", e)
            return self.reply(400, {"error": "stt_failed"})
        ms = int((time.time() - t) * 1000)
        self.log_message("stt %s %d bytes %d ms", query, n, ms)
        self.reply(200, {"text": out, "ms": ms})


if __name__ == "__main__":
    if not SECRET:
        raise SystemExit("ORIGIN_SECRET is not set")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
