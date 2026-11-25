---
name: writing-sourced-documentation
description: Use when writing, extending, restructuring or reviewing technical reference documentation — a docs site (Sphinx/MyST, MkDocs, Read the Docs), a wiki, one page per step/tool/material/component/concept, a research-backed explainer, or any page that states facts, numbers, quotations or claims about what an organisation does or owns. Trigger on "write a page about", "document how X works", "reference docs", "add citations", "footnotes", "sources", "make it skimmable", "readability pass", "wall of text", "review this page", and whenever a draft would carry a number without a source, even if the user never says "documentation".
---

# Writing sourced documentation

## Overview

Reference documentation earns trust in two ways at once. A reader must be able to tell, for
every sentence, **what kind of statement it is and where it comes from**; and they must be
able to **skim the page on a phone** and find its three important numbers in ten seconds.
Everything below serves one of those two ends.

The rules are generic. They were distilled from one large project — a 300-page,
publicly-sourced manufacturing reference whose pages were each written, independently
reviewed with claims verified against the fetched sources, restructured for readability
under a "change nothing it claims" rule, and machine-checked before merge — and the
mistakes its reviewers kept finding are the mistakes this skill exists to stop. That
project's concrete templates, checker names and policies are kept apart in
`references/worked-example-sky130.md`: read it to see the rules instantiated, never copy
its subject-specific terms into another site.

Two halves, both mandatory:

1. **Evidence discipline** — what may be said, and how its basis is shown.
2. **Presentation discipline** — the shape that makes a dense page skimmable without
   changing what it claims.

Read `references/readability-rules.md` before restructuring an existing page and
`references/page-templates.md` before writing a new one. `references/citations.md`,
`references/figures.md` and `references/review-and-tooling.md` cover the rest.

## Part 1 — Evidence discipline

### The five kinds of statement

Every sentence that asserts something is one of these, and the wording says which. Readers
and reviewers rely on this vocabulary; never blur it.

| Kind | Wording | Needs |
|---|---|---|
| Public fact | "The vendor lists …", "the datasheet gives …", the source's words in quotation marks | a citation right after the claim |
| Typical value | "typical", "industry-typical", "era-typical" | a textbook, paper, standard or roadmap citation; never presented as the subject's own number |
| Inference | "we infer … because …", "(inference)" | the reasoning shown on the page, and the evidence it rests on cited |
| Reading | "our reading of the published drawing", "on this page's reading", "(our arithmetic)" | the source read, cited; the result never stated as the source's fact |
| Not public | "not public", "not stated", "—" in a table | a bullet under Open questions saying what is unknown and what evidence would settle it |

A **hedge** is any of the words in that table. Hedges are content, not style: moving a sentence
moves its hedge word for word, splitting a sentence puts the hedge on every half it covers,
and a summary box condenses a sentence *with* its hedge. "Upgrading" a hedge ("our reading"
→ "the datasheet gives") is the single most damaging edit a page can suffer, because the
reader has no way to notice it.

### Where a claim may come from

* **Only sources the reader can obtain.** Anything behind a login, an NDA, a private drive or
  a memory is not a source. A publicly hosted document is citable whatever is stamped inside
  it. Private material is never named, alluded to or thanked, in pages or commit messages.
* **Verify before citing.** Fetch the page or paper; never cite from memory, and never cite a
  search-engine snippet or a page you did not retrieve. A claim about a paper goes no further
  than the part you read (the abstract, the table of contents) unless you say the rest was
  not checked. Chapter titles come from the edition you cite, not another.
* **Quote verbatim.** The source's words inside quotation marks, exactly, including its units
  and spelling; cut with "[…]" inside the quotation marks; never "fix" a quotation. A reviewer
  will diff it against the source.
