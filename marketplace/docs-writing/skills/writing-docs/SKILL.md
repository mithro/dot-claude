---
name: writing-docs
description: 'How to write, restructure or review documentation pages that a reader can use — user guides, how-tos, tutorials, reference tables, explanations, README sections, bench and wiring guides, runbooks, docs sites (Sphinx, MkDocs, Docusaurus, Markdown in a repo). Use this skill whenever the task produces or changes documentation of any kind, even when the user does not say "docs", such as "write up how to set this up", "document the API", "add a guide for", "fix this page", "the docs are confusing", "review this README", "split this page", "make instructions for the bench". It gives the page types, the fixed how-to skeleton, the limits, the picture rules, the review procedure, page templates and a linter.'
---

# Writing documentation a reader can use

A page is written for one reader with one need at one moment, in the form that serves that need fastest.
It is not a record of what you found out. Everything below follows from that sentence, and when a rule
seems to be in the way, that sentence decides.

Four readers, four needs:

- someone **doing a task** at a bench or a terminal needs the picture, the action and the check, right there;
- someone **looking something up** needs a table or list to scan, complete and consistent, with nothing to read;
- someone **trying to understand** needs prose that explains one thing well, with a diagram where words are slower;
- a **newcomer** needs one safe path to a first success, every step showing its result.

Your sources, your plan, your uncertainty, your description of the picture and your to-do list serve none of
them. They go in the pull request body, the review record, the issue tracker or a roadmap page.

The reason this skill exists: pages written to pass a fact check come out correct and unusable. A reviewer who
checks facts confirms the scaffolding, so the scaffolding ships. The fix is to write for use and to review by
use. The evidence behind every rule is in [references/evidence.md](references/evidence.md).

## Generic rules and house decisions

Everything in this file and in the generic references applies to any project's documentation, and each rule
has a published source. A few things are not rules but **house decisions**: choices a site makes once and then
applies everywhere (the names of the fixed how-to headings, the verb form of titles, the front-matter keys, the
top-level sections). This skill marks each one and gives a default to use when the site has not decided.

Before writing, find out whether the site has made its house decisions: a contributing page, an "about these
docs" section, a style guide, page templates, a linter configuration. If it has, follow them. If it has not,
use the defaults here and say in the pull request that you did.

**Working on docs.fpgas.online, or any repository under fpgas-online/ or mithro/?** Read
[references/fpgas-online.md](references/fpgas-online.md) as well: it holds that site's house decisions and
the project lead's standing rules, which bind there and nowhere else.

## The workflow

Work through these in order. Each step says which reference to read when you reach it; read it then, not before.

### 1. Decide the pages

- Name the reader (what they have in their hands, what they already know) and the one thing they want.
- Pick the page's type: **tutorial** (a lesson), **how-to** (a task), **reference** (a lookup), **explanation**
  (understanding). A page that would be two types becomes two pages that link each other. Mixed pages are the
  root failure of most documentation: each reader hunts through the other's material.
- Write the scope sentences first: what the page covers, for whom, what it leaves out. One to three sentences.
  You will revise them last, but they steer everything between.
- Find where the content belongs. A page lives beside the thing it describes and the docs site pulls it in; a
  docs repository keeps only what has no other home. Duplicated content disagrees within weeks.
- Read [references/page-types.md](references/page-types.md) for each type's shape, and
  [references/structure.md](references/structure.md) when adding, moving or re-nesting pages.

### 2. Gather what the page will say

- Every fact comes from a source you can link: the schematic sheet, the datasheet page, the code, the owning
  repository's page, a measurement you made. A fact with no source is left out and filed as an issue saying
  what would settle it. Never write around a gap ("not yet verified", "TODO", "unverified"): the reader cannot
  act on a hedge, and the hedge never gets removed.
- When the owning repository and an older page disagree, the owning repository wins. "Nothing lost" against a
  stale page preserves stale facts.
- For physical things, find the facts in photos, schematics and CAD renders before asking anyone. If a photo is
  too small, find a larger one; if none is good enough, render from the CAD source. Do not ask a person what a
  photo could show.
- Check the names: one name per thing, as printed on the part or shown in the interface; the printed marking in
  bold as printed; a pin or connector by its visible marker, never by colour or by "left" and "above".

### 3. Draft the skeleton

Start from the template for the type in [assets/templates/](assets/templates/). Copy it; keep its headings.

- **How-to**: the steps as plain imperative actions, one sentence each, in the order the hands work. Then each
  step's check (what the reader sees) and its "if it fails" entry (what you see, the likely cause, the fix).
  Then the prerequisites. The parts are fixed and ordered: prerequisites, steps, verification, error recovery,
  next. Fixed headings make a missing part visible. *House decision*: the headings' names. Default:
  `What you need · Steps · Check · If it fails · Next`.
- **Explanation**: a noun title, the one question the page answers, an outline of at most seven headings, and
  the diagram that would replace the longest paragraph. No numbered steps.
