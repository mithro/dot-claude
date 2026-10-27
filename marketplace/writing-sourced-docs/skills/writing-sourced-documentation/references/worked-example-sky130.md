# Worked example: the SKY130 process-technology reference

This file is **specific to one repository** (`sky130-process-tech`, the public step-by-step
reference on how the SKY130 130 nm CMOS process is manufactured). It shows how that project
instantiates the generic rules in `SKILL.md` and the other reference files: its page kinds,
exact headings, checkers, policies and numbers. Use it as a model of *how concrete* the
instantiation should be. Do not copy its subject-specific terms (SkyWater, masks, MPW runs,
Cypress, patents in force) into a site about something else.

## The site

* 171 step pages (`docs/steps/NNN-code.md`), 10 category pages, 30 machine-class pages, 12
  material-class pages, 36 mask pages, an overview, a glossary of ~220 terms, a source
  inventory of ~1,700 keyed entries, generated paper / patent / filing indexes, and a
  separate history section on the predecessor company's processes.
* Sphinx + MyST, furo theme, Read the Docs; `sphinx-build -W` with `nitpicky = True`.
* Every page cites only publicly obtainable sources; the step list itself is a public sheet
  cited as `[^steps-sheet]`, and a step's *name* in that sheet is never evidence of films,
  chemistries, tools or doses.
* The subject organisation is SkyWater; its public capability list (`[^skw-01]`) is quoted
  verbatim and graded **strong** for a tool's existence, with the assignment to a step always
  an **inference**, because the list never names a step.

## Exact mandatory headings (what the checkers test)

* **Step page** (`tools/check_steps.py`, all 13, each alone on its line): `## What this step
  is`, `## Step category`, `## Why this step exists`, `## How it is typically performed`,
  `## Machines typically used`, `## Machines likely used at SkyWater`, `## Resources
  required`, `## Related steps and cross-references`, `## References`, `### Cross-check`,
  `### High-level understanding`, `### Deep dive`, `## Open questions`.
* **Machine page** (`check_machines.py`, H2s in order): `What the machine class is and how it
  works`, `Representative 200 mm-era models`, `At SkyWater`, `Consumables and facilities`,
  `Process-integration notes for SKY130`, `Related pages`, `References`, `Open questions`;
  H3s under `At SkyWater` exactly `What SkyWater lists`, `Strength of the evidence`, `SKY130
  steps assigned to this class`.
* **Material page** (`check_materials.py`): `What the class is and what it does`,
  `Representative materials and grades`, `At SkyWater` (`What SkyWater's filings and pages
  list`, `Strength of the evidence`, `SKY130 steps that use this class`), `Supply, handling,
  safety and facilities`, `Process-integration notes for SKY130`, `Related pages`,
  `References`, `Open questions`. The summary table starts `What they do` and ends `SkyWater
  evidence`, `SKY130 steps | N steps; see …`.
* **Mask page** (`check_masks.py`): `What the mask defines`, `Drawn layers and derivation`
  (`In the PDK`, `In the public renders`), `Plates and reticle sets` (optional H3 `The
  mask-type record`), `Lithography and pattern transfer`, `Steps that use this mask`, `Design
  rules and critical dimensions`, `Related pages`, `References`, `Open questions`. The quick
  facts rows are compared cell by cell with the masks index; `In the public renders` must keep
  "renders of *drawn* data" and "not SkyWater's"; the words `custody`, `shipment`, `exp_ship`
  are forbidden on any mask page.
* Deep dive minimums: 8 on a step or per-mask page; 12 on a category, machine, material or
  overview page and the masks index.

## House values

* The generic-practice scope line on every step page: *An industry-generic recipe for a
  200 mm, 130 nm-era fab:* (166 of 171 pages carry it), rendered as an italic lead-in, never
  an admonition.
* Hedge vocabulary: "SkyWater has publicly stated …", "the PDK documentation shows …", "a
  200 mm fab of this vintage would typically use …", "we infer … because …", "our reading",
  "our arithmetic", "our extraction", "not public".
* Evidence scale for tools at SkyWater: strong = SkyWater or tool-vendor statement; medium
  = SkyWater job posting or interview with a named employee; weak = indirect.
* Related-steps labels on a step page: Previous · Next · Same module · Depends on · Feeds ·
  Same category · Mask · Evidence · Category page.
* Step-link runs on machine and material pages: ≤ 25 links stay in the open and get a
  generated `Step | Code | Name` table; > 25 are wrapped by the generator in a collapsed "All
  N steps as one line of links" block (`tools/gen_step_tables.py`).
