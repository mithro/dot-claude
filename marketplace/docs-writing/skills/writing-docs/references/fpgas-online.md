# docs.fpgas.online: house decisions, standing rules and the case study

This file is specific to docs.fpgas.online (fpgas-online/fpgas.online-docs and the repositories it pulls
from). Nothing here is a general rule of documentation; the general rules are in SKILL.md and the other
references. Read this when working on that site. The project lead's words are quoted where they are the
clearest statement of a rule; the full verbatim record is in the coordinator's scratch repository
(`00-brief/2026-10-04-tim-decisions.md`) and the site's own "About these docs" section under Developer
documentation carries the rules as published, each numbered so a review finding can cite it.

## House decisions

| Decision | docs.fpgas.online's choice |
|---|---|
| Top-level sections | User documentation · Admin documentation · Developer documentation · Resources (by reader, because the audiences are disjoint: a visitor with no hardware, an operator with a bench, a developer with a checkout, anyone looking something up). A starting framework, built out as pages need, never with empty sections. |
| Admin documentation's parts | how the system works · how to maintain it · how to set up sites and devices (the Pi + FPGA board guides belong with the third) |
| Page types | Diátaxis's four inside every section; `landing` for an index page |
| How-to title form | "How to <exactly what the page shows>", unique, at most 65 characters |
| How-to headings | What you need · Steps · Check · If it fails · Next, in that order, no others |
| Front matter | `type`, `owner`, `reader`, `review` (a date); every page shows its last-modified date linked to the commit |
| Each board's tree | Overview · Which one do I have · Set one up (one sub-tree per host carrier, e.g. Raspberry Pi 5, Compute Blade) · Checks · Troubleshooting; one typed page per leaf; the same shape for every board |
| Set-up guide split | by part: parts list, wires, housing, bench check, fitting; a page is at most about 4 or 5 printed A4 sheets with its diagrams |
| User boards tree | a second tree under User documentation about using a board from the website, cross-linked with the admin tree |
| Forward-looking content | per-site "what this site provides and plans" pages and one site-wide roadmap page, every item tied to an issue or milestone; nowhere else |
| Where content lives | in the repository of the thing (infra: gateway, netboot, network, Pi; test-designs: board pages, wiring, checks; site: the web application; and so on), pulled in by `tools/sync_repos.py` at a pinned commit; the docs repository keeps the entrance, landing pages, site overviews, contributing, "About these docs" |
| Figures | generated from one model in test-designs (board geometry, pin 1, the Pi header, `wiring.toml`, the cable), each view by id; light and dark twins from one palette shown by the theme's class; `tools/test_dark_twins.py` enforces the pair |
| Print | `tools/print_pages.py` renders published pages to one PDF for the bench; a step and its picture stay on one sheet |
| Redirects | none for pages moved during the October 2026 rebuild ("the old documentation was not of high enough quality that anyone actually used it"); the redirect rule applies from the end of the rebuild on |
| Placeholders | allowed during the rebuild only, each naming its GitHub issue |
| Names | hardware by its label name and value (`acorn-holly 0x00200c8664b04854`), never by switch port; a bare host name means the Welland site, so "pi20 at ps1" for the other site; "GPIO 4" never "pin 4"; no names of people on a page |
| Private devices | the project lead's `iot.welland` development devices may be named and measurements on them recorded, stated as cross-check devices and not identical to the fleet |
| Dates | day-first or ISO 8601; clock times in Australia/Adelaide |
| Merge gate | an independent sub-agent review record at the exact head; every check green; not a draft; the head contains `origin/main`, checked in the same command as `gh pr merge --merge --match-head-commit <sha>`; the coordinator's explicit word per SHA; one page or one coherent set per pull request. Merged is not published: the site rebuilds from the pull, and a change is "live" only after it has been read on the site as the reader. |
| Bench runs | done virtually by a sub-agent as the named reader when nobody has the hardware; never ask the project lead or a collaborator to do a task for us (rule 25) |
| Nothing upstream | issues and pull requests only in repositories under github.com/mithro and github.com/fpgas-online; never in LiteX, Tiny Tapeout, Raspberry Pi or any other upstream |
| Tiny Tapeout boards | no code writes, replaces or deletes a file on a Tiny Tapeout demo board; bitstreams are loaded by streaming |

