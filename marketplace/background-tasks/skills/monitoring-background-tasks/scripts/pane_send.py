#!/usr/bin/env python3
"""Type one message into another Claude Code session's tmux pane, safely.

    uv run --no-project pane_send.py TARGET (--file FILE | --text TEXT)
        [-L SOCKET] [--host HOST] [--wait SECS] [--queue] [--no-enter]
    uv run --no-project pane_send.py TARGET [-L SOCKET] [--host HOST] --read [--history N]

    pane_send.py default:1 -L main --host other.example --read        # only read the pane
    pane_send.py default:1 -L main --host other.example --file msg.txt --wait 900

TARGET is a tmux target: `session:window`, `session:window.pane` or `%pane-id`. It is
resolved to a pane id once, at the start; every later step uses that id.

Before typing, the pane must show a Claude Code input box that is EMPTY (a grey
suggestion counts as empty; text in the default colour is the person's and is never
touched), must not be in copy mode, and must not be mid-turn ("esc to interrupt")
unless --queue is given: a message sent mid-turn is queued and read at the session's
next step. By default it refuses at once; with --wait it re-checks every 10 s for up
to that many seconds. It never sends Escape or Ctrl-C.

After typing and before Enter, the box must hold exactly the message and nothing
else, read without regard to colour. If the person typed at the same moment, or a
dialog appeared, Enter is NOT sent and the text is left where it is (exit 4): tell
the person. One gap remains: the instant between that last look and the Enter key
(one tmux call; one ssh round trip with --host).

Newlines in the message become spaces (a newline would submit early). A message with
control characters (they would arrive as keys) or longer than 400 characters (Claude
Code shows a long paste as a "[Pasted text]" placeholder that cannot be checked) is
refused before anything is typed: write a file the other session can read and send a
one-line pointer to it.

--no-enter fills the input box and stops, for when the person wants to review and press
Enter themselves.

Exit codes:
  0  sent and confirmed (or --read, or --no-enter filled the box)
  1  error: bad arguments, empty or unsafe message (control characters, over 400
     characters), tmux or ssh failed. Nothing was typed unless the message says otherwise.
  2  refused: nothing was typed
  3  Enter was sent but the box still holds the message: look at the pane
  4  the message was typed but Enter was withheld: the box holds text that is not
     (only) the message. Nothing was submitted; the text is still in the box.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelib  # noqa: E402


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("-L", "--socket")
    ap.add_argument("--host")
    ap.add_argument("--file")
    ap.add_argument("--text")
    ap.add_argument("--read", action="store_true", help="print the pane and exit; sends nothing")
    ap.add_argument("--history", type=int, default=80, help="with --read: scrollback lines to print above the visible screen")
    ap.add_argument("--wait", type=int, default=0, help="seconds to keep re-checking for a safe, empty input box (default: refuse at once)")
    ap.add_argument("--queue", action="store_true", help="allow sending while the session is mid-turn")
    ap.add_argument("--no-enter", action="store_true")
    a = ap.parse_args(argv)
    given = [n for n in ("read", "file", "text") if getattr(a, n) not in (None, False)]
    if len(given) != 1:
        ap.error("give exactly one of --read, --file FILE, --text TEXT")
    return a


def run(a: argparse.Namespace, tm, clock: panelib.Clock) -> int:
    if a.read:
        print(tm.capture(a.target, history=a.history))
        return 0

    if a.file:
        with open(a.file) as fh:
            text = fh.read()
    else:
        text = a.text
    try:
        text = panelib.clean_message(text)
    except ValueError as e:
        print(f"REFUSED, nothing sent: {e}", file=sys.stderr)
        return 1
    if not text:
        print("empty message; nothing sent", file=sys.stderr)
        return 1

    pane = tm.resolve(a.target)
    deadline = clock.now() + a.wait
    while True:
        in_mode, screen = tm.look(pane)
        why = panelib.why_not_send(in_mode, screen, allow_working=a.queue)
        if why is None:
            break
        if why == "the session is mid-turn":
            why += "; pass --queue to queue the message behind its current step"
        if clock.now() >= deadline:
            print(f"REFUSED, nothing sent: {why}\n" + "\n".join(panelib.status_tail(screen)), file=sys.stderr)
            return 2
        print(f"{time.strftime('%H:%M:%S')} waiting: {why}", flush=True)
        clock.sleep(10)
    working = panelib.is_working(screen)

    tm.paste(pane, text)
    ok, screen, reason = panelib.confirm_typed(tm, pane, text, clock)
    if not ok:
        print(f"NOT SENT: {reason}. Enter was withheld; whatever is in the input box of {a.target} is still "
              f"there, unsubmitted. Tell the person; do not clear it.\n" + "\n".join(panelib.status_tail(screen)),
              file=sys.stderr)
        return 4
    if a.no_enter:
        print(f"filled the input box of {a.target} with {len(text)} chars; Enter not sent (--no-enter)")
        return 0

    tm.key(pane, "Enter")
    end = clock.now() + 6
    while True:
        clock.sleep(0.5)
        _, screen = tm.look(pane)
        left = panelib.input_box(panelib.plain(screen))
        if panelib.squash(text) not in panelib.squash(left or ""):
            break
        if clock.now() >= end:
            print("\n".join(l[:200] for l in panelib.status_tail(screen, 12)))
            print(f"\nNOT CONFIRMED: Enter was sent but the input box still holds {left!r}.", file=sys.stderr)
            return 3
    print("\n".join(l[:200] for l in panelib.status_tail(screen, 12)))
    print(f"\nsent {len(text)} chars to {a.target} ({pane})" + (f" on {a.host}" if a.host else "")
          + ("; queued behind the running turn" if working else ""))
    return 0


def main() -> None:
    a = parse()
    try:
        sys.exit(run(a, panelib.Tmux(a.socket, a.host), panelib.Clock()))
    except (RuntimeError, ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
