# Scope — Mexican Spanish voice dictation (2026-09-28)

**Written at HEAD `34903df`**; answers `docs/HANDOFF-VOICE-DICTATION-20260928.md`.
Scope only. **Nothing is built.** Harness: `tools/voice-eval/`.

## Paul's answers (2026-09-28)

| Question | Answer | What it changes |
|---|---|---|
| Phone | **iPhone** | Every browser on iPhone is WebKit. Chrome's on-device Translator API is unavailable, and `SpeechRecognition` means Apple's recognizer, not Google's. |
| Direction | **Two-way from day one** | Needs English speech-to-text and English→Spanish, which must sound Mexican (usted, *carro*, *cloro*). |
| Offline download | **Up to ~500 MB** | Allows Whisper **small** in the browser; turbo does not fit (below). |
| Online v1 cost | **A small cost is OK** | v1 can use a server-side model through one Cloudflare Worker. |

## The problem we are solving (Paul, 2026-09-28)

> When I select Spanish in Google Translate, I get non-Mexican Spanish, and I have no idea
> how to select Mexican Spanish, which means most other people don't either.

So the product is **Mexican Spanish out, with no setting to find.** In practice that means:
- **English→Spanish must come out Mexican.** That means Mexican words (*carro, cloro, jarabe,
  popote, alberca, celular*), *usted* by default when talking to a clerk, a driver or a
  mechanic, and never *vosotros*.
- **Spanish→English must understand Mexican words** (*piquete, cajero, ¿pica?, ahorita*).
- **Speech-to-text is not the gap.** §2 shows Whisper already ties Google on Mexican speech.
  The gap is in the **translation**, and §3 shows it.

As far as a search found (2026-09-28), Google Translate offers a single "Spanish" as a
translation target, with no Mexican variant to pick. This is unconfirmed. Low-quality SEO pages
dominate the results, and Google's help pages were not checked.

## 1. Recommended setup

**v1 (online):** a mic button for each speaker (🇲🇽 / 🇺🇸), like Google's manual conversation
mode. Automatic language detection on short utterances is the usual failure, so we skip it.
1. **Speech-to-text:** Whisper **large-v3-turbo** on **Cloudflare Workers AI**, reached through one
   small Worker. Its `initial_prompt` is built from the `phrases.js` vocabulary. Cost: $0.0005 per
   audio minute, and 10k free neurons a day covers about 200 audio minutes a day.
2. **Glossary layer (in the app, plain JS):** if the transcript matches a curated phrase
   (normalised, fuzzy), show the curated English. Otherwise run MT, with `phrases.js` words
   pinned as a glossary. §3 shows why this layer is the real accuracy win.