## The figures every board gets

| Figure | Shows |
|---|---|
| Whole board | top and bottom, photo and render |
| Connectors | each one, with pin 1 marked |
| Wiring | the cable as the ribbon lies (the as-laid, debugging view) |
| Programming | the three layers: protocol (JTAG), connection (the host's GPIO pins to P1, or PCIe), tool (OpenOCD, openFPGALoader) |
| Variants | the comparison side by side, same orientation and scale, the tell marked |

## The project lead's standing guidance, in his words

On every piece of documentation (5 October 2026):

> - When following instructions, I should never have to scroll to another section or look something up
>   separately. All the details I need should be included directly with the relevant area. Computer
>   documentation can trivially include the same element/information/stuff in multiple places without issues
>   normally associated with "do not repeat yourself".
> - Anything which is describing something should include pictures and diagrams of that something.
> - Reuse existing diagram and text rather than creating new versions of something. That way any improvement
>   fixes multiple locations.
> - Make sure that you think about the person viewing the document and what they are trying to achieve and ask
>   yourself "how can I make it easier for them to achieve their goal? how can I make it so the person has to
>   think less and get things done more quickly?"

On the site's purposes (10 October 2026):

> https://docs.fpgas.online has multiple purposes -- at a high level it describes how the fpgas.online system
> works - what it does, how it does it, what you can use it for, how to set up your own version, etc. … This
> isn't a comprehensive list of everything the docs should include. It is a starting framework / structure that
> should be built out around. There are lots of good guides and resources on the web about writing / creating
> good documentation. In particular look at the presentations "What nobody tells you about documentation".
> Documentation is a constant evolution and nobody has everything 100% figured out.

On build guides (10 October 2026):

> When constructing a build guide, there should be multiple diagrams which serve different purposes -- for
> example (and not a complete list): an overview diagram which shows the cable that is being built in the final
> intended configuration / installation position; an overview diagram of cable and its internals; an overview
> diagram showing how the connectors and the various pin functions; step by step diagrams which show how to put
> together the cable; step by step diagrams which show how to verify the cable is wired correctly; step by step
> diagrams which show how to plug in the cable correctly; final diagrams which show what the result should look
> like after each major set of steps; diagrams which show incorrect configurations and common issues that people
> should look out for (putting connectors one too high, swapping uart tx & rx, etc) and how to identify them.

On wiring diagrams: "It is expected the physical wires will cross when everything is connected -- that is
unavoidable. The diagrams used in the building guide should be drawn with a focus on clarity and ease of cable
construction. The diagrams used in a debugging guide should be drawn with a focus on making sure the layout
matches reality while still trying to be as clear as possible."

On record pages: "There should be pages which list what is available at various sites and what is in the
process of being deployed in the future. This should read as 'here is what the site provides and what the site
plans to provide in the future', not an inventory, that is what the dashboards are for. There is no reason to
keep random history stuff. Bugs / stuff that is broken should be github issues, not in the documentation."

On photos: "Find and create new photos from existing items. Use clear line diagrams where no photo will work.
Keep a list of new photos that would be helpful. Make sure these photos are only requested when no existing
photo that fits the purpose can be found on the web." And: "Don't be lazy, go look at photos / schematics /
renders of the boards and extract the information. … we should *always* try and have stylized renders (which
only show the relevant details and area clearer / less noisy than photos of real set ups) as well as photos."

On where content lives (rule 14): "Make sure that the majority of docs are found in the relevant repo *not* in
the docs repo. The docs repo should only have content that doesn't have another repo which is logically where
it should be. The docs repo should import the majority of its content from the other repos. Make sure there is
no duplication between content in the docs repo and other repos."

On numbers (3 October 2026, about a CI page whose test count went stale in a day): no number that constantly
changes in a document; describe what is checked and link the live value; a dated measurement may stay, with its
date and host.

General principles for every deliverable (9 October 2026): finish the thing that was asked for (output that
explains why there is no output is unfinished work; a tool that does not report the data is fixed to report
it); values in tables, sentences in prose; one column, one form; unambiguous icons; tables with striping and
sorting; reviewers told in so many words to hunt for shortcuts; fail fast and loud on unexpected results.

## The case study: what went wrong, and what the site looks like now

The first review of the Acorn pages (9 October 2026), which produced most of the rules in this skill:

> The links on the side should be properly nested by the same type of headers found on the index page. Opening
> the Acorn section of the boards has like a bazillion links under it. As a rule, if some header has more than
> 5-10 items under it then it probably needs sub-sections.
>
> Looking at the Acorn Device Info; There is a single giant diagram on the top and then describes each item. The
> diagram is not connected to any of the stuff on the page -- it shows the two P1 and P2 connectors. Where are
> the pictures of the acorn in general? Each section talks about items but show no pictures of that item.
>
> Looking at the Acorn variants, there are no pictures of the different variants, nor how to tell them apart.
>
> Why is there an section on Acorn functionality about `JTAG over an FT232H (OpenOCD)` but no FT232H is used
> anywhere with the Acorns?
>
> Why is the tooling confused with the protocol and connections? The Acorn can be programmed using JTAG with
> OpenOCD or openfpgaloader via the RPI GPIO pins. It can also be programmed with these tools directly via PCIe
> when that is loaded.
>
> Why is there a random "Future: XXXX" header? Why are you repeating a figure in words? Why are you linking to
> the dark and light version rather than just displaying the right one? The order of the pages doesn't make
> sense. Why are there random "Sources:" text in the middle of description of things? Why is there a giant
> `Where the facts come from` sections? Why have you written in giant text blob "What you need"? Why does the
> section which is talking about P1 also highlight P2? Why does the part highlighting P1 not show the full acorn
> and show which one is P1? Why does it instructions now show P1 before and after a cable has been inserted? Why
> is the same diagram repeated so many times on the jtag connector page? The parts of the diagram which are
> relevant to the step being looked at should be shown, not the whole diagram each time. Why is the connector
> placed in such a way that makes the most number of wires cross?
>
> All this indicates that you are not properly reviewing the docs critically and thinking about how the
> information is being displayed, how a person will read it, what the relevant information is and what is not
> relevant here, when you are providing a summary verse when you need to provide the full details, how to
> properly reference sources without interrupting the rest of the document, etc.

And of the diagrams: "Many of the diagrams are pretty good as overview but fail when trying to follow
instructions."

The cable-building section (5 October 2026): written as prose plus a wire-to-cavity table of numbers, reviewed
by sub-agents who checked the numbers against the pin tables, passed by the coordinator from a glance at the
rendered sheet, then sent to the project lead with a question about whether it was right. "The 'Building the
Cables' section is pretty unreadable and useless. It needs proper pictures and diagrams for all steps. … If
this content was properly reviewed, why did the reviewer not catch these extremely basic issues? If it wasn't
properly reviewed, then why are you asking me questions about it?"

The booklet (6 October 2026): a printed cable guide for a collaborator ran to 93 sheets because whole published
pages were printed as chapters; four reviews had found faults in the steps and none had judged the booklet as a
product for its reader (a blade owner with one board, no Pi 5). Hence: one review of the whole deliverable as
the named reader, with the reader's hardware and task in a brief written by the dispatcher; structural findings
reported with their cost. And "reviews test truth, not only consistency": the wiring page said a Pi 4 "takes the
same cable"; the board is an M.2 PCIe card. Every review brief since carries a claims pass and a hardware fact
sheet.

What the site looks like after the rebuild (10 to 18 October 2026):

- Four top-level sections, each a landing page of one line per destination; the home page opens with the
  sections and six "I want to…" paths.
- Each board has one tree of the house shape, the sidebar nested like the index.
- The Acorn set-up guide is split by part, each a how-to with the fixed headings, each step with its generated
  view pulled in from test-designs.
- "Programming an Acorn" is an explanation in three layers; "Acorn variants" is a reference with a tells table;
  troubleshooting pages are reference tables of what you see, the cause, the fix.
- Developer documentation carries "About these docs": the structure, what a page contains (numbered rules),
  how a page is reviewed, the references with quotes, and where each limit comes from.
- The build fails on banned words, over-long titles and sentences, over-long lists and missing front matter; a
  dark-twin check fails a drawing without its pair; the print tool keeps a step and its picture together.
- Record pages, audits and `Sources:` sections are gone; what was still broken became issues; one roadmap page
  carries the plans, each tied to an issue.
