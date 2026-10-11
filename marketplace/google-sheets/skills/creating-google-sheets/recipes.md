# Sheets API `batchUpdate` recipes

Each request below has been run against a live spreadsheet and checked in a
browser. `G` is the tab's `sheetId`; row and column indexes are 0-based and
end-exclusive. Omit a bound to mean "to the edge of the tab".

Send related requests in **one** `batchUpdate`: it is applied atomically, so
anyone with the sheet open sees a single change.

## Grid: trim and freeze

```python
{"updateSheetProperties": {
    "properties": {"sheetId": G, "gridProperties": {
        "rowCount": n_rows, "columnCount": n_cols, "frozenRowCount": 2}},
    "fields": "gridProperties(rowCount,columnCount,frozenRowCount)"}}
```

## Alignment

```python
# Vertically centre the whole tab; leave horizontal unset so Sheets aligns by type
{"repeatCell": {"range": {"sheetId": G},
    "cell": {"userEnteredFormat": {"verticalAlignment": "MIDDLE"}},
    "fields": "userEnteredFormat.verticalAlignment"}}

# Header over a numeric column, or a centred narrow column
{"repeatCell": {"range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": 2,
                          "startColumnIndex": 2, "endColumnIndex": 3},
    "cell": {"userEnteredFormat": {"horizontalAlignment": "RIGHT"}},   # or "CENTER"
    "fields": "userEnteredFormat.horizontalAlignment"}}
```

## Number formats

```python
{"repeatCell": {"range": {"sheetId": G, "startRowIndex": 2,
                          "startColumnIndex": 2, "endColumnIndex": 3},
    "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}}},
    "fields": "userEnteredFormat.numberFormat"}}
```

`type` is `NUMBER`, `DATE`, `DATE_TIME`, `PERCENT`, `CURRENCY` or `TEXT`.

| Want | Pattern | 1234567.891 shows as |
|---|---|---|
| Integer | `#,##0` | 1,234,568 |
| Two decimals | `#,##0.00` | 1,234,567.89 |
| With a unit | `0.00" mm²"` | 1234567.89 mm² |
| Thousands | `$#,##0,"k"` | $1,235k |
| Millions | `$#,##0.00,,"m"` | $1.23m |
| Percent (value 0.25) | `0.0%` | 25.0% |
| Ratio | `0.0"×"` | 1234567.9× |
| Date | `yyyy-mm-dd` | |
| Date-time | `yyyy-mm-dd hh:mm` | |

Each trailing `,` in a pattern divides by 1,000. The cell still holds the
full number, so sums and ratios stay exact. Use one pattern for the whole
column.

## Zebra stripes

```python
{"addBanding": {"bandedRange": {
    "range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": n_rows,
              "startColumnIndex": 0, "endColumnIndex": n_cols},
    "rowProperties": {
        "headerColor":     {"red": 0.74, "green": 0.74, "blue": 0.74},
        "firstBandColor":  {"red": 1,    "green": 1,    "blue": 1},
        "secondBandColor": {"red": 0.93, "green": 0.93, "blue": 0.93}}}}}
```

`addBanding` over cells that are already banded is rejected ("You cannot add
alternating background colors to a range that already has alternating
background colors"). When rebuilding a tab, list the existing ones
(`sheets.bandedRanges`) and `deleteBanding` each by its `bandedRangeId` first;
that also removes stale stripes left outside the new table.

## Borders

```python
thin  = {"style": "SOLID",        "color": {"red": 0.6, "green": 0.6, "blue": 0.6}}
thick = {"style": "SOLID_MEDIUM", "color": {"red": 0,   "green": 0,   "blue": 0}}

# Box around a table, thin lines between its columns
{"updateBorders": {"range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": n_rows,
                             "startColumnIndex": 0, "endColumnIndex": n_cols},
    "top": thick, "bottom": thick, "left": thick, "right": thick, "innerVertical": thin}}

# Line above a totals row
{"updateBorders": {"range": {"sheetId": G, "startRowIndex": n_rows - 1, "endRowIndex": n_rows,
                             "startColumnIndex": 0, "endColumnIndex": n_cols},
    "top": thick}}
```

A border between two cells is shared: setting B13's right edge and then C13's
left edge leaves only the second (B13's right edge reads back as unset). This
is how a box ends up with one side thinner than the others. Draw a box with
one request over the whole range, and draw outer boxes after inner lines.

## Checkboxes

```python
{"setDataValidation": {"range": {"sheetId": G, "startRowIndex": 2, "endRowIndex": n_rows,
                                 "startColumnIndex": 4, "endColumnIndex": 5},
    "rule": {"condition": {"type": "BOOLEAN"}, "strict": True}}}
```

Write the values as `TRUE` / `FALSE`, and centre the column.

## Merged group header

```python
{"mergeCells": {"range": {"sheetId": G, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 3, "endColumnIndex": 6},
    "mergeType": "MERGE_ALL"}}
```

Freezing columns that contain only part of a merged cell is rejected, so a
merged title or group header limits `frozenColumnCount`. Keep merged cells out of
anything being auto-sized: their whole width is charged to the first column.

## Shortened header that keeps its full name

```python
{"updateCells": {"range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": 2,
                           "startColumnIndex": 1, "endColumnIndex": 2},
    "rows": [{"values": [{"userEnteredValue": {"stringValue": "Ports"},
                          "note": "Number of Ethernet Ports Available"}]}],
    "fields": "userEnteredValue,note"}}

# Wrapped, bold, smaller header row
{"repeatCell": {"range": {"sheetId": G, "startRowIndex": 1, "endRowIndex": 2},
    "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP",
                                   "textFormat": {"bold": True, "fontSize": 9}}},
    "fields": "userEnteredFormat(wrapStrategy,textFormat)"}}
```

## Row heights

```python
{"autoResizeDimensions": {"dimensions": {
    "sheetId": G, "dimension": "ROWS", "startIndex": 0, "endIndex": n_rows}}}
```

Run it after the column widths are final. The API keeps reporting
`pixelSize: 21` for auto-sized rows whatever their rendered height, so the
result can only be checked in the browser.

## Hidden scratch tab

```python
{"duplicateSheet": {"sourceSheetId": G, "newSheetId": SCRATCH, "newSheetName": "~scratch"}},
{"updateSheetProperties": {"properties": {"sheetId": SCRATCH, "hidden": True}, "fields": "hidden"}},
# ... measure or build on SCRATCH ...
{"deleteSheet": {"sheetId": SCRATCH}}
```

Choosing `newSheetId` yourself lets the duplicate and everything done to it
go in the same `batchUpdate`. Always delete scratch tabs, including on error.