* Glossary first-use links: `tools/link_terms.py`, at most 3 new links per paragraph, skip
  list for ambiguous terms (`via`, `liner`, `TED`, `spacer`, …), opt-out comment
  `<!-- link_terms: skip <term> -->`, idempotent.
* British spelling, ISO dates, SI units with a space, fetch user agent
  `sky130-process-tech docs checker`.

## Policies particular to this project

* **Patents shown as in force.** A patent family in `data/patents.yaml` whose `expired` is not
  `true` is restricted: its publication numbers in any spelling, its titles of five words or
  more, and listed distinctive phrases may appear only inside a `{dropdown}` titled `From a
  patent shown as in force (US N; estimated expiry YYYY-MM-DD) — open to read`, with the
  footnote definition and inventory entry carrying "Shown as in force; estimated expiry
  YYYY-MM-DD (estimate from public records, not legal advice)." Nothing from such a note may
  appear in a glance box, table, caption or figure. `tools/check_inforce.py` enforces it.
* **The mask renders site** may be cited for plate IDs, reticle-set IDs, lot IDs, mask-type
  codes and per-die shape counts; never for project, customer or recipient names, lot status,
  custody or shipping, and never naming the software that produced the renders.
* **Cypress qualification reports** hosted publicly by the successor company are citable
  despite "confidential" markings; staff names printed on them are never copied.
* **The history section** (`docs/history/`) needs two independent sources per claim, keeps
  evidence as YAML with verbatim quotes checked against a local fetch cache
  (`tools/check_history.py`, `tools/check_history_quotes.py`, `tools/history_cache.py`), and
  is linked from the landing page only.

## Checker catalogue

| Checker | Holds |
|---|---|
| `check_steps.py`, `check_machines.py`, `check_materials.py`, `check_masks.py` | mandatory headings; quick-facts rows; page ↔ index cross-reference; forbidden words; stale generated blocks |
| `check_refs.py` | markers ↔ definitions; labels in `docs/references/public-sources.md`; no reference-style links; Deep dive minimums; inline URL ⊂ the page's own footnote URLs; `[text](<URL>)` form |
| `check_inforce.py` | in-force patent content only inside collapsed blocks; flag sentence matches the dataset character for character |
| `check_links.py` | every URL/DOI in definitions and inventory resolves; dead → Wayback suggestion; polite, resumable, chunkable |
| `check_preserved.py` | before/after multisets (markers, definitions, numbers, ordered number tuples, quotes, roles, URLs, hedges, identifiers, dropdown bodies, words) for presentation passes; `--allow-regrouped`, `--allow-deduplicated`, `--strict-words` |
| `gen_index_links.py`, `gen_step_tables.py`, `gen_steps.py`, `gen_papers.py`, `gen_patents.py`, `gen_filings.py`, `gen_figures.py` (each with `--check`) | generated blocks and pages are current; figure lint |
| `shoot.py` | tiled headless-Chrome screenshots at 1280 px and `--width 400` |
| `measure*.py` (in `docs/plans/readability/prototypes/measure/`) | caps worklists per page kind |

All checkers are positional text parsers: they split on headings, blank lines and `| ` at
the start of a line; `docs/plans/readability-guide.md` §5 documents, per checker, exactly
which structure it depends on and the verified failure modes.

## Where the rules live in that repository

* `docs/plans/agent-briefs.md` — the standing briefs given verbatim to every writer, reviewer
  and provenance auditor (the common rules, the per-page-kind writer briefs, the reviewer
  brief).
* `docs/plans/citation-style.md` — the footnote style and the reading tiers.
* `docs/plans/readability-guide.md` — the 31 `R-…` rules with triggers, steps, real
  before/after examples with `file:line`, do-not-touch lists, greps and the per-page
  procedure; §2 the Never list; §8 the reviewer checklist.
* `docs/plans/figure-authoring.md` and `docs/figure-conventions.md` (generated) — figures.
* `docs/plans/readability/report-{A,B,C,D}.md` — the four reviewer reports the guide was
  consolidated from; `docs/plans/progress-rd-*.md` — per-batch progress files, each ending
  with "guide problems" and "content problems for the owner".
* `docs/plans/model-comparison.md` — the Sonnet-vs-Opus writer and reviewer comparison that
  set the model policy.

## Numbers that calibrated the caps

From report A on the 171 step pages before the readability phase: paragraphs median 53
words, p90 158, max 438; 25 % of paragraphs ≥ 120 words; sentences median 22, p90 51, max
173; 759 sentences with two or more em-dashes; zero tables beyond quick facts, zero figures,
zero headings below H2 outside References; up to 15 footnote markers in one paragraph. The
caps in `SKILL.md` were set so that a cheaper model could apply them mechanically, with the
three reports' differing numbers resolved to one value and the resolution recorded.
