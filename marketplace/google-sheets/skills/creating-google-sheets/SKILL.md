---
name: creating-google-sheets
description: Use when creating, populating, restructuring, reformatting or tidying a Google Sheets spreadsheet or tab (via the Sheets API, an MCP connector, Apps Script or the browser) - before writing the first cells, and again before reporting the sheet as done. Also when a sheet has clipped or wrapping cells, columns that are too wide or too narrow, numbers stored as text, misaligned decimals, missing borders or striping, or was called ugly, unreadable or badly formatted.
---

# Creating Google Sheets

## Overview

**The data decides the layout; the headers adapt to it.** A column is as wide
as its *values* need. A header that does not fit that width gets wrapped,
shortened or shrunk. Headers **never** set the width.

**The header cell is a label; the note on it is the documentation.** The cell
holds the shortest name that tells the column apart; its note holds the full
name and the description.

**A sheet is not done until it has been looked at in a browser.** API calls
succeeding says nothing about how it renders.

**The structure and formatting carry the meaning** - not explainer text,
legends or paragraphs.

## Order of work

1. **Get the spreadsheet.** A new one is created under the owner's Google
   account, not by a service account (see New spreadsheets). On an existing
   one, read the current contents and formatting first, including any manual
   edits the owner made (see Existing sheets).
2. **Structure** - one fact per cell, one kind of fact per column (see Data).
3. **Write values** with `valueInputOption=USER_ENTERED` so numbers and dates
   become real numbers and dates; derived values as formulas.
4. **Format the data** - one explicit number format per column, alignment.
5. **Title + header rows**, then freeze exactly those rows.
6. **Zebra stripes, borders, emphasis** (see Layout).
7. **Trim** the grid to the used rows and columns.
8. **Size columns from the data**: `sheetcheck.py fit-columns ... --apply`.
9. **Make each header fit** the width its column was given: the shortest
   label in the cell, the full name and description in its note (see
   Headers).
10. **Lint**: `sheetcheck.py lint ...` until it reports 0 findings.
11. **Look at every tab in a browser** (see Visual inspection). Fix, and
    repeat from the step that was wrong.
12. **End with the link** (see Finishing).

Any later change to the data or formats means repeating 8-12.

## Data

| Rule | Wrong | Right |
|---|---|---|
| Cells hold numbers, not text that looks like numbers | `'940 Mbit/s`, `"2 wafers"`, `~$8k` typed as text | the number, with the unit in the number format (`0.00" mm²"`) or the header |
| Dates are dates | `'2026-07-20` (text) | date value, format `yyyy-mm-dd` |
| No lists in a cell | `5, 10, 20, 90`; `af/at/bt` | one column per item (checkbox or tick), or one row per item |
| No paragraphs, no facts buried in text | three sentences in `Notes`; `28 @ $7k` | each fact in its own typed column |
| A label never shares a cell with its number | `Total: 4,200` | label in one cell, number in the next |
| Never mix kinds in a column | numbers and text; actual and predicted; `%` and counts | split into columns, or move the text elsewhere |
| A short value where one will do | `Yes, supported via adapter` | checkbox; detail in a cell note |
| One explicit number format per column | Automatic: `1234.5`, `899`, `7.125` | `#,##0.00`: `1,234.50`, `899.00`, `7.13` |
| One scale and one precision per column, so separators and decimal points line up | `$8k` beside `$7.63m`; `0.0` beside `0.00` | all thousands, or all millions; pick one precision |
| No excess precision | `20.1400 mm²`, `130.91 MTr` | about 2-3 significant figures, never more than the source has |
| Derived values are formulas | a pasted total | `=SUM(...)`, references to the source cells or a source tab |
| Links are links; several in a cell go on separate lines | bare URL text; `a, b, c` | `HYPERLINK`, newline between entries |

Identifiers that only look numeric (serials, phone numbers, zero-padded IDs)
are text: give the column the plain-text format (`numberFormat.type: TEXT`).

Use one consistent order for the same categories everywhere they appear, on
every table and tab, and one consistent short name for each thing.

## Layout

- **Frozen rows contain the sheet title and the header row(s), nothing else.**
  No paragraphs, legend or instructions. Usually 1-2 rows.
- **With frozen columns, the title goes in the first non-frozen column**
  (column B when one column is frozen). Text overflowing out of a frozen
  column is cut off at the freeze line.
- **No explainer text or legends** on the sheet. Put a definition in a cell
  note on the header it explains. If a table needs a paragraph to be
  understood, restructure the table.
- **Always zebra-stripe** every table (`addBanding`), visibly, not subtly.
  No stray banding left over outside a table.
