# Page templates (generic)

One skeleton per page kind. Mandatory headings are exact strings, alone on their line, in
this order; a checker tests them, so new structure goes under them as H3s. `+` marks what a
readability pass adds; everything else is content the writer provides. Fill the angle
brackets for your site: `<subject>` is the organisation or system the reference describes;
a "step" may be a process step, a procedure, an API call, a pipeline stage; a "class" is a
tool class, material class, component family or library. The concrete instantiation this
skill was distilled from is in `worked-example-sky130.md`.

## Leaf page (one step, one procedure, one endpoint)

```
(step-NNN)=
# Step NNN — CODE: Name

| quick-facts table |        number · code · category · phase · previous · next (navigation; do not reword)

+ :::{admonition} At a glance
+ :class: at-a-glance
+ * **Does:** one line.[^x]
+ * **Why:** one line.
+ * **Public numbers:** one to three of the subject's own values with markers, or "none published"
+ * **Likely tool:** name — existence strong / assignment inference.[^y]
+ * **Not public:** the one or two biggest unknowns (→ Open questions).
+ :::

## What this step is              lead ≤ 2 paragraphs, ≤ 120 words; first sentence ≤ 25 words: "`CODE` <verb> <object>"
   (generated figure block)       directly after the lead; any new H3 goes after the caption
+ ### Key numbers                  table: Quantity · Value · Source · Basis
+ ### What the public record shows short paragraphs; measured-against-nominal tables
+ ### How <quantity> is estimated  input table, numbered arithmetic, hedged result
+ ### Competing readings           where the page weighs two readings
## Step category                  one classification sentence ≤ 35 words; then "**Specific to this step:**" and bullets only if ≥ 2 sentences remain
## Why this step exists           1–2 lead sentences; 3–5 labelled bullets ≤ 60 words; studies as sub-bullets "Author (year) — finding.[^x]"; closing "Without `X` …" paragraph
## How it is typically performed  *italic scope line, word for word*; numbered list for a sequence; parameter table or labelled bullets for a parameter set; subject-specific statements last
## Machines typically used        bullets ≤ 40 words: class link, then example models   (rename for your domain: "Tools typically used", "Libraries typically used")
## Machines likely used at <subject>   three-line evidence items (below)
## Resources required             bullets; the supplier sentence once, last
## Related steps and cross-references  labelled bullets in the fixed order
   (generated index-links block)
## References
### Cross-check
### High-level understanding
### Deep dive                      ≥ house minimum
## Open questions                 labelled bullets; restricted-content notes last
<!-- footnotes -->
```

**Three-line evidence items** under "likely used at <subject>":

```
* **<Tool or implementation name>**
  - *<Subject> says:* lists it with "<quoted entry>".[^src]
  - *Tool exists:* strong (<subject> statement).
  - *Runs this step:* inference — <the reason, in the page's words>.
```

*Says:* holds only the subject's own statements, verb-first, quoted; this page's gloss goes in
a continuation paragraph after the grades. A statement from any other party stays a plain
paragraph. With four or more items, a two-column recap table `Tool | Evidence` goes above the
list; quotations stay out of it (they overflow a phone).

**Related-pages labels**, in this order: Previous · Next · Same module (only items whose
phase cell matches) · Depends on · Feeds · Same category · <artefact used> · Evidence ·
Category page. Keep every gloss and link; a link that fits no label stays unlabelled after
the labelled ones.

## Class page (a tool class, a material class, a component family)

```
(class-slug)=
# Title

intro ≤ 70 words: what the thing is and what it does for the subject
| quick facts |                    What it does · <defining attributes> · <Subject>-listed item (quoted) · N steps; see {ref}`…`
+ :::{seealso} pointer sentences moved out of the intro :::

## What the class is and how it works              H3 per subsystem; opening paragraph ≤ 60 words
+  (generated block-chain figure)
## Representative models                            table `Vendor | Model | Year | Published figures`, ≤ 3 remarks after it
## At <subject>
### What <subject> lists                            blockquote of the entries, then a table `Entry as listed | What it names | Status`
### Strength of the evidence                        grade in bold in the first sentence, ≤ 80 words
### <Subject> steps assigned to this class          the link run (byte-identical), then the generated membership table, then the grading bullets
## Consumables and facilities                       bullets whose lead-ins link the material/dependency pages
## Integration notes for <subject>                  bullets ≤ 60 words, lead-in names the steps
## Related pages                                    grouped under bold labels: Steps · Category · <sibling classes> · Indexes
   (generated index-links block)
## References                                       ≥ house minimum Deep dive bullets
## Open questions                                   one question per bullet
```

