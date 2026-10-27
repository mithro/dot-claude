# Readability rules for an existing page

Each rule has the same six fields, so a less capable model can apply it mechanically:
**Applies when** (a trigger decidable without judging content) · **Do** · **Example** ·
**Do not touch** · **Find** (the grep or measurement) · **Kind** (hand / scripted / generator).
Apply the rules in the order the page type lists (structure first, then tables and
derivations, then lists, then paragraphs and sentences, then the fixed-pattern sections, then
hedges and repeats, the summary box last). One rule at a time over the whole page, not one
paragraph at a time over all rules. Commit after each rule.

The one sentence that outranks everything: **this changes presentation, never content.** If
you cannot re-present a passage without changing what it claims, leave it exactly as it is
and write a line in your progress file.

## Prose

### R-PARA — paragraphs and list items that are too long

**Applies when** a prose paragraph exceeds 100 words, or a list item outside References
exceeds 60.

**Do.** Find the seams: a new source, a new quantity, a new question, a change of subject.
Split there, keeping every sentence in its original order and wording. Never start a new
paragraph with a connective (So, This, But, Which): the seam was not real. If the only split
point is before one, do not split; a split that leaves a block over the cap is no split. Give
each new paragraph a bold run-in label of 2–4 words and a full stop (`**Published thickness.** …`)
when the block is an evidence sequence; a narrative passage takes no label. A list item over
60 words keeps a lead sentence ≤ 30 words; the rest becomes sub-bullets (one fact and one
marker each) or an indented continuation paragraph. Reword only as far as the split requires
(a pronoun may need its noun back: "it" → "the oxide"). If the block is mostly numbers, apply
R-TABLE instead; if mostly arithmetic, R-DERIVATION.

**Example (worked example).** A 278-word paragraph covering a documentation quotation, a
model parameter, two measured results and their caveats becomes four paragraphs —
`**Published thickness.**`, `**Measured capacitance.**` … — same sentences, same order, same
markers.

**Do not touch.** Quotations, numbers, the parenthetical hedge, the order of claims, the
markers. Never split between a quotation and its attribution or between a claim and its marker.

### R-SENTENCE — long sentences, dash chains, nested parentheticals

**Applies when** a sentence exceeds 45 words, or contains two or more em-dash pairs, or a
parenthetical of 12 words or more, or a semicolon joining two separately cited facts.

