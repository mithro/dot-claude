---
name: creating-google-sheets
description: Use when creating, populating, restructuring, reformatting or tidying a Google Sheets spreadsheet or tab (via the Sheets API, an MCP connector, Apps Script or the browser) - before writing the first cells, and again before reporting the sheet as done. Also when a sheet has clipped or wrapping cells, columns that are too wide or too narrow, numbers stored as text, or misaligned decimals.
---

# Creating Google Sheets

## Overview

**The data decides the layout; the headers adapt to it.** A column is as wide
as its *values* need. A header that does not fit that width gets wrapped,
shortened or shrunk - the column is never widened for it.

**A sheet is not done until you have looked at it in a browser.** API calls
succeeding says nothing about how it renders.

## Order of work

Work in this order; the later steps depend on the earlier ones.

1. **Structure** - one fact per cell, one kind of fact per column (see Data).
2. **Write values** with `valueInputOption=USER_ENTERED` so numbers and dates
   become real numbers and dates.
3. **Format the data** - one explicit number format per column, alignment.
4. **Title + header rows**, then freeze exactly those rows.
5. **Zebra stripes** over the header + data range.
6. **Trim** the grid to the used rows and columns.
7. **Size columns from the data**: `sheetcheck.py fit-columns ... --apply`.
8. **Make each header fit** the width its column was given (see Headers).
9. **Lint**: `sheetcheck.py lint ...` until it reports 0 findings.
10. **Look at every tab in a browser** (see Visual inspection). Fix, and
    repeat from the step that was wrong.

Any later edit to the data (new rows, new formats) means repeating 7-10.

## Data

| Rule | Wrong | Right |
|---|---|---|
| Cells hold numbers, not text that looks like numbers | `'940 Mbit/s`, `"12 GB"`, `'42` | `940` under a `Mbit/s` header, or a number format with the unit |
| Dates are dates | `'2026-07-20` (text) | date value, format `yyyy-mm-dd` |
| No lists in a cell | `5, 10, 20, 90` | one column per item, or one row per item |
| No paragraphs in a cell | three sentences in `Notes` | the facts split into their own columns; at most a short phrase left over |
| One explicit number format for the whole column | Automatic: `1234.5`, `899`, `7.125` | `#,##0.00`: `1,234.50`, `899.00`, `7.13` |
| Same precision down a column, so thousands commas and decimal points line up | mixed `0.0` / `0.00` | pick one |
| Text left, numbers right, everything vertically centred | Sheets' default is bottom-aligned | `verticalAlignment: MIDDLE` on the whole tab; leave horizontal unset so Sheets aligns by type |

Identifiers that only look numeric (serials, phone numbers, zero-padded IDs)
are text: give the column the plain-text format (`numberFormat.type: TEXT`).

Explanations, methodology and caveats go on a separate notes tab or in cell
notes - not in the data columns and not in the frozen rows.

## Layout

- **Frozen rows contain the sheet title and the header row(s), nothing else.**
  No paragraphs, no legend, no instructions. Usually 1-2 rows.
- **Always zebra-stripe** the data (`addBanding`), header row included.
- **Trim**: no empty rows below the data, no empty columns to its right.
- A header sits over its values: right-align headers of numeric columns.
- Put a long title in one cell and let it overflow to the right.

## Column widths: from the data, never from the header

`autoResizeDimensions` and the UI's "fit to data" both measure the header
along with the data, and both skip columns whose cells wrap. Do not use them
on the real tab. Use the tool in this skill's directory:

```bash
export GSHEETS_TOKEN_FILE=path/to/oauth-authorized-user.json   # scope: spreadsheets
uv run sheetcheck.py fit-columns SPREADSHEET_ID_OR_URL --sheet 'Tab name'          # dry run
uv run sheetcheck.py fit-columns SPREADSHEET_ID_OR_URL --sheet 'Tab name' --apply
```

It duplicates the tab twice into scratch tabs, deletes the header rows from
one and the data rows from the other, lets Sheets measure each, deletes the
scratch tabs, and prints per column: the width the data needs, the width the
header would need, the width it will set, and a verdict for the header.
`--header-row N` if the header is not the last frozen row. `--max` (default
420px) caps free-text columns; a `CLAMPED` column wraps, which should be a
decision, not an accident.

## Headers: fit the column you were given

For every header the tool does not mark `fits`, in this order of preference:

1. **Wrap** on word boundaries (`wrapStrategy: WRAP`), up to 2-3 lines.
2. **Drop words** the title or neighbouring columns already imply:
   `Purchase Price (AUD)` -> `Price (AUD)`; `Number of Ethernet Ports Available` -> `Ports`.
