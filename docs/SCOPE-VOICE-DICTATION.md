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

## 1. Recommended setup

**v1 (online):** a mic button for each speaker (🇲🇽 / 🇺🇸), like Google's manual conversation
mode. Automatic language detection on short utterances is the usual failure, so we skip it.
1. **Speech-to-text:** Whisper **large-v3-turbo** on **Cloudflare Workers AI**, reached through one
   small Worker. Its `initial_prompt` is built from the `phrases.js` vocabulary. Cost: $0.0005 per
   audio minute, and 10k free neurons a day covers about 200 audio minutes a day.
2. **Glossary layer (in the app, plain JS):** if the transcript matches a curated phrase
   (normalised, fuzzy), show the curated English. Otherwise run MT, with `phrases.js` words
   pinned as a glossary. §3 shows why this layer is the real accuracy win.
3. **Translation:** a model that takes a glossary and a register instruction. Candidates:
   an instruction LLM on Workers AI, or Google Cloud Translation. **Not yet measured — see §5.**
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

**Google Translate was not scored.** Bulk queries to its free endpoint were rate-limited
(HTTP 429), and I did not work around that. See §5.

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

**Open, before anything final:**
1. **Paul's recordings.** 30–50 short clips in the app's situations (taxi, pharmacy, mechanic,
   bank), recorded with permission, each with a note of what was actually said.
   `tools/voice-eval/` scores them unchanged. This is the only test of "better than Google
   *here*".
2. **A 10-minute iPhone speed test.** A throwaway page that loads Whisper small (WASM) and
   times five utterances on Paul's phone. It decides whether v2 can stay a PWA.
3. **Translation engine for v1.** Compare Google Cloud Translation with a Workers AI LLM plus
   glossary, on the 200-phrase set and Paul's clips. Both need a server key. That key lives on
   Paul's PC and was not copied to this session.
4. **Also worth testing as an online STT:** OpenAI `gpt-4o-transcribe`. It takes a prompt and
   costs about $0.006/min; its key is in `triumvirate/.env`. It was not run this session (same
   key-copy restriction). Anthropic's API is excluded under the standing rule.
5. **Vosk** is small and streams (39 MB, 0.14× real time) but is 5.8 points behind Google on
   free speech. Its restricted-grammar mode could be very accurate for recognising the 153
   `hear` phrases. That makes it a possible v2 "phrasebook mode", not the main engine.

Sources: [Workers AI whisper-large-v3-turbo](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/),
[iOS 26 WebGPU](https://appdevelopermagazine.com/webgpu-in-ios-26/),
[Whisper-on-WebGPU iPhone failure](https://github.com/rubasace/sidevoice/issues/31),
[Mozilla translations / model mirror](https://github.com/mozilla/translations),
[SpeechAnalyzer locales](https://www.callstack.com/blog/on-device-speech-transcription-with-apple-speechanalyzer),
[CIEMPIESS test](https://huggingface.co/datasets/ciempiess/ciempiess_test).
