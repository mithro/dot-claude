#!/usr/bin/env python3
"""Capture Claude Code's "Background tasks" dialog from this session's own tmux pane.

    uv run --no-project uitasks.py [--pane TARGET] [-L SOCKET] [--state-dir DIR]

It only reads the screen and presses navigation keys. It makes no health decision.
Output: a JSON snapshot (footer count, dialog header, every row, the detail view of
each shell row, the sub-agent panel under the footer), the raw screen captures beside
it, and a diff against the previous snapshot of the same pane on the same tmux server.

Safety, so it does not disturb the person using the pane:
  * Aborts unless the pane is out of copy mode and the input box is on screen and
    empty. Grey or dim text there is the UI's own suggestion and counts as empty;
    anything in the default colour is theirs.
  * One key at a time, each only after a fresh capture shows the state the previous
    key should have produced: Down only when the footer (not the transcript) says
    "to manage", Enter only when it says "enter to view tasks", a row's Enter only
    when the list shows that row selected and still holds the same rows as when it
    was first read (a task that finishes mid-run shifts the rows: it then stops,
    exit 3), Left only from a detail view.
  * Escape only while a dialog is visibly open below the last rule line (outside a
    dialog, Escape interrupts the running turn), and never a second Escape until 5 s
    have passed with the dialog still open on a fresh capture.
  * Never sends "x", which stops the selected task.
  * Opens the detail view of shell rows only. What Enter does on an agent, scheduled
    or monitor row has not been captured, so those rows are listed but not opened.
  * If anything fails after the dialog was opened, it still closes the dialog, and if
    focus is left on the task footer it hands it back with one Up.
  * Afterwards it checks the dialog is closed and the input box is unchanged.

Exit codes: 0 ok, 1 error (bad arguments, tmux failed), 2 skipped (person typing, copy mode, or an
unexpected screen; nothing was sent), 3 a self-check failed.
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
# Rows whose detail view is known: titled "Shells", or the untitled list of 2.1.332,
# which holds shells only (a sub-agent's shell is listed too, marked "· <type> subagent").
OPENABLE = ("Shells", "Tasks")

BULLET = re.compile(r"^[^\w\s(\[]+\s+")  # the status dot in front of a row


def parse_list(screen: str) -> dict:
    """Parse the task LIST dialog. Tolerant of both layouts seen so far: a
    'N background tasks' header with titled sections, and a breakdown header
    ('2 shells') with bulleted rows and no section titles. If the list dialog is not
    open, returns the same shape with no rows and count None."""
    out = {"count": None, "header": "", "sections": {}, "rows": [], "selected": None}
    if not panelib.list_open(screen):
        return out
    body = panelib.dialog_lines(screen)
    body = body[next(i for i, l in enumerate(body) if l.strip() == "Background") + 1:]
    header = next((l.strip() for l in body if l.strip()), "")
    m = re.search(r"(\d+) background tasks?", header)
    nums = re.findall(r"(\d+) [a-z]", header)
    out["header"] = header
    out["count"] = int(m.group(1)) if m else (sum(int(n) for n in nums) if nums else None)
    sec, active, seen_header, untitled = None, None, False, False
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
            # No section titles (2.1.332). The rows are all shells only if the header
            # says so; otherwise nothing tells a shell row from another kind, and no
            # row may be opened.
            sec = active = "Tasks" if re.fullmatch(r"\d+ shells?", header) else "Tasks (not only shells)"
            untitled = True
            out["sections"].setdefault(sec, [])
        elif untitled and sec == active and not BULLET.match(t):
            # In the untitled layout every active row starts with a status dot, so a
            # line without one is the previous row's command wrapping on. (Only here:
            # under "Earlier in this session" the last row of `rows` is a different row.)
            out["sections"][sec][-1] += " " + t
            out["rows"][-1]["text"] += " " + t
            continue
        t = BULLET.sub("", t)
        out["sections"][sec].append(t)
        if not sec.startswith("Earlier"):
            if sel:
                out["selected"] = len(out["rows"])
            out["rows"].append({"section": sec, "text": t})
    return out


def parse_detail(screen: str) -> dict:
    lines = panelib.dialog_lines(screen) or panelib.plain(screen).splitlines()
    s = "\n".join(lines)
    d = {}
    for field in ("Status", "Runtime", "Command", "Subagent"):
        m = re.search(rf"^\s*{field}:\s+(.*)$", s, re.M)
        d[field.lower()] = m.group(1).strip() if m else None
    if d["command"]:  # the command wraps onto indented continuation lines
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


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    ap = panelib.ArgParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pane", default=os.environ.get("TMUX_PANE"), help="tmux target (default: $TMUX_PANE, this session's own pane)")
    ap.add_argument("-L", "--socket", help="tmux socket name, when --pane is on another tmux server")
    ap.add_argument("--state-dir", default=os.path.join(
        os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")), "claude-bgtasks"))
    a = ap.parse_args(argv)
    if not a.pane:
        ap.error("not inside tmux (no TMUX_PANE) and no --pane given")
    return a


def report(snaps: pathlib.Path, stamp: str, snap: dict) -> None:
    """Save the snapshot, print it, and print what changed since the previous one."""
    prev = sorted(snaps.glob("*.json"))
    (snaps / f"{stamp}.json").write_text(json.dumps(snap, indent=2))
    print(json.dumps(snap, indent=2))
    if not prev:
        print("\n(first snapshot for this pane)")
        return
    try:
        old = json.loads(prev[-1].read_text())
        if not isinstance(old, dict):
            raise ValueError("not a JSON object")
    except (OSError, ValueError) as e:
        print(f"\n{prev[-1].name} could not be read ({e}): not compared.")
        return
    if old.get("tmux_server") != snap.get("tmux_server"):
        # Pane ids start again from %0 when the tmux server restarts.
        print(f"\n{prev[-1].name} is from another tmux server, so this pane id may have been another session: not compared.")
        return
    print(f"\nChanges since {prev[-1].name}:")
    if old.get("count") != snap.get("count"):
        print(f"  count {old.get('count')} -> {snap.get('count')}")
    was_s, now_s = dict(old.get("sections", {})), dict(snap["sections"])
    was_s["Agent panel"], now_s["Agent panel"] = old.get("agent_panel", []), snap["agent_panel"]
    for sec in sorted(set(was_s) | set(now_s)):
        was, now = was_s.get(sec, []), now_s.get(sec, [])
        for r in now:
            if r not in was:
                print(f"  + [{sec}] {r}")
        for r in was:
            if r not in now:
                print(f"  - [{sec}] {r}")
    if (old.get("count"), was_s) == (snap.get("count"), now_s):
        print("  rows IDENTICAL to the previous snapshot: confirm that is expected, not a stale capture")


def run(a: argparse.Namespace, tm, clock: panelib.Clock) -> int:
    pane = tm.resolve(a.pane)
    # One snapshot directory per pane: a shared one makes the diff compare against another session.
    snaps = pathlib.Path(a.state_dir) / (re.sub(r"[^A-Za-z0-9]+", "_", f"{a.socket or ''}_{pane}").strip("_"))
    stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    raw = snaps / f"{stamp}-screens"
    raw.mkdir(parents=True)
    # The snapshots hold every task's full command line and whatever the transcript
    # showed. mkdir's mode only applies to the last directory it creates, so set it here.
    snaps.chmod(0o700)
    n_raw = 0

    def log(label: str, screen: str) -> None:
        nonlocal n_raw
        (raw / f"{n_raw:02d}-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}.txt").write_text(panelib.plain(screen))
        n_raw += 1

    def wait_for(pred, label: str, timeout: float = 3.0) -> str | None:
        """A fresh colour capture satisfying `pred` with the pane out of copy mode, or None."""
        end = clock.now() + timeout
        while True:
            in_mode, s = tm.look(pane)
            if not in_mode and pred(s):
                log(label, s)
                return s
            if clock.now() >= end:
                log(label + " TIMEOUT", s)
                return None
            clock.sleep(0.1)

    def skip(msg: str) -> int:
        print(f"SKIPPED, nothing sent: {msg}\nraw screens: {raw}")
        return 2

    # ---- 0. preconditions
    in_mode, s0 = tm.look(pane)
    log("start", s0)
    if in_mode:
        return skip("the pane is in copy mode (the person is scrolling back)")
    if panelib.dialog_open(s0):
        return skip("a dialog is already open (the person may be using it)")
    before = panelib.input_box(s0)
    if before is None:
        return skip("no input box on screen (permission prompt, or not a Claude Code pane)")
    if before:
        return skip(f"the person has text in the input box: {before!r}")
    if not panelib.footer_has(s0, "to manage"):
        return skip("the footer has no 'to manage' (no background tasks, or an unexpected screen)")
    footer_n = panelib.footer_task_count(s0)
    if footer_n is None:
        # "↓ to manage" with no count: only sub-agents are running. Down would then move
        # focus to the sub-agent panel, which shows no "enter to view tasks" to confirm
        # against, and what Enter opens from there has never been captured.
        panel = panelib.agent_panel(s0)
        return skip("the footer shows no task count (only sub-agents are running?), so there is no task list this "
                    "script knows how to open. Sub-agent panel: " + (" | ".join(panel) if panel else "(none shown)"))
    snap = {"count": None, "header": "", "sections": {}, "rows": [], "selected": None,
            "time": stamp, "pane": pane, "tmux_server": tm.run("display-message", "-p", "#{pid} #{start_time}").strip(),
            "footer_count": footer_n, "agent_panel": panelib.agent_panel(s0), "details": [], "not_opened": []}
    problems: list[str] = []
    opened = False

    def close() -> bool:
        """Escape, only while a dialog is visibly open on a fresh capture. True once the input box is back."""
        for _ in range(3):
            in_mode, s = tm.look(pane)
            if in_mode or not panelib.dialog_open(s):
                break
            tm.key(pane, "Escape")
            if wait_for(lambda n: not panelib.dialog_open(n), "after Escape", 5.0):
                break
        return wait_for(panelib.has_input_box, "closed, input box back") is not None

    up_sent = False

    def unfocus() -> None:
        """Hand focus back from the task footer to the input box: Up, only while a fresh
        capture shows the footer focused under a live input box, and AT MOST ONCE per
        run. Up in an input box that already has focus recalls the previous message
        (over whatever the person typed), and a capture taken straight after an Up can
        still show the frame from before it was drawn."""
        nonlocal up_sent
        if up_sent:
            return
        in_mode, s = tm.look(pane)
        if in_mode or not panelib.has_input_box(s) or not panelib.footer_focused(s):
            return
        up_sent = True
        tm.key(pane, "Up")
        wait_for(lambda n: not panelib.footer_focused(n), "focus back on the input box")

    def drive() -> None:
        nonlocal opened
        # ---- 1. open the dialog
        tm.key(pane, "Down")
        s = wait_for(lambda n: panelib.footer_has(n, "enter to view tasks"), "after Down")
        if not s:
            problems.append("Down did not focus the task footer; nothing else was sent")
            return
        if panelib.input_box(s):
            unfocus()
            problems.append("the person started typing; stopped (focus handed back with Up if the footer still had it)")
            return
        tm.key(pane, "Enter")
        opened = True
        s1 = wait_for(panelib.dialog_open, "dialog open")
        if not s1:
            problems.append("Enter did not open a task dialog")
            return

        if panelib.detail_open(s1):
            # A single task: its detail view opens directly, there is no list to parse.
            d = parse_detail(s1)
            text = d.get("command") or "(no Command line)"
            snap.update(count=1, header="(single task: detail view opened directly)",
                        sections={"Tasks": [text]}, rows=[{"section": "Tasks", "text": text}])
            snap["details"].append(dict(d, row=text))
            return
        if not panelib.list_open(s1):
            problems.append("an unknown dialog opened (neither the task list nor a detail view)")
            return
        snap.update(parse_list(s1))

        # ---- 2. open each shell row to read its full details
        rows = snap["rows"]

        def moved(s: str, idx: int) -> bool:
            """The list no longer holds the rows first read: a task finished or started,
            so position idx may now be a different row, perhaps one that must not be opened."""
            if parse_list(s)["rows"] == rows:
                return False
            if not any("the task list changed" in p for p in problems):
                problems.append(f"the task list changed while it was being read (before row {idx}); "
                                "stopped navigating. Run again for a complete snapshot")
            return True

        for idx, row in enumerate(rows):
            if row["section"] not in OPENABLE:
                snap["not_opened"].append(row)
                continue
            cur = parse_list(s1)["selected"]
            for _ in range(len(rows) + 1):
                if cur == idx or moved(s1, idx):
                    break
                tm.key(pane, "Down" if (cur is None or cur < idx) else "Up")
                was = cur
                s1 = wait_for(lambda n: panelib.list_open(n) and parse_list(n)["selected"] != was, f"select towards row {idx}", 2.0)
                if not s1:
                    break
                cur = parse_list(s1)["selected"]
            if s1 and moved(s1, idx):
                return
            if not s1 or cur != idx:
                problems.append(f"could not select row {idx}; stopped navigating")
                return
            tm.key(pane, "Enter")
            sd = wait_for(lambda n: panelib.detail_open(n) or not panelib.dialog_open(n), f"row {idx} detail")
            if not sd or not panelib.detail_open(sd):
                problems.append(f"row {idx}: Enter did not open a detail view; stopped navigating")
                return
            snap["details"].append(dict(parse_detail(sd), row=row["text"]))
            tm.key(pane, "Left")
            s1 = wait_for(panelib.list_open, f"back to list after row {idx}")
            if not s1:
                problems.append(f"row {idx}: Left did not return to the list; stopped navigating")
                return

    # ---- 3. drive, and close whatever happened
    closed = True
    try:
        drive()
    finally:
        if opened:
            closed = close()
        unfocus()

    # ---- 4. self-checks
    in_mode, end = tm.look(pane)
    after = panelib.input_box(end)
    expected = [r for r in snap["rows"] if r["section"] in OPENABLE]
    if not problems:
        if snap["count"] is None:
            problems.append(f"no task count parsed from the dialog header {snap['header']!r}")
        elif len(snap["rows"]) != snap["count"]:
            problems.append(f"header says {snap['count']} but parsed {len(snap['rows'])} active rows (a section name this script does not know?)")
        if footer_n is not None and snap["count"] is not None and footer_n != snap["count"]:
            problems.append(f"footer said {footer_n} but the dialog says {snap['count']}")
        if len(snap["details"]) != len(expected):
            problems.append(f"read {len(snap['details'])} detail views of {len(expected)} shell rows")
        if any(not d.get("status") for d in snap["details"]):
            problems.append("a detail view had no Status line")
    if not closed or panelib.dialog_open(end):
        problems.append("a dialog is still open at the end: LOOK AT THE PANE NOW")
    if after != before:
        problems.append(f"input box changed: {before!r} -> {after!r}")
    if panelib.footer_focused(end):
        problems.append("focus is still on the task footer: press Up in the pane before typing or sending anything")
    snap["self_check_problems"] = problems
    report(snaps, stamp, snap)
    if problems:
        print("\nSELF-CHECK FAILED: " + "; ".join(problems))
    else:
        skipped = f"; {len(snap['not_opened'])} non-shell rows listed but not opened" if snap["not_opened"] else ""
        print(f"\nself-check ok: footer count = header count = parsed rows ({snap['count']}), "
              f"{len(snap['details'])} shell detail views read{skipped}, dialog closed, input unchanged")
    print(f"raw screens (compare with the JSON by eye): {raw}")
    return 3 if problems else 0


def main() -> None:
    a = parse()
    try:
        sys.exit(run(a, panelib.Tmux(a.socket), panelib.Clock()))
    except (RuntimeError, ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
