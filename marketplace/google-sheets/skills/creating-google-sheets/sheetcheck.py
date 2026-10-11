#!/usr/bin/env python3
# /// script
# dependencies = ["requests", "google-auth"]
# ///
"""
Mechanical checks for Google Sheets layout (companion to the
creating-google-sheets skill).

    uv run sheetcheck.py lint        SPREADSHEET [--sheet NAME | --gid N]
    uv run sheetcheck.py fit-columns SPREADSHEET  --sheet NAME [--apply]

SPREADSHEET is a spreadsheet ID or any docs.google.com/spreadsheets URL.

Auth: --token-file or $GSHEETS_TOKEN_FILE naming either a service-account
key (the spreadsheet must be shared with its client_email as an editor) or an
OAuth "authorized user" JSON (client_id, client_secret, refresh_token) with
the `spreadsheets` scope; or a ready-made access token in
$GSHEETS_ACCESS_TOKEN.

`lint` is read-only. `fit-columns` measures on temporary duplicates of the
tab (deleted again before it exits) and only changes the real tab's column
widths, and only with --apply.
"""

import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

import requests

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"

DEFAULT_ROW_PX = 21
MAX_MERGES = 150      # merged cells measured individually per run


# --------------------------------------------------------------------------
# Auth + REST plumbing
# --------------------------------------------------------------------------

def get_access_token(token_file: str | None) -> str:
    token = os.environ.get("GSHEETS_ACCESS_TOKEN")
    if token:
        return token
    token_file = token_file or os.environ.get("GSHEETS_TOKEN_FILE")
    if not token_file:
        sys.exit("No credentials: pass --token-file, or set GSHEETS_TOKEN_FILE "
                 "or GSHEETS_ACCESS_TOKEN.")
    creds = json.loads(Path(token_file).expanduser().read_text())
    if creds.get("type") == "service_account":
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        sa = service_account.Credentials.from_service_account_info(
            creds, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        sa.refresh(Request())
        return sa.token
    resp = requests.post(creds.get("token_uri", "https://oauth2.googleapis.com/token"), data={
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "grant_type": "refresh_token",
    })
    if resp.status_code != 200:
        sys.exit(f"Token refresh failed: {resp.status_code}\n{resp.text}")
    return resp.json()["access_token"]


class Sheets:
    def __init__(self, spreadsheet: str, token: str):
        m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", spreadsheet)
        self.id = m.group(1) if m else spreadsheet
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, fields: str, ranges: list[str] | None = None, grid: bool = False) -> dict:
        params = {"fields": fields}
        if ranges:
            params["ranges"] = ranges
        if grid:
            params["includeGridData"] = "true"
        resp = requests.get(f"{SHEETS_API}/{self.id}", headers=self.headers, params=params)
        if resp.status_code != 200:
            hint = ("\nIs the spreadsheet shared with the account these credentials belong to?"
                    if resp.status_code in (403, 404) else "")
            sys.exit(f"spreadsheets.get failed: {resp.status_code}\n{resp.text}{hint}")
        return resp.json()

    def batch_update(self, reqs: list[dict]) -> dict:
        resp = requests.post(f"{SHEETS_API}/{self.id}:batchUpdate", headers=self.headers,
                             json={"requests": reqs})
        if resp.status_code != 200:
            raise RuntimeError(f"batchUpdate failed: {resp.status_code}\n{resp.text}")
        return resp.json()

    def sheet_properties(self) -> list[dict]:
        return [s["properties"] for s in self.get("sheets.properties")["sheets"]]

    def find_sheet(self, name: str | None, gid: int | None) -> dict:
        props = self.sheet_properties()
        for p in props:
            if (name is not None and p["title"] == name) or (gid is not None and p["sheetId"] == gid):
                return p
        titles = ", ".join(repr(p["title"]) for p in props)
        sys.exit(f"No such tab (name={name!r}, gid={gid}). Tabs: {titles}")


def col_letter(index: int) -> str:
    """0-based column index -> A1 letter(s)."""
    out = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