3. **Abbreviate** with a standard abbreviation; a unit alone is a fine header
   (`Mbit/s`).
4. **Smaller font** for the header row, not below 8pt.
5. **Rotate** the header text for very narrow columns (checkboxes, flags).

Whenever the visible header loses information, put the full name in a **cell
note** on the header. Then re-run `fit-columns` (dry run): every header should
read `fits` or the wrap you intended.

## Lint

```bash
uv run sheetcheck.py lint SPREADSHEET_ID_OR_URL [--sheet 'Tab name']
```

Read-only. Reports `TRIM`, `FREEZE`, `STRIPE`, `TYPE` (numbers/dates/units
stored as text), `FORMAT` (mixed or missing number formats), `ALIGN` and
`PROSE` (paragraphs, delimited lists) findings with column and row numbers.
Fix the sheet rather than arguing with a finding; if one is a genuine false
positive, say so in your report.

## Visual inspection (required)

The API cannot tell you how the sheet renders: a row whose cell wraps onto
four lines still reads `pixelSize: 21` from `spreadsheets.get`. Open the
sheet in a browser signed in to the owner's account (browser automation
tools) and look at **every tab you touched**, at 100% zoom:

- Click an empty cell first - the selected cell clips its own overflow and
  will look truncated when it is not.
- Screenshot, and zoom into regions; scroll right and down on tabs larger
  than the window.

Check, and fix anything that fails:

- [ ] No data cell is clipped, shows `####`, or wraps when it was not meant to
- [ ] No column is visibly wider than its widest value needs
- [ ] Every header is fully readable inside its column
- [ ] Decimal points and thousands separators line up down each numeric column
- [ ] Numbers and dates are right-aligned, text left-aligned, all vertically centred
- [ ] Stripes cover exactly the data; no stray formatting beyond it
- [ ] The frozen section is the title + header only, and stays put when scrolling
- [ ] The grid ends where the data ends

If no signed-in browser is available, say that the sheet has **not** been
visually verified. Do not describe it as checked.

## Request recipes (Sheets API `batchUpdate`)

`G` is the tab's sheetId; row/column indexes are 0-based, end-exclusive.

```python
# Trim the grid and freeze the title + header rows
{"updateSheetProperties": {
    "properties": {"sheetId": G, "gridProperties": {
        "rowCount": n_rows, "columnCount": n_cols, "frozenRowCount": 2}},
    "fields": "gridProperties(rowCount,columnCount,frozenRowCount)"}}

# Vertically centre the whole tab
{"repeatCell": {"range": {"sheetId": G},
    "cell": {"userEnteredFormat": {"verticalAlignment": "MIDDLE"}},
    "fields": "userEnteredFormat.verticalAlignment"}}

# One number format for a column's data rows (types: NUMBER, DATE, PERCENT, CURRENCY, TEXT)
{"repeatCell": {"range": {"sheetId": G, "startRowIndex": 2,
                          "startColumnIndex": 2, "endColumnIndex": 3},
    "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}}},
    "fields": "userEnteredFormat.numberFormat"}}

# Zebra stripes over header + data
{"addBanding": {"bandedRange": {
    "range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": n_rows,
              "startColumnIndex": 0, "endColumnIndex": n_cols},
    "rowProperties": {
        "headerColor":     {"red": 0.74, "green": 0.74, "blue": 0.74},
        "firstBandColor":  {"red": 1,    "green": 1,    "blue": 1},
        "secondBandColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}}}}

# Shortened header that keeps its full name in a note
{"updateCells": {"range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": 2,
                           "startColumnIndex": 1, "endColumnIndex": 2},
    "rows": [{"values": [{"userEnteredValue": {"stringValue": "Ports"},
                          "note": "Number of Ethernet Ports Available"}]}],
    "fields": "userEnteredValue,note"}}
```

Common patterns: integers `#,##0`; money `#,##0.00`; percent `0.0%`; dates
`yyyy-mm-dd`; date-times `yyyy-mm-dd hh:mm`.

## Common mistakes

| Mistake | Fix |
|---|---|
| Auto-resizing the real tab, so a long header sets the width | `fit-columns`, then make the header fit |
| Widening a column because its header was clipped | Wrap / shorten / shrink the header instead |
| Writing with `RAW`, or prefixing values with `'` | `USER_ENTERED`, then set the number format |
| Units, `~`, or "approx" typed into number cells | Number in the cell; unit in the header or format; qualifiers in a note |
| Explanatory paragraph in the rows above the header | Notes tab or cell note; freeze only title + header |
| Reporting "done" after the API calls returned 200 | Lint, then look at it in the browser |
| Lint is clean so the browser step is skipped | Lint cannot see clipping or wrapping |
