#!/usr/bin/env python3
"""Tests for the screen-reading and loop-flagging logic. No tmux needed.

    uv run --no-project test_bgtasks.py

The fixtures are escape sequences captured from Claude Code 2.1.332 with
`tmux capture-pane -e` (2026-11-26). When a Claude Code update changes the TUI,
capture the new screen, add it here as a fixture, then fix the parser.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bgcheck  # noqa: E402
import panelib  # noqa: E402
import uitasks  # noqa: E402

G, R = "\x1b[38;5;246m", "\x1b[39m"
RULE = "\x1b[38;5;244m" + "─" * 60
FOOT = f"{R}  \x1b[38;5;220m⏵⏵ auto mode on{G} (shift+tab to cycle){R}"


def screen(prompt_line: str, *more: str, above: str = "● pong") -> str:
    return "\n".join([above, RULE, prompt_line, *more, RULE, FOOT])


EMPTY = screen(f"{G}❯\xa0{R}")
SUGGESTION = screen(f"{R}❯\xa0{G}Try \"fix lint errors\"{R}")
TYPED = screen(f"{R}❯\xa0typed text here")
WRAPPED = screen(f"{R}❯\xa0/goal Design, simulate and verify", "suitable structures needed")
PAST_MESSAGE_ONLY = "\n".join(["❯ an earlier message from the person", "● reply", "  Do you want to proceed?", "  ❯ 1. Yes"])

LIST_NEW = """
● Working…
────────────────────────
  Background
  2 shells

  ❯ ● sleep 800   running
    ● sleep 900   running

      Earlier in this session (0)

  ↑/↓ to navigate · x to stop · Enter to view · Esc to close
"""

LIST_OLD = """
  Background
  4 background tasks

  Shells
  ❯ make renders   running
    until ! pgrep -f "make renders"; do sleep 30; done   running
  Background agents
    Charon Phase 4 Task B
  Scheduled
    43 * * * * health check
  Earlier in this session (3)
    old finished thing

  ↑/↓ to navigate · x to stop · Enter to view · Esc to close
"""

DETAIL = """
────────────────────────
  Hold a harmless background task open
  shell

  Status:   running
  Runtime:  14s
  Command:  sleep 900 &&
            echo done

  Output
  No output yet

  ← to go back · x to stop · Enter/Space to close · Esc to close
"""

FOOTER_NEW = "  ⏵⏵ auto mode on · 2 shells · esc to interrupt · ↓ to manage"
FOOTER_OLD = "  3 background tasks · ↓ to manage"


def check(name: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"{name}: got {got!r}, want {want!r}")
    print(f"ok  {name}")


# --- the input box: what decides whether a key may be sent
check("empty box", panelib.input_box(EMPTY), "")
check("grey suggestion counts as empty", panelib.input_box(SUGGESTION), "")
check("typed text is the person's", panelib.input_box(TYPED), "typed text here")
check("wrapped typed text", panelib.input_box(WRAPPED), "/goal Design, simulate and verify suitable structures needed")
check("no input box (permission prompt)", panelib.input_box(PAST_MESSAGE_ONLY), None)
check("without colour a suggestion reads as typed (so always capture with -e)",
      panelib.input_box(panelib.plain(SUGGESTION)), 'Try "fix lint errors"')

# --- turn state and footer
check("working", panelib.is_working(FOOTER_NEW), True)
check("idle", panelib.is_working(panelib.plain(EMPTY)), False)
check("footer breakdown", panelib.footer_task_count(FOOTER_NEW), 2)
check("footer old wording", panelib.footer_task_count(FOOTER_OLD), 3)
check("footer absent", panelib.footer_task_count(panelib.plain(EMPTY)), None)

# --- dialogs: Escape is only safe while one of these is true
check("list open", (panelib.list_open(LIST_NEW), panelib.detail_open(LIST_NEW)), (True, False))
check("detail open", (panelib.list_open(DETAIL), panelib.detail_open(DETAIL)), (False, True))
check("no dialog", panelib.dialog_open(panelib.plain(EMPTY)), False)
check("a tool output mentioning the words is not a dialog",
      panelib.dialog_open("  Background\n  Status:   running\n  Esc to close\n" + "\n".join(["x"] * 5) + "\n" + panelib.plain(EMPTY)), False)

# --- list parsing, both layouts
new = uitasks.parse_list(LIST_NEW)
check("new layout count", new["count"], 2)
check("new layout rows", [r["text"] for r in new["rows"]], ["sleep 800   running", "sleep 900   running"])
check("new layout selected", new["selected"], 0)
old = uitasks.parse_list(LIST_OLD)
check("old layout count", old["count"], 4)
check("old layout active rows exclude 'Earlier'", len(old["rows"]), 4)
check("old layout sections", [r["section"] for r in old["rows"]], ["Shells", "Shells", "Background agents", "Scheduled"])
det = uitasks.parse_detail(DETAIL)
check("detail command joins wrapped lines", det["command"], "sleep 900 && echo done")
check("detail status", det["status"], "running")

# --- loop flags (prompts to investigate, not verdicts)
H = 3600
check("pgrep -f loop self-matches",
      bgcheck.classify('until ! pgrep -f "make renders"; do sleep 30; done', "S", 0, H, False, 900), ["LOOP", "PGREP-F"])
check("while pgrep -f", "PGREP-F" in bgcheck.classify('while pgrep -f "make renders"; do sleep 30; done', "S", 0, H, False, 900), True)
check("marker wait with no failure exit",
      bgcheck.classify("until [ -f tmp/done ]; do sleep 5; done", "S", 0, H, False, 900), ["LOOP", "NO-EXIT"])
check("marker wait bounded by the job pid is not NO-EXIT",
      bgcheck.classify("until [ -f tmp/done ] || ! kill -0 4242; do sleep 5; done", "S", 0, H, False, 900), ["LOOP"])
check("marker wait under timeout is not NO-EXIT",
      bgcheck.classify("timeout 600 bash -c 'until [ -f tmp/done ]; do sleep 5; done'", "S", 0, H, False, 900), ["LOOP"])
check("idle leaf", bgcheck.classify("tail -f run.log", "S", 0, H, True, 900), ["IDLE"])
check("a parent waiting on a child is not idle", bgcheck.classify("make renders", "S", 0, H, False, 900), [])
check("sleep itself is not flagged idle", bgcheck.classify("sleep 900", "S", 0, H, True, 900), [])
check("zombie", bgcheck.classify("[sh] <defunct>", "Z", 0, 10, True, 900), ["ZOMBIE"])
check("shell wrapper body", bgcheck.body("/bin/bash -c source snap.sh && eval 'make renders' < /dev/null"), "'make renders' < /dev/null")
check("claude process", (bgcheck.is_claude("/home/u/.local/bin/claude --resume x"), bgcheck.is_claude("node claude-helper.js")), (True, False))

# --- tmux command construction (ssh gets ONE shlex-quoted string)
check("local argv", panelib.Tmux("main").argv("send-keys", "-t", "a:1", "Enter"), ["tmux", "-L", "main", "send-keys", "-t", "a:1", "Enter"])
check("remote argv quotes once",
      panelib.Tmux("main", "h.example").argv("capture-pane", "-t", "f.o bench:1"),
      ["ssh", "-o", "BatchMode=yes", "h.example", "tmux -L main capture-pane -t 'f.o bench:1'"])
try:
    panelib.Tmux().key("%1", "x")
    raise AssertionError("sending x must be refused")
except ValueError:
    print("ok  refuses to send x")
print("\nall passed")