- **A background colour never flattens the stripes.** A cell's own
  background hides the banding beneath it, so one fill colour over several
  rows erases the alternation. Every background you apply - highlight,
  status colour, category tint, conditional format - comes as **two shades
  of the same hue**, a lighter and a darker one, following the same odd/even
  rows as the stripes: rows turned red are light red / darker red, never one
  flat red. Both shades stay clearly that colour, and clearly different from
  each other (see `recipes.md`, Coloured rows that keep their stripes).
- **Borders divide the logical groups**: around each table, between column
  groups, above and around totals. Not a full grid on every cell by default.
  An empty spacer column or row may separate groups; it touches no table.
- **Totals and key results are visually distinct**: bold or larger, bordered.
  Never grey out the value the reader came for.
- **Alignment**: vertical middle everywhere. Text left, numbers and dates
  right, money always right. A narrow column whose values are all short
  (counts of at most two digits, ticks, flags, ratios) may be centred. Never
  mix alignments within a column. A header aligns like its values.
- **Colour means one thing.** Give each category one colour and use it
  everywhere that category appears. Distinguish predicted or estimated values
  from actual ones (text colour), and keep them in separate columns.
- **Row heights fit their contents** - nothing cut off, no rows left tall.
  Aim for rows of one line, two at most: split a wrapping cell into more
  columns (`eth0` / `wlan0`, `type` / `size`) and give notes a smaller font
  before letting rows grow.
- **Fixed-width font** for values compared character by character: serial
  numbers, MAC addresses, hashes, IDs, port names.
- **Rows are in a deliberate order** - the owner's stated sort keys, else the
  natural reading order - and columns too, most important first.
- **Trim**: no empty rows below the data, no empty columns to its right.
- **Tab names** are short, consistent with each other, and say what is on the
  tab.

## Splitting and merging cells

A column can only be one width and one alignment. When the content wants
something else, do not compromise the widths: **split the grid into finer
columns, then merge cells back together** wherever a wider cell is needed.
Reach for this whenever a column is wide only because of a few cells, or
values will not line up.

| Situation | Split into | Merge back |
|---|---|---|
| A composite value: `1,420 × 980 µm`, `200 µm ± 10`, `28 @ $7k`, `36 (90%)` | one column per part, the joiner (`×`, `±`, `@`) in its own narrow centred column | the group header across the parts; any text that replaces the whole value ("not specified") |
| A column that mixes numbers with the odd text cell | - | the text across the neighbouring columns, so the number column keeps the width of its numbers |
| Several tables stacked on one tab, each needing different widths | a grid fine enough for the narrowest column of any table | each table's cells across as many grid columns as its own data needs |
| A label next to a total | label and number in separate cells | the label across the columns to its left |
| A value that belongs to several rows (site, host, group) | - | vertically, down all the rows it applies to |
| A diagram drawn in cells beside a table | rows and columns at the diagram's exact pitch | the table's cells across whole numbers of diagram columns |
| Parts that must look symmetrical | - | set the matching columns to the same width explicitly |

Rules that keep this workable:

- Every number stays a real number in its own cell: right-align the part
  before a joiner, centre the joiner, left-align the part after it.
- Merge within one table only. Never merge across a table's outer border.
- A merged cell is centred or left-aligned over its span on purpose, and its
  text must fit the span: `fit-columns` lists each merged cell with the
  width it needs and the width it has.
- Merged cells break sorting, filtering and freezing across them. Use them in
  headers, labels and presentation tables; keep a tab that people sort or
  that a script reads back as one plain row per record.
- Sheets charges a merged cell's entire width to its *first* column when
  auto-sizing (a long merged title turned a 73px column into 423px in
  testing). `fit-columns` leaves merged cells out when sizing the columns
  they span; never run the UI's "fit to data" over them.
- Measure stacked tables one at a time: `fit-columns --rows FIRST:LAST`, then
  choose grid widths that satisfy all of them.

## Column widths: from the data, never from the header

`autoResizeDimensions` and the UI's "fit to data" both measure the header
along with the data, skip columns whose cells wrap, and mis-measure merged
cells. Do not use them on the real tab. Use the tool in this skill's
directory:

```bash
export GSHEETS_TOKEN_FILE=path/to/key.json   # service-account key, or OAuth authorized-user JSON
uv run sheetcheck.py fit-columns SPREADSHEET_ID_OR_URL --sheet 'Tab name'          # dry run
uv run sheetcheck.py fit-columns SPREADSHEET_ID_OR_URL --sheet 'Tab name' --apply
```

It duplicates the tab into two hidden scratch tabs in a single request,
deletes the header rows from one and the data rows from the other, lets
Sheets measure each, deletes the scratch tabs, and prints per column: the
width the data needs, the width the header would need, the width it will
set, and a verdict for the header. `--header-row N` if the header is not the
last frozen row; `--rows FIRST:LAST` to measure one table. `--max` (default
420px) caps free-text columns: a `CLAMPED` column will wrap, which must be a
decision, not an accident. Bold and larger fonts are measured as formatted,
so apply the formatting first.

