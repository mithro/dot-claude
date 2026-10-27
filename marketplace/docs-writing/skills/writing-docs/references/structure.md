# Structure and upkeep: the site, the sidebar, where content lives, keeping pages true

## The site

- The top level is a small set of sections. Label them by activity ("Getting started", "Tasks", "Reference")
  unless the audiences are genuinely disjoint, in which case label them by reader. A site with a visitor who has
  no hardware, an administrator with a bench, and a developer with a checkout has disjoint audiences, so "User
  documentation / Admin documentation / Developer documentation / Resources" is right for it. Inside each
  section the four page types apply.
- A section exists only when a real page sits under it. "It certainly does not mean that you should create
  empty structures … Don't do that. It's horrible." The structure is built by re-nesting pages that exist.
- Pages are ordered as the reader works: what it is, which one I have, set it up, check it, look it up.
- Pages are organised by the reader's task and hardware, not by topic or tool: one wiring page per carrier
  board, one setup page per host type, the by-hand checks apart from the tool reference. If the site prints
  pages for the bench, page structure is booklet structure.
- A landing page is one line per destination and nothing else. The home page opens with the sections and then
  "I want to…" paths for the first things readers come for.
- Two trees for one subject when two readers need it: a user tree about using a board from the website, an
  admin tree about setting it up. They cross-link; neither restates the other.

## The sidebar

- The sidebar nests exactly like the index page's headings above it. A heading with more than seven entries
  gets sub-headings so any one group can be scanned. Forty pages under one heading cannot be.
- A page joins the sidebar through its line on the index page above it.
- Depth is controlled per page, not by a sidebar rule: at most five heading levels, at most 15 links; deeper
  or longer means a new page.

## Where content lives

- A page's source lives in the repository of the thing it describes: the wiring page beside the wiring
  generator, the gateway page beside the gateway's code, the tool's page in the tool's repository. The docs site
  pulls each page in at build time (a sync tool with a pinned commit, or a submodule), and nothing is copied by
  hand. The docs repository keeps only what has no other home: the entrance, the landing pages, site overviews,
  the pages about the docs themselves.
- Why: content written away from the code drifts from it; the owning repository's reviewers never see it;
  duplicates disagree. "There can be only one source of truth."
- A change to a pulled page is made in its own repository and travels in the same pull request as the code
  change that made the page wrong. Docs are part of the definition of done.
- Where the docs repository's copy has become better than the source, move it back to the source by pull
  request there, then pull it.
- Before writing or splitting a page, ask which repository owns the subject; put that page in the brief as the
  source of truth; when the owning page and the old docs page disagree, the owning page wins.

## Keeping pages true

The sites that stay current do it with machinery, not better prose.

- Every page has an owner and a review (freshness) date in its front matter; an expired date opens an issue to
  the owner.
- Every page shows its last-modified date linked to the commit.
- Every rename or move leaves a redirect, and the build refuses one that does not (after a rebuild of unused
  pages, the project lead may waive this for the pages moved during the rebuild).
- Reference generated from source data fails the build when the data changed and the page did not.
- Status is anchored to a version or an issue, never "currently" or "new".
- Deprecated content is deleted, not annotated. A procedure nobody has executed is removed, not left.
  "Consider incorrect documentation to be worse than missing documentation."
- Duplicated content is replaced by a link to the one source.
- Every page offers "was this useful", routed to the issue tracker, so the "not useful" signal lands beside
  the fix.
- Forward-looking content lives on one roadmap page (and per-site "what this site provides and plans" pages
  where a site needs one), every item tied to an issue or milestone. Nothing about the future on a how-to,
  reference or explanation page.

## What the build checks

Automate everything a machine can decide, so reviewers spend their time on what it cannot. Fail on:

- a banned word or forbidden phrase on a reader page;
- a title over 65 characters or not unique; a step sentence over 25 words;
- a how-to with missing or extra headings; a bench step with no figure; missing alt text;
- a light/dark pair outside a switched figure; a sidebar group over seven; more than five heading levels;
- a link-only page; a rename without a redirect; missing front matter;
- stale generated reference; a broken internal link;
- a bench page whose print splits a step from its picture.

Warn on: a figure used twice with the same view; more than 15 links or two callouts; an expired review date.
Check external links on a schedule, not per change: it needs the network and takes minutes.

The bundled `scripts/docs_lint.py` covers the prose and structure checks on a Markdown page; the figure, redirect,
generated-reference and print checks need the site's own tooling.

## Builds

- Build locally the way CI builds: warnings as errors, `--keep-going`, and parallel (`-j auto`) if CI is
  parallel. A serial build can pass where a parallel one fails (two pages defining one anchor target).
- Read the whole output. Explain every warning or remove its cause.

## Working through a messy tree

1. Restructure first: move files, retitle, re-nest the sidebar, type every page, split mixed pages. One view of
   the docs at any moment.
2. Then the pages a visitor meets first, in the order they meet them: the home page, the user section, the pages
   the product itself links to, then each board or feature tree from its landing page inward.
3. Then the cheapest, most visible fixes: wrong facts, wrong links, wrong heading levels, contradictions between
   pages, missing one-line facts the owning repository already settles. Rework of what exists (shape, order,
   headings, wording) before hunts for new facts.
4. Then what needs hardware, photos, generated views or new tooling, each tracked by an issue; during a rebuild
   only, a page may carry a placeholder that names its issue.
5. Delete record pages, audits and logs; file what is still broken.
6. Keep going when the ranked list runs dry: re-rank and continue. A hold is itself a decision someone has to
   notice.
