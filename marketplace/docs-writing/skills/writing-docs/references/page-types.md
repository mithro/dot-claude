# Page types: what each one is, and what it looks like

Every page is one of four types, plus the landing page that holds the others together. The type is decided
first, from the reader's need, and it fixes the page's shape. The test for a mixed page: can you name two
different readers who would come to it with different needs? Then it is two pages.

| Type | The reader's need | Answers | Title | Shape |
|---|---|---|---|---|
| Tutorial | a first success | "Can you teach me to…?" | the success it reaches | one safe path, each step with a visible result |
| How-to | one task done | "How do I…?" | "How to <exactly what the page shows>" | fixed headings, numbered steps |
| Reference | a fact looked up | "What is…?" | the thing looked up | a table or list to scan; no steps |
| Explanation | one thing understood | "Why…?" | a noun phrase | prose, one idea per paragraph; no numbered steps |
| Landing | where do I go | | the section | one line per destination, nothing else |

Two cheap leak detectors: a noun-titled page containing numbered imperatives is a how-to hiding in an
explanation; a "How to" page growing sub-headings and background paragraphs is an explanation hiding in a how-to.
"If it's boring and unmemorable it's probably reference; if you can imagine reading it in the bath, it's
explanation" (Diátaxis).

## Every page

- Opens with one to three sentences: what the page covers, for whom, and what it does not cover. A reader
  arrives from search and needs to know within the first paragraph whether this is their page. On a bench page
  this opening can be one bold sentence: "**You have the P1 cable with its wires flagged and crimped, and are
  putting them into their housing. On this page: which wire goes in which cavity, and a meter check of every
  wire.**"
- Carries front matter: type, owner, reader, review date. A page without an owner goes stale; a page without a
  review date is never re-read.
- Is more than links alone and more than two sentences. A page that is only links is a landing page; a page
  that is two sentences is a paragraph on another page.
- Shows its last-modified date linked to the commit, if the site can.
- Leaves a redirect when moved or renamed.

## How-to

The parts are fixed and ordered: prerequisites, steps, verification, error recovery, next. Fixed headings make
a missing part visible: a how-to with no error-recovery part is unfinished by inspection, and a how-to with a
"Background" heading is carrying explanation that belongs on its own page. The headings' names are a *house
decision* made once per site (Red Hat uses Prerequisites · Procedure · Verification · Troubleshooting · Next
steps); the default in this skill, and the one the linter checks, is **What you need · Steps · Check · If it
fails · Next**, in this order and no others.

- **Title**: names the task and nothing else, uniquely, in at most 65 characters. The verb form is a *house
  decision* (Diátaxis: "How to integrate…"; Red Hat: "Integrating…"; Google: "Integrate…"); the default here
  is "How to <exactly what the page shows>". "How to fill the cable's housing (Raspberry Pi 5)", not "Housing"
  and not "Filling housings".
- **What you need**, bench page: every part with its quantity and a picture, and every tool, one line each, so
  it can be checked off at the bench. Software page: only the non-obvious prerequisites, in plain text. Do not
  list what the reader obviously has.