Cells merged across columns are left out when sizing those columns and
reported in their own table: the width each one's text needs against the
combined width of the columns it spans. A header merged over several columns
is judged against all of them.

**Widths the owner set by hand win.** If the owner has adjusted columns on a
tab, read the current widths back and keep them (and make them the defaults
in whatever script builds the tab) rather than re-fitting over them.

No way to run the tool (an MCP connector without `batchUpdate`)? Follow the
same method by hand: measure the data rows on a hidden scratch copy with no
header, then set the widths on the real tab.

## Headers: shortest label in the cell, everything else in the note

A header cell and its note are the two halves of one header, and both are
always written:

- **The header cell** holds the shortest label that tells this column apart
  from its neighbours, on **one line** at the width the data gave the
  column: a word, an abbreviation the reader already knows, or the unit
  alone (`W`, `Mbit/s`, `AUD`). Words that the sheet title, a group header
  or the neighbouring columns already imply are dropped.
- **The note** on that header cell holds the full column name on its first
  line, then a blank line, then the description: what the value is, its
  unit, how and when it was measured or where it came from, and any caveat.
  Everything the owner said about the column that is not in the cell goes
  here, so shortening loses nothing. **Every header gets a note**, including
  headers that fit untouched: the note is where the description lives, not a
  fallback for shortened names.

Shrink in this order, stopping as soon as the header fits on one line:

1. **Drop words** the title, group header or neighbours imply:
   `Purchase price in AUD including GST` -> `Price`;
   `Number of Ethernet ports available` -> `Ports`.
2. **Abbreviate, or keep only the unit**: `Power consumption at idle in
   watts` -> `W`. Only abbreviations the reader already knows; never invent
   jargon.
3. **Move the shared part into a merged group header** over the columns that
   share it: `Power (W)` over `idle` and `load`; `Wafers for X chips` over
   `50` and `1,000`.
4. **Wrap** to two lines (`wrapStrategy: WRAP`) when no one-line label tells
   the column apart.
5. **Smaller font** for that header, down to 6pt.
6. **Rotate** the header text for very narrow columns (ticks, flags).
7. Still unreadable? Raise the font size of everything else, so the owner
   can zoom out. The column still does not get wider.

Then re-run `fit-columns` (dry run) until every header reads `fits`, and
`lint` until it reports no `HEADER` findings.

A 40px column of idle power readings, described by the owner as "Power
consumption at idle in watts: read from the smart plug, averaged over 10
minutes with the device idle at the login prompt":

| | Wrong | Right |
|---|---|---|
| Header cell | `Idle W`, wrapped onto two lines | `W` (or `idle` under a merged `Power (W)` group header) |
| Note | none, or `Power consumption at idle in watts` alone | `Power consumption at idle in watts` + blank line + `Read from the smart plug, averaged over 10 minutes with the device idle at the login prompt.` |

## Lint

```bash
uv run sheetcheck.py lint SPREADSHEET_ID_OR_URL [--sheet 'Tab name']
```

Read-only. Reports `TRIM`, `FREEZE`, `STRIPE`, `HEADER` (a header cell with
no note, or whose text cannot fit its column on one line), `TYPE` (numbers,
dates and units stored as text; mixed columns), `FORMAT` (mixed or missing
number formats), `ALIGN` and `PROSE` (paragraphs, delimited lists) findings
with column and row numbers. It assumes one table per tab; on a multi-table tab
read its findings with that in mind. Fix the sheet rather than arguing with a
finding; if one is a genuine false positive, say so in your report.

## Visual inspection (required)

The API cannot tell you how the sheet renders: a row whose cell wraps onto
four lines still reads `pixelSize: 21` from `spreadsheets.get`. Open the
sheet in a browser signed in to the owner's account (browser automation
tools) and look at **every tab you touched**, at 100% zoom:

- Use a large window so as much of the tab as possible is in view; scroll
  right and down for the rest. Do not take over the owner's desktop to do it.
- Click an empty cell first - the selected cell clips its own overflow and
  will look truncated when it is not.
- Screenshot, then zoom into regions to read them.

Check, and fix anything that fails:

- [ ] No data cell is clipped, shows `####`, or wraps when it was not meant to
- [ ] No column is visibly wider than its widest value needs
- [ ] Every header is fully readable inside its column
- [ ] Decimal points and thousands separators line up down each numeric column
- [ ] Alignment is right for each column and never mixed within one
- [ ] Rows are the right height: nothing cut off, nothing needlessly tall
- [ ] Stripes cover exactly each table; no stray formatting beyond it
- [ ] Coloured rows and cells still alternate: two shades, in step with the stripes
- [ ] Every border is where it was intended, same weight on all sides of a box
- [ ] The frozen section is the title + header only, and stays put when scrolling
- [ ] The grid ends where the data ends
- [ ] The numbers themselves are right, not just their styling

