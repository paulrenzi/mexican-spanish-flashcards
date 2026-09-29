# Handoff: voice dictation v1 built, one link missing (2026-09-29)

**Written on top of HEAD `9edf2c3`** (repo `mexican-spanish-flashcards`, branch `main`); the build is in the commit
that adds this file. **Supersedes** `docs/HANDOFF-VOICE-DICTATION-BUILD-20260929.md` (the build plan).
The authority is still `docs/SCOPE-VOICE-DICTATION.md` §1 / §3b.

## State in one line

Every piece is built and tested. The **Worker → origin link is NOT connected**, because the Cloudflare Tunnel was
refused by the session's permission classifier ("External Ingress Tunnel"), so it needs Paul's explicit OK. Speech-to-text is also
**untested live**, because the Workers AI allowance was already spent today (`4006`).

## What exists

| Piece | Where | Status |
|---|---|---|
| **Origin** (stdlib Python) | `voice/origin/server.py`, systemd `mx-voice-origin` on **claude-dev** (the oracle VM this repo lives on, tailnet `100.76.150.60`, where `claude` is logged in) | ✅ running, `127.0.0.1:8791` only. Runs `claude -p --model opus --effort low`, with `ANTHROPIC_*` stripped. 2 concurrent slots. The secret is in `~/.config/mx-voice/origin.env` (mode 600, not in git). |
| **Worker** `mx-voice` | `voice/worker/`, `https://mx-voice.paulmichaelrenzi.workers.dev` | ✅ deployed. `/stt` = Whisper large-v3-turbo with the §2 vocab prompt (`vocab.js`, rebuild with `node make_vocab.cjs`). `/translate` → origin. Rate limit 12/min per IP per route. CORS allows GitHub Pages and localhost:8765. No Anthropic secret. |
| **Talk tab** in the app | `talk.js`, `index.html`, `style.css`; `app.js` exposes `window.oraleSpeak` | ✅ The mics record, the page converts the audio to 16 kHz mono WAV in the browser (so Whisper never sees iPhone mp4/AAC), and results show Spanish big with English under. Spanish from English is spoken with the es-MX voice. There is also a type-it fallback. |
| **Glossary layer** | `talk.js` `matchPhrase()` | ✅ normalised Levenshtein ≥ 0.88 against every `phrases.js` phrase and word (template "…" phrases skipped). A match skips the model and is labelled "From the phrasebook". |

## Verified

- `python3 tests/render_check.py`: **ALL PASS**, including 19 new Talk checks. Chromium's fake mic records → the WAV is POSTed
  (`RIFF`, ~50 KB) → the mocked `/stt` → a phrasebook hit with no `/translate` call. An unmatched sentence goes to `/translate`,
  the `stt_quota` message appears, typed input works, and the 360px header fits. Screenshots: `tests/shots/11-talk.png`, `12-talk-narrow.png`.
- That test also caught a **pre-existing-class bug**: the header needed 394px, so mobile Chrome zoomed the whole page out at
  ≤390px. The old overflow checks passed anyway, because `innerWidth` grows with the content. Fixed (`.sub` hidden ≤420px), and the
  check now asserts `innerWidth == 360`.
- **The origin works live** through the CLI on Max: *Can you give me a discount?* → *¿Me puede hacer un descuento?*; *That is all, thanks* →
  *Eso es todo, gracias.* (translated, not answered). **es→en on 30 phrasebook lines:** 0 meaning errors, median 3.1 s.
  The es→en prompt is new (the en→es prompt is byte-for-byte the measured `mt_workers_llm_v2` one). It names *piquete, cajero, ¿pica?, cloro,
  bomba, cada tercer día, pipa*, so those rows are partly circular.
- The deployed Worker was probed: `GET /` gives `{"ok":true,"origin":false}`; `/stt` gives `503 stt_quota`; `/translate` gives `503 origin_not_connected`. CORS was checked too.

## Blocked, and what unblocks it

1. **Worker → origin (Paul's OK needed).** `POST /accounts/…/cfd_tunnel` was never sent: the classifier refused it as opening
   internet ingress into the VM. The tokens *can* list tunnels (`cfd_tunnel` GET succeeds on all four); create was not attempted.
   **To finish:** Paul approves, then the steps below run.
   - Create a remotely managed tunnel `mx-voice-origin` → `http://127.0.0.1:8791`. `~/bin/cloudflared` (arm64, 2026.9.3) is already installed.
   - Give it a hostname on a zone we hold (`akumalwildlife.com`, `emunexus.com`, `tokenoptimal.com`; there is no zone for this app).
     Alternatively, bind it to the Worker with a Workers VPC service, which needs no public hostname.
   - Run cloudflared as a systemd unit.
   - Then `wrangler secret put ORIGIN_URL` and `ORIGIN_SECRET` (the value from `~/.config/mx-voice/origin.env`).
   - The origin already refuses anything without the secret (403). Cloudflare Access with a service token would add a second lock.
2. **Speech-to-text live test**: after 00:00 UTC. POST a 16 kHz WAV to `/stt?lang=es`, e.g. one from `/tmp/vd/wav/`.
   The allowance is 10k neurons/day on Workers Free and it was already spent when this session started. If real use keeps
   hitting it, **Workers Paid ($5/mo) is Paul's call.**
3. **iPhone test**: Safari `MediaRecorder` → `decodeAudioData` → WAV has only run in Chromium. Open the Talk tab on the phone.

## Known limits

- **Max plan = one person.** Nothing here throttles *total* traffic except 12/min per IP and 2 origin slots. Public traffic is the trigger for the
  Anthropic API switch, and that is Paul's call. Until then, no API calls, including test calls.
- The Talk tab ships on the live site with the rest of the app. Until the link is connected, only phrasebook matches and the error
  messages work there.
