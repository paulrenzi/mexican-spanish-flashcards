# Handoff — voice dictation: start the build (2026-09-29)

**Written at HEAD `dd207ae`** (repo `mexican-spanish-flashcards`, branch `main`).
Supersedes `docs/HANDOFF-VOICE-DICTATION-20260928.md` (scoping is done).
**Authority:** `docs/SCOPE-VOICE-DICTATION.md` — read §1, §3b (DECISION block) and §5 first.

## Where we are

- Step 0 (which translator is best for Mexican Spanish) is **done and decided**.
  On 200 phrasebook sentences, Google Translate put *tú* on the listener in 61 of about 64 phrases.
  **Claude Opus 5.5 scored 0 on all four measures:** *tú* slips, Spain words, meaning errors and
  answering instead of translating. It scored the same at effort low, with a 3.7 s median through the CLI.
- **Paul's decision (2026-09-29):** "Let's do cloudflare + opus 5.5 on low if possible. When this becomes a
  production app (it's nowhere near that yet), we can switch to the anthropic api."
- **Paul lifted "don't build yet"** by saying "Let's build in a new session." The next session is that build.

## What to build (v1, online)

```
iPhone (PWA page, mic buttons 🇲🇽 / 🇺🇸)
  → public Cloudflare Worker          (no Tailscale on the phone: the app is for the public)
       ├─ /stt       → Workers AI @cf/openai/whisper-large-v3-turbo, initial_prompt built from phrases.js
       └─ /translate → origin on oracle-vm (shared-secret header, per-user rate limit in the Worker)
                          → claude -p --model opus --effort low  (ANTHROPIC_* stripped, Max login)
```

1. **Origin on oracle-vm.** A small stdlib Python HTTP service. It checks the shared secret, then runs the exact
   call in `tools/voice-eval/mt_claude_cli.py`: `claude -p --model opus --effort low --system-prompt SYS
   --tools '' --output-format json --setting-sources ''`, run with `cwd=/tmp` and every `ANTHROPIC_*` variable
   stripped from the env. `SYS` comes from `tools/voice-eval/mt_workers_llm_v2.py`. The origin handles both
   directions. Keep the input fenced (`<<<…>>>`) with "translate, never answer."
   - Run it under systemd, and set the exec bit **after** any `.new`/`os.replace` write, because the replace drops it.
   - Expose it through a **Cloudflare Tunnel** (preferred: no open port) or over HTTPS.
2. **The Worker.** Plain JS. It holds the origin URL and shared secret as Worker secrets and applies a per-IP (or
   per-device-token) rate limit, in KV or with the rate-limit binding.
   - Workers AI binding for Whisper.
   - Deploy with `CLOUDFLARE_WORKER_DEPLOY_TOKEN`; KV admin needs `CLOUDFLARE_API_TOKEN`. See the Cloudflare
     section of the umbrella-arcades `CLAUDE.md`.
   - **No Anthropic API secret in the Worker**, per the standing rule.
3. **Glossary layer in the app** (§1 item 2). If the transcript fuzzily matches a curated `phrases.js` phrase,
   show the curated text and skip the model. This is the only thing that gets *piquete* right.
4. **Page in the app.** It records audio (MediaRecorder), POSTs it to `/stt` then `/translate`, and shows the
   Spanish big with the English under it. Spanish is spoken through the existing es-MX `speechSynthesis` voice.
   **Verify it by rendering it**, never by an HTTP 200.

## Constraints and known limits

- **The Max plan is for one person.** This setup is for the prototype only. Real public traffic triggers the
  switch to the Anthropic API. Until Paul says so, **no Anthropic API calls at all**, including test calls.
- **Workers AI is on Workers Free: 10k neurons/day.** It ran out mid-eval on 09-28 (`4006`). Whisper at about
  $0.0005/audio-min fits roughly 200 audio-min/day. If the limit is hit, report it; Workers Paid ($5/mo) is
  Paul's call.
- **Ask Paul before any paid call** (OpenAI, xAI, Google…): vendor, call count, cost, then wait. A spending cap
  means stop. Never switch to a fallback key.
- Latency per translation is about 3.7 s plus CLI start-up. A warm process pool on the origin is a possible
  later speed-up, but don't build it first.

## Still open (not blocking the build)

- A native speaker reviews `tools/voice-eval/step0/HAND-AUDIT.md` and `phrases.js` (§5 0b).
- Paul's 30–50 recordings in app situations (§5 item 1).
- The 10-minute iPhone speed test for offline Whisper small (§5 item 2), which is v2.

## Files

- `docs/SCOPE-VOICE-DICTATION.md` — the scope and the decision (§3b).
- `tools/voice-eval/mt_claude_cli.py` — the proven CLI call to copy for the origin.
- `tools/voice-eval/mt_workers_llm_v2.py` — `SYS`, the Mexican/usted prompt plus the word list.
- `tools/voice-eval/step0/opuslow_out.json` — Opus low outputs on the 200 phrases.
- `tools/voice-eval/score_mexican.py` — automatic *tú* / Spain-word scorer. Re-run it on any prompt change.