def quote_title(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


# --------------------------------------------------------------------------
# fit-columns
# --------------------------------------------------------------------------

def measure_widths(sheets: Sheets, props: dict, header_row: int, data_first: int, data_last: int,
                   merges: list[dict]) -> tuple[list[int], list[int], list[int]]:
    """Return (data_widths, header_widths, merge_widths) in pixels, measured by Sheets itself.

    autoResizeDimensions has no way to ignore the header row, so measure on
    throwaway duplicates of the tab: one with everything down to the header row
    deleted (data only) and one with everything except the header row deleted.
    Rows are 1-based; the data rows measured are data_first..data_last inclusive.

    `merges` are the multi-column merged ranges inside the data rows. Sheets
    charges a merged cell's whole width to its first column, so they are blanked
    on the data copy (the columns are then sized by their unmerged values) and
    each one is measured on its own in a third scratch tab.

    The scratch tabs are hidden and built in one batchUpdate, so people with the
    spreadsheet open never see them.
    """
    sheet_id = props["sheetId"]
    grid = props["gridProperties"]
    rows, cols = grid["rowCount"], grid["columnCount"]
    if not header_row < data_first <= data_last <= rows:
        sys.exit(f"Nothing to measure: header row {header_row}, data rows {data_first}-{data_last}, "
                 f"tab has {rows} rows.")

    data_id = random.randrange(10**8, 2 * 10**9)
    head_id, merge_id = data_id + 1, data_id + 2
    tag = f"{data_id:x}"

    def unfreeze(sid):
        return {"updateSheetProperties": {
            "properties": {"sheetId": sid, "hidden": True, "gridProperties": {"frozenRowCount": 0}},
            "fields": "hidden,gridProperties.frozenRowCount"}}

    def delete_rows(sid, start, end):
        return {"deleteDimension": {"range": {
            "sheetId": sid, "dimension": "ROWS", "startIndex": start, "endIndex": end}}}

    def autosize(sid, n_cols=cols):
        return {"autoResizeDimensions": {"dimensions": {
            "sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": n_cols}}}

    def unwrap(sid):
        # autoResize leaves a column alone when its cells wrap, so measure the
        # natural single-line width whatever the current wrap setting is.
        return {"repeatCell": {"range": {"sheetId": sid},
                               "cell": {"userEnteredFormat": {"wrapStrategy": "OVERFLOW_CELL"}},
                               "fields": "userEnteredFormat.wrapStrategy"}}

    reqs = [
        {"duplicateSheet": {"sourceSheetId": sheet_id, "newSheetId": data_id,
                            "newSheetName": f"~fit-data-{tag}"}},
        unfreeze(data_id),
        # Blank the merged cells (no "rows" given = clear) while the row numbers still match.
        *[{"updateCells": {"range": {**m, "sheetId": data_id}, "fields": "userEnteredValue"}} for m in merges],
        *([delete_rows(data_id, data_last, rows)] if data_last < rows else []),
        delete_rows(data_id, 0, data_first - 1),
        unwrap(data_id),
        autosize(data_id),

        {"duplicateSheet": {"sourceSheetId": sheet_id, "newSheetId": head_id,
                            "newSheetName": f"~fit-head-{tag}"}},
        unfreeze(head_id),
        delete_rows(head_id, header_row, rows),
    ]
    if header_row > 1:
        reqs.append(delete_rows(head_id, 0, header_row - 1))
    reqs += [
        {"unmergeCells": {"range": {"sheetId": head_id}}},
        unwrap(head_id),
        autosize(head_id),
    ]

    # One slot of columns per merged cell, so each gets its own measured width.
    offsets, total = [], 0
    for m in merges:
        offsets.append(total)
        total += m["endColumnIndex"] - m["startColumnIndex"]
    if merges:
        reqs.append({"addSheet": {"properties": {
            "sheetId": merge_id, "title": f"~fit-merge-{tag}", "hidden": True,
            "gridProperties": {"rowCount": 1, "columnCount": total}}}})
        for m, off in zip(merges, offsets):
            anchor = {"sheetId": sheet_id,
                      "startRowIndex": m["startRowIndex"], "endRowIndex": m["startRowIndex"] + 1,
                      "startColumnIndex": m["startColumnIndex"], "endColumnIndex": m["startColumnIndex"] + 1}
            dest = {"sheetId": merge_id, "startRowIndex": 0, "endRowIndex": 1,
                    "startColumnIndex": off, "endColumnIndex": off + 1}
            # Values, not formulas: a formula pasted elsewhere would compute something else.
            for paste in ("PASTE_VALUES", "PASTE_FORMAT"):
                reqs.append({"copyPaste": {"source": anchor, "destination": dest, "pasteType": paste}})
        reqs += [{"unmergeCells": {"range": {"sheetId": merge_id}}}, unwrap(merge_id), autosize(merge_id, total)]

    scratch = [data_id, head_id] + ([merge_id] if merges else [])
    try:
        sheets.batch_update(reqs)
        meta = sheets.get("sheets(properties.sheetId,data.columnMetadata.pixelSize)",
                          ranges=[f"~fit-data-{tag}", f"~fit-head-{tag}"]
                          + ([f"~fit-merge-{tag}"] if merges else []), grid=True)
    finally:
        # Never leave the scratch tabs behind, whatever went wrong above.
        existing = {p["sheetId"] for p in sheets.sheet_properties()}
        cleanup = [{"deleteSheet": {"sheetId": sid}} for sid in scratch if sid in existing]
        if cleanup:
            sheets.batch_update(cleanup)

    widths = {}
    for s in meta["sheets"]:
        widths[s["properties"]["sheetId"]] = [
            c.get("pixelSize", 100) for c in s["data"][0].get("columnMetadata", [])]
    merge_px = [widths[merge_id][off] for off in offsets] if merges else []
    return widths[data_id], widths[head_id], merge_px


def header_verdict(header: str, header_px: int, width: int) -> str:
    if not header.strip():
        return ""
    if header_px <= width:
        return "fits"
    # Rough per-character scaling of the measured single-line width.
    px_per_char = header_px / max(len(header), 1)
    words = header.split()
    longest_word_px = max(len(w) for w in words) * px_per_char
    if len(words) > 1 and longest_word_px <= width:
        lines = -(-header_px // width) + (1 if len(words) > 2 else 0)
        if lines <= 3:
            return f"WRAP header (~{min(lines, len(words))} lines)"
    fit_chars = int(width / px_per_char)
    return f"SHORTEN header to <= ~{fit_chars} chars/line (or smaller font / rotate)"


def a1_range(m: dict) -> str:
    return (f"{col_letter(m['startColumnIndex'])}{m['startRowIndex'] + 1}:"
            f"{col_letter(m['endColumnIndex'] - 1)}{m['endRowIndex']}")


def cmd_fit_columns(args) -> int:
    sheets = Sheets(args.spreadsheet, get_access_token(args.token_file))
    props = sheets.find_sheet(args.sheet, args.gid)
    frozen = props["gridProperties"].get("frozenRowCount", 0)
    header_row = args.header_row or frozen or 1
    title = props["title"]

    data_first, data_last = header_row + 1, props["gridProperties"]["rowCount"]
    if args.rows:
        data_first, data_last = (int(x) for x in args.rows.split(":"))

    current = sheets.get("sheets(merges,data(columnMetadata.pixelSize,rowData.values(formattedValue,"
                         "effectiveFormat.wrapStrategy)))", ranges=[quote_title(title)], grid=True)
    data0 = current["sheets"][0]["data"][0]
    cur_px = [c.get("pixelSize", 100) for c in data0.get("columnMetadata", [])]
    all_rows = [r.get("values", []) for r in data0.get("rowData", [])]

    def text_at(r, c):
        return all_rows[r][c].get("formattedValue", "") if r < len(all_rows) and c < len(all_rows[r]) else ""

    wide = [m for m in current["sheets"][0].get("merges", [])
            if m["endColumnIndex"] - m["startColumnIndex"] > 1]
    # Merged cells with text inside the measured rows, and merged headers by their first column.
    merges = [m for m in wide if data_first - 1 <= m["startRowIndex"] < data_last
              and text_at(m["startRowIndex"], m["startColumnIndex"])][:MAX_MERGES]
    header_span = {m["startColumnIndex"]: m["endColumnIndex"] for m in wide
                   if m["startRowIndex"] <= header_row - 1 < m["endRowIndex"]}
    in_merge = {(r, c) for m in merges for r in range(m["startRowIndex"], m["endRowIndex"])
                for c in range(m["startColumnIndex"], m["endColumnIndex"])}

    data_px, head_px, merge_px = measure_widths(sheets, props, header_row, data_first, data_last, merges)

    def body_cells(i):
        return [all_rows[r][i] for r in range(data_first - 1, min(data_last, len(all_rows)))
                if (r, i) not in in_merge and i < len(all_rows[r]) and all_rows[r][i].get("formattedValue")]

    # First pass: the width each column gets (columns with no unmerged data keep their width).
    final, sized = list(cur_px), {}
    for i, measured in enumerate(data_px):
        if body_cells(i):
            sized[i] = measured + args.pad
            final[i] = max(args.min, min(args.max, sized[i]))

    print(f"Tab {title!r}: header row {header_row}, sizing columns from data rows "
          f"{data_first}-{data_last} only (pad {args.pad}px, min {args.min}px, max {args.max}px)\n")
    print(f"{'Col':<4}{'Header':<28}{'Now':>5}{'Data':>6}{'Hdr':>6}{'New':>6}  Verdict")
    updates = []
    for i, measured in enumerate(data_px):
        header = text_at(header_row - 1, i)
        shown = header.replace("\n", " ")
        shown = shown if len(shown) <= 26 else shown[:25] + "…"
        # A header merged over several columns has all of their widths to fit in.
        end = header_span.get(i, i + 1)
        span = f" (merged over {col_letter(i)}:{col_letter(end - 1)})" if end > i + 1 else ""
        # No pad here: a header measured at N px renders on one line in an N px column.
        verdict = header_verdict(header, head_px[i], sum(final[i:end]))
        if i not in sized:
            if header.strip():
                print(f"{col_letter(i):<4}{shown:<28}{cur_px[i]:>5}{'':>6}{head_px[i]:>6}{'':>6}  "
                      f"no unmerged data: width left alone; {verdict}{span}")
            continue
        notes = []
        wraps = any(c.get("effectiveFormat", {}).get("wrapStrategy") == "WRAP" for c in body_cells(i))
        if sized[i] > args.max:
            notes.append(f"data CLAMPED (longest value needs {sized[i]}px): "
                         + ("wraps" if wraps else "set WRAP on this column on purpose")
                         + ", or split the text into more columns")
        elif wraps:
            notes.append("has WRAP cells that now fit on one line")
        if verdict:
            notes.append(verdict + span)
        print(f"{col_letter(i):<4}{shown:<28}{cur_px[i]:>5}{measured:>6}{head_px[i]:>6}{final[i]:>6}  "
              f"{'; '.join(notes)}")
        updates.append({"updateDimensionProperties": {
            "range": {"sheetId": props["sheetId"], "dimension": "COLUMNS",
                      "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": final[i]}, "fields": "pixelSize"}})

    if merges:
        print(f"\nMerged cells in the data rows (left out when sizing the columns they span):\n"
              f"{'Range':<12}{'Text':<28}{'Needs':>6}{'Has':>6}  Verdict")
        for m, need in zip(merges, merge_px):
            text = text_at(m["startRowIndex"], m["startColumnIndex"]).replace("\n", " ")
            text = text if len(text) <= 26 else text[:25] + "…"
            has = sum(final[m["startColumnIndex"]:m["endColumnIndex"]])
            verdict = "fits" if need <= has else (f"{need - has}px TOO WIDE: wrap or shorten the text, "
                                                  f"or merge it over more columns")
            print(f"{a1_range(m):<12}{text:<28}{need:>6}{has:>6}  {verdict}")

    if args.apply:
        sheets.batch_update(updates)
        print(f"\nApplied {len(updates)} column widths. Now fix every header and merged cell that is "
              f"not 'fits', then look at the tab in a browser.")
    else:
        print("\nDry run: nothing changed. Re-run with --apply to set the 'New' widths.")
    return 0


# --------------------------------------------------------------------------
# lint
# --------------------------------------------------------------------------

NUMBER_AS_TEXT = re.compile(r"^\s*[-+]?[$€£]?\s?\d[\d,]*(\.\d+)?\s*%?\s*$")
NUMBER_WITH_UNIT = re.compile(r"^\s*[-+~]?[$€£]?\d[\d,]*(\.\d+)?\s*[A-Za-zµ°Ω/%]{1,6}\s*$")
DATE_AS_TEXT = re.compile(r"^\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})(\b.*)?$")
LIST_SEPARATOR = re.compile(r",\s|;\s|\s/\s|\n")

LINT_FIELDS = (
    "sheets(properties,merges,bandedRanges.range,conditionalFormats.booleanRule.condition,"
    "data(columnMetadata(pixelSize,hiddenByUser),rowMetadata(pixelSize,hiddenByUser,hiddenByFilter),"
    "rowData.values(formattedValue,effectiveValue,"
    "effectiveFormat(numberFormat,horizontalAlignment,verticalAlignment,wrapStrategy))))"
)


def has_striping(sheet: dict) -> bool:
    if sheet.get("bandedRanges"):
        return True
    for rule in sheet.get("conditionalFormats", []):
        for value in rule.get("booleanRule", {}).get("condition", {}).get("values", []):
            formula = value.get("userEnteredValue", "").upper().replace(" ", "")
            if "ROW()" in formula and any(f in formula for f in ("ISEVEN", "ISODD", "MOD(")):
                return True
    return False


def decimals_of(formatted: str) -> int | None:
    m = re.search(r"\d(?:[\d,]*)(?:\.(\d+))?", formatted)
    if not m:
        return None
    return len(m.group(1) or "")


def lint_sheet(sheet: dict, header_row_arg: int | None) -> list[str]:
    props = sheet["properties"]
    grid = props.get("gridProperties", {})
    data = (sheet.get("data") or [{}])[0]
    rows = [r.get("values", []) for r in data.get("rowData", [])]
    row_meta = data.get("rowMetadata", [])  # explicit heights only: auto-grown rows still read 21
    findings = []

    frozen = grid.get("frozenRowCount", 0)
    header_row = header_row_arg or frozen or 1

    last_row = max((i + 1 for i, r in enumerate(rows)
                    if any(c.get("formattedValue") for c in r)), default=0)
    last_col = max((j + 1 for r in rows for j, c in enumerate(r)
                    if c.get("formattedValue")), default=0)
    if last_row == 0:
        return ["tab is empty"]

    # --- trimmed grid -------------------------------------------------------
    extra_rows = grid.get("rowCount", 0) - last_row
    extra_cols = grid.get("columnCount", 0) - last_col
    if extra_rows > 0 or extra_cols > 0:
        findings.append(f"TRIM: {extra_rows} empty rows below row {last_row} and {extra_cols} "
                        f"empty columns right of {col_letter(last_col - 1)} "
                        f"(grid is {grid.get('rowCount')}x{grid.get('columnCount')})")

    # --- frozen section -----------------------------------------------------
    if frozen == 0:
        findings.append("FREEZE: no frozen rows; freeze the title + header rows")
    elif frozen > 3:
        findings.append(f"FREEZE: {frozen} rows frozen; only the title and header rows belong there")
    frozen_px = sum(m.get("pixelSize", DEFAULT_ROW_PX) for m in row_meta[:frozen])
    if frozen_px > 120:
        findings.append(f"FREEZE: frozen section is {frozen_px}px tall; move prose to a notes tab")
    for i, r in enumerate(rows[:frozen]):
        for j, c in enumerate(r):
            text = c.get("formattedValue", "")
            if len(text) > 100:
                findings.append(f"FREEZE: {col_letter(j)}{i + 1} holds a {len(text)}-char "
                                f"paragraph inside the frozen section")
    # A title overflowing out of a frozen column is cut at the freeze line.
    frozen_cols = grid.get("frozenColumnCount", 0)
    for i, r in enumerate(rows[:header_row - 1]):
        for j, c in enumerate(r[:frozen_cols]):
            right_empty = j + 1 >= len(r) or not r[j + 1].get("formattedValue")
            if c.get("formattedValue") and right_empty:
                findings.append(f"FREEZE: title in {col_letter(j)}{i + 1} is inside the {frozen_cols} frozen "
                                f"column(s), so its overflow is cut at the freeze line; put it in "
                                f"{col_letter(frozen_cols)}{i + 1}, the first non-frozen column")

    # --- striping -----------------------------------------------------------
    if last_row - header_row >= 3 and not has_striping(sheet):
        findings.append("STRIPE: no alternating colours (addBanding) on the data rows")

    # --- per-column data checks ----------------------------------------------
    body = rows[header_row:last_row]
    headers = rows[header_row - 1] if header_row - 1 < len(rows) else []
    valign_bad = 0
    # Text merged across several columns (a section label, a note standing in for
    # split values) belongs to no single column, so the column checks skip it.
    spanning = {(r, c) for m in sheet.get("merges", []) if m["endColumnIndex"] - m["startColumnIndex"] > 1
                for r in range(m["startRowIndex"], m["endRowIndex"])
                for c in range(m["startColumnIndex"], m["endColumnIndex"])}
    # A column holding one repeated symbol ("×", "±", "@") joins two number columns;
    # the number to its right may sit left-aligned against it.
    joiner_cols = set()
    for j in range(last_col):
        symbols = {r[j]["formattedValue"] for i, r in enumerate(body)
                   if j < len(r) and r[j].get("formattedValue") and (header_row + i, j) not in spanning}
        if len(symbols) == 1 and len(next(iter(symbols))) <= 2 and not next(iter(symbols)).isalnum():
            joiner_cols.add(j)
    for j in range(last_col):
        name = headers[j].get("formattedValue", "") if j < len(headers) else ""
        label = f"{col_letter(j)} ({name.strip()[:24]!r})" if name.strip() else col_letter(j)
        cells = [(header_row + 1 + i, r[j]) for i, r in enumerate(body)
                 if j < len(r) and r[j].get("formattedValue") and (header_row + i, j) not in spanning]
        if not cells:
            continue

        numbers, texts = [], []
        for rownum, c in cells:
            ev = c.get("effectiveValue", {})
            (numbers if "numberValue" in ev else texts if "stringValue" in ev else []).append((rownum, c))
            if c.get("effectiveFormat", {}).get("verticalAlignment") != "MIDDLE":
                valign_bad += 1

        def fmt(c, key):
            return c.get("effectiveFormat", {}).get(key)

        def where(items):
            rownums = [r for r, _ in items]
            shown = ", ".join(str(r) for r in rownums[:4])
            return f"{len(rownums)} cells (rows {shown}{', …' if len(rownums) > 4 else ''})"

        typed_text = [(r, c) for r, c in texts if (fmt(c, "numberFormat") or {}).get("type") != "TEXT"]
        num_text = [(r, c) for r, c in typed_text if NUMBER_AS_TEXT.match(c["formattedValue"])]
        if num_text:
            findings.append(f"TYPE: {label}: {where(num_text)} are numbers stored as text "
                            f"(e.g. {num_text[0][1]['formattedValue']!r})")
        date_text = [(r, c) for r, c in typed_text if DATE_AS_TEXT.match(c["formattedValue"])]
        if date_text:
            findings.append(f"TYPE: {label}: {where(date_text)} are dates stored as text "
                            f"(e.g. {date_text[0][1]['formattedValue']!r})")
        unit_text = [(r, c) for r, c in typed_text if NUMBER_WITH_UNIT.match(c["formattedValue"])
                     and not NUMBER_AS_TEXT.match(c["formattedValue"])]
        if len(unit_text) >= max(2, len(cells) // 2):
            findings.append(f"TYPE: {label}: {where(unit_text)} are number+unit text "
                            f"(e.g. {unit_text[0][1]['formattedValue']!r}); store the number and "
                            f"put the unit in the header or the number format")

        if numbers:
            patterns = Counter((fmt(c, "numberFormat") or {}).get("pattern", "") for _, c in numbers)
            if len(patterns) > 1:
                shown = ", ".join(f"{p or 'Automatic'!r}×{n}" for p, n in patterns.most_common())
                findings.append(f"FORMAT: {label}: mixed number formats in one column: {shown}")
            elif "" in patterns:
                decs = Counter(decimals_of(c["formattedValue"]) for _, c in numbers)
                if len(decs) > 1:
                    findings.append(f"FORMAT: {label}: no explicit number format and values show "
                                    f"{sorted(d for d in decs if d is not None)} decimal places, "
                                    f"so decimal points will not line up")
            allowed = {"RIGHT", None} | ({"LEFT"} if j - 1 in joiner_cols else set())
            centred = {fmt(c, "horizontalAlignment") for _, c in numbers} == {"CENTER"}
            narrow = all(len(c["formattedValue"]) <= 2 for _, c in numbers)
            misaligned = [(r, c) for r, c in numbers if fmt(c, "horizontalAlignment") not in allowed]
            if misaligned and not (centred and narrow):
                findings.append(f"ALIGN: {label}: {where(misaligned)} numeric but not right-aligned")
            if texts and len(texts) < len(numbers):
                findings.append(f"TYPE: {label}: mostly numbers but {where(texts)} are text "
                                f"(e.g. {texts[0][1]['formattedValue']!r})")

        right_text = [(r, c) for r, c in texts if fmt(c, "horizontalAlignment") == "RIGHT"]
        if right_text and not numbers:
            findings.append(f"ALIGN: {label}: {where(right_text)} text but right-aligned")
        for kind, group, default in (("text", texts, "LEFT"), ("numeric", numbers, "RIGHT")):
            aligns = Counter(fmt(c, "horizontalAlignment") or default for _, c in group)
            if len(aligns) > 1:
                shown = ", ".join(f"{a}×{n}" for a, n in aligns.most_common())
                findings.append(f"ALIGN: {label}: mixed alignment among {kind} cells in one column: {shown}")

        paragraphs = [(r, c) for r, c in texts if len(c["formattedValue"]) > 120]
        if paragraphs:
            findings.append(f"PROSE: {label}: {where(paragraphs)} hold paragraphs "
                            f"(>120 chars); break the facts out into columns")
        lists = [(r, c) for r, c in texts if len(LIST_SEPARATOR.findall(c["formattedValue"])) >= 2]
        if len(lists) >= max(2, len(texts) // 3):
            findings.append(f"PROSE: {label}: {where(lists)} look like delimited lists "
                            f"(e.g. {lists[0][1]['formattedValue'][:40]!r}); use one column or "
                            f"row per item")

    if valign_bad:
        findings.append(f"ALIGN: {valign_bad} data cells are not vertically centred (MIDDLE)")

    return findings


def cmd_lint(args) -> int:
    sheets = Sheets(args.spreadsheet, get_access_token(args.token_file))
    ranges = None
    if args.sheet is not None or args.gid is not None:
        ranges = [quote_title(sheets.find_sheet(args.sheet, args.gid)["title"])]
    doc = sheets.get(LINT_FIELDS, ranges=ranges, grid=True)
    total = 0
    for sheet in doc["sheets"]:
        title = sheet["properties"]["title"]
        if sheet["properties"].get("sheetType", "GRID") != "GRID":
            continue
        findings = lint_sheet(sheet, args.header_row)
        total += len(findings)
        print(f"== {title!r}: {len(findings)} finding(s)")
        for f in findings:
            print(f"   {f}")
    print(f"\n{total} finding(s). A clean lint is not a pass: header fit and rendering still "
          f"need fit-columns and a look in the browser.")
    return 1 if total else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("spreadsheet", help="spreadsheet ID or URL")
        p.add_argument("--sheet", help="tab name")
        p.add_argument("--gid", type=int, help="tab gid (sheetId)")
        p.add_argument("--header-row", type=int,
                       help="1-based row holding the column headers (default: last frozen row, else 1)")
        p.add_argument("--token-file", help="service-account key or OAuth authorized-user JSON (default: $GSHEETS_TOKEN_FILE)")

    p_lint = sub.add_parser("lint", help="read-only layout/data checks (all tabs by default)")
    common(p_lint)
    p_lint.set_defaults(func=cmd_lint)

    p_fit = sub.add_parser("fit-columns", help="size columns from the data rows, ignoring headers")
    common(p_fit)
    p_fit.add_argument("--apply", action="store_true", help="set the widths (default: dry run)")
    p_fit.add_argument("--rows", metavar="FIRST:LAST",
                       help="1-based data rows to measure (default: everything below the header row); "
                            "use it to measure one table on a tab that stacks several")
    p_fit.add_argument("--pad", type=int, default=8, help="px added to each measured width")
    p_fit.add_argument("--min", type=int, default=40, help="narrowest column, px")
    p_fit.add_argument("--max", type=int, default=420, help="widest column, px (free text wraps instead)")
    p_fit.set_defaults(func=cmd_fit_columns)

    args = parser.parse_args()
    if args.cmd == "fit-columns" and args.sheet is None and args.gid is None:
        parser.error("fit-columns needs --sheet or --gid")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
