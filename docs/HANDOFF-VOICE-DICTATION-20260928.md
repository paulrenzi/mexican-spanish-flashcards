# Handoff — scope a Mexican-Spanish voice dictation feature (2026-09-28)

**Written at HEAD `40d24e1`** (Doctor & dentist section). Supersedes nothing — this is the first
handoff in this repo. The phrasebook work before it is finished and live; see `git log`.

## The goal for the next session

**Scope, don't build (yet).** Paul wants a voice feature that works like Google Translate's
conversation mode — you tap a mic, someone speaks Mexican Spanish, you see the Spanish text and
an English translation (and ideally the reverse direction) — but **more accurate for Mexican
Spanish**, especially the local vocabulary this app already teaches (Riviera Maya / Akumal,
Quintana Roo). **Offline** is a strong wish for a *future* version, so the v1 choice should not
paint us into a corner that rules it out.

Deliverable of the next session: a short written scope (in `docs/`) with a recommended stack,
a measured accuracy comparison against Google Translate on real Mexican Spanish audio, the
size/latency cost on a phone, and a v1 / v2 (offline) split. Ask Paul before building.

## Where the app stands (so the scope fits it)

- Static vanilla-JS PWA, **no build step, no backend**. GitHub Pages from `main`:
  https://paulrenzi.github.io/mexican-spanish-flashcards/
- Files: `index.html`, `app.js`, `phrases.js` (951 phrases, 13 situation tabs), `style.css`,
  `sw.js` (cache `orale-v6` — **bump it on every shipped change**), `tests/render_check.py`
  (Playwright render gate — run it, a page is verified by rendering, never by HTTP 200; live
  checks need `?cb=` to dodge the Pages cache).
- It already **speaks** Spanish with `speechSynthesis` (`app.js` ~line 23–41, prefers an `es-MX`
  voice). It does **not listen** yet — that is the new part.
- 🔑 `phrases.js` is an asset for accuracy: ~950 curated Mexican phrases + local words (Oxxo,
  colectivo, cenote, predial, CLABE, ajustador, Chopo…). Usable as a recognizer vocabulary /
  prompt bias and as a translation glossary.

## Candidate building blocks (checked on GitHub 2026-09-28 — re-verify, don't trust)

| Piece | Option | Notes |
|---|---|---|
| Speech-to-text, online, zero effort | Web Speech API `SpeechRecognition` with `lang="es-MX"` | Chrome/Android send audio to Google — this *is* roughly Google's recognizer, so it can't beat it on accuracy. iOS Safari support is patchy. Good as a baseline / fallback only. |
| STT in the browser, offline | **Whisper via `huggingface/transformers.js`** (Apache-2.0, ★16k, active) — demo app `xenova/whisper-web` (MIT, ★3.3k, last push 2024-10) | Runs on WebGPU/WASM, model cached by the service worker ⇒ offline. Whisper accepts an **initial prompt** — feed it Mexican vocabulary from `phrases.js`. Size vs accuracy: tiny/base are small but weak; small/turbo are better but hundreds of MB. Measure on a mid-range phone. |
| STT native/server | `ggml-org/whisper.cpp` (MIT, ★54k, very active), `SYSTRAN/faster-whisper` (MIT) | whisper.cpp also has a WASM build. faster-whisper would need a server (we have none; oracle-vm or a Cloudflare Worker AI endpoint are options to price). |
| STT offline, lightweight | `alphacep/vosk-api` (Apache-2.0, ★15k) + `ccoreilly/vosk-browser` (WASM) | Small Spanish model (~40–50 MB), streaming, supports a **restricted grammar/word list** — could be very accurate *for our phrasebook* and weak on free speech. Worth measuring. |
| STT small/fast | `moonshine-ai/moonshine` (★11k, license NOASSERTION — check) | Was English-first; check whether a Spanish model exists now. |
| Translation offline | Bergamot / Firefox Translations (`browsermt/bergamot-translator`, MPL-2.0); `mozilla/firefox-translations-models` is **archived** (models moved — find where) | es↔en models are small (~15–40 MB), run in WASM. |
| Translation offline, alt | Marian `opus-mt-es-en` / `opus-mt-en-es` via transformers.js | Easy if Whisper is already on transformers.js. |
| Translation built-in | Chrome's on-device Translator API | Free, offline once downloaded, Chrome-only. Check status. |
| Also look for | Whisper checkpoints **fine-tuned on Mexican Spanish** on Hugging Face; Mexican Spanish test sets (Common Voice es with MX accent tag, CIEMPIESS corpus) | This is the likeliest real accuracy win over Google. |

**Note:** Whisper can translate Spanish→English directly (`task: "translate"`), which may remove
the separate translation model for the listen direction.

## How "more accurate than Google" should be judged

Don't claim it — measure it. Suggested method for the scope:
1. Collect 30–50 short clips of real Mexican Spanish in the app's situations (a taxi quote, a
   pharmacy question, a mechanic's answer). Paul is in Mexico and can record people (with
   permission) — ask him. Common Voice/CIEMPIESS clips can fill in.
2. Score word error rate for: Web Speech API (≈Google), Whisper base/small/turbo, Whisper +
   vocabulary prompt, a Mexican fine-tune, Vosk.
3. Separately rate translation quality on the same clips vs Google Translate's output.
4. Record model download size and time-to-text on a real phone.

## Open questions for Paul (ask, don't assume)

- Which phone(s)? iPhone vs Android changes what runs well in the browser (WebGPU, mic APIs).
- One-way (understand what they say) first, or two-way conversation from day one?
- Is a one-time download of ~100–500 MB acceptable for offline mode?
- Is a small server/API cost OK for an online v1, or must it stay free and static?

## Standing rules for this repo

- Push every finished change to `main` (Pages deploys it); bump `sw.js` cache version.
- Run `tests/render_check.py` locally and against the live URL with `?cb=` before calling it done.
- No secrets in git. Commit with `git commit -F -` and a quoted heredoc.
- The Spanish in `phrases.js` has **not** been reviewed by a native speaker — say so in any
  accuracy claim.
