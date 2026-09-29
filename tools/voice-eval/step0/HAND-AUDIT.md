# Step 0 hand audit (2026-09-29)

Row numbers index `sample200.json` and every `*_out.json` in this folder (0-based).
Judged by Claude against the curated `phrases.js` text. **Not a native speaker, and neither is
the reference** (`phrases.js` is unreviewed). A native speaker should re-check these lists
before any number here is quoted outside the project.

`score_mexican.py` gives the automatic count. The lists below are that count corrected by reading all 200 lines.

## Google Translate (consumer model `en_es_2023q1`, free gtx endpoint)

- **tú where usted belongs: 61** — 2 3 7 8 21 30 34 38 39 41 44 52 53 64 69 73 75 78 79 80 81 84 88
  92 95 97 100 102 106 110 112 113 114 117 121 123 128 133 141 143 144 145 148 149 152 154 157
  159 161 164 165 168 171 172 174 175 176 181 189 190 194 195 197.
  The automatic count was 48; reading added the imperatives it cannot see (*Termina, Entra, saca, lava,
  Quítate, Mézclalo…*). Excluded: 156 (*¿Cómo estás?* for "How's it going?", a casual greeting).
  Google used usted in only about 3 phrases that address the listener (33, 67, 68).
- **Spain / other-region words: 8 phrases** — 12 *surtidor* (bomba), 24 *día por medio*
  (cada tercer día), 32 + 113 *lejía* (cloro), 38 *almíbar* for cough syrup (jarabe),
  69 + 133 *nevera* (refri), 91 *fontanero* (plomero).
  Softer, not counted: 77/193 *de alquiler* (rentado), 51 *pago inicial* (enganche),
  111 *camión cisterna* (pipa), 112 *resfriado* (gripa), 19/75/176 *pequeño* (chico).
- **Meaning errors: 10** — 4 *tendré…* ("I'll have"), 73 *empujón* (jump start), 95 *romper este
  billete*, 126 *¿Cuanto arreglarlo?*, 131 *¿Puede tomar viento?*, 140 *salida* (outlet),
  159 *Voy a tener tu licencia*, 177 *agua tranquila*, 183 *por aquí* ("for here"),
  189 *¿Puedes llamarme?* ("ring me up").

## Workers AI `@cf/openai/gpt-oss-120b`, "Mexican Spanish, usted" + `glossary.txt`

- **tú where usted belongs: 1** — 92 *¡Que te vaya bien!*
- **Spain words: 2** — 8 *hacer la colada*, 77 *coche de alquiler*. Softer: 112 *resfriado*, 193 *de alquiler*.
- **Meaning errors / broken: 6** — 2, 48 and 64 *answered* the sentence instead of translating it
  (a prompt-framing defect; `mt_workers_llm_v2.py` is the fix, not yet run), 73 *arranque*,
  78 *¿Se llama Akumal?*, 120 *¿Necesita usted mucha agua?* (asks the person, not the plant).

## Workers AI Llama 3.3 70B and Mistral Small 3.1 — rejected

- **Llama:** tú 0. But 58 questions came back ending in `!` instead of `?`, 4 carry "should be…"
  commentary (11 76 79 147), and several are answers or meaning errors (4 6 48 52 73).
- **Mistral:** tú 1. But it moves usted onto the wrong person at least 9 times, e.g.
  96 *Usted es diabético*, 135 *Usted se torció el tobillo*, 46 *Le duele aquí*,
  134 *Su teléfono fue robado*. It also answers instead of translating (2 6).

## All three models say *mordida* for row 0

The phrase is an insect bite; Mexico says *piquete*, Google said *picadura*. *Mordida* is an
animal bite, and in Mexico it is also slang for a bribe.

## `phrases.js` itself

Row 193's reference is *Es un coche rentado* (*coche* is the Spain word), and row 77 says
*auto rentado* for the same English. More evidence the phrasebook needs its native review.

## Second round (same day): fixed prompt (`mt_workers_llm_v2.py` SYS) via `mt_chat_api.py`

- **gpt-5, reasoning low** (`gpt5_out.json`): tú 1 (133 *Si tienes hambre, sírvete*). Spain 0.
  Meaning errors 0. Soft: 19 *pequeño*. Mexican wins: 73 *pasar corriente*, 140 *contacto*,
  112 *gripa*, 182 *contratar la luz*, 77/193 *carro de renta*.
- **gpt-5, reasoning minimal** (`gpt5min_out.json`): tú 1 (92 *¡Que te vaya bien!*). Spain 2
  (77 *coche de renta*, 193 *coche de alquiler*). Meaning errors 0. Soft: 112 *resfriado*.
- **gpt-5-mini, reasoning low** (`gpt5mini_out.json`): tú 0. Spain 1 (24 *día por medio*). Soft:
  77/193 *de alquiler/de renta*, 112 *resfriado*, 19/75/176 *pequeño*. Meaning errors 2:
  78 *¿Se hace llamar Akumal?*, 177 *un agua quieta*.
- **grok-4.3** (`grok_out.json`, fallback key): tú 1 (92). Spain 0. Soft: 112 *resfriado*,
  111 *camión de agua*. Meaning error 1: 165 *empastes* (dental fillings). About 20 rows carry a
  redundant *Yo* / *usted* (23 55 63 65 91 99 105 108 111 123 138 159 169 170 182…).
- Excluded again: 156 *¿Cómo te va?* (casual greeting). Scorer false positive: 33 *¿Me trae…?* is usted.
- Row 0: gpt-5 and gpt-5-mini say *mordedura*/*mordida*; grok says *picadura*. None says *piquete*.
- Row 175: the reference *puntadas* is itself doubtful; *puntos* (gpt-5) is the medical word.

## Third round: Claude Sonnet 5.5 and Opus 5.5 via `claude -p` on the Max plan (2026-09-29)

Same prompt and the same 200 phrases, run through `tools/voice-eval/mt_claude_cli.py`. ANTHROPIC_* was stripped from the environment, so no paid API was used. The automatic scorer found 0 Spain words and 0 tú slips for both.

- **Opus 5.5: nothing to flag.** Soft: 112 *resfriado*. It is the closest of any system to the reference idiom: 10 *¿Pica?*, 111 *pipa de agua*, 194 *trastes*, 198 *¿A cómo está el dólar?*, 188 *¿Cómo le vamos a hacer con esto?*, 136 *media sombra*.
- **Sonnet 5.5: 3 meaning errors.**
  - 44 *Termine todo el curso*: the English means a course of treatment. The output also contains a stray note, "Correction: with proper accents…", so the output itself is unusable.
  - 73 *¿Puede darme pasa corriente?* is ungrammatical.
  - 177 *Agua quieta* (the same error gpt-5-mini made).
- **Sonnet 5.5, Spain word:** 193 *coche*, counted the same way as it was for gpt-5 minimal.
- **Sonnet 5.5, soft:** 111 *camión de agua*, 112 *resfriado*.
- **Sonnet 5.5, style:** a redundant *usted* in about 8 rows (8 68 78 84 88 97 121 171).
- Row 0 is unchanged: both say *picadura*, and neither says *piquete*.
- Latency: 4.5 s (Sonnet) and 4.8 s (Opus) median. This includes CLI start-up, so it is not the API latency.