For anything beyond a small table, also have a **fresh subagent** open the
sheet in the browser and report layout, formatting and readability problems,
without being told what you think is fine. Fix what it finds and have it look
again.

A PDF or image export is **not** the browser: it paginates and rescales, and
shows neither frozen panes nor overflow as the owner sees them. If no
signed-in browser is available, say plainly that the sheet has not been
visually verified, and what you looked at instead.

## New spreadsheets

**Create the spreadsheet under the owner's Google account, then share it with
the service account** - almost never the other way round. A service account
usually has no Drive storage quota, so its create call fails, and a file it
does manage to create lives in a Drive the owner cannot see.

1. Create the blank spreadsheet as the owner: the owner's OAuth credentials,
   or a Google Drive / Sheets connector signed in as them.
2. Share it with the service account's `client_email` (from its key file) as
   an Editor.
3. Do all further work as the service account, on that one spreadsheet. Record
   its ID where the script that maintains it can find it.

If you cannot create or share it as the owner, or the service account gets a
403 on a sheet it needs, stop and ask the owner to create or share it, giving
them the `client_email`. Do not work around it.

## Existing sheets

- **Reuse the spreadsheet.** Update the same spreadsheet and the same tabs so
  URLs and `gid`s stay stable. Never create a new spreadsheet per run, and
  never delete and re-add a tab to rebuild it: replace its contents.
- **Format in place through the API.** Not by building an `.xlsx` and
  uploading or importing it.
- **Preserve the owner's manual edits.** Read values and formats before
  writing; change only what was asked. If the owner formatted one table or
  tab by hand, that is the style to match on the others.
- **Never leave the sheet blank mid-update.** Build on a hidden scratch tab
  and apply the final change to the visible tab in a single `batchUpdate`.
- Hidden tabs are obsolete unless told otherwise: do not read data from them.
- The work lives in the spreadsheet: charts and summaries are built there,
  not as local images or scripts' console output.
- Images go in cells as real in-cell images, not `=IMAGE()` of an external
  URL. The Sheets API cannot place them; use an Apps Script bound and scoped
  to that one spreadsheet.
- Summaries and totals are live formulas or pivot tables over the data tab,
  so they follow edits the owner makes by hand.

## Finishing

The **last thing** in your final message, every time you finish work on a
spreadsheet, is its full URL on a line of its own:

```
https://docs.google.com/spreadsheets/d/<spreadsheet id>/edit#gid=<tab gid>
```

The complete `https://` link to the tab you worked on - not the ID alone, not
a short link, not "the same link as before", and nothing after it.

## Reference

`recipes.md` in this directory has tested `batchUpdate` requests for: trim +
freeze, alignment, number formats (units, scaled money, percent, dates),
banding, coloured rows that keep their stripes, borders, checkboxes, merged group headers, header notes, row-height
auto-fit and hidden scratch tabs.

## Common mistakes

| Mistake | Fix |
|---|---|
| Auto-resizing the real tab, so a long header or merged title sets the width | `fit-columns`, then make the header fit |
| Widening a column because its header was clipped | Shorten the header; its full name goes in the note |
| Header wrapped onto two lines when a one-word label would do | Shortest label in the cell; the rest in its note |
| Notes only on the headers that were shortened | Every header has a note: full name, then description |
| Description, unit or method typed into the header text | The header is the label; the note is the description |
| All columns left at the default 100px | `fit-columns` on every tab |
| Writing with `RAW`, or prefixing values with `'` | `USER_ENTERED`, then set the number format |
| Units, `~` or "approx" typed into number cells | Number in the cell; unit in the format or header; qualifiers in a note |
| Wide column because one table's text sits above another table's numbers | Split the grid and merge cells |
| `W × H` or `value ± error` typed into one cell | One column per part, joiner in its own column, merged group header |
| Title in A1 with column A frozen, cut off at the freeze line | Title in the first non-frozen column |
| Service account creates the spreadsheet | Owner's account creates it and shares it with the service account |
| Final message ends with a summary and no link | Full `https://docs.google.com/spreadsheets/d/...` URL as the last line |
| Explanatory paragraph or legend above or below the table | Cell notes; restructure so it is not needed |
| Tinted backgrounds replacing the stripes | Stripe first; tints alternate too |
| One flat fill colour (all-red failed rows) over a striped table | Two shades of that colour, alternating with the stripes |
| Clearing a tab and rebuilding it over 30 seconds | Hidden scratch tab, then one `batchUpdate` |
| Reporting "done" after the API calls returned 200 | Lint, then look at it in the browser |
| Checking a PDF export and calling it inspected | Browser, or say it was not visually verified |
| Lint is clean so the browser step is skipped | Lint cannot see clipping, wrapping, borders or row heights |
