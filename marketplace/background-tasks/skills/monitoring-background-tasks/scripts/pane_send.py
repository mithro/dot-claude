#!/usr/bin/env python3
"""Type one message into another Claude Code session's tmux pane, safely.

    uv run --no-project pane_send.py TARGET (--file FILE | --text TEXT)
        [-L SOCKET] [--host HOST] [--wait SECS] [--queue] [--no-enter] [--read]

    pane_send.py default:1 -L main --host other.example --read        # only read the pane
    pane_send.py default:1 -L main --host other.example --file msg.txt --wait 900

TARGET is a tmux target: `session:window`, `session:window.pane` or `%pane-id`.

Refuses unless the pane shows a Claude Code input box that is EMPTY (a grey suggestion
counts as empty; text in the default colour is the person's and is never touched).
With --wait it re-checks every 10 s until the box is empty, then sends.
If the session is mid-turn ("esc to interrupt") it refuses unless --queue is given: a
message sent then is queued and read at the session's next step. It never sends
Escape or Ctrl-C.

Newlines in the message become spaces (a newline would submit early). For anything long,
write a file the other session can read and send a one-line pointer to it.

--no-enter fills the input box and stops, for when the person wants to review and press
Enter themselves. Exit codes: 0 sent (or read), 2 refused, 3 sent but not confirmed.
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
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file")
    src.add_argument("--text")
    ap.add_argument("--read", action="store_true", help="print the pane (last --history lines) and exit")
    ap.add_argument("--history", type=int, default=80)
    ap.add_argument("--wait", type=int, default=0, help="seconds to wait for an empty input box")
    ap.add_argument("--queue", action="store_true", help="allow sending while the session is mid-turn")
    ap.add_argument("--no-enter", action="store_true")
    a = ap.parse_args()
    tm = panelib.Tmux(a.socket, a.host)

    if a.read or not (a.file or a.text):
        print(tm.capture(a.target, history=a.history))
        return

    text = open(a.file).read() if a.file else a.text
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        sys.exit("empty message")

    deadline = time.time() + a.wait
    while True:
        screen = tm.capture(a.target, colour=True)
        box = panelib.input_box(screen)
        working = panelib.is_working(screen)
        why = None
        if box is None:
            why = "no Claude Code input box on screen (a dialog, a permission prompt, or not a Claude session)"
        elif box:
            why = f"the person has text in the input box: {box!r}"
        elif working and not a.queue:
            why = "the session is mid-turn; pass --queue to queue the message behind its current step"
        if why is None:
            break
        if time.time() >= deadline:
            print(f"REFUSED, nothing sent: {why}\n" + "\n".join(panelib.status_tail(screen)), file=sys.stderr)
            sys.exit(2)
        print(f"{time.strftime('%H:%M:%S')} waiting: {why}", flush=True)
        time.sleep(10)

    tm.paste(a.target, text)
    time.sleep(1.0)
    filled = panelib.input_box(tm.capture(a.target, colour=True))
    if not filled:
        print("FAILED: the text did not appear in the input box; Enter NOT sent. Look at the pane.", file=sys.stderr)
        sys.exit(3)
    if a.no_enter:
        print(f"filled the input box of {a.target} with {len(text)} chars; Enter not sent (--no-enter)")
        return
    tm.key(a.target, "Enter")
    time.sleep(3.0)
    screen = tm.capture(a.target, colour=True)
    left = panelib.input_box(screen)
    print("\n".join(l[:200] for l in panelib.status_tail(screen, 12)))
    if left:
        print(f"\nNOT CONFIRMED: the input box still holds {left!r}. Enter may not have been accepted.", file=sys.stderr)
        sys.exit(3)
    print(f"\nsent {len(text)} chars to {a.target}" + (f" on {a.host}" if a.host else "")
          + ("; queued behind the running turn" if working else ""))


if __name__ == "__main__":
    main()
