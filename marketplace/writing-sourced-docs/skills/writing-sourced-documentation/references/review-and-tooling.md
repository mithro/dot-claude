# Review, tooling and process

## Why machine checks

Every page kind has a checker that tests the template (mandatory headings as exact strings,
quick-facts rows, index cross-references), one checker tests citations (every marker defined
and used, every label in the inventory, Deep dive minimums, inline URLs equal a footnote URL),
one tests that restricted content stays collapsed, one re-fetches every URL and DOI, and every
generator has a `--check` mode that fails if its output on disk differs by one character from
what it would write. The build runs with warnings as errors and nitpicky cross-references. A
hosted build runs all offline checkers first. A reviewer cannot re-check 300 pages by hand;
the checkers hold the floor so review effort goes to what only reading can catch.

Design the checkers as **positional text parsers** and say so: they split on headings, blank
lines and `| ` at the start of a line. Document, per checker, exactly what structure it depends
on and the verified failure modes ("a four-column table with a machine link in its first cell
placed after the main table silently replaces the checked row"), because layout changes break
checks that seem unrelated to the text edited. Every checker has a `--selftest` that touches no
files.

Generated content is fenced with begin/end comments naming the generator, is never
hand-edited, and is regenerated in its own commit after a generator change.

## The preservation check

A presentation pass is verified by comparing each page before and after in multiset
categories: footnote markers and definitions; numeric tokens (identifiers that contain digits,
like a product code, and list numerals masked); the ordered tuple of numbers within each table row, list item, heading
or sentence (catches a swap the multiset cannot see); quoted strings, paired per paragraph;
cross-reference targets and URLs; hedge-phrase counts; whole identifier tokens; the text
inside every collapsed block; and a case-folded word multiset printed informationally. Any
loss fails; any addition fails unless its category is declared; a changed collapsed block
always fails. A regrouping flag downgrades a lost number tuple to a warning only when the
same digits still occur, unchanged and in order, as a contiguous run in the new page. Duplicate
lines or eight-word runs that the base did not have fail too. Two warnings name the two slips
writers keep making: a glance-box number or marker that no longer recurs in the body, and a
"the subject says" line with no quotation mark or subject marker.

The check is necessary, not sufficient: it has no notion of "the same claim" across a move, so
a marker moved to a neighbouring sentence that already carries one passes silently. Read every
split by eye. `scripts/measure_docs.py --preserve` is a lightweight version of this check.

## Review protocol

* The reviewer did not write the branch and reads with both the diff and the rendered tiles
  (desktop and 400 px).
* **Mandatory scripted check first**: the preservation diff on every changed page with no
  allowances except regrouping; then, for every split sentence, confirm by eye that each half
  carrying a claim still has the marker and the hedge the original had.
* Technical accuracy: verify at least three specific claims per page against the cited
  sources by fetching them; diff quotations; check that a cited source actually says what the
  page claims and that a derivation's reasoning holds (a trench depth derived from a drawing
  by double-counting a step height passed a cheaper reviewer and failed a stronger one).
* Consistency: names, thicknesses, layer order, step numbers agree with already-merged pages;
  list every conflict with both locations.
* Inference hygiene: every "likely" claim is backed by stated evidence with its grade.
* Tables: pick three cells of every new table and find the same value in the original prose —
  same digits, same significant figures, same quotation marks, same marker; confirm empty
  cells are empty in the source too.
* Hedges: every "our reading", "inference", "industry-typical", "not public" is still present
  at the same strength, a table-wide hedge directly under its table.
* Labels: read every new bold label, H3 and related-pages label as a claim about the text
  under it.
* Rendered: can I find the page's three numbers in ten seconds? Does the first screen say what
  the step does? Is any table wider than the column, any cell taller than five lines?
* Reject the page if any item of the Never list was broken, however good the rest.
* Findings: `file:line — severity — what is wrong — what the source says`; verdict approve /
  approve with fixes / reject; the writer fixes in a fix round and the reviewer verifies.
  Content doubts the writer flagged are findings for the coordinator, not for the reviewer to
  fix in a presentation branch.

Record which review classes keep recurring and turn each into a rule (with its "D" ruling id)
or a checker warning; the guide grows by rulings, not by rewrites.

## Model choice

In head-to-head batches on the same guide, the cheaper writer repeated the same mistake
classes every batch despite explicit instructions (markers and hedges dropped off split
sentences, hedges dropped from summary boxes, readings filed under "the subject says", false
related-steps labels, added facts, rewritten open questions); the stronger writer produced
none of them. Reviews by the stronger model found derivation errors, wrong-edition chapter
titles and non-verbatim quotations the cheaper one passed. Use the strongest model for prose
that builds tables and summaries from sentences and for verification reviews; cheaper models
for scripted and generator work. Record the comparison in a table so the choice is evidence,
not habit.

## Process

* One worktree and branch per task; never work in the shared checkout. Small commits (one
  page per commit, the page name in the subject, the rule ids or finding ids in the body).
  Regenerated output in its own commit.
* A progress file per branch (for example `docs/plans/progress-<branch>.md`): method, per-page notes,
  every allowance used and why, every doubt found with file:line, batch measurements against
  the caps, guide problems for the coordinator. It is what lets a stopped agent be restarted
  by a fresh one ("read the progress file and continue").
* Coordinator state and the task log live in the repository, not in anyone's conversation.
* Merge: rebase on main, fast-forward only, push main, delete the branch; tooling first, then
  site pages, then content batches.
* Writers do not launch sub-agents of their own; the coordinator caps concurrency.
* Fetch politely: one fixed non-browser user agent, no personal details in any request, a
  shared on-disk cache under `tmp/`, pacing per host, never looping on a bot check or 429.
* Never write to the system temp directory; use the project's git-ignored `tmp/`.
* Commit messages obey the source policy as strictly as page text.

## Checker catalogue (what to build for a new site)

Names are yours to choose; the worked example's file names are in `worked-example-sky130.md`.

| Checker | Holds |
|---|---|
| One template checker per page kind | mandatory headings as exact strings in order; quick-facts rows; index cross-reference (page rows ↔ index cells); forbidden words; stale generated blocks |
| Citation checker | markers ↔ definitions; labels in the inventory; no reference-style links; reading-list minimums; inline URL ⊂ the page's footnote URLs; angle-bracket link form |
| Restricted-content checker | restricted content only inside collapsed blocks; status sentence matches the dataset |
| Link checker | every URL/DOI in definitions and inventory resolves; dead → archive suggestion; polite, resumable, chunkable |
| Preservation checker | before/after multisets for presentation passes (`scripts/measure_docs.py --preserve` is a starting point) |
| Every generator's `--check` | generated indexes, membership tables, figures and the conventions page are current |
| Measurement script | caps worklists (paragraphs, items, sentences, cells, link runs); `scripts/measure_docs.py` |
| Screenshot tool | tiled headless-browser screenshots at desktop and 400 px for human and reviewer eyes |
| Term linker | first-use glossary links with context guards and an opt-out comment; idempotent |
