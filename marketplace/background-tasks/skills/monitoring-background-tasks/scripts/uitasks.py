#!/usr/bin/env python3
"""Capture Claude Code's "Background tasks" dialog from this session's own tmux pane.

    uv run --no-project uitasks.py [--pane %N] [--state-dir DIR]

It only reads the screen and presses navigation keys. It makes no health decision.
Output: a JSON snapshot (header count, every row per section, the full command and
runtime of each task), the raw screen captures beside it, and a diff against the
previous snapshot of the SAME pane.

Safety, so it does not disturb the person using the pane:
  * Aborts unless the input box is on screen and empty. Grey or dim text there is the
    UI's own suggestion and counts as empty; anything in the default colour is theirs.
  * Each key is sent only after the screen shows the state the previous key should have
    produced: Down only when the footer says "to manage", Enter only when it says
    "enter to view tasks", Escape only while the dialog is visibly open (outside the
    dialog, Escape interrupts the running turn).
  * Never sends "x", which stops the selected task.
  * Afterwards it checks the dialog is closed and the input box is unchanged.

Exit codes: 0 ok, 2 skipped (person typing, or an unexpected screen), 3 a self-check failed.
After every run, compare the saved raw screens by eye with the JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelib  # noqa: E402

SECTIONS = ("Shells", "Background agents", "Scheduled", "Teammates", "Monitors")


BULLET = re.compile(r"^[^\w\s(\[]+\s+")  # the status dot in front of a row


def parse_list(screen: str) -> dict:
    """Parse the task LIST dialog. Tolerant of both layouts seen so far: a
    'N background tasks' header with titled sections, and a breakdown header
    ('2 shells') with bulleted rows and no section titles."""
    lines = panelib.plain(screen).splitlines()
    start = max(i for i, l in enumerate(lines) if re.match(r"^\s*Background\s*$", l))
    body = [l for l in lines[start + 1:]]
    header = next((l.strip() for l in body if l.strip()), "")
    m = re.search(r"(\d+) background tasks?", header)
    nums = re.findall(r"(\d+) [a-z]", header)
    count = int(m.group(1)) if m else (sum(int(n) for n in nums) if nums else None)
    out = {"count": count, "header": header, "sections": {}, "rows": [], "selected": None}
    sec, seen_header = None, False
    for l in body:
        t = l.strip()
        if not seen_header:
            seen_header = bool(t)
            continue
        if not t:
            continue
        if "to navigate" in t or "Esc to close" in t:
            break
        if t in SECTIONS or t.startswith(("Earlier in this session", "Remote")):
            sec = t
            out["sections"].setdefault(sec, [])
            continue
        sel = t.startswith(panelib.PROMPT)
        t = t.lstrip(panelib.PROMPT + " ").strip()
        if sec is None:
            if not BULLET.match(t):
                continue
            sec = "Tasks"
            out["sections"].setdefault(sec, [])
        t = BULLET.sub("", t)
        out["sections"][sec].append(t)
        if not sec.startswith("Earlier"):
            if sel:
                out["selected"] = len(out["rows"])
            out["rows"].append({"section": sec, "text": t})
    return out


def parse_detail(screen: str) -> dict:
    s = panelib.plain(screen)
    d = {}
    for field in ("Status", "Runtime", "Command", "Subagent"):
        m = re.search(rf"^\s*{field}:\s+(.*)$", s, re.M)
        d[field.lower()] = m.group(1).strip() if m else None
    if d["command"]:  # the command wraps onto indented continuation lines
        lines = s.splitlines()
        i = next(i for i, l in enumerate(lines) if re.match(r"^\s*Command:", l))
        label_indent = len(lines[i]) - len(lines[i].lstrip())
        cont = []
        for l in lines[i + 1:]:
            indent = len(l) - len(l.lstrip())
            if not l.strip() or re.match(r"^\s*(Subagent|Status|Runtime|Output)\b", l) or indent <= label_indent + 2:
                break
            cont.append(l.strip())
        d["command"] = " ".join([d["command"]] + [c for c in cont if c])
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pane", default=os.environ.get("TMUX_PANE"))
    ap.add_argument("--state-dir", default=os.path.join(
        os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")), "claude-bgtasks"))
    a = ap.parse_args()
    if not a.pane:
        sys.exit("not inside tmux (no TMUX_PANE) and no --pane given")

    tm = panelib.Tmux()
    # One snapshot directory per pane: a shared one makes the diff compare against another session.
    snaps = pathlib.Path(a.state_dir) / re.sub(r"[^A-Za-z0-9]+", "_", a.pane).strip("_")
    stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    raw = snaps / f"{stamp}-screens"
    raw.mkdir(parents=True)
    n_raw = 0

    def log(label: str, screen: str) -> None:
        nonlocal n_raw
        (raw / f"{n_raw:02d}-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}.txt").write_text(screen)
        n_raw += 1

    def wait_for(pred, label: str, timeout: float = 3.0) -> str | None:
        end = time.time() + timeout
        while time.time() < end:
            s = tm.capture(a.pane)
            if pred(s):
                log(label, s)
                return s
            time.sleep(0.1)
        log(label + " TIMEOUT", tm.capture(a.pane))
        return None

    def typed() -> str | None:
        return panelib.input_box(tm.capture(a.pane, colour=True))

    def finish(code: int, msg: str, snap: dict | None = None) -> None:
        if snap is not None:
            path = snaps / f"{stamp}.json"
            prev = sorted(p for p in snaps.glob("*.json"))
            path.write_text(json.dumps(snap, indent=2))
            print(json.dumps(snap, indent=2))
            if prev:
                old = json.loads(prev[-1].read_text())
                print(f"\nChanges since {prev[-1].name}:")
                if old.get("count") != snap.get("count"):
                    print(f"  count {old.get('count')} -> {snap.get('count')}")
                for sec in sorted(set(old["sections"]) | set(snap["sections"])):
                    was, now = old["sections"].get(sec, []), snap["sections"].get(sec, [])
                    for r in now:
                        if r not in was:
                            print(f"  + [{sec}] {r}")
                    for r in was:
                        if r not in now:
                            print(f"  - [{sec}] {r}")
                strip = lambda d: {k: v for k, v in d.items() if k not in ("time", "shells")}  # noqa: E731
                if strip(old) == strip(snap):
                    print("  rows IDENTICAL to the previous snapshot: confirm that is expected, not a stale capture")
            else:
                print("\n(first snapshot for this pane)")
        print(f"\n{msg}\nraw screens (compare with the JSON by eye): {raw}")
        sys.exit(code)

    # ---- 0. preconditions
    before = typed()
    s0 = tm.capture(a.pane)
    log("start", s0)
    if panelib.dialog_open(s0):
        finish(2, "SKIPPED: a task dialog is already open (the person may be using it)")
    if before is None:
        finish(2, "SKIPPED: no input box on screen (permission prompt, dialog or not a Claude Code pane)")
    if before:
        finish(2, f"SKIPPED: the person has text in the input box: {before!r}")
    if "to manage" not in s0:
        finish(2, "SKIPPED: footer has no 'to manage' (no background tasks, or an unexpected screen)")

    def close() -> str | None:
        """Escape, only while a task dialog is visibly open, until the footer is back."""
        for _ in range(4):
            if not panelib.dialog_open(tm.capture(a.pane)):
                break
            tm.key(a.pane, "Escape")
            time.sleep(0.4)
        return wait_for(lambda s: not panelib.dialog_open(s) and "to manage" in s, "closed, footer redrawn")

    # ---- 1. open the dialog
    footer_n = panelib.footer_task_count(s0)
    tm.key(a.pane, "Down")
    if not wait_for(lambda s: "enter to view tasks" in s, "after Down"):
        finish(3, "FAILED: Down did not focus the task footer; nothing else sent")
    if typed():
        tm.key(a.pane, "Up")
        finish(2, "SKIPPED: the person started typing; returned focus with Up")
    tm.key(a.pane, "Enter")
    s1 = wait_for(panelib.dialog_open, "dialog open")
    if not s1:
        finish(3, "FAILED: Enter did not open a task dialog; nothing else sent. LOOK AT THE PANE NOW.")

    if panelib.detail_open(s1) and not panelib.list_open(s1):
        # A single task: the detail view opens directly, there is no list to parse.
        d = parse_detail(s1)
        shells = [d.get("command") or "(no Command line: an agent or monitor)"]
        snap = {"count": 1, "sections": {"Single task (detail opened directly)": shells}, "selected": None}
        snap.update(time=stamp, pane=a.pane, footer_count=footer_n, shells=[d])
    else:
        snap = parse_list(s1)
        snap.update(time=stamp, pane=a.pane, footer_count=footer_n, shells=[])
        # ---- 2. open every active row to read its full details
        shells = snap["rows"]
        for idx in range(len(shells)):
            cur = parse_list(tm.capture(a.pane))["selected"]
            steps = 0
            while cur != idx and steps < 60:
                tm.key(a.pane, "Down" if (cur is None or cur < idx) else "Up")
                time.sleep(0.15)
                cur = parse_list(tm.capture(a.pane))["selected"]
                steps += 1
            if cur != idx:
                break
            tm.key(a.pane, "Enter")
            sd = wait_for(lambda s: panelib.detail_open(s) and not panelib.list_open(s), f"row {idx} detail")
            if sd:
                snap["shells"].append(dict(parse_detail(sd), row=shells[idx]["text"]))
            tm.key(a.pane, "Left")
            if not wait_for(panelib.list_open, f"back to list after row {idx}"):
                break

    # ---- 3. close
    closed = close()
    after = typed()

    # ---- 4. self-checks
    problems = []
    n_rows = len(snap["rows"]) if "rows" in snap else 1
    if snap["count"] is None:
        problems.append(f"no task count parsed from the dialog header {snap.get('header')!r}")
    elif n_rows != snap["count"]:
        problems.append(f"header says {snap['count']} but parsed {n_rows} active rows (a section name this script does not know?)")
    if footer_n is not None and snap["count"] is not None and footer_n != snap["count"]:
        problems.append(f"footer said {footer_n} but the dialog says {snap['count']}")
    if len(snap["shells"]) != len(shells):
        problems.append(f"read {len(snap['shells'])} detail views of {len(shells)} rows")
    if any(not d.get("status") for d in snap["shells"]):
        problems.append("a detail view had no Status line")
    if not closed or panelib.dialog_open(tm.capture(a.pane)):
        problems.append("dialog still open at the end: LOOK AT THE PANE NOW")
    if after != before:
        problems.append(f"input box changed: {before!r} -> {after!r}")
    snap["self_check_problems"] = problems
    finish(3 if problems else 0,
           "SELF-CHECK FAILED: " + "; ".join(problems) if problems else
           "self-check ok: footer count = header count = parsed rows, every row's detail read, dialog closed, input unchanged", snap)


if __name__ == "__main__":
    main()
