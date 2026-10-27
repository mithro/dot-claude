# Style: limits, words, names, numbers, sources, tables, links, callouts

The limits are numbers because most readers read a fifth to a quarter of a page in an F-shaped pattern. A
scanning reader must still find the step. Each limit has a published source; see
[evidence.md](evidence.md).

## Limits

| Item | Limit | Why |
|---|---|---|
| Title | 65 characters, unique | fits a search result and a tab; the reader knows which page they are on |
| Sentence | 25 words | split anything longer |
| Paragraph | 3 to 5 sentences | one idea; many one-sentence paragraphs mean the organisation is faulty |
| List | 2 to 7 items | more than seven cannot be scanned; nest or split |
| Callouts on a page | 2, never next to each other | readers skip them |
| Steps or prerequisites inside a callout | 0 | a skipped callout is a skipped step |
| Links on a page | 15 | more and the page is a list of links |
| "Next" links | 5 | a tail, not a second page |
| Heading levels | 5 | deeper means a new page |
| Entries under one sidebar heading | 7 | more gets sub-headings |
| Alt text | 150 characters | screen readers |
| Printed length of a bench guide | about 4 or 5 A4 sheets with diagrams | more is a second page |

## Words

Banned, because they minimise the reader's difficulty or rot with time:
`just`, `simply`, `easy`, `easily`, `straightforward`, `please note`, `click here`, `currently`, `soon`,
`e.g.`, `i.e.`, `etc.`, `in order to`, `as of this writing`.

Watched, allowed only when not about time: `new`, `now`, `latest`. "A new feature today might not be
considered new in a few months." If you must, give the reference point: "new in version 1.4".

Forbidden phrases on a reader page: `Future:`, `Sources:`, `unverified`, `TODO`, `not yet`, `as read on`.
Each is the author's process showing through. The unknown becomes an issue; the plan goes to the roadmap; the
source becomes a link; the audit goes to the review record.

Plain, emotionless English. No exclamation marks. No "please". If you mean the same thing, use the same word;
a term is explained in plain words at its first use. Headings are not questions: readers want answers.

A mention of a banned word in code or in quotation marks is a mention, not a use; the linter skips those.

## Names

- One name per thing, as printed on the part or shown in the interface. The reader matches what they read to
  what they see.
- Board markings in bold as printed: **GND**, **3V3**, **P1**. "GPIO 4", never "pin 4" (which confuses the
  GPIO number with the header position).
- Pin 1 by its visible marker (the triangle, the square pad, the stripe), never by colour. Directions by a
  visible feature ("the connector nearest the M.2 edge"), never "left", "above" or "on the right-hand side".
- Interface controls in bold, with generic verbs: "select **Add**", not "click the Add button".
- No names of people on a page. Attribution goes in the commit.

## Numbers and dates

- No number that drifts: no test counts ("160 passed"), host counts ("five at Welland"), file counts, role
  counts. Describe what is checked, not how many; link where the reader can see the live value.
- No date except on a fact that is itself dated. A measurement says when it was taken and on what; a page does
  not say "as of October".
- What changes is anchored by a version or an issue number: "since v1.4", "tracked in issue #123", never
  "currently" or "in the current version".
- Day-first or ISO 8601 dates ("29 Nov 2025", "2025-11-29"), never month-first.

## Detail and repetition

- Full detail where the reader acts; summary only where the reader orients. A step page has the pin numbers in
  the step; the overview page says which pages exist.
- A reader following instructions never scrolls to another section or opens another page for something the
  step needs. Repeat the fact in place. Repetition is done by including one source fragment (an include, a
  generated snippet, a view by id) in every place it is needed, so a fix lands everywhere; never by copying text.
- Explanation longer than one sentence of purpose leaves a how-to for an explanation page, linked.

## Sources

A source is one descriptive link in the sentence that needs it, front-loaded with the relevant words:
"a Molex Pico-EZmate 8-way housing ([datasheet](…))", "the bootloader reads `config.txt` first
([Raspberry Pi documentation: boot sequence](…))".

Not allowed: `Sources:` lines, a "Where the facts come from" section, footnotes, superscripts, a "Further
reading" list. Every web style guide rejects footnotes; the audit of which claim came from where belongs in the
review record, not on the page.

## Links

- In context, at the point where the reader needs it. Not collected at the bottom (except the capped "Next").
- Descriptive link text that makes sense out of context: "[How to crimp the JTAG wires](…)", never "here" or
  "this page". The same text never links to two destinations.
- Within a page, link a destination once.
- A link to an outside authority is better than a copy of its content.

## Tables

- A table when each row has three or more attributes; a list otherwise; a single-column table is a list.
- Headers name the attribute. One line before the table says what each column holds.
- Values in cells, sentences in prose. One column, one form: every row formatted the same way. If a value is
  missing, the tool that produces it is wrong; fix the tool, do not write a note in the cell.
- No merged cells, no blank cells ("none", "not applicable"), cells kept to one line where possible.
- Tables of dense identifiers (MAC addresses, serials) are told not to wrap; tables of prose wrap.
- Rendered tables are striped and sortable where the site allows; column widths come from the values, never
  from a long header (shorten the header instead).
- No table in the middle of a numbered procedure.

## Callouts

- At most two per page; never two in a row; never carrying a step, a prerequisite or a cross-reference.
- Write the content as ordinary text first; make it a callout only if it is relevant but not necessary to what
  the reader is doing right now.
- A warning explains the problem, its cause and the fix that works: "Detach the PCIe endpoint before loading a
  bitstream. Reconfiguring the FPGA underneath an enumerated endpoint is a surprise removal and the host
  crashes. The per-host bus address is on …"

## Code and output

- Terminal output is text in a code block, never an image.
- A command block shows the command as typed and the output as seen; a prompt character marks which is which.
- Every code sample is runnable as written; a sample that "never ran as written" is a finding.

## Icons

An icon must be unambiguous without a legend. "…" can mean searching, not found or skipped; if an icon needs
explaining it is the wrong icon. Status is a word or an unambiguous mark (✓, ✗), never a colour alone.
