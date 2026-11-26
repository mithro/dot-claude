#!/usr/bin/env python3
"""Run /compact in a Claude Code session through its tmux pane, and verify it started AND finished.

    uv run --no-project pane_compact.py TARGET [-L SOCKET] [--host HOST]
        [--keep TEXT] [--wait-idle SECS] [--timeout SECS]

A slash command can only come from the terminal input, so a session cannot compact another
session (or reliably itself) any other way. Typing `/compact` without checking is not
enough: a missed Enter leaves the command sitting in the input box and nothing happens.

Steps: wait up to --wait-idle (default 600 s) for an empty input box with no turn running;
type `/compact [KEEP]` and Enter; require "Compacting" on screen within 45 s; then require
a "Compacted" marker and an idle input box within --timeout (default 420 s).
Exit 0 only on a verified finish; 2 never idle, 4 did not start, 5 did not finish.

To compact YOURSELF: start this detached (run_in_background) with your own $TMUX_PANE as
TARGET, then end your turn. Your input box is busy while you run a tool, so the script
waits for you to go idle.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelib  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("-L", "--socket")
    ap.add_argument("--host")
    ap.add_argument("--keep", default="", help="what the summary must keep: role, handoff file, rules file, what it waits on")
    ap.add_argument("--wait-idle", type=int, default=600)
    ap.add_argument("--timeout", type=int, default=420)
    a = ap.parse_args()
    tm, t = panelib.Tmux(a.socket, a.host), a.target

    def done(code: int, msg: str) -> None:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {t}: {msg}")
        sys.exit(code)

    def idle() -> bool:
        s = tm.capture(t, colour=True)
        return panelib.input_box(s) == "" and not panelib.is_working(s)

    deadline = time.time() + a.wait_idle
    while not idle():
        if time.time() > deadline:
            done(2, f"FAILED: no empty, idle input box within {a.wait_idle} s; nothing sent")
        time.sleep(5)

    tm.paste(t, re.sub(r"\s+", " ", f"/compact {a.keep}").strip())
    time.sleep(1.5)
    tm.key(t, "Enter")

    t0, started = time.time(), False
    while True:
        low = panelib.plain(tm.capture(t)).lower()
        if not started and "compacting" in low:
            started = True
            print(f"compaction started after {time.time() - t0:.0f} s", flush=True)
        if started and "compacted" in low and "compacting" not in low and idle():
            done(0, f"ok: compacted in {time.time() - t0:.0f} s")
        if not started and time.time() - t0 > 45:
            done(4, "FAILED: compaction did not start within 45 s (Enter not accepted?). Pane tail: "
                 + " | ".join(l.strip()[:80] for l in panelib.status_tail(tm.capture(t))))
        if time.time() - t0 > a.timeout:
            done(5, f"FAILED: started but not finished within {a.timeout} s")
        time.sleep(2)


if __name__ == "__main__":
    main()
