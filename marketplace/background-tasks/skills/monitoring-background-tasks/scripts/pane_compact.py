#!/usr/bin/env python3
"""Run /compact in a Claude Code session through its tmux pane, and verify it started AND finished.

    uv run --no-project pane_compact.py TARGET [-L SOCKET] [--host HOST]
        [--keep TEXT] [--wait-idle SECS] [--timeout SECS] [--ignore-agents]

A slash command can only come from the terminal input, so a session cannot compact another
session (or reliably itself) any other way. Typing `/compact` without checking is not
enough: a missed Enter leaves the command sitting in the input box and nothing happens.

Steps:
 1. Resolve TARGET to a pane id once. Wait up to --wait-idle (default 600 s) until the
    pane is not in copy mode, shows an empty input box, has no turn running and shows no
    sub-agent running. Text the person has typed counts as not empty and is never
    touched. A footer that only says "N background tasks" could be hiding an agent, so
    it also waits; pass --ignore-agents once you have checked there is none.
 2. Type `/compact [KEEP]`, then look again: the box must hold exactly that command and
    no turn may have started. Otherwise Enter is withheld (exit 3).
 3. Enter. "Started" means the command left the input box AND either a "Compacting"
    spinner shows or the command is newly echoed in the transcript, within 45 s.
 4. "Finished" means a "Compacted" result line below that echo, no spinner, and an idle
    empty input box, within --timeout (default 420 s). The same words anywhere else on
    screen (an earlier compaction, the --keep text, prose) do not count.

To compact YOURSELF: start this detached (run_in_background) with your own $TMUX_PANE as
TARGET, then end your turn. Your input box is busy while you run a tool, so the script
waits for you to go idle. (The script is then one of your background shells; that does
not block it. A running sub-agent does.)

Exit codes:
  0  compaction verified finished
  1  error: --keep has control characters or makes the command longer than 400
     characters (nothing typed), or tmux or ssh failed
  2  never safe to type within --wait-idle; nothing was typed
  3  the command was typed but Enter was withheld; it is still in the input box
  4  Enter was sent but compaction did not start
  5  compaction started but did not finish within --timeout
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelib  # noqa: E402

# What Claude Code 2.1.332 draws (captured 2026-11-26). The submitted command is echoed
# at column 0 and its result is an indented line under it:
#     ❯ /compact that this is a dialog test
#       ⎿  Compacted
# The old transcript stays on screen above, so an earlier "Compacted" proves nothing:
# only a result line BELOW the last echoed /compact counts.
ECHO = re.compile(r"^❯\s+/compact\b")
SPINNER = re.compile(r"^\S ?Compacting\b")
DONE = re.compile(r"^\s*⎿?\s*(?:Compacted\b|Conversation compacted\b)")


def marks(screen: str) -> tuple[list[str], bool, bool]:
    """(echoed /compact lines in the transcript, a Compacting spinner is showing,
    a Compacted result follows the last echo)."""
    lines = panelib.plain(screen).replace("\xa0", " ").splitlines()
    span = panelib._box(lines)
    transcript = lines[:span[0]] if span else lines
    echoes = [i for i, l in enumerate(transcript) if ECHO.match(l)]
    spinner = any(SPINNER.match(l) for l in panelib.above_box(screen))
    done = bool(echoes) and any(DONE.match(l) for l in transcript[echoes[-1] + 1:])
    return [transcript[i] for i in echoes], spinner, done


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("-L", "--socket")
    ap.add_argument("--host")
    ap.add_argument("--keep", default="", help="what the summary must keep: role, handoff file, rules file, what it waits on")
    ap.add_argument("--wait-idle", type=int, default=600)
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--ignore-agents", action="store_true", help="compact even though a sub-agent may be running")
    return ap.parse_args(argv)


def run(a: argparse.Namespace, tm, clock: panelib.Clock) -> int:
    def done(code: int, msg: str, screen: str = "") -> int:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {a.target}: {msg}")
        if screen:
            print("  pane tail: " + " | ".join(l.strip()[:80] for l in panelib.status_tail(screen)))
        return code

    def blocked(in_mode: bool, screen: str) -> str | None:
        why = panelib.why_not_send(in_mode, screen)
        if why or a.ignore_agents:
            return why
        agents = panelib.background_agents(screen)
        if agents:
            return "a sub-agent of that session is still running"
        if agents is None:
            return "the footer shows a task total that may include a sub-agent (pass --ignore-agents if you have checked)"
        return None

    try:
        cmd = panelib.clean_message(f"/compact {a.keep}")
    except ValueError as e:
        return done(1, f"FAILED: --keep cannot be typed safely: {e}; nothing sent")

    pane = tm.resolve(a.target)
    deadline = clock.now() + a.wait_idle
    while True:
        in_mode, screen = tm.look(pane)
        why = blocked(in_mode, screen)
        if why is None:
            break
        if clock.now() >= deadline:
            return done(2, f"FAILED: not safe to type within {a.wait_idle} s ({why}); nothing sent", screen)
        clock.sleep(5)
    before_echoes = marks(screen)[0]

    tm.paste(pane, cmd)
    ok, screen, reason = panelib.confirm_typed(tm, pane, cmd, clock)
    if ok and panelib.is_working(screen):
        ok, reason = False, "a turn started while the command was being typed"
    if not ok:
        return done(3, f"FAILED: {reason}. Enter was withheld; whatever is in the input box is still there, "
                       "unsubmitted. Tell the person; do not clear it.", screen)
    tm.key(pane, "Enter")

    t0, started = clock.now(), False
    while True:
        clock.sleep(2)
        in_mode, screen = tm.look(pane)
        elapsed = clock.now() - t0
        echoes, compacting, compacted = marks(screen)
        box = panelib.input_box(panelib.plain(screen))
        if not started and panelib.squash(cmd) not in panelib.squash(box or "") and (compacting or echoes != before_echoes):
            started = True
            print(f"compaction started after {elapsed:.0f} s", flush=True)
        if started and compacted and not compacting and panelib.why_not_send(in_mode, screen) is None:
            return done(0, f"ok: compacted in {elapsed:.0f} s")
        if not started and elapsed > min(45, a.timeout):
            return done(4, "FAILED: Enter was sent but compaction did not start (Enter not accepted, or /compact refused)", screen)
        if elapsed > a.timeout:
            return done(5, f"FAILED: started but not finished within {a.timeout} s", screen)


def main() -> None:
    a = parse()
    try:
        sys.exit(run(a, panelib.Tmux(a.socket, a.host), panelib.Clock()))
    except (RuntimeError, ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
