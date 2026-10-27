# Reviewing a page

A documentation review tests whether the page can be used, then whether it is true. A review that only checks
facts confirms the scaffolding and ships a correct, unusable page (the case study in
[fpgas-online.md](fpgas-online.md) has one: four fact reviews passed a cable guide its reader could not follow).
So: use it first, audit it second, and brief the reviewer to hunt for shortcuts.

## Who

- The reviewer is never the author. In an agent workflow, the reviewer is a separate sub-agent that has not
  seen the author's reasoning.
- The brief is written by whoever dispatches the review, not by the author. An author's brief frames the
  review around the fix; the dispatcher's brief names the reader.
- A procedure is executed by someone other than the author before it merges. On real hardware or in a clean
  environment where possible; where nobody has the hardware, a sub-agent follows the rendered page as the named
  reader, step by step, with nothing but the page. (*House decision* whether anyone outside the team may be asked
  to run a procedure; docs.fpgas.online never asks.)

## What the reviewer is given

- The pull request, whose body names each page's reader and type, the views used and still missing, the photos
  wanted, every fact left out with its issue.
- The rendered page: screenshots of every step at desktop and phone width, light and dark if the site has
  themes, plus the image files. Markup alone is not enough: a wrong highlight cannot be seen in markup.
- A hardware fact sheet for the thing on the page: what it is, which hosts can physically carry it, what its
  connectors are. A reader walk as the right reader skips a claim about the wrong hardware (a page once said a
  single-board computer without the card's slot "takes the same cable").
- The page type's rules ([page-types.md](page-types.md)) and the shortcut list below.

## The brief

Use this shape. Fill every bracket; do not send a brief with a bracket left in.

```
Review <page or set> as <the reader: what they have in their hands, what they know, what they want>.
Hardware fact sheet: <what the thing is; which hosts carry it; its connectors and markings>.
Rendered pages: <paths to the screenshots and images>. Read the images, not only the markup.

Pass 1, use it. Follow the page from start to finish with nothing but the page. Return one row per step:
  step | could I do it from the picture and one line? | what did I guess? | what did I look for and not find?
Every stop is a finding.

Pass 2, audit it. For each figure, first say what it shows, then judge it. For each statement of fact,
mark it measured / from the vendor's document (link) / without a source. Compare every pin row and claim
with <the owning repository's page>, not with the old docs page.

Hunt, in so many words, for places where a shortcut was taken and the work was not completed:
<the shortcut list>.

Scope: the change, as rendered. File problems outside the change as issues; do not fix them here.
Return findings as fix-or-file items, each citing the rule it breaks. Do not return only an audit.
```

## The two passes

**Pass 1, use it.** The reviewer follows the page as the reader named in its front matter and returns one row per
step. Could I do it from the picture and one line? What did I guess? What did I look for and not find? Guesses
and stops are findings. "Could I do this step with only what is on screen at that point?" is the question.

**Pass 2, audit it.** Before judging a figure, the reviewer describes what it shows (this catches the wrong
highlight and the overview reused as a step). Then each hardware or software statement is marked measured, from
the vendor's document, or without a source. Unsourced is a finding. The audit goes in the review record, never on
the page.

A review that returns only the audit is sent back. A review that returns only "nothing lost" against the old
page preserves the old page's stale facts.

## The shortcuts to hunt for

- The overview figure reused as a step view; the same figure repeated across steps.
- A figure narrated in the words beside it; the wrong item highlighted; a look-alike highlighted as strongly as
  the subject; a part shown without the whole; no before and after.
- A `Sources:` line; `Future:`, `not yet`, `TODO` content; parts or tools the project does not use; protocol,
  connection and tool confused.
- Light and dark offered as links; "What you need" as a block of text; a building diagram drawn as laid.
- Variants without pictures; a mapping as a table of numbers; a step that cannot be done from its picture and
  one line; a page that mixes types; a sentence where a table cell wants a value.
- A command that never ran as written; a measurement with no date or host; a count that will drift.
- A title that names the tool or the topic instead of the task; a "Next" list over five entries or without
  link targets; a placeholder URL; an opening that does not say what the page leaves out.
- Output that explains why there is no output ("not enough data yet"); a fallback or "unknown" where the tool
  should have failed loud.

## The whole deliverable, as the reader

Reviewing the diff is not reviewing the deliverable. Once per deliverable (a booklet, a board's tree, a site
section), one review of the whole thing as the named reader, separate from the review of the change. Its first
questions: what does this reader need, what are they given, what is in the way (length, other readers'
material, structure)? A structural finding (whole chapters printed where one page was needed; 93 sheets for a
cable guide) is reported with the cost of fixing it; it is never silently marked "leave".

## Taking the findings

Verify each finding before acting on it; a reviewer can be wrong, and performative agreement is as bad as
ignoring the review. Then every finding ends in one of two places: fixed in the pull request, or filed as an
issue the pull request body names. None is left. Findings about generator or tooling code in the same change get
a code review as well.

## The merge gate

The generic gate, which any site can adopt (a site may add its own conditions; docs.fpgas.online's are in
[fpgas-online.md](fpgas-online.md)):

- The independent review is clean (every finding fixed or filed).
- The build is green on the exact head that will merge.
- That head contains the main branch at merge time, so the merged result is what was reviewed and built.
- Someone other than the author has followed one procedure on the page from start to finish.
- The pull request holds one page or one coherent set; a change that makes a page wrong carries the page's fix.

Merged is not published: a docs site that pulls content in from other repositories, or deploys on a schedule,
has a second step. Say "merged" until the reader can see it, then say "live" after looking at it as the reader.
