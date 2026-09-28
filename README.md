# ¡Órale! Mexican Spanish Phrasebook

A mobile phrasebook for the Mexican Spanish you actually use: everyday phrases, ordering at restaurants, and shopping.

**Live:** https://paulrenzi.github.io/mexican-spanish-flashcards/

- **Phrases** (the default) is organized by situation: Everyday, Restaurant, Store, Garden (vivero). Each situation is a list of topic keywords (e.g. *Water requirements*, *Light requirements*) that expand into what you ask, what you'll hear back, and single words.
- 🔊 reads the phrase aloud with a Mexican Spanish voice when your phone has one. ⤢ shows it full-screen to hand to the staff.
- Search covers every situation at once.
- **Practice** is the old flashcard mode for the current situation: tap to flip, swipe right if you know it.
- Progress and open topics are saved on your device. Works offline after the first visit.

Plain HTML/CSS/JS, no build step. Phrases live in `phrases.js`.

Test: `python tests/render_check.py` (Playwright, iPhone and 360px viewports).