3. **Translation:** a model that takes a glossary and a register instruction ("Mexican
   Spanish, usted"). An instruction LLM on Workers AI is the first candidate, because an
   instruction is the only way to get register right. A glossary alone can fix words but not
   *tú/usted*. Google Cloud Translation is the comparison. **Not yet measured — see §5.**
4. **Output:** Spanish shows big; English goes underneath. Spanish is spoken with the existing
   `speechSynthesis` es-MX voice.

**v2 (offline, iPhone):** Whisper **small** in the browser (whisper.cpp WASM `ggml-small-q5_1`,
190 MB, or transformers.js ONNX int8, 249 MB). Bergamot es↔en for translation (WASM, tens
of MB per direction). The **same glossary layer**. The service worker caches all of it.
Fallback if iPhone WASM is too slow: see §4.

**Why this keeps offline open:** v1 and v2 use the same model family (Whisper), the same
prompt-from-`phrases.js` trick, and the same client-side glossary layer. v2 only swaps
where the model runs.

## 2. Speech-to-text accuracy vs Google (measured)

**Test set:** CIEMPIESS-TEST (UNAM). Mexican Spanish broadcast conversation, 20 speakers
(10 F / 10 M), 3 clips each, 60 clips, 8.2 min. Real, spontaneous, accented speech.
It is **not** the app's situations (no taxis, pharmacies or mechanics). **Google** here is
Google's Web Speech endpoint with `es-MX`, the recognizer behind Chrome's `SpeechRecognition`.
Google Translate's app may use a newer model.

The references are verbatim ("e", "eh", "entoces", stutters). Whisper tidies these, so a
**content WER** (fillers, tag-"no", repeats dropped, accents folded) is the fairer column.
Lower is better.

| Engine | Size (phone download) | Verbatim WER | **Content WER** | CPU speed here¹ |
|---|---|---|---|---|
| Google Web Speech es-MX | server | **12.1%** | **8.8%** | — |
| Whisper large-v3-turbo **+ phrasebook prompt** | server (563–759 MB in browser) | 13.3% | **8.8%** | 1.5× real time |
| Whisper large-v3-turbo | same | 14.1% | 9.7% | 1.4× |
| **LATAM** fine-tune (turbo)² | 820 MB (CT2 int8) | 15.0% | 10.2% | 1.6× |
| Whisper small | 190 MB q5_1 / 249 MB ONNX | 15.9% | 11.1% | 0.65× |
| Whisper small + prompt | same | 16.4% | 11.1% | 0.79× |
| Vosk small es 0.42 | 39 MB zip / 58 MB | 18.2% | 14.6% | **0.14×** (streams) |
| Whisper base | 60 MB q5_1 / 77 MB | 20.6% | 15.9% | 0.51× |
| Whisper tiny | 41 MB | 23.3% | 19.0% | 0.29× |

¹ Time to transcribe ÷ audio length. int8, beam 5, 4 vCPU x86 (oracle `claude-dev`), not a phone.
² `marianbasti/whisper-large-v3-turbo-latam` (MIT; Common Voice 17 es, filtered to Latin American
accents), run as `nekusu/faster-whisper-large-v3-turbo-latam-int8-ct2`. **No Whisper checkpoint
trained specifically on Mexican Spanish exists on Hugging Face** (searched 2026-09-28: `mexican`,
`mexico`, `es-mx`, `ciempiess`, `latam`). The only `es_mx` hits are ERISLab
question-answering experiments, not transcribers. **The LATAM fine-tune is worse than stock
turbo here (+0.5 pts) and slower, so it is not recommended.** Its gain on its own card is
measured on Common Voice *read* speech, which is not what people say in a taxi.

**What this says, plainly:**
- **Nothing beats Google on general Mexican speech.** Turbo with the vocabulary prompt **ties**
  it: the difference is 0.0 points, with a 95% bootstrap interval of −1.4 to +1.4. It wins on
  9 of 20 speakers and ties on 4. Plain turbo is about 1 point worse (interval −0.4 to +2.3).
  **Small is clearly worse, by 2.3 points (interval +0.7 to +3.9)**, winning on only 3 of 20
  speakers.
- The vocabulary prompt did **not** hurt on unrelated speech (radio talk). It helped turbo
  and was neutral for small. So it is safe to leave on.
- **"More accurate than Google" is not demonstrated.** The likely win is local vocabulary
  (*Oxxo, colectivo, predial, tinaco, cajero*) and the glossary layer. This test set has none of
  that, so the claim needs Paul's recordings (§5).

## 3. Translation — where the real gap is (measured on the phrasebook)

200 random `say`/`hear` phrases from `phrases.js`, translated with opus-mt (the offline
candidate, 78 MB int8 per direction, about 45 ms per sentence on CPU). chrF against the
curated text: **es→en 58.8, en→es 59.6.** It gets **exactly the local words** wrong:

| Spanish | opus-mt says | Should be |
|---|---|---|
| Tengo un **piquete** que se ve infectado | I have a **picket** | a **bite** |
| ¿Puedo pagar … en la **bomba**? | at the **bomb** | at the **pump** |
| ¿**Pica**? / Que no **pique** | Pica? / **Don't bite** | Is it spicy? / Not spicy |
| ¿Hay un **cajero** por aquí? | a **cashier** | an **ATM** |
| Ya se acabó el **cloro** | the **chlorine**'s over | the **bleach** is gone |
| **Cada tercer día** | every third day | every other day |

English→Spanish comes out **Spain Spanish and tú**: *lejía* (Mex. *cloro*), *sirope* (*jarabe*),
*olla* for flowerpot (*maceta*), *¿Puedes…?* where Mexican service Spanish uses *¿Puede…?*.

**Conclusion:** for this app the accuracy lever is **translation plus the glossary**, more than
speech-to-text. The curated `phrases.js` pairs (not yet reviewed by a native speaker) are what
fix it, in both v1 and v2.

**Google Translate was not scored on 09-28** (its free endpoint returned HTTP 429). It was on
09-29; see §3a.

## 3a. Step 0 — Google vs the v1 candidate, English→Spanish (measured 2026-09-29)

The same 200 phrases (seed 7), English→Spanish, with parentheticals like "(lit. give me)"
stripped so both systems got identical input.
- **Google** is the consumer Translate model (`en_es_2023q1`), reached through the free gtx
  endpoint. It answered all 200 at one request every 2 s, with no 429.
- **v1 candidate** is `@cf/openai/gpt-oss-120b` on Workers AI (reasoning effort low). It was told
  "Spanish as spoken in Mexico, usted unless clearly casual, never vosotros", with the 182
  `kind: "word"` entries of `phrases.js` as the word list. The test sentences are not in that
  list, so the model could not copy the answer.

Counts are per phrase, out of 200, against the curated text. Automatic count
(`tools/voice-eval/score_mexican.py`), then corrected by reading every line. Row-by-row lists:
`tools/voice-eval/step0/HAND-AUDIT.md`.

| | **tú where usted belongs** | **Spain / other-region word** | **Meaning error or broken** |
|---|---|---|---|
| **Google Translate** | **61** (of ~64 phrases that address the listener) | **8** | 10 |
| **gpt-oss-120b + "Mexican, usted" + word list** | **1** | **2** | 6 (3 of them are prompt framing, below) |
| Llama 3.3 70B, same prompt | 0 | 1 | many: 58 `?`→`!`, commentary, answers — **rejected** |
| Mistral Small 3.1, same prompt | 1 | 2 | moves usted onto the wrong person ≥9× (*Usted es diabético*) — **rejected** |

**What this says, plainly:**
- **The problem is real, and it is mostly register.** Google speaks tú to the clerk, the
  mechanic and the doctor: *¿Puedes darme un descuento?*, *¿Qué te debo?*, *Necesitas una
  radiografía*, *Quítate la camisa*. It did this in 61 of the roughly 64 phrases that speak to the
  listener. The Spain words are fewer but they are the telling ones: *lejía*, *nevera*,
  *fontanero*, *surtidor*, *almíbar* for cough syrup, and the Argentine *día por medio*.
- **The instruction fixes register almost completely.** The v1 candidate made 1 tú slip and
  2 Spain words (*hacer la colada*, *coche de alquiler*).
- **But the candidate is not finished.** Three of its six failures *answered* the
  sentence instead of translating it: "That's all, thanks" → *De nada, estoy a sus órdenes*. That is
  a prompt-framing defect. `mt_workers_llm_v2.py` fences the input and says "never answer it,
  keep the same speaker", but **it did not get to run** (next bullet). Its other misses:
  *¿Se llama Akumal?* for "Do you go by Akumal?", and a question about the plant turned onto the person.
- **Workers AI free tier ran out mid-test.** `POST /ai/run/@cf/openai/gpt-oss-120b` returned `4006 "you have used up
  your daily free allocation of 10,000 neurons, please upgrade to Cloudflare's Workers Paid
  plan"` after about 600 translations with the word list in each prompt. **The account is on
  Workers Free, and v1 cannot serve real use without Workers Paid** ($5/month minimum). That is Paul's
  call. The allowance resets at 00:00 UTC.
- **None of the models knows the insect *piquete*.** All three LLMs said *mordida* for "a bite that
  looks infected" (Google said *picadura*). In Mexico *mordida* is also slang for a bribe. This is the
  case for the glossary layer in §1: a curated phrase match should win before any model runs.
- **The judge is not a native speaker, and neither is the reference.** The counts are
  Claude's reading against unreviewed `phrases.js`, which itself says *coche rentado* in one
  row and *auto rentado* in another. The *tú* count is the robust one: it is grammar, not taste.
  The word counts need the native review before anyone quotes them.

## 3b. Which service is best for Mexican Spanish (measured 2026-09-29, same 200 phrases)

The prompt is the fixed one from `mt_workers_llm_v2.py`: the input is fenced, with "translate,
never answer, keep the same speaker", plus the same word list. It was sent through
`tools/voice-eval/mt_chat_api.py` to the two other LLM vendors whose keys are in the portfolio
(`triumvirate/.env`). There is no DeepL or Microsoft Translator key anywhere, so those are
unmeasured. The latency figure is the median of 10 sequential calls from oracle-vm.

| | **tú slips** | **Spain / other-region** | **Meaning errors** | **Answered instead of translating** | **Latency** |
|---|---|---|---|---|---|
| Google Translate (§3a) | 61 | 8 | 10 | 0 | fast |
| gpt-oss-120b, Workers AI (§3a, old prompt) | 1 | 2 | 3 | 3 | — |
| **OpenAI gpt-5, reasoning low** | **1** (#133) | **0** | **0** | **0** | 2.4 s |
| **OpenAI gpt-5, reasoning minimal** | 1 (#92) | 2 (#77, #193 *coche*) | 0 | 0 | **0.9 s** |
| OpenAI gpt-5-mini, reasoning low | 0 | 1 (*día por medio*) + soft *de alquiler*, *resfriado*, *pequeño* | 2 (#78 *¿Se hace llamar Akumal?*, #177 *agua quieta*) | 0 | 1.9 s (0.7 s minimal) |
| xAI grok-4.3 | 1 (#92) | soft only (*resfriado*, *camión de agua*) | 1 (#165 *empastes*, dental fillings, for taco fillings) | 0 | 5.0 s |
| **Claude Opus 5.5** (`claude -p`, Max plan) | **0** | **0** (soft: *resfriado*) | **0** | **0** | 4.8 s* |
| **Claude Opus 5.5, effort low** (`claude -p --effort low`, Max plan) | **0** | **0** | **0** | **0** | 3.7 s* |
| Claude Sonnet 5.5 (`claude -p`, Max plan) | 0 | 1 (#193 *coche*) + soft *resfriado*, *camión de agua* | 3 (#44 *curso* for a course of antibiotics, **plus a stray "Correction: …" note left in the output**; #73 *darme pasa corriente*; #177 *agua quieta*) | 0 | 4.5 s* |

\* Measured through the `claude` CLI, which adds its own start-up time to every call, so this is not
the model's API latency. The API is unmeasured: the paid Anthropic API is banned in this portfolio.

**Best quality: Claude Opus 5.5.** It is the only system with zero on every column, and it is the
closest to the reference's own Mexican idiom: *¿Pica?*, *pipa de agua*, *lave los trastes*, *¿A cómo
está el dólar?*, *¿Cómo le vamos a hacer con esto?*, *media sombra*, *carro rentado*.
**But it cannot serve this app as the rules stand.** The app is meant to be public, for
non-technical users (Paul, 2026-09-29), so there is no Tailscale on the phone. A Max subscription is
for one person, so it cannot back a public service; that would need the paid Anthropic API, which is
banned. Using Opus here is Paul's call to reopen.

**DECISION (Paul, 2026-09-29): Cloudflare + Claude Opus 5.5 at effort low.** Runs on the Max plan
through `claude -p` while the app is a prototype; **switch to the Anthropic API when it becomes a
production app** (Paul: "it's nowhere near that yet"). The standing no-API rule is untouched until then.
- **Opus low vs default, same 200 phrases:** both are 0 / 0 / 0 / 0. 39 rows differ; none is a
  meaning error. Low is often *more* Mexican: *Cada tercer día*, *Me da…*, *¿Gusta un café…?*,
  *Ya se acabó el cloro*, *licencia de construcción*, all matching the reference. It loses a little
  elsewhere: *¿Cómo vamos a manejar esto?* (a calque, where default had *¿Cómo le vamos a hacer?*),
  *Sombra parcial* for *media sombra*, and *refrigerador* for *refri*. Median 3.7 s against 4.8 s,
  both including CLI start-up. Output: `step0/opuslow_out.json`.
- **Shape:** phone → a public Cloudflare Worker (no Tailscale on the phone) → an origin running
  `claude -p --model opus --effort low` with `ANTHROPIC_*` stripped. The Worker holds a shared secret
  for the origin and applies a per-user rate limit. The origin is the always-on oracle VM, where the
  CLI is logged in; the Worker reaches it over HTTPS or a Cloudflare Tunnel. Speech-to-text stays on
  Workers AI Whisper (§1).
- **Limit to remember:** a Max plan is for one person, so this cannot carry public traffic. That is
  the trigger for the API switch.

**Best that the rules allow today: OpenAI gpt-5 with the Mexican instruction and the phrasebook word list.**
It has zero meaning errors and zero Spain words, and it often lands on the Mexican phrasing
the reference uses: *¿Me puede pasar corriente?*, *Este contacto no sirve*, *¿Tiene algo para la
gripa?*, *carro de renta*, *Quiero contratar la luz*. At reasoning `minimal` it drops to 0.9 s and
loses a little: *coche* twice and one *te*. For a voice app, `minimal` plus the curated glossary
layer is the practical setting. The fixed prompt stopped every model answering the sentence,
where gpt-oss had done it 3 times under the old prompt.
- **Every model still says *mordedura/mordida*** for the insect bite except grok, which says
  *picadura*. Only the glossary layer gets *piquete*.
- **Grok** adds a stilted *Yo…* / *usted* to about 20 rows (*Yo quiero abrir una cuenta*). That is
  not wrong, but it is unnatural. It is also the slowest, and **the primary `XAI_API_KEY` is out of credits**
  (`permission-denied: … used all available credits or reached its monthly spending limit`).
  These runs used the fallback key.
- **Cost:** 200 phrases used 311k input and 3–22k output tokens per run, mostly the 1.5k-token word
  list repeated. That is about a fifth of a cent per phrase on gpt-5 at list prices (quoted from memory,
  not checked), and less with prompt caching. The whole comparison cost roughly $2.
- **Architecture consequence.** The phone calls our Worker, and the Worker calls OpenAI with the key as
  a Worker secret. **This uses no Workers AI neurons, so it does not need Workers Paid.** Worker
  requests are a separate allowance: 100k/day free, and the account used 4,276 on 2026-09-29.
  **v1 speech-to-text is still planned on Workers AI Whisper, which does spend neurons.** That
  choice is open again: either take Workers Paid for Whisper, or use OpenAI's transcription for
  STT as well. The latter is unmeasured against §2.

## 4. Download size and speed on an iPhone

| Offline v2 bundle | Size |
|---|---|
| Whisper small (ggml q5_1 **190 MB**, or ONNX int8 249 MB) | 190–249 MB |
| Bergamot es→en + en→es | tens of MB each (check the exact files in the HF mirror) |
| `phrases.js` glossary | already in the app |
| **Total** | **about 250–320 MB, inside the 500 MB budget** |

Whisper turbo in the browser is **563 MB (q4f16) to 759 MB (q4)**. That is over budget and
near iOS Safari's per-tab memory ceiling, so turbo stays server-side.

**Speed on a phone: NOT measured. There is no iPhone on this machine.** What is known:
- iPhone browsers have **no Neural Engine access**. WebGPU arrived in iOS 26 Safari, but a
  2026-09-18 report shows Whisper failing to load on iPhone WebKit through onnxruntime-web's
  WebGPU backend even though the adapter is present. Plan on **WASM, CPU only**.
- On this 4-vCPU box, native int8 small runs at 0.65× real time. Browser WASM is typically
  2–3× slower than native, and an A-series core is roughly comparable to one of these.
  **Rough expectation: a 5-second utterance takes about 5–10 s to text on an iPhone with small.**
  Too slow to feel like Google, but usable for "what did she just say". **This is the first
  thing to measure** (§5).
- **If WASM small is too slow**, the offline fallback is a thin **native iOS shell** (Capacitor
  around the same web app). It would use Apple's on-device `SpeechAnalyzer` (iOS 26; confirm
  es-MX is in `supportedLocales`) or whisper.cpp with CoreML/Neural Engine, plus Apple's
  offline Translation framework. That needs an Apple developer account and TestFlight. It is a
  real fork in the road, so it is **Paul's call, later**.

## 5. v1 / v2 split, and what is still open

| | **v1 — online** | **v2 — offline** |
|---|---|---|
| Speech-to-text | Whisper turbo + prompt on Workers AI (≈ Google, measured) | Whisper small WASM, 190 MB (−2.3 pts vs Google, measured) |
| Translation | glossary layer + glossary-aware MT (online) | glossary layer + Bergamot |
| Backend | one Cloudflare Worker, pennies a month | none; service worker caches the models |
| Two-way | both mic buttons; Whisper handles English well | same |
| Unknown | Mexican-situation accuracy; translation choice | iPhone WASM latency |

**The hardest piece is offline English→Mexican Spanish.** Bergamot and opus-mt are trained
largely on European data, and §3 shows opus-mt producing *lejía* and *tú*. The glossary layer
fixes words but not register. Options for v2 are: accept this for free-form sentences and
prefer curated phrases whenever the English matches one; a small on-device LLM (likely too big
next to Whisper within 500 MB, unmeasured); or Apple's Translation framework through the native
shell in §4 (its Spanish variant is unchecked).

**Open, before anything final:**
0. ✅ **Measured 2026-09-29, §3a.** Google puts tú on the listener in 61 of about 64 phrases.
   The v1 candidate (gpt-oss-120b + instruction + word list) does it once. **§3b then measured
   OpenAI and xAI with the fixed prompt: gpt-5 is the best service** (0 Spain words, 0 meaning
   errors, 0.9 s at minimal reasoning). (a) ✅ **Decided 2026-09-29: Cloudflare Worker + Opus 5.5 at effort low on the Max plan,
   the Anthropic API at production (§3b).** Still open: (b) a native speaker
   re-checks `step0/HAND-AUDIT.md` and `phrases.js`.
1. **Paul's recordings.** 30–50 short clips in the app's situations (taxi, pharmacy, mechanic,
   bank), recorded with permission, each with a note of what was actually said.
   `tools/voice-eval/` scores them unchanged. This is the only test of "better than Google
   *here*".
2. **A 10-minute iPhone speed test.** A throwaway page that loads Whisper small (WASM) and
   times five utterances on Paul's phone. It decides whether v2 can stay a PWA.
3. **Translation engine for v1.** Compare Google Cloud Translation with a Workers AI LLM plus
   glossary, on the 200-phrase set and Paul's clips. The consumer Google model was compared in
   §3a instead. **No portfolio key can call Cloud Translation** (live-checked 2026-09-29 on the
   oracle VM, where the portfolio `.env` files are present):
   - `POST translation.googleapis.com/language/translate/v2` returns `403 SERVICE_DISABLED`
     ("Cloud Translation API has not been used in project … or it is disabled") for the Places
     keys of happy-hour-finder / hhf-menus30 / riviera-maya-eats (project 987413506322) and for
     emunexus' YouTube key (716109928961).
   - cenote-map's key returns `403 API_KEY_SERVICE_BLOCKED` (the key is restricted to other APIs).
   - The Google OAuth refresh tokens carry no `cloud-translation` or `cloud-platform` scope, and
     `GOOGLE_CLOUD_CREDENTIALS` points to a Windows path that is not on the VM.
   The one-click fix, if Cloud Translation is ever wanted: enable "Cloud Translation API" in one
   GCP project and use that project's key. This is not needed for v1 on current evidence.
4. **Also worth testing as an online STT:** OpenAI `gpt-4o-transcribe`. It takes a prompt and
   costs about $0.006/min; its key is in `triumvirate/.env`. The key is present on the oracle VM
   (`~/repos/triumvirate/.env`); not run yet. Anthropic's API is excluded under the standing rule.
5. **Vosk** is small and streams (39 MB, 0.14× real time) but is 5.8 points behind Google on
   free speech. Its restricted-grammar mode could be very accurate for recognising the 153
   `hear` phrases. That makes it a possible v2 "phrasebook mode", not the main engine.

Sources: [Workers AI whisper-large-v3-turbo](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/),
[iOS 26 WebGPU](https://appdevelopermagazine.com/webgpu-in-ios-26/),
[Whisper-on-WebGPU iPhone failure](https://github.com/rubasace/sidevoice/issues/31),
[Mozilla translations / model mirror](https://github.com/mozilla/translations),
[SpeechAnalyzer locales](https://www.callstack.com/blog/on-device-speech-transcription-with-apple-speechanalyzer),
[CIEMPIESS test](https://huggingface.co/datasets/ciempiess/ciempiess_test).