**Do.** Split at the semicolon or at the dash pair: the material inside the dashes becomes its
own sentence directly after the sentence it interrupted. A mid-sentence hedge moves,
unchanged, to the end of its own sentence. Keep at most one dash pair or parenthetical per
sentence. Put the subject and the verb in the first 12 words. **Markers travel with their
clause.** A trailing hedge or marker that covered the whole sentence must cover every
sentence the split makes: repeat it, or do not split; when in doubt, repeat. It may stay with
one clause only if the page itself ties it to that clause (an Open-questions bullet names it)
and every other half is cited or carries its own hedge. Never split inside a quotation. A
split may add a subject and a verb ("It is", "This is"); it may not add a clause ("This holds
even though"), which states a relationship the original did not. A gloss of 12+ words may
stand as its own parenthetical sentence after the sentence it explains, capitalised and
closed inside the parentheses; a leading "which" becomes "That". At a ", though" split the
second sentence keeps "though" after its first phrase; never open on "Though" and never
substitute "However". When one whole-sentence hedge would appear three or more times in a
paragraph, prefer one closing sentence with the marker ("These are our extractions from the
published measurements.[^x]").

**Example (worked example; the dash material is a hedge, so it moves whole).** "It is made
through the same resist windows as the arsenic tip of ASTI — we infer that the two share the
NTM resist, since the halo belongs to the same transistors as the tip (see below) — but with
a tilted beam, so that boron ions …" becomes: "It is made through the same resist windows as
the arsenic tip of ASTI, but with a tilted beam, so that boron ions … We infer that the two
share the NTM resist, since the halo belongs to the same transistors as the tip (see below)."

**Do not touch.** Quotations; "we infer" (it survives the move); roles and link text.

### R-LIST — enumerations written as sentences

**Applies when** a sentence announces a count ("Two things can go wrong", "three reasons",
"first … second …"), or lists three or more parallel items of which at least one carries its
own clause, number or marker.

**Do.** End the announcing sentence with a colon; a marker on it supports every item and stays
there. One bullet per item in the original order with its own clause and marker; open each
with a bold 2–4 word label taken verbatim from the item's words, then an em dash — or, where
no such label exists without adding words, and always for lists of studies and "First …
Second …" items, plain bullets. The closing sentence ("Both are controlled by …") stays as
prose after the list. A list of four or fewer bare nouns stays inline. Numbered lists are for
sequences only; nest at most two levels.

**Do not touch.** Roles, markers, the closing sentence.

### R-H3 — no structure below H2; bold run-ins that are really headings

**Applies when** an H2 holds more than 120 words before its first H3 or list, or a paragraph
starts with a bold run-in that introduces a whole passage rather than one point.

**Do.** Keep ≤ 2 paragraphs and 120 words between the H2 and the first H3. Move nothing
between H2 sections. New H3s on a leaf page use a fixed vocabulary — `### Key numbers`,
`### What the public record shows`, `### How <quantity> is estimated`, `### Competing
readings` — and are added only over a passage of ≥ 120 words with its own subject whose
title is true of it. A bold run-in that introduces a passage becomes an H3 with the same
words minus trailing punctuation (`**How deep?**` → `### How deep?`); one that labels a single
paragraph stays bold. H3 titles unique on the page, never a mandatory heading's text, at most
six. If none of the titles is true, add no H3; structure with R-LIST or R-PARA instead. Never
invent a title such as "What this reference infers".

**Do not touch.** Mandatory headings; the position of collapsed notes (a note stays directly
after its paragraph; no H3 between them); the figure block's position.

### R-INTRO — long intros and pointer sentences on class pages

**Applies when** the text before the quick-facts table exceeds 70 words, or a page has no
intro, or the intro contains the template sentence ("This page describes the class in
general, lists …").

**Do.** Keep the sentences that say what the thing is and does, up to 70 words. Move pointer
sentences ("… is on the category page") into one `:::{seealso}` block under the quick-facts
table, unchanged. Delete only the template sentence (no fact, no marker; if it carries a
marker, keep it). Text cut to meet the cap moves, unchanged, to open the first H2; the only
change allowed is a leading pronoun → the class name.

### R-CATEGORY — the classification section as one dense paragraph

**Applies when** `## Step category` is a single paragraph over 35 words.

**Do.** First paragraph: the classification sentence with its markers (≤ 35 words where an
existing seam allows; never reword to reach it). If two or more sentences remain and describe
this step, add `**Specific to this step:**` and one bullet per sentence; one remaining
sentence stays a plain second paragraph. "What is specific … is that X, and that Y" over the
cap becomes "… is that:" and one bullet per complement; a clause with its own subject and
verb is a sentence, not a complement. A sentence repeating another section is R-REPEAT.

### R-HEDGE — hedge placement and the scope line

**Applies when** the generic-practice section opens with a scope sentence ("industry-generic
…"), or a hedge sits mid-sentence in a sentence you are splitting.

**Do.** Render the scope sentence, word for word, as an italic lead-in paragraph, not an
admonition (a note box renders as a 13 px callout holding one sentence ending in a colon,
cut off from the list it introduces, and spends the admonition budget). Move a mid-sentence
hedge to the end of the sentence it qualifies; four end tags are allowed — "(inference)",
"(our reading)", "(our arithmetic)", "(industry-typical)" — only when the existing hedge
already means exactly that; otherwise keep its own words. Where a body "not public" has a
matching Open-questions bullet, the body keeps its hedge and may add "(see Open questions)".
Never delete, weaken, strengthen or add a hedge.

### R-REPEAT — the same sentence twice

**Applies when** a run of ten or more words appears in two different H2 sections.

**Do.** Decide the home section (suppliers → Resources; tool quotations → likely-used;
unknowns → Open questions; numbers → Key numbers; classification → the classification
section). The home
copy keeps the full sentence and markers; the other becomes a pointer ≤ 12 words. **Before
deleting, check every footnote label in the deleted text still occurs elsewhere on the page.**
Cross-page boilerplate stays on every page. This is the only rule that deletes words; a
reviewer checks every instance.

### R-GLANCE — the summary box

**Applies when** a leaf page has no "At a glance" box. Written **last**.

**Do.** Four to six bullets, each ≤ 25 words, each condensing a sentence already on the page
with that sentence's marker and hedge. *Public numbers*: the subject's own values only, or
"none published"; a literature value only with the page's own qualifier. *Likely tool*: a
tool named in the evidence section with its grades, or "none assignable"; never a supplier or
material. Every qualifier in the source sentence ("part of", "typical", "our reading") survives
the condensing. No new fact, number or source; every marker in the box recurs below it;
nothing from a collapsed note. A glance line may not state as fact anything the page's Open
questions calls not public.

### R-TOOLS — evidence grading buried in run-on bullets

**Applies when** a bullet in the evidence section names a tool and contains "Strength:".

**Do.** Keep the tool name as the bold head; three sub-bullets with the original words moved
unchanged: `*<Subject> says:*` (only the subject's statements, verb-first, no leading pronoun),
`*Tool exists:*` (the grade and its reason), `*Runs this step:*` (the grade and its reason).
Omit the third when the page grades only existence. Do not normalise grade words. With four
or more tools add a `Tool | Evidence` recap table above the list, quotations excluded.

### R-OPENQ — unlabelled open questions

**Applies when** a bullet under Open questions does not start `* **`.

**Do.** Add a bold label of 2–5 words naming the unknown, from the bullet's own words, a full
stop, then the text unchanged. A bullet over 60 words stays in the section, split per R-PARA
inside the bullet; never moved, never rewritten as a summary.

### R-RELATED — related-links sections

**Do.** Leaf pages: labels in the fixed order (Previous · Next · Same module · Depends on ·
Feeds · Same category · <artefact used> · Evidence · Category page). Class pages: bold group
labels (Steps · Category · <sibling class kinds> · Indexes), each gloss ≤ 12 words. Drop no
link, add no link, change no link text. Every label must be true of its links.

### R-CODE — identifiers

**Applies when** an identifier the same page writes in backticks also appears bare in prose
outside a quotation. Add backticks there only; never inside a quotation, heading, link text,
footnote definition or table header; never to design-rule identifiers the whole site writes
bare; never to an English word that happens to be a layer name.

## Tables, data and derivations

### R-TABLE — numeric data written as prose or bullets

**Applies when** a block holds three or more parallel items that each carry two or more
attributes (a source and a value, a rule and a number, a layer and a thickness). Proxies: five
or more unit-bearing numbers plus two or more semicolons; three or more rule identifiers.

**Do.** Choose the columns from the kind of block:

| Kind | Columns |
|---|---|
| Published recipes from other sources | Source · Species · Energy · Dose · Note |
| Film stacks | Report (year, technology) · Stack as quoted · Total |
| Design rules | Rule · Constrains · Value |
| Measured against nominal | Parameter · Geometry · Measured · Nominal · Limits |
| Generic recipe parameters | Parameter · Typical · Public for the subject? |

One row per item in the original order; a source with several values gets one row per value,
its name and marker on the first row. Every row keeps its marker. Units in the header; per-cell
units only where the source is inconsistent, said in the caption. A hedge covering the whole
table goes word for word in one sentence directly under it; a row-level hedge in a final
*Basis* column. Quoted values stay quoted inside the cell; a value the page does not give is
`—`. Numbers, step numbers and years right-aligned; never centred. The concluding sentence
stays as prose after the table and may keep its opening connective ("So"), because it
concludes the table. A column whose value is the same in every row is not a column: put it in
the lead-in. Obey the column budget; if the table still fails the phone test, transpose it.

The column kinds above are the worked example's; choose yours from the kinds of block your
site has, and record the choice so every page uses the same columns for the same kind.

**Example (worked example).** "500, 275 and 130 keV phosphorus in a Harris twin-well flow;[^a] 700 keV at
2.0 × 10¹³ cm⁻² plus 120 keV at 2.0 × 10¹² cm⁻² in a Hynix flow;[^b] …" becomes

```
| Source | Energy (keV) | Dose (cm⁻²) |
|---|---:|---:|
| Harris twin-well[^a] | 500, 275, 130 (phosphorus) | — |
| Hynix[^b] | 700 | 2.0 × 10¹³ |
|  | 120 | 2.0 × 10¹² |
```

The Harris row has no published dose, so its cell is `—`, not a number from memory. One row per
implant, so no cell joins two numbers with `+` or `/`, which also breaks across lines at 400 px.

**Do not touch.** Significant figures, thousands spacing, "about", "~", the order, the markers.

### R-DERIVATION — arithmetic buried in prose

**Applies when** a passage writes out at least one operation and either performs two or more
or takes two or more inputs; or contains "our arithmetic", an inline `=` chain or "≈" with an
operation shown. Not when the page only names inputs and states a result with no operation
shown — that is a reading, and forcing it into the template invents working the page never
showed.

**Do.** An H3 `### How <quantity> is estimated` when the passage is ≥ 120 words. Input table
first (one row per input, each with its marker and the source's wording). Numbered list, one
operation per line, the line's result in bold; a reason line uses the page's own comparison.
A bold result line. Then every hedge the original carried, word for word, in order. A
single-operation estimate stays inline. Worked once; a second place keeps the result, hedge,
marker and "(derived above)". **Check the arithmetic as you copy it; if it does not come out,
copy it exactly and report it.**

### R-MODELS — representative models as vendor paragraphs

**Applies when** the representative-models section contains no table.

**Do.** `Vendor | Model | Year | Published figures` (tool-class pages) or `Item | Source |
What the source says` (material or dependency pages; drop Source when every cell would be
`—`). One source
per row. Quotation marks and markers travel into the cell. Sentences that fit no column
(litigation, "no vendor description was retrieved") stay as a short paragraph under the table.
Year is the year the page gives *for that model*; a capture or statement date stays in
Published figures. Caption per R-CAPTION. Shoot at 400 px; if it scrolls, merge Vendor and
Model.

### R-ENTRIES — "read term by term" paragraphs

**Applies when** a paragraph glosses the entries of a quoted list one after another (two or
more entries glossed one by one).

**Do.** `Entry as listed | What it names | Status`. The entry is the quotation, unchanged;
Status is the page's own hedge ("subject statement", "our reading", "not stated") — `—` where
the page gives none; never invented, never upgraded. Sentences about the list as a whole stay
as prose above or below.

### R-QUICKFACTS — quick-facts cells that are not quick

**Applies when** a cell exceeds 20 words or holds more than one quotation.

**Do.** Value first, in the page's words; at most one quotation; then the markers; then a
pointer ("see *Excimer laser source*"). **Before deleting anything from a cell, find the same
words in the body**; if absent, move them into the right section with their markers and
quotation marks first, then shorten the cell. Keep every row label and the row order. Rows
that a checker compares with an index are not touched. Navigation rows are not reworded.

### R-PARAMS — number-dense paragraphs beside a table

**Applies when** a paragraph names four or more identified parameters with values next to an
existing table. Second table `Parameter | Table | Published description | Value`; values and
identifiers exactly as written; the interpretation stays as prose after it; never merged into
the quoted-rule table (that is quoted text, this is parameters).

### R-CAPTION — every table says what it is

**Applies when** a table other than quick facts has no caption. Wrap in `:::{table} caption`
on **one line** (a caption wrapped onto a second source line makes the directive fail
silently; an incremental build can hide the warning). The caption says what one row is, where
the values come from, and any unit caveat. On a leaf page the lead-in sentence ending in a
colon *is* the caption; wrap only tables with a prose column. `:widths:` is inert in a
MyST pipe table; control phone fit by column count and cell length, and prove it with a
400 px tile. Never `{numref}`; refer to a table by its caption words.

## Links, references, navigation

### R-LINKS — reading-list heads become links

Link the head (text before the first " — ") to the first URL of the bullet's own footnote
definition, `[head](<URL>)`; the marker stays. With roles or backticks in the head, link only
the italic title; N titles and N markers in order → pair them; anything else, leave alone.
Named italic titles in prose link the same way, first occurrence per H2. Never a bullet inside
a collapsed note; never a URL the page's definitions do not carry. The bullet count is checked.

### R-WAYBACK — a cited page that no longer resolves

See `citations.md`, "Dead links".

### R-STEPRUN — runs of step links

A run of six or more links to step pages, or a link whose text is a bare number instead of
the code, is generator territory: a run of ≤ 25 links stays in the open and gets a generated
`Step | Code | Name` table after it (a *Role* column only when roles differ); a run of > 25 is
wrapped by the generator in a collapsed "All N steps as one line of links" block. Never
hand-build either. The run itself stays byte-identical, because a checker compares it with
the index.

### R-INDEX — methodology before navigation

Reorder whole H2 sections (with their anchor lines) into purpose → navigation → detail →
"How to read this index" → open questions → references. Move sections whole; rewrite nothing.
A new navigation table gets its own heading and never sits above a checked table in the same
section.

### R-TERM — glossary links

Per page, link the first prose occurrence of each term; whole word; acronyms case-sensitive;
plurals as `{term}`vias <via>``. Never in a heading, code span, link text, table header,
footnote definition, the References lists, or a quotation; never two links touching (they read
as one). Skip ambiguous terms. At most three new links per paragraph; a term deferred by that
cap takes its next occurrence. A page can opt a term out with a comment.

### R-CARDS — the landing page and section fronts

Keep the existing paragraphs verbatim; add a card grid with one sentence and a counted count
per section; the module table copied from the overview; four lines on how to read a page;
hidden toctrees.

### R-DROPDOWN — collapsed notes as the reader meets them

Title unchanged; body untouched, byte for byte; nothing crosses the fence; the note stays
directly after the paragraph it belongs to; never empty. Pointer prose in the body may shrink
to one end-of-sentence clause only when the sentence keeps its meaning.

### R-GENBLOCK — generated blocks

Nothing by hand. A one-character difference fails the generator's `--check` and every template
checker that calls it. Keep the splice-point heading (`## References`) exactly once.

## Per-page procedure

0. Own worktree and branch; copy the measurement scripts; `tmp/` for scratch.
1. **Baseline**: build, shoot the page at desktop and 400 px, open the tiles. You are fixing
   what you can see there.
2. Save the "before" copy of the page.
3. Apply the rules in the page type's order, one rule at a time over the whole page; commit
   after each rule.
4. **Preservation check** against the committed before: `measure_docs.py --preserve`. Declare
   additions you can name (the glance box, labels, restored subjects); treat any other loss
   as a bug in your edit. Read every regrouped-numbers line and confirm same digits, same
   order. Run the strict words check last and name every lost content word.
5. Template checkers, citation checker, generator `--check`s.
6. Build with warnings as errors; use a fresh output directory when sections were reordered.
7. Shoot again, both widths; compare with the before tiles; fix what looks wrong.
8. Self-review checklist: markers and hedges all present at the same strength; dropdowns
   untouched; no filled cell; no new external link outside the definitions; Deep dive count
   unchanged; mandatory headings untouched; caps met; every new table captioned; every scope
   sentence italic; phone tiles scroll only inside tables; doubts written down, not fixed.
9. Commit with the page name in the subject and the rule ids in the body; update the
   progress file in the same commit.
