# Case study: docs.fpgas.online, October 2026

The rules in this skill were distilled from one site's rebuild: docs.fpgas.online, the documentation of a
fleet of FPGA boards on Raspberry Pi hosts reachable over the internet. Its pages were written by AI sessions,
reviewed by AI sub-agents, and read by the project lead. What follows is what the project lead found, in his own
words where they are the clearest statement of a rule, and what the site looks like after the rules were applied.
Read it to see the rules in use, and to recognise the faults when you are about to make them.

## The first review of the Acorn pages (9 October 2026)

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

And, of the diagrams: "Many of the diagrams are pretty good as overview but fail when trying to follow
instructions."

## The cable-building section (5 October 2026)

A "Building the cables" section had been written as prose plus a wire-to-cavity table of numbers, reviewed by
sub-agents who checked the numbers against the pin tables, passed by the coordinator from a glance at the
rendered sheet, and then sent to the project lead with a question about whether it was right.

> The "Building the Cables" section is pretty unreadable and useless. It needs proper pictures and diagrams for
> all steps. The `Push each terminal into its cavity…` section is particularly bad as it is random table of
> numbers which clearly should be a diagram. … If this content was properly reviewed, why did the reviewer not
> catch these extremely basic issues? If it wasn't properly reviewed, then why are you asking me questions about
> it?
>
> - When following instructions, I should never have to scroll to another section or look something up
>   separately. All the details I need should be included directly with the relevant area. Computer documentation
>   can trivially include the same element/information/stuff in multiple places without issues normally
>   associated with "do not repeat yourself".
> - Anything which is describing something should include pictures and diagrams of that something.
> - Reuse existing diagram and text rather than creating new versions of something. That way any improvement
>   fixes multiple locations.
> - Make sure that you think about the person viewing the document and what they are trying to achieve and ask
>   yourself "how can I make it easier for them to achieve their goal? how can I make it so the person has to
>   think less and get things done more quickly?"

## The booklet (6 October 2026)

A printed cable-building booklet for a collaborator ran to 93 sheets because whole published pages were printed
as chapters. Four reviews had found faults in the cable steps; none had judged the booklet as a product for its
reader (a blade owner with one board, no Pi 5, no other hardware). The lesson: one review of the whole
deliverable as the named reader, with the reader's hardware and task in the brief, written by the dispatcher
and not the author; structural findings reported with their cost, never silently dropped. And: "Reviews test
truth, not only consistency": the wiring page said a Pi 4 "takes the same cable"; the board is an M.2 PCIe card.
Every review brief since carries a claims pass and a hardware fact sheet.

## What the project lead asked for (10 October 2026)

The site's purposes and top level:

> User documentation -- docs for people who are using the fpgas.online website … Admin documentation -- docs for
> people who are running the fpgas.online website … Understanding how the system works; Understanding how to
> maintain the system; Understanding how to setup new sites and devices … Developer documentation … API
> documentation; How the various bits of software are tested; Where to make which type of changes; What software
> packages are used … Resources -- docs which provide raw information and details and external references.
>
> This isn't a comprehensive list of everything the docs should include. It is a starting framework / structure
> that should be built out around. There are lots of good guides and resources on the web about writing /
> creating good documentation. In particular look at the presentations "What nobody tells you about
> documentation". Documentation is a constant evolution and nobody has everything 100% figured out.

The build-guide diagram set:

> When constructing a build guide, there should be multiple diagrams which serve different purposes -- for
> example (and not a complete list): an overview diagram which shows the cable that is being built in the final
> intended configuration / installation position; an overview diagram of cable and its internals; an overview
> diagram showing how the connectors and the various pin functions; step by step diagrams which show how to put
> together the cable; step by step diagrams which show how to verify the cable is wired correctly; step by step
> diagrams which show how to plug in the cable correctly; final diagrams which show what the result should look
> like after each major set of steps; diagrams which show incorrect configurations and common issues that people
> should look out for (putting connectors one too high, swapping uart tx & rx, etc) and how to identify them.

Wiring diagrams:

> It is expected the physical wires will cross when everything is connected -- that is unavoidable. The diagrams
> used in the building guide should be drawn with a focus on clarity and ease of cable construction. The diagrams
> used in a debugging guide should be drawn with a focus on making sure the layout matches reality while still
> trying to be as clear as possible.

Record pages:

> Most of this seems to be terrible and unhelpful. There should be pages which list what is available at various
> sites and what is in the process of being deployed in the future. This should read as "here is what the site
> provides and what the site plans to provide in the future", not an inventory, that is what the dashboards are
> for. There is no reason to keep random history stuff. Bugs / stuff that is broken should be github issues, not
> in the documentation.

Photos: "Find and create new photos from existing items. Use clear line diagrams where no photo will work. Keep
a list of new photos that would be helpful. Make sure these photos are only requested when no existing photo that
fits the purpose can be found on the web." And on finding facts: "Don't be lazy, go look at photos / schematics /
renders of the boards and extract the information. … we should *always* try and have stylized renders (which
only show the relevant details and area clearer / less noisy than photos of real set ups) as well as photos."

Where content lives: "Make sure that the majority of docs are found in the relevant repo *not* in the docs repo.
The docs repo should only have content that doesn't have another repo which is logically where it should be. …
Make sure there is no duplication between content in the docs repo and other repos."

Drifting numbers (3 October, about a CI page whose pytest count went stale in a day): no number that constantly
changes in a document; describe what is checked, link the live value; dated measurements may stay, with their
date and host.

General principles for every deliverable (9 October): finish the thing that was asked for (output that explains
why there is no output is unfinished work; a tool that does not report the data is fixed to report it); values in
tables, sentences in prose; one column, one form; unambiguous icons; tables that behave like tables; reviewers
told in so many words to hunt for shortcuts; fail fast and loud on unexpected results.

## What the site looks like after

- Four top-level sections (User, Admin, Developer, Resources), each a landing page of one line per destination;
  the home page opens with the sections and six "I want to…" paths.
- Each board has one tree: Overview · Which one do I have · Set one up (one sub-tree per host carrier) · Checks ·
  Troubleshooting, one typed page per leaf, the sidebar nested like the index.
- The build guide is split by part: parts list, wires, housing, bench check, fitting, each a how-to with the
  fixed headings, each step with its generated view; the views come from one model by id and are pulled in from
  the owning repository.
- A "Programming an Acorn" explanation keeps protocol, connection and tool apart; "Acorn variants" is a
  reference with a tells table; troubleshooting pages are reference tables of what you see, the cause, the fix.
- The developer section carries "About these docs": the structure, what a page contains (every rule numbered so
  a finding can cite it), how a page is reviewed, the references with quotes, and where each limit comes from.
- A linter fails the build on banned words, over-long titles and sentences, over-long lists, and missing front
  matter; a dark-twin check fails a drawing without its theme pair; a print tool keeps a step and its picture on
  one sheet.
- Record pages, audits and "Sources:" sections are gone; what was still broken became issues; one roadmap page
  carries the plans, each tied to an issue.
- Reviews use the two-pass brief; the merge gate is an independent clean review, green CI on the exact head,
  the head containing main in the merge command, and one procedure followed on the page by someone other than the
  author.
