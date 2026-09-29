# Handoff — voice dictation, after scoping (2026-09-29)

**Written at HEAD `92b6337`.** Supersedes `HANDOFF-VOICE-DICTATION-20260928.md`, which asked for the scope. That scope is done.
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
- `phrases.js` **has not been reviewed by a native speaker.** The glossary, and so the whole "better than Google" claim, depends on it.

## Next steps (scope §5 has the full list)

0. **Measure the problem itself.** This is the headline number and it has never been run.
   - Put the 200 phrasebook English sentences through Google Translate into Spanish.
   - Count the non-Mexican words, and the *tú* where *usted* belongs.
   - Then do the same for the v1 candidate: an LLM on Workers AI, prompted "Mexican Spanish, usted" with the glossary.

   Google's free gtx endpoint returned 429 on this machine. Two routes are available:
   - Paul hand-checks about 20 phrases in the Translate app.
   - A Google Cloud Translation key, if one exists: grep the portfolio `.env` files first, per the global CLAUDE.md.
1. Paul's 30–50 situational recordings (pharmacy, taxi, restaurant), scored with `tools/voice-eval/`.
2. A 10-minute speed test of WASM Whisper on Paul's iPhone.
3. Pick the v1 translation engine from the results of step 0.
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