- **Reference**: the data file the table comes from and its columns (three or more attributes per row). If the
  data exists in a file, generate the table; a hand-typed copy of machine-readable data is stale by the next
  commit. No steps, no prose beyond the scope sentences and the column definitions.
- **Tutorial**: the one path from nothing to the first success, every step with a visible result, the success
  state pictured at the top. Nothing can go wrong in a tutorial; if it can, it is a how-to.
- **Landing**: one line per destination and nothing else.

### 4. Pictures and diagrams

Read [references/pictures.md](references/pictures.md) before placing any figure. The short form:

- Every physical thing named is pictured at first mention, the whole object before its parts.
- Every bench step gets its own picture, placed in the step, showing the object as it sits in that step. One
  overview reused across steps is the worst pattern measured: testers stopped reading. One action diagram per
  step at a fixed viewpoint cut assembly time by about a third and errors by half.
- Mappings (wire to cavity, pin to pin) are drawn, never tabulated. A table of numbers where a diagram belongs
  is the fault readers complain about first.
- The text beside a picture says the action and the check. It never narrates the picture.
- A figure about one part highlights that part only; a look-alike appears muted, as the thing not to confuse it
  with. A crop carries a whole-object inset so the reader knows where they are.
- Generate figures from one source model and reuse the generated views; a fix then lands everywhere.
- A render is matched against a photo of the same state before it ships. No photo: an existing one, one from
  the web, or a line drawing, and the wanted photo goes on the list in the pull request.

### 5. Write the copy

Read [references/style.md](references/style.md) for the full word and limit rules. The ones that bite:

- Each step: the place, then the action, then the result, in one paragraph, imperative verb first. "In the
  **Network** tab, select **Add**. The new row appears at the bottom." Where the action happens comes before
  the action so the reader's eyes are already there.
- Full detail where the reader acts; summary only where the reader orients. Repeat information in place rather
  than send the reader to another section. A reader following instructions must never scroll away to look
  something up. Repetition is done by including one source fragment in every place it is needed, never by
  copying text, so that a fix lands everywhere.
- Limits: title 65 characters; sentence 25 words; paragraph 3 to 5 sentences; list 2 to 7 items; at most two
  callouts, never carrying a step or a prerequisite; at most 15 links; five heading levels.
- A procedure that needs more than seven steps is split into two pages at a natural result, or its steps are
  grouped under level-3 headings inside "Steps". Never merge two actions into one step to fit the limit: a
  step with three commands and no result is the fault the limit exists to prevent.
- Never write a URL you have not opened. A source you cannot link is named in words and the missing link is
  filed; a placeholder such as `OWNER/REPO` or `example.org` never reaches a reader page.
- Banned words: `just`, `simply`, `easy`, `easily`, `straightforward`, `please note`, `click here`, `currently`,
  `soon`, `e.g.`, `i.e.`, `etc.`, `in order to`, `as of this writing`. They minimise the reader's difficulty or
  rot with time. Not on a reader page: `Future:`, `Sources:`, `unverified`, `TODO`, `not yet`.
- A source is one descriptive link in the sentence that needs it: "an 8-way housing ([datasheet](…))". No
  `Sources:` lines, no "Where the facts come from" section, no footnotes. The audit of claims belongs in the
  review record.
- No number that drifts (test counts, device counts, "five in the lab") and no date except on a fact that is
  itself dated. Anchor change to a version or an issue number, never to "currently" or "new".
- Nothing about the future, the unproven or the unused on a reader page. Planned work lives on one roadmap
  page, every item tied to an issue. Tools and hardware the project does not use are not described.
- Values in table cells, sentences in prose. One column, one form. No blank cells: "none" or "not applicable".

### 6. Finish

- Revise the scope sentences to match what the page became. Fill the front matter. *House decision*: the keys.
  Default: `type`, `owner`, `reader`, `review` (a date). The point is that every page has an owner and a
  freshness date; a page without either goes stale unnoticed.
- Self-edit: set the page aside, then read it aloud as the named reader. Delete anything outside the scope
  sentences.
- Run the linter on every page you touched:
  `uv run --no-project <skill-dir>/scripts/docs_lint.py docs/path/page.md`
  It fails on banned words, over-long titles and sentences, over-long lists, missing front matter, missing alt
  text, wrong how-to headings, and more than five heading levels. Fix every failure; explain or remove every
  warning. Flags: `--no-front-matter` for a repository without front matter, `--front-matter-keys` to set the
  required keys. If the site has its own linter, run that too.
- Build the site the way CI builds it (warnings as errors, parallel if CI is parallel) and read the output.
- Render each page as the reader will see it: desktop and phone width, light and dark theme if the site has
  them. Screenshot every step of a procedure and follow the procedure from the screenshots alone.

### 7. Review by use, then submit

Read [references/review.md](references/review.md). A docs review has two passes and the first is the one that
is usually skipped:

- **Use it.** The reviewer follows the page as the named reader and returns one row per step: could I do this
  from the picture and one line? what did I guess? what did I look for and not find?
