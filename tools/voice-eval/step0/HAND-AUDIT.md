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