* **A name is not evidence of a mechanism.** An entry in a list — a step code, a product
  name, a function name — proves the thing exists and what the list calls it, not what it
  does or how. Write "the list does not explain X; we read …" and support the reading from a
  source that does. Soft forms ("as the name suggests", "consistent with the name", "the
  pairing of A then B is the evidence") are the same mistake.
* **Numbers always carry a citation** — a dimension, temperature, dose, time, price, count —
  or a "typical" label with its own citation. A number with neither is a defect, not a detail.
* **Dates for things that change.** A capability list, a job posting, a product page: give the
  retrieval date. A dead link gets an archive copy cited first, the original kept in backticks
  (`references/citations.md`). A page with no copy anywhere loses its quotations and drops to a
  dated mention.
* **Several sources per claim where they exist**, compared with each other. A claim resting on
  the subject's own documents says so ("the manufacturer's reports"); a claim with one source
  is marked "(single source)". Where sources disagree, show both versions and say which you
  follow and why; never pick silently.
* **Grade evidence about a specific organisation** on a stated scale — **strong** (the
  organisation's or its vendor's own statement), **medium** (a job posting, an interview),
  **weak** (indirect) — and grade *that the thing exists* separately from *that it is used for
  this purpose*, because a capability list names what an organisation owns, never which
  procedure uses it. Write the grade's reason, not just the word.
* **Never fill a gap from memory.** An empty table cell is `—` or the page's own words ("not
  stated"); a missing figure is an Open question. A model that "completes" a table with a
  value the sources do not give has invented a fact, and every reviewer looks for exactly that.
* **Never silently fix a doubtful number.** In a presentation pass, a wrong sum, a wrong unit
  or a source that contradicts the text is reported (file:line) in a progress note, not
  corrected; content edits are their own reviewed change.

### Citations

Markdown footnotes: `[^label]` directly after the claim, number or quotation it supports
(`[^a][^b]` for several, no separators); full citation — authors, title, venue, date,
identifier, URL in angle brackets — in a definition at the foot of the page under
`<!-- footnotes -->`. Labels are lower-case, stable across the whole site, and taken from the
site's source inventory key where one exists. Every definition is referenced and every
reference defined (a build with warnings as errors enforces it). Reading-list bullets link
their head to the source's own URL so a source is one click away, and keep the marker, which
carries the key. Details, the dead-link form and the three reading tiers:
`references/citations.md`.

## Part 2 — Presentation discipline

### What a page is

Pages of one kind share one skeleton, so they are comparable and a script can check them.
Mandatory headings are exact strings, alone on their line, in order; new structure goes
*under* them as H3s, never beside them. A reference page, top to bottom:

1. **Anchor and title** — a label the site can cross-reference, then `# CODE — Name`.
2. **Quick-facts table** — the navigation and identity cells (number, code, category,
   previous/next; or a class's what-it-does / sources / members rows). Cells ≤ 20 words, one
   quotation at most, markers inside the cell.
3. **At a glance** box — four to six bullets, each ≤ 25 words, each condensing a sentence
   that is already on the page *with that sentence's marker and hedge*: Does · Why · Public
   numbers (the subject's own, or "none published") · Likely tool or implementation, with its
   grades · Not public (→ Open questions). Written **last**, from the finished page; it adds
   no fact.
4. **Lead** — ≤ 2 paragraphs, ≤ 120 words; first sentence ≤ 25 words, "`CODE` <verb>
   <object>". What is done, what arrives, what leaves, where it sits.
5. **Body sections** per the page type's template (`references/page-templates.md`). A
   section describing generic practice opens on an italic scope line (*Industry-generic
   practice for <this class of system>; the subject's own values are not public:*) so the
   reader knows those values are not the subject's.
6. **Related pages** — labelled bullets in a fixed order (for a sequence page: Previous · Next
   · Same module · Depends on · Feeds · Same category · Index); every label true of its links.
7. **References** — three annotated tiers: *Cross-check* (primary sources for this page's
   claims), *High-level understanding* (encyclopaedia, textbooks), *Deep dive* (papers,
   theses, patents from several assignees, standards, application notes), with a house minimum
   for the deep-dive list (the worked example uses 8 on a leaf page, 12 on a class or index
   page). Each bullet: linked head — one clause on what the reader gets from it — marker.
8. **Open questions** — one labelled bullet per unknown (`* **Trench depth.** …`), the hedge
   and the evidence that would settle it; restricted-content notes last.
9. **Footnote definitions.**

Generated blocks (index links, membership tables, figures) are fenced with
`<!-- name:begin -->` / `<!-- name:end -->` comments and never hand-edited: change the
generator, regenerate, commit the regeneration separately.

### Limits

Numbers, not adjectives, because "too long" is negotiable and 100 words is not. Count a
quotation or a code span as one word; ignore footnote markers and role wrappers.

| Element | Target | Hard cap |
|---|---|---|
| Prose paragraph | 40–80 words | 100; ≥ 120 must be split |
| List item (outside References) | ≤ 40 words | 60; lead sentence ≤ 30 when it has sub-bullets |
| Sentence | ≤ 30 words | 45; subject and verb in the first 12 words |
| Dash pairs or parentheticals per sentence | 0–1 | 1; a parenthetical ≥ 12 words becomes its own sentence |
| Page lead | ≤ 120 words, ≤ 2 paragraphs | first sentence ≤ 25 words |
| Class-page intro before the quick-facts table | ≤ 70 words | pointer sentences move to a *see also* box |
| Glossary entry | ≤ 80 words | first sentence expands the acronym |
| Table cell | ≤ 25 words | quick-facts cell ≤ 20, one quotation; ≤ 8 links |
| Table columns | ≤ 3 if any holds prose; ≤ 5 if every cell is a number, code or ≤ 3 words | must not scroll sideways at 400 px; no number broken across lines |
| Footnote markers in one paragraph | ≤ 4 | 6; at 5 or more, ask whether it is a table |
| H3s per page | ≤ 6 | each over ≥ 120 words with its own subject |
| Admonitions per page | ≤ 2 | the glance box is one of them |
| Figure alt text | 60–450 characters, geometry only | no citations |

`scripts/measure_docs.py` prints every block over a cap with its file and line; run it before
handing a page over, and again on the whole batch.

### Which form for which content

| Content | Form |
|---|---|
| ≥ 3 parallel items each with ≥ 2 attributes (parameters from several sources, layer stacks, rules, measured vs nominal, derivation inputs) | **Table**: one row per item in the original order; units in the header; numbers right-aligned; every row keeps its marker in the first or last cell; a hedge covering the whole table in one sentence directly under it, a row-level hedge in a final *Basis* column; `—` for a value the page does not give; a caption saying what one row is, where the values come from and any unit caveat; ≤ 3 prose columns, tested at phone width |
| A sequence, or arithmetic with ≥ 2 inputs or operations | **Numbered list**; for a derivation: input table (one marker per input) → one operation per line with its result in bold → bold result line → every hedge the original carried, in order. Check the arithmetic as you copy it; if it does not come out, copy it unchanged and report it |
| Reasons, failure modes, tools, resources, unknowns | **Bullets**, each opening with a bold 2–4 word label taken from the item's own words, then an em dash or a full stop; plain bullets for lists of studies and "first … second …" items |
| A sentence that announces a count ("two things can go wrong") or chains ≥ 3 clauses with semicolons | Lead-in ending in a colon (keeping the marker that covers all the items), then bullets, then the closing sentence as prose |
| The page summary | One admonition, the glance box |
| Content the reader must opt in to see | A collapsed **dropdown**, and nothing from inside it repeated anywhere outside — not in a summary, a table, a caption or a figure |
| A geometry, a chain of blocks, a flow, a to-scale stack | A **generated figure** (`references/figures.md`); it never replaces text and is always followed by prose |
| Term → explanation, two columns only | A definition list |

**Headings and labels are claims.** A label "Fastest ramp" over a bullet that says the tool is
the slower one, or "Same module:" over links that span the whole flow, passes every checker;
only reading the label against its text catches it. Use a fixed H3 vocabulary (*Key numbers*,
*What the public record shows*, *How <quantity> is estimated*, *Competing readings*) and add
no H3 when none is true of the passage.

**Never open a paragraph with a connective** (So, This, But, Which): it means the seam was
not real and the reader must infer a cause the split removed. If the only split point is
before a connective, do not split; leave the block over the cap and say so.

### Links and terms

* The source is one click away: reading-list heads and italic titles in prose link to the
  first URL of their own footnote definition, copied character for character. Never write an
  external URL that is not already in one of the page's footnote definitions, so link-rot
  checking stays complete.
* Glossary terms link on their **first** prose use per page, as whole words, never inside a
  heading, a code span, a quotation, link text, a table header or a footnote definition.
  Skip ambiguous words rather than link them wrongly.
* Cross-references use resolvable roles (`{ref}`, `{term}`) with the build set to fail on a
  broken target; never a bare path that rots quietly. Never `{numref}` with `numfig` off.
* Identifiers the page writes in backticks stay in backticks everywhere outside quotations.

### House conventions (this owner's)

British spelling (planarisation, aluminium), ISO 8601 or day-first dates, SI units with a
space (`1.8 V`, `900 °C`), thousands spacing as the source gives it, and a line never
starting with a bare `>` or `<` figure (CommonMark reads `>` as a blockquote).

## Revising an existing page: the Never list

A readability or formatting pass **changes presentation, never content**. A reviewer who finds
one of these rejects the whole page, however good the rest is.

1. Never change a fact, a number, a unit, a significant figure, a quotation, a hedge or a
   citation — not "1 800 Å" → "1800 Å", not "about 0.33 µm" → "0.33 µm".
2. Never upgrade or delete a hedge, even one that already appears two lines above.
3. Never move a footnote marker away from the claim it supports; when a sentence splits, each
   half keeps the markers and the hedge of its own clauses — a trailing hedge that covered the
   whole sentence is repeated on every half, or the sentence is not split.
4. Never fill an empty cell, never add a fact, a number or a source — the glance box and every
   new table are built only from words already on the page.
5. Never move text across a collapsed-note boundary, and never edit inside one.
6. Never change a mandatory heading, the count of reading-list bullets, or a generated block.
7. Never delete a duplicate sentence before checking that its footnote labels still occur
   elsewhere on the page.
8. Never fix arithmetic or a doubtful fact; write it down with file:line and move on.
9. Never let a pronoun's referent change: after a split, "it" must still name what it named.

Prove it: run `scripts/measure_docs.py --preserve BEFORE.md AFTER.md`. It diffs the multisets
of markers, numbers, quoted strings, hedge words, URLs and roles, and lists every word lost or
gained. The tool is necessary, not sufficient: it cannot see a marker that moved to the next
sentence, so read every split by eye as well.

## Review protocol

Nothing merges without an independent review by an agent that did not write it. The
reviewer:

1. Verifies at least three specific claims per page by **fetching the cited source**, and
   diffs every quotation against it.
2. Reads the diff as a **fact diff**: for every hunk, did a number, unit, quotation, hedge or
   marker change? Spot-checks three cells of every new table against the original prose.
3. Reads the **rendered page**, desktop and 400 px wide, not only the source: tables that
   scroll, cells five lines tall, a directive that silently failed to render, a label fan on a
   figure were all found only in screenshots.
4. Reads every new bold label, heading and related-pages label as a claim about its text.
5. Checks consistency with already-merged pages (names, values, order, identifiers) and lists
   each conflict with both locations.
6. Returns findings as `file:line — severity (High/Medium/Low) — what is wrong — what the
   source says`, then a verdict: approve, approve with fixes, reject.

Before hand-over the writer runs the template checkers, the citation checker, the generator
`--check`s, the measurement script and the build with warnings as errors, and records in a
progress file every allowance used and every doubt found. Use the strongest available model
for prose that turns sentences into tables and summaries: in head-to-head batches the cheaper
model dropped markers and hedges off split sentences in every batch despite explicit
instructions; the stronger one never did.

## Red flags — stop and re-read Part 1

| Thought | Reality |
|---|---|
| "I know this value" | Then you know where it is published. Cite it, or label it typical with a source, or leave it out. |
| "The hedge is obvious from context" | Context is lost the moment the sentence is quoted or summarised. Keep it. |
| "The step is called X, so it must do X" | A name is what a list calls a thing. Find the source that says what it does. |
| "A summary can be looser than the body" | The summary is the most-read text on the page and the easiest place to upgrade a hedge. |
| "I'll fix that sum while I'm here" | Report it. A presentation pass that changes a number cannot be reviewed as a presentation pass. |
| "The cell looks empty" | `—` is information: the source does not give it. A guessed value is a lie with a citation next to it. |
| "The snippet says the paper found …" | You did not read the paper. Cite what you read, or fetch it. |
| "It renders fine on my screen" | Shoot it at 400 px. Phones are where tables fail. |
| "The checkers pass" | Checkers are positional text parsers; a wrong label, a moved marker and an invented cell all pass. Read it. |

## Common mistakes seen in review

* Markers and hedges dropped off the second half of a split sentence; "(our extraction)"
  left on one of two halves it covered.
* An inference filed under "the vendor says"; a reading written as a fact in the glance box.
* A pronoun whose referent changed after a split; a sentence moved below the grade that
  refers to it.
* A list continuation that lost its indentation; a `{table}` caption wrapped onto a second
  line (the table silently fails to render); a wrapped `>550 °C` at the start of a line
  rendering as a blockquote.
* A new table "completed" with a value the page never gave; a Year cell holding a capture
  date rather than the model's year.
* Reading-list bullets merged or split, breaking the minimum count; a quotation's marks
  dropped when the quotation moved into a cell.
* Names used as evidence; search snippets cited; chapter titles taken from the wrong edition.