- **Audit it.** Each statement of fact is marked measured, from the vendor's document, or without a source.
  Before judging a figure the reviewer says what it shows. This goes in the review record, never on the page.
- The reviewer is never the author, and the brief is not written by the author. The brief names the reader's
  hardware and task and says, in so many words: hunt for places where a shortcut was taken and the work was not
  completed. Reviews test truth, not only consistency: a fact check against the generator confirms a wrong
  sentence that lives in the generator.
- A procedure is executed before it merges, by someone other than the author, on real hardware or in a clean
  environment; when nobody has the hardware, an agent follows the rendered page as the named reader with
  nothing but the page. Every stop is a finding; the page does not merge until the stop is answered on the page.
- Review the whole deliverable as the reader, not only the diff: a printed booklet that runs to 93 sheets
  because whole pages were printed is a structural finding the diff review never sees. Structural findings are
  reported with their cost; they are never silently marked "leave".
- The pull request holds one page or one coherent set. Its body names each page's reader and type, the views
  used and missing, the photos wanted, every fact left out with its issue, and every problem found outside the
  change, filed as an issue.

## What a reader page never contains

Each of these was found on a shipped page; the case study in
[references/fpgas-online.md](references/fpgas-online.md) has the originals.

| Found on the page | Why it fails the reader | What to do instead |
|---|---|---|
| A dated log of work, an audit, a session record | A reader needs the current state, not history | Delete; broken things become issues |
| A "Future:" heading; "coming soon"; "not yet" | Promises rot; the reader cannot act | One roadmap page, items anchored to issues |
| `Sources:` in the prose; a "Where the facts come from" section | The audit shows through; the reader loses the thread | One descriptive link in the sentence; audit in the review record |
| "What you need" as a paragraph | Cannot be checked off at the bench | A list: one part per line, quantity, picture |
| A wire-to-cavity table of numbers | Numbers cannot be matched to a housing by eye | A diagram of the housing with the wires drawn in |
| The same wiring sheet at every step | Testers stop reading; nothing says which part this step touches | One view per step, cropped and highlighted, the whole as an inset |
| A figure about one connector that highlights its neighbour as strongly | The reader wires the wrong connector | Highlight the subject only; mute the look-alike |
| A figure described in the words beside it | Twice the reading, no action | The text says what to do and what to check |
| Light and dark images both offered as links | The reader has to choose | One figure that follows the theme |
| A device count, a test count, "as of October" | Wrong by the next change | Describe what is checked; link the live count |
| A page that explains, then instructs, then lists | Every reader hunts through the others' material | Three pages that link each other |
| The protocol, the connection and the tool confused | The reader cannot reason about what talks to what | Three layers kept apart, one figure in those layers |
| Hardware or tools the project does not use | The reader buys the wrong thing | Describe this project's setup only |
| A sidebar with forty pages under one heading | Nothing can be scanned | Nest like the index; sub-headings above seven entries |
| Output that explains why there is no output ("not enough data yet") | Unfinished work presented as a result | Make the missing data a fatal error in the tool; fix the tool |

## When the work is larger than one page

- A set of pages or more than one pull request: write a plan first (with `superpowers:writing-plans` if
  available) and have it read before starting. Restructure first (move, retitle, re-nest), then change
  content, so the site has one coherent view at every moment.
- Rebuilding a messy tree: the order is structure, then the pages a visitor meets first, then the cheapest and
  most visible fixes (wrong facts, wrong links, wrong heading levels, contradictions), then photos, diagrams and
  bench runs. Do not build empty sections for types that have no pages yet.
- Pages are organised by the reader's task and the thing in their hands, not by topic or tool: one setup page
  per host or platform variant, one short "checking it" page apart from the checking tool's reference. If the
  site prints pages for the bench, page structure is booklet structure.
- A hardware build guide carries a set of diagrams with different jobs (the finished thing in place; the parts
  and their internals; the connectors and every pin's function; assembly steps; verification steps; plugging-in
  steps; the result after each group of steps; the wrong configurations and how to recognise them). The full
  list is in [references/pictures.md](references/pictures.md).

## Bundled resources

| Resource | Use it when |
|---|---|
| `assets/templates/*.md` | Starting any page: how-to, tutorial, reference, explanation, landing, troubleshooting |
| `scripts/docs_lint.py` | Before every commit of a page; in CI |
| `references/page-types.md` | Choosing or checking a page's type and shape; worked examples |
| `references/style.md` | Writing or editing copy: limits, words, names, tables, links, callouts |
| `references/pictures.md` | Any figure, photo, render, diagram or diagram set |
| `references/review.md` | Dispatching or performing a review; the reviewer brief; the shortcut list |
| `references/structure.md` | Adding, moving or re-nesting pages; where content lives; keeping pages true |
| `references/evidence.md` | Wanting the source of a rule, with the quote |
| `references/fpgas-online.md` | Working on docs.fpgas.online: its house decisions, standing rules and the case study behind this skill |
