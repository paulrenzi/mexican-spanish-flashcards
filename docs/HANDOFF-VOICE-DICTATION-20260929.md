# Handoff — voice dictation, after scoping (2026-09-29)

**Written at HEAD `92b6337`; step 0 results added 2026-09-29 on top of `b98efb7`.** Supersedes `HANDOFF-VOICE-DICTATION-20260928.md`, which asked for the scope. That scope is done.
**The authority is `docs/SCOPE-VOICE-DICTATION.md`. Read it first.** This file only says where things stand and what comes next.

## The goal, in Paul's words

> "When I select Spanish in Google Translate, I get non Mexican Spanish, and I have no idea how
> to select Mexican Spanish, which means most other people don't either. That's what we are solving for."

The product is **Mexican Spanish out, with no setting to find.** It is a two-way conversation mode on the iPhone.

## What is settled

- **Paul's answers:** iPhone, two-way from day one, up to about 500 MB offline download, and a small server cost is OK.
- **Speech-to-text is not the gap.** Content WER on 60 CIEMPIESS clips of real Mexican speech:
  - Google es-MX: 8.8%
  - Whisper large-v3-turbo with the phrasebook vocabulary as prompt: 8.8% (a tie)
  - Turbo alone: 9.7%
  - The LATAM fine-tune: 10.2% (it does not beat stock turbo)
  - small: 11.1%
  - Vosk: 14.6%

  Full table and confidence intervals are in scope §2.
- **Translation is the gap.** opus-mt, the offline candidate, produces Spain Spanish:
  - It uses *lejía* and *sirope* where Mexicans say *cloro* and *jarabe*.
  - It uses *tú* where *usted* belongs.
  - Going into English, it misreads *piquete* and *cajero*.
  - chrF is about 59 in each direction.

  Details are in scope §3.
- **v1 (online) plan:**
  1. Whisper turbo on Cloudflare Workers AI (about $0.0005 per audio minute).
  2. An **instruction LLM** told "Mexican Spanish, usted", with `phrases.js` as a glossary.
  3. Google Cloud Translation as the comparison.

  A glossary alone cannot fix *tú/usted*.
- **v2 (offline):** English→Mexican Spanish offline is the hardest unsolved piece (scope §5). The candidates are:
  - Curated phrases first.
  - A small on-device LLM, which is probably too big.
  - Apple Translation through a native shell (Capacitor).

  WebGPU Whisper reportedly fails on iPhone WebKit, so plan for WASM on the CPU.

## 🛑 Rules that still hold

- **Don't build yet.** Paul has not approved a build.
- Never use the paid Anthropic API. Never commit or print a key.
- Copying credentials from paulspc was refused by the classifier. Do not try that again by any route.
  (The portfolio `.env` files are already present on the oracle VM under `~/repos/*/.env`. Step 0 used those, and nothing was copied.)
- `phrases.js` **has not been reviewed by a native speaker.** The glossary, and so the whole "better than Google" claim, depends on it.

## Next steps (scope §5 has the full list)

0. ✅ **Done 2026-09-29 — scope §3a.** Google puts *tú* on the listener in **61 of about 64**
   phrases that address someone. The v1 candidate (`gpt-oss-120b` on Workers AI, "Mexican Spanish,
   usted" + the 182-word list) does it **once**. Spain words: Google 8 phrases, candidate 2.
   Llama 3.3 70B and Mistral Small 3.1 were rejected. Still open from step 0:
   - Run `tools/voice-eval/mt_workers_llm_v2.py` (the fix for "answers instead of
     translating"). It was blocked by the Workers AI **free** allowance
     (`4006 … daily free allocation of 10,000 neurons`). The allowance resets at 00:00 UTC, or put
     the account on Workers Paid, which v1 needs anyway ($5/month; Paul's call).
   - A native speaker re-checks `tools/voice-eval/step0/HAND-AUDIT.md`.
   - No portfolio key can call Google Cloud Translation (scope §5 item 3 has the live-check errors).
     It is not needed: the consumer model was measured instead.
1. Paul's 30–50 situational recordings (pharmacy, taxi, restaurant), scored with `tools/voice-eval/`.
2. A 10-minute speed test of WASM Whisper on Paul's iPhone.
3. Pick the v1 translation engine. Step 0 points at gpt-oss-120b + instruction + glossary layer, pending the v2 prompt run.
4. Optional: a gpt-4o-transcribe test (the key is in `triumvirate/.env`), and Vosk grammar mode.

## Where things are

- Harness: `tools/voice-eval/`. The README explains setup and every script.
- Audio, models and the scored outputs were in `/tmp/vd` and `/tmp/stt` on the oracle VM. They are **not in git and are gone after this container.**
  - To rebuild: re-run `sample.py` on CIEMPIESS test (Hugging Face `ciempiess/ciempiess_test`).
  - Whisper speed on the VM CPU, as real-time factor (seconds to process each second of audio), for the 60-clip sample:

    | Model | RTF |
    |---|---|
    | tiny | 0.29 |
    | base | 0.51 |
    | small | 0.65 |
    | turbo | 1.39 |
    | turbo + prompt | 1.50 |

- No background processes are running.
