// mx-voice: the public half of voice dictation.
//   POST /stt?lang=es|en   body = 16 kHz mono WAV (the page converts)  -> {text}
//   POST /translate        {"text", "from": "en"|"es"}                   -> {text, ms}
// Both forward to the oracle-vm origin with the shared secret: /stt runs Parakeet on its CPU (free, no quota),
// /translate runs claude -p on the Max plan. No Anthropic key lives here, by rule.

const ALLOWED = ["https://paulrenzi.github.io", "http://localhost:8765"];
const MAX_AUDIO = 1_000_000; // ~30 s of 16 kHz mono 16-bit WAV
const MAX_TEXT = 400;

function cors(req) {
  const o = req.headers.get("Origin");
  return {
    "Access-Control-Allow-Origin": ALLOWED.includes(o) ? o : ALLOWED[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}
const json = (req, code, obj) =>
  new Response(JSON.stringify(obj), { status: code, headers: { "Content-Type": "application/json; charset=utf-8", ...cors(req) } });

async function stt(req, env, url) {
  if (!env.ORIGIN_URL || !env.ORIGIN_SECRET) return json(req, 503, { error: "origin_not_connected" });
  const lang = url.searchParams.get("lang");
  if (lang !== "es" && lang !== "en") return json(req, 400, { error: "lang must be es or en" });
  const buf = await req.arrayBuffer();
  if (!buf.byteLength || buf.byteLength > MAX_AUDIO) return json(req, 413, { error: "audio empty or longer than ~30 s" });
  return forward(req, env, "/stt?lang=" + lang, "audio/wav", buf);
}

async function forward(req, env, path, type, body) {
  const r = await fetch(env.ORIGIN_URL.replace(/\/$/, "") + path, {
    method: "POST",
    headers: { "Content-Type": type, "X-Origin-Secret": env.ORIGIN_SECRET },
    body,
  }).catch(() => null);
  if (!r) return json(req, 502, { error: "origin_unreachable" });
  const d = await r.json().catch(() => ({ error: "origin_bad_reply" }));
  return json(req, r.ok ? 200 : r.status === 503 ? 503 : 502, d);
}

async function translate(req, env) {
  if (!env.ORIGIN_URL || !env.ORIGIN_SECRET) return json(req, 503, { error: "origin_not_connected" });
  let body;
  try { body = await req.json(); } catch { return json(req, 400, { error: "bad json" }); }
  const text = String(body.text || "").trim();
  if (!text || text.length > MAX_TEXT || (body.from !== "en" && body.from !== "es")) return json(req, 400, { error: "need text and from en|es" });
  return forward(req, env, "/translate", "application/json", JSON.stringify({ text, from: body.from }));
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(req) });
    if (req.method === "GET" && url.pathname === "/") return json(req, 200, { ok: true, origin: !!env.ORIGIN_URL });
    if (req.method !== "POST" || !["/stt", "/translate"].includes(url.pathname)) return json(req, 404, { error: "not found" });
    if (url.pathname === "/stt") return stt(req, env, url);
    // Only translation spends the Max plan, so only it is capped per IP.
    const ip = req.headers.get("CF-Connecting-IP") || "?";
    const { success } = await env.LIMIT.limit({ key: ip });
    if (!success) return json(req, 429, { error: "rate_limited", detail: "Too many requests; wait a minute." });
    return translate(req, env);
  },
};