- **Steps**: numbered. Each step is one bullet, one imperative sentence: the place, then the action, then the
  result in the same paragraph. "On the housing's open side, push the **GND** wire into cavity 1 until it
  clicks. The latch is now flush." Where the action happens comes first so the eyes are already there. Bench
  steps carry their picture in the step. Several actions per picture, or several pictures per step, are both
  wrong: one action, one picture. Identical repeated actions are shown in full twice, then collapsed ("Repeat
  for cavities 3 to 8").
- **Check**: what success looks like, pictured or quoted (the meter reading, the command's output, the LED).
- **If it fails**: at the step where it happens, three parts: what you see, the likely cause, the fix. This is
  the one part of a procedure with a measured effect on readers; it is also the part most often left out.
- **Next**: at most five links. Never a second procedure.
- A how-to does not explain. One sentence of purpose before the steps is enough; anything longer links to an
  explanation page. "Explanation is only pertinent at the moment the user wants it. It is not for the
  documentation author to decide."
- A how-to with one step writes it as one sentence in a bulleted list.
- No table in the middle of a procedure; no callout carrying a step or a prerequisite.

### Example: a how-to step page (bench), from docs.fpgas.online

```markdown
---
type: how-to
owner: test-designs maintainers
reader: someone making the JTAG cable for an Acorn on a Raspberry Pi 5
review: 2026-11-10
---

# How to fill the JTAG cable's housing (Raspberry Pi 5)

**You have the P1 cable with its wires flagged and crimped, and are putting them into their housing.
On this page: which wire goes in which cavity, and a meter check of every wire.**

## What you need

- The crimped P1 cable from [How to crimp the JTAG wires](jtag-wires.md).
- 1 × 8-way Pico-EZmate housing ![the 8-way housing, latch side up](views/housing-8.png)
- A multimeter with continuity.

## Steps

1. Hold the housing with its latch window facing you and cavity 1 at the pin-1 triangle. The triangle is
   moulded into the housing beside cavity 1.
   ![housing with the pin-1 triangle marked and cavity 1 highlighted](views/housing-cavity-1.png)
2. Push the **GND** wire's terminal into cavity 1 until it clicks. A gentle pull does not move it.
   ![the GND wire entering cavity 1, arrow for the push](views/housing-gnd.png)
3. Push the **TDI** wire into cavity 2 the same way.
   ![TDI entering cavity 2; GND seated and muted](views/housing-tdi.png)
4. Repeat for **TDO** (3), **TCK** (4) and **TMS** (5).
   ![all five terminals seated, viewed from the latch side](views/housing-full.png)

## Check

Buzz each wire from its terminal to its header pin against the diagram. Every pair reads a short; no other pair does.
![the cable with each wire's cavity and its header pin drawn end to end](views/cable-check.png)

## If it fails

- A terminal pushes back out: the retention tab is flattened. Lift it with a blade until it stands, then push
  the terminal in again.
- Two wires buzz to each other: two terminals touch in one cavity, or a wire is in the wrong cavity. Compare
  the housing with the picture in step 4 and move the wire.

## Next

- [How to check the cable at the bench](bench-check.md)
- [How to fit the cable to the Acorn and the Pi](fitting.md)
```

## Tutorial

The one path from nothing to the first success, for someone who does not yet know what they want. It is
built so that nothing can go wrong; if a step can fail in a way the reader must diagnose, the page is a how-to.
Every step shows its result; the success state is pictured at the top so the reader knows where they are going.
A tutorial does not explain and does not offer choices. It is the most expensive page to keep true, so a site
has few of them, each re-run on every release.

## Reference

A table or list of things to look up: pinouts, part numbers, command flags, error messages, the tells that
distinguish variants. Austere by design: one hardly reads reference, one consults it.

- Generated from source data where the data exists in a file. A hand-typed copy of a pin table is wrong by the
  next commit, and the build should fail when the data changed and the page did not.
- No steps. A reference page that says "then run" is a how-to.
- No prose beyond the scope sentences and one line defining what each column holds ("Tell names what is read,
  Reads is the value it shows, and Identifies is the card it points to").
- A table only when each row has three or more attributes; otherwise a list. No merged cells. No blank cells:
  "none" or "not applicable". One column, one form of value. Headers name the attribute ("Board", "FPGA",
  "DDR3"), not "Name" or "Value".
- Values in cells, never sentences. "its own word at registration, 9 Oct 12:17" is a sentence where a value
  belongs; if the value is missing, that is a fault in the tool that produces it, not a note for the cell.
- Troubleshooting is a reference page: rows of what you see, the likely cause, the fix.

### Example: a troubleshooting reference, from docs.fpgas.online

```markdown
# Acorn wiring faults on a Raspberry Pi 5

**Your Acorn on a Raspberry Pi 5 does not answer on JTAG or on its serial port, and you want the likely cause.**

Each row gives what you see, the likely cause, and the fix.

| Problem | Likely cause | Fix |
|---|---|---|
| `JTAG init failed with: Unable to open gpio chip` | `/dev/gpiochip0` is missing or is not the header's chip | Link it to the chip `sudo gpiodetect` lists as `pinctrl-rp1` |
| No `/dev/ttyAMA0` | RP1 uart0 disabled; `disable-bt` does not enable it on bcm2712 | `[pi5] dtoverlay=uart0-pi5` |
| Pi reboots when a serial design loads | Kernel console on the FPGA UART; SysRq | `console=ttyAMA10` and `kernel.sysrq=0` |
```

## Explanation

Prose that helps a reader understand one thing: how a design reaches the board, why the endpoint is detached
before a load, what the three layers of programming are. A noun title. One idea per paragraph, its opening
sentence carrying it. No numbered steps; an explanation that wants to instruct links the how-to. A diagram
wherever it would replace the longest paragraph; a diagram carries one paragraph's worth of information.

Two special explanations recur on hardware sites:

- **Orientation** (what is this thing): opens with the whole object (photo and render), then a master picture
  whose numbered callouts are the page's sections, each section showing its own crop with the whole as an inset.
- **The layered model** (how it is driven): one page per device, keeping the **protocol** (JTAG, I²C), the
  **connection** (which pins or bus carry it) and the **tool** (the program that drives it) apart, with one
  figure drawn in those three layers. Confusing the tool with the connection ("program it over OpenOCD") leaves
  the reader unable to reason about what talks to what.

## Identification (a reference)

"Which one do I have": the variants side by side, same orientation and scale, the distinguishing feature
marked, and a table of the tells (what to read, what it reads, what that identifies). Photos rather than line
art: readers with low spatial ability need realistic mappings to the actual pieces.

## Landing

One line per destination and nothing else: the destination's name as the link, then what the reader finds
there. "[Variants](which-one.md): which card of the family you have." A landing page that explains, lists
contents twice, or carries notes is doing more than being a traffic cop and is not doing its job. Entries are
ordered as the reader works: what it is, which one I have, set it up, check it, look it up.

## What is not a page

- A dated record of work, an audit, a session log: delete it; anything still broken becomes an issue.
- An FAQ: start from reader needs and no FAQ is needed; each question becomes a how-to or a reference row.
- A "what is coming" section on a reader page: one roadmap page for the site, every item tied to an issue or
  milestone; per-site "what this site provides and plans" pages where a site needs one.
- A plan, a spec, a design note: they live beside the code, not in the reader's tree.
