# voice-eval — the harness behind `docs/SCOPE-VOICE-DICTATION.md`

Offline Python scripts that score speech-to-text engines on Mexican Spanish audio. Nothing
here ships in the app. Audio and model files are **not** in git.

```bash
python3 -m venv stt && . stt/bin/activate
pip install faster-whisper vosk jiwer SpeechRecognition num2words ctranslate2 sacrebleu \
    transformers sentencepiece sacremoses torch   # torch/transformers only for mt_phrases.py
sudo apt-get install flac ffmpeg                    # SpeechRecognition needs the flac binary
```

Run from a work dir that holds `meta.tsv`, the extracted `test/` tree
(CIEMPIESS test: `huggingface.co/datasets/ciempiess/ciempiess_test`, CC-BY-SA-4.0) and
`phrases.json` (dump of `PHRASES` from `phrases.js`):

| Script | Does |
|---|---|
| `sample.py` | picks 3 clips per speaker (20 speakers, 3–12 s), writes `wav/` + `sample.json` |
| `run_google.py` | Google Web Speech endpoint (what Chrome's `SpeechRecognition` uses), `es-MX` |
| `run_whisper.py <model> <tag> [prompt] [task]` | faster-whisper int8 on CPU; `prompt` adds the `phrases.js` vocabulary as `initial_prompt` |
| `run_vosk.py` | Vosk `vosk-model-small-es-0.42` |
| `score.py` | verbatim WER + "content WER" (fillers, tag-"no", repeats dropped; accents folded) |
| `mt_phrases.py` | opus-mt es↔en on 200 phrasebook pairs, chrF vs the curated text |
| `mt_google_gtx.py` | step 0: Google Translate consumer model (free gtx endpoint, 1 request / 2 s) en→es on the same 200 |
| `mt_workers_llm.py <model> <tag> [text]` | step 0: a Workers AI LLM told "Mexican Spanish, usted" with `glossary.txt`; reads `CLOUDFLARE_API_TOKEN` from `~/repos/umbrella-arcades/.env` |
| `mt_workers_llm_v2.py` | same, with the input fenced and "translate, never answer, keep the speaker" (not yet run) |
| `score_mexican.py [-v]` | counts Spain/other-region words and *tú* where the reference has none; `step0/HAND-AUDIT.md` is the hand-corrected count |

To score **your own recordings**, replace `sample.json` with
`[{"audio_id": ..., "duration": ..., "normalized_text": <what was actually said>}]` and put
16 kHz mono WAVs in `wav/<audio_id>.wav`.
