---
name: creating-google-sheets
description: Use when creating, populating, restructuring, reformatting or tidying a Google Sheets spreadsheet or tab (via the Sheets API, an MCP connector, Apps Script or the browser) - before writing the first cells, and again before reporting the sheet as done. Also when a sheet has clipped or wrapping cells, columns that are too wide or too narrow, numbers stored as text, misaligned decimals, missing borders or striping, or was called ugly, unreadable or badly formatted.
---

# Creating Google Sheets

## Overview

**The data decides the layout; the headers adapt to it.** A column is as wide
as its *values* need. A header that does not fit that width gets wrapped,
shortened or shrunk. Headers **never** set the width.

**A sheet is not done until it has been looked at in a browser.** API calls
succeeding says nothing about how it renders.

**The structure and formatting carry the meaning** - not explainer text,
legends or paragraphs.

## Order of work

1. **Read first.** On an existing spreadsheet read the current contents and
   formatting, including any manual edits the owner made (see Existing sheets).
2. **Structure** - one fact per cell, one kind of fact per column (see Data).
3. **Write values** with `valueInputOption=USER_ENTERED` so numbers and dates
   become real numbers and dates; derived values as formulas.
4. **Format the data** - one explicit number format per column, alignment.
5. **Title + header rows**, then freeze exactly those rows.
6. **Zebra stripes, borders, emphasis** (see Layout).
7. **Trim** the grid to the used rows and columns.
8. **Size columns from the data**: `sheetcheck.py fit-columns ... --apply`.
9. **Make each header fit** the width its column was given (see Headers).
10. **Lint**: `sheetcheck.py lint ...` until it reports 0 findings.
11. **Look at every tab in a browser** (see Visual inspection). Fix, and
    repeat from the step that was wrong.

Any later change to the data or formats means repeating 8-11.

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
- **No explainer text or legends** on the sheet. Put a definition in a cell
  note on the header it explains. If a table needs a paragraph to be
  understood, restructure the table.
- **Always zebra-stripe** every table (`addBanding`), visibly, not subtly.
  Highlighted or colour-coded rows still alternate (light / lighter tint).
  No stray banding left over outside a table.
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
- **Trim**: no empty rows below the data, no empty columns to its right.
- **Tab names** are short, consistent with each other, and say what is on the
  tab.

### Several tables on one tab

Tables stacked on one tab share its columns, so one table's widths wreck
another's. Mixed content is not an excuse for wrong widths: **split the grid
into finer columns and merge cells** so every table gets the widths its own
data needs. Measure each table on its own with `fit-columns --rows FIRST:LAST`.

Sheets charges a merged cell's entire width to its *first* column when
auto-sizing (a long merged title turned a 73px column into 423px in testing),
so merged cells must be kept out of whatever is being measured.

## Column widths: from the data, never from the header

`autoResizeDimensions` and the UI's "fit to data" both measure the header
along with the data, skip columns whose cells wrap, and mis-measure merged
cells. Do not use them on the real tab. Use the tool in this skill's
directory:

```bash
export GSHEETS_TOKEN_FILE=path/to/oauth-authorized-user.json   # scope: spreadsheets
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

Other credentials (a service account, an MCP connector without
`batchUpdate`): follow the same method by hand - measure the data rows on a
hidden scratch copy with no header, then set the widths on the real tab.

## Headers: fit the column you were given

For every header the tool does not mark `fits`, in this order of preference:

1. **Wrap** on word boundaries (`wrapStrategy: WRAP`), up to 2-3 lines.
2. **Drop words** the title, group header or neighbours already imply:
   `Purchase Price (AUD)` -> `Price (AUD)`; `Number of Ethernet Ports Available` -> `Ports`.
   A merged group header over several columns ("Wafers for X chips") lets
   each column header shrink to its distinguishing value (`50`, `1,000`).
3. **Abbreviate**, using an abbreviation the reader already knows. A unit
   alone is a fine header (`Mbit/s`). Never invent jargon.
4. **Smaller font** for that header, down to 6pt.
5. **Rotate** the header text for very narrow columns (ticks, flags).
6. Still too small to read? Raise the font size of everything else, so the
   owner can zoom out. The column still does not get wider.

Whenever the visible header loses information, put the full name in a **cell
note** on the header. Then re-run `fit-columns` (dry run): every header should
read `fits` or the wrap you intended.

## Lint

```bash
uv run sheetcheck.py lint SPREADSHEET_ID_OR_URL [--sheet 'Tab name']
```

Read-only. Reports `TRIM`, `FREEZE`, `STRIPE`, `TYPE` (numbers, dates and
units stored as text; mixed columns), `FORMAT` (mixed or missing number
formats), `ALIGN` and `PROSE` (paragraphs, delimited lists) findings with
column and row numbers. It assumes one table per tab; on a multi-table tab
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

## Existing sheets

- **Reuse the spreadsheet.** Update the same spreadsheet and the same tabs so
  URLs and `gid`s stay stable. Never create a new spreadsheet per run.
- **Preserve the owner's manual edits.** Read values and formats before
  writing; change only what was asked. If the owner formatted one table or
  tab by hand, that is the style to match on the others.
- **Never leave the sheet blank mid-update.** Build on a hidden scratch tab
  and apply the final change to the visible tab in a single `batchUpdate`.
- Hidden tabs are obsolete unless told otherwise: do not read data from them.
- The work lives in the spreadsheet: charts and summaries are built there,
  not as local images or scripts' console output.
- Images go in cells as real in-cell images, not `=IMAGE()` of an external URL.

## Reference

`recipes.md` in this directory has tested `batchUpdate` requests for: trim +
freeze, alignment, number formats (units, scaled money, percent, dates),
banding, borders, checkboxes, merged group headers, header notes, row-height
auto-fit and hidden scratch tabs.

## Common mistakes

| Mistake | Fix |
|---|---|
| Auto-resizing the real tab, so a long header or merged title sets the width | `fit-columns`, then make the header fit |
| Widening a column because its header was clipped | Wrap / shorten / shrink the header instead |
| All columns left at the default 100px | `fit-columns` on every tab |
| Writing with `RAW`, or prefixing values with `'` | `USER_ENTERED`, then set the number format |
| Units, `~` or "approx" typed into number cells | Number in the cell; unit in the format or header; qualifiers in a note |
| Wide column because one table's text sits above another table's numbers | Split the grid and merge cells |
| Explanatory paragraph or legend above or below the table | Cell notes; restructure so it is not needed |
| Tinted backgrounds replacing the stripes | Stripe first; tints alternate too |
| Clearing a tab and rebuilding it over 30 seconds | Hidden scratch tab, then one `batchUpdate` |
| Reporting "done" after the API calls returned 200 | Lint, then look at it in the browser |
| Checking a PDF export and calling it inspected | Browser, or say it was not visually verified |
| Lint is clean so the browser step is skipped | Lint cannot see clipping, wrapping, borders or row heights |