A material or dependency class uses the same shape with its own section names (what the
class is and does · representative grades, as a table `Item | Source | What the source says` ·
at <subject> · supply, handling, safety · integration notes · related · references · open
questions). The summary table's last row reads "N steps; see …" with N equal to the number
of step links on the page.

**Year cell** holds only the year the page gives for that model; a capture, award or
statement date stays in *Published figures* in the page's words. A value the page does not
give is `—`.

## Artefact page (a mask, a schema, a file format, a configuration)

```
(artefact-code)=
# CODE — Name

intro ≤ 70 words
| quick facts |     rows compared with the index: step that uses it · catalogue entry · defining attributes · readings marked as readings, with their basis · N steps; see …

## What the artefact defines
## Derivation                    ### In the catalogue   ### In the public derivation (say whose derivation it is, and that it is not the subject's)
## Records                       one table row per record; "none recorded" where none
## How it is used
## Steps that use it             a `Steps:` line, the link run, one bullet per step attributed to that step's page
## Rules and limits              quoted rules table `Rule | Description (published wording, abridged where marked "[…]") | Value`
## Related pages
## References
## Open questions
```

Every description of an adjacent step is attributed to that step's page ("on its page's
reading"). A rule's purpose (a margin, a budget) is a reading, never a fact. Claims about a
paper go no further than its abstract unless marked as not checked.

## Category page (a kind of step, a kind of component)

```
(category-slug)=
# Title
+ intro ≤ 60 words, assembled from the first paragraph below
+ | quick facts | What it does · Steps in <subject> (N) · Tool classes (links) · Consumable classes (links) · Governing relation
## What this class of step does
+ (generic mechanism figure)
## Background                             H3s welcome; comparisons as tables with a caption
## Typical equipment                      `Tool class (link) | Representative models | Note`; model history stays on the class page
## Typical consumables                    lead-ins link the material pages
## Steps in this category                 + `Tool class` column
   (generated index-links block)
## References                             ≥ house minimum Deep dive bullets
```

## Index pages

Purpose (≤ 80 words) → navigation (a card grid or a lookup table of `thing → one clause →
count`) → detail tables → "How to read this index" (the evidence and grading methodology,
moved whole) → open questions → references. Methodology never comes before navigation: the
reader who wants "the tool for step 89" should not scroll past the evidence policy. A new
navigation table gets its own heading and never sits inside a checked section above the
checked table. The sidebar toctree is `:hidden:` once cards or a table carry the same links.

## Landing page

Three paragraphs saying what the site is, where it comes from and what every page cites;
then a card grid (one card per section with a count); then the flow in modules as a table
(cells copied from the overview); then four lines on how to read a page (fact / typical /
inference; footnotes; hover cards); hidden toctrees. Counts are counted (`ls … | wc -l`),
not remembered.

## Overview

Order: how to read this reference → the flow by module (H3 per module, so modules appear in
the contents list) → a simplified cross-section or architecture → phases → what the subject
is → the big open questions → references. A five-bullet "On this page" list after the
opening paragraph, because the theme hides the contents list on narrow screens. Paragraphs
≤ 90 words; more than four markers in one means a list or a table.

## Glossary

One glossary block per initial under `## A` … `## Z`, plus an A–Z link line; entries ≤ 80
words, first sentence expands the acronym; only `{term}` and `{ref}` roles inside; bold terms
by CSS, not markup.

## Source inventory

One entry per key: anchor line `(src-key)=`, `**KEY** —` bibliographic sentence, URL(s), what
the source gives, then `Tier:` and the "used on" lines last. Grouped by provenance (the
subject's own documentation; announcements; corporate filings; job listings; predecessor
organisations; trade press; independent analyses; general-era references by module; evidence
about specific tools weighed by strength; gaps). The header count equals the number of
`**KEY** —` lines; no duplicate keys. Many tools read this file, so run every checker after
touching it.

## History / lineage section

Kept apart from the main reference in its own top-level section with its own toctree and its
own generated source list; one pointer from the landing page. Every claim has two independent
sources or is marked "(single source)" or "(the subject's reports)"; evidence lives as data
(verbatim quotes with locations, claims normalised to entity · attribute · value, notes on
conflicts), with a claims matrix checked by a script that ties every claim's sources to the
page's footnotes and every quote to a cached copy of its source. Never copy staff names
printed on a source document.
