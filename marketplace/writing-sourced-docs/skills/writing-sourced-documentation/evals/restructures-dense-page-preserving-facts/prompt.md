---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

`018-nwi.md` is one of our process-step pages (Sphinx + MyST, furo, Read the Docs). On a phone it's a wall of text: 150-word paragraphs, half a dozen implant recipes with energies and doses buried in one bullet, the SkyWater tool evidence run together in sentences, open questions with no labels. The content itself has already been fact-checked and reviewed, so this is purely about making it readable and skimmable — it must not change anything the page claims.

Restructure it for readability. Keep all the existing `##` headings (a checker depends on them) and keep the generated index-links block exactly as it is. Save the result as `018-nwi.md`, overwriting the input.

Input files: 018-nwi.md
