#!/usr/bin/env python3
"""Tests for the screen reading, the loop flags and the key-sending control flow. No tmux needed.

    uv run --no-project test_bgtasks.py

Fixtures are hand-built to the shapes captured from Claude Code 2.1.332 with
`tmux capture-pane -e` (2026-11-26): the escape sequences of the prompt line, the
cursor, a suggestion, the footer, the agent panel and the Background dialogs are copied
from real captures; the surrounding text is made up. The "old layout" list (titled
sections) is reconstructed from notes of 2026-11-24 and was never captured.

The control-flow tests drive each script's run() against FakePane, a scripted pane
that reacts to keys the way the real TUI was seen to. It can also misbehave on cue:
the person types mid-paste, a permission prompt appears, a redraw lags.

When a Claude Code update changes the TUI, capture the new screen, add it here as a
fixture, then fix the parser.
"""
import contextlib
import io
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bgcheck  # noqa: E402
import pane_compact  # noqa: E402
import pane_send  # noqa: E402
import panelib  # noqa: E402
import uitasks  # noqa: E402

G, R, DIM, INV, RESET = "\x1b[38;5;246m", "\x1b[39m", "\x1b[2m", "\x1b[7m", "\x1b[0m"
RULE = "\x1b[38;5;244m" + "─" * 60
FOOT = f"{R}  \x1b[38;5;220m⏵⏵ auto mode on{G} (shift+tab to cycle){R}"
N_CHECKS = 0


def check(name: str, got, want) -> None:
    global N_CHECKS
    if got != want:
        raise AssertionError(f"{name}: got {got!r}, want {want!r}")
    N_CHECKS += 1
    print(f"ok  {name}")


def screen(prompt_line: str, *more: str, above: str = "● pong", foot: tuple = (FOOT,)) -> str:
    return "\n".join([above, RULE, prompt_line, *more, RULE, *foot])


# ---------------------------------------------------------------- the input box
EMPTY = screen(f"{G}❯\xa0{INV}{R} {RESET}")                                  # cursor on an empty box
SUGGESTION = screen(f"{R}❯\xa0{DIM}fix the issues the review finds{RESET}")  # unfocused: all dim
SUGGESTION_CURSOR = screen(f"{R}❯\xa0{INV}w\x1b[0;2mait for the agent{RESET}")  # cursor on its first letter
SUGGESTION_GREY = screen(f"{R}❯\xa0{G}Try \"fix lint errors\"{R}")
SUGGESTION_WRAPPED = screen(f"{R}❯\xa0{DIM}a long suggestion that wraps", "onto a second line" + RESET)
TYPED = screen(f"{R}❯\xa0typed text here")
TYPED_WRAPPED = screen(f"{R}❯\xa0/plan design and check the", "structures that are needed")
TYPED_ONE_CHAR_UNDER_CURSOR = screen(f"{R}❯\xa0{INV}w{RESET}")
TYPED_CURSOR_MID = screen(f"{R}❯\xa0del{INV}e{RESET}te it")
GREY_THEN_COLOUR = screen(f"{R}❯\xa0{G}hint\x1b[38;5;220mREAL TYPED TEXT{R}")
PERMISSION_PROMPT = "\n".join(["❯ an earlier message from the person", "● reply", "  Do you want to proceed?", "  ❯ 1. Yes"])
BOX_IN_TOOL_OUTPUT = "\n".join(["● Bash(tmux capture-pane)", "  " + "─" * 60, "  ❯ ", "  " + "─" * 60, "  Do you want to proceed?", "  ❯ 1. Yes"])
TITLED_RULE = "\n".join(["● pong", "─" * 40 + " my session title ─", f"{R}❯\xa0", "─" * 60, FOOT])

check("empty box (inverse-video cursor is not text)", panelib.input_box(EMPTY), "")
check("dim suggestion counts as empty", panelib.input_box(SUGGESTION), "")
check("suggestion with the cursor on its first letter counts as empty", panelib.input_box(SUGGESTION_CURSOR), "")
check("256-colour grey suggestion counts as empty", panelib.input_box(SUGGESTION_GREY), "")
check("suggestion wrapped onto a second line stays grey (colour carries over lines)", panelib.input_box(SUGGESTION_WRAPPED), "")
check("typed text is the person's", panelib.input_box(TYPED), "typed text here")
check("wrapped typed text", panelib.input_box(TYPED_WRAPPED), "/plan design and check the structures that are needed")
check("one typed letter under the cursor is the person's", panelib.input_box(TYPED_ONE_CHAR_UNDER_CURSOR), "w")
check("cursor moved back into typed text", panelib.input_box(TYPED_CURSOR_MID), "delete it")
check("a new colour after grey ends the grey", panelib.input_box(GREY_THEN_COLOUR), "REAL TYPED TEXT")
check("no input box (permission prompt)", panelib.input_box(PERMISSION_PROMPT), None)
check("a box drawn inside indented tool output is not the input box", panelib.input_box(BOX_IN_TOOL_OUTPUT), None)
check("rule with the session title embedded", panelib.input_box(TITLED_RULE), "")
check("colour-blind reading returns everything in the box",
      panelib.input_box(panelib.plain(SUGGESTION_CURSOR)), "wait for the agent")
check("OSC hyperlinks are stripped, BEL and ST terminated",
      panelib.plain("a\x1b]8;;http://x\x1b\\link\x1b]8;;\x1b\\ b\x1b]8;;http://y\x07l2\x1b]8;;\x07"), "alink bl2")

# ---------------------------------------------------------------- turn state and footer
PANEL = ("", "  ● main", *(f"  ◯ general-purpose  task {i} · since 10:26 PM" for i in range(12)))
F_WORKING = f"{R}  ⏵⏵ auto mode on · 2 shells · esc to interrupt · ↓ to manage"
F_IDLE = f"{R}  ⏵⏵ auto mode on · 2 shells · ↓ to manage"
check("working", panelib.is_working(screen(f"{R}❯\xa0", foot=(F_WORKING,))), True)
check("working, with a 12-row agent panel under the footer", panelib.is_working(screen(f"{R}❯\xa0", foot=(F_WORKING, *PANEL))), True)
check("working, footer cut short by a narrow pane", panelib.is_working(screen(f"{R}❯\xa0", foot=("  ⏵⏵ auto mode on · esc to inter…",))), True)
check("idle", panelib.is_working(EMPTY), False)
check("'esc to interrupt' quoted in the transcript is not a running turn",
      panelib.is_working(screen(f"{R}❯\xa0", above="  it said esc to interrupt")), False)
check("bare footer string still works", panelib.is_working("  ⏵⏵ auto mode on · 2 shells · esc to interrupt · ↓ to manage"), True)
check("footer breakdown", panelib.footer_task_count(screen(f"{R}❯\xa0", foot=(F_IDLE,))), 2)
check("footer old wording", panelib.footer_task_count(screen(f"{R}❯\xa0", foot=("  3 background tasks · ↓ to manage",))), 3)
check("footer absent", panelib.footer_task_count(EMPTY), None)
check("'↓ to manage' in the transcript is not the footer",
      panelib.footer_has(screen(f"{R}❯\xa0", above="  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)"), "to manage"), False)
check("footer has it", panelib.footer_has(screen(f"{R}❯\xa0", foot=(F_IDLE,)), "to manage"), True)

AGENT_WAIT = screen(f"{R}❯\xa0", above=f"{G}✻{R} {G}Waiting for \x1b[1m1{RESET}{G} background agent to finish{R}", foot=(f"{R}  ⏵⏵ auto mode on · ↓ to manage",))
check("agent: 'Waiting for 1 background agent' spinner", panelib.background_agents(AGENT_WAIT), True)
check("agent: panel under the footer", panelib.background_agents(screen(f"{R}❯\xa0", foot=(F_IDLE, *PANEL[:3]))), True)
check("agent: shells only", panelib.background_agents(screen(f"{R}❯\xa0", foot=(F_IDLE,))), False)
check("agent: a bare total cannot say", panelib.background_agents(screen(f"{R}❯\xa0", foot=("  3 background tasks · ↓ to manage",))), None)
check("agent: none", panelib.background_agents(EMPTY), False)

# ---------------------------------------------------------------- dialogs: Escape is only safe while one is open
DRULE = "─" * 60
LIST_NEW = f"""
● Working…
{DRULE}
  Background
  2 shells

  ❯ ● sleep 800   running · general-purpose subagent
    ● sleep 900   running

      Earlier in this session (0)

  ↑/↓ to navigate · x to stop · Enter to view · Esc to close
"""

LIST_OLD = f"""
{DRULE}
  Background
  4 background tasks

  Shells
  ❯ make renders   running
    until ! pgrep -f "make renders"; do sleep 30; done   running
  Background agents
    Review the parser changes
  Scheduled
    43 * * * * health check
  Earlier in this session (3)
    old finished thing

  ↑/↓ to navigate · x to stop · Enter to view · Esc to close
"""

DETAIL = f"""
{DRULE}
  Hold a harmless background task open
  shell

  Status:    running
  Runtime:   14s
  Command:   sleep 900 &&
             echo done
  Subagent:  general-purpose subagent

  Output
  No output yet

  ← to go back · x to stop · Enter/Space to close · Esc to close
"""

check("list open", (panelib.list_open(LIST_NEW), panelib.detail_open(LIST_NEW)), (True, False))
check("detail open", (panelib.list_open(DETAIL), panelib.detail_open(DETAIL)), (False, True))
check("no dialog", panelib.dialog_open(EMPTY), False)
check("a list under a transcript line 'Status: all good' is only a list",
      (panelib.list_open("  Status: all good\n" + LIST_NEW), panelib.detail_open("  Status: all good\n" + LIST_NEW)), (True, False))
check("a detail view under a transcript line 'Background' is only a detail view",
      (panelib.list_open("  Background\n" + DETAIL), panelib.detail_open("  Background\n" + DETAIL)), (False, True))
check("tool output showing a dialog, above a live input box, is not a dialog",
      panelib.dialog_open("\n".join("  " + l for l in LIST_NEW.splitlines()) + "\n" + EMPTY), False)
check("a rule inside a task's output does not hide the detail view",
      panelib.detail_open(DETAIL.replace("  No output yet", "  " + DRULE + "\n  No output yet")), True)

new = uitasks.parse_list(LIST_NEW)
check("new layout count", new["count"], 2)
check("new layout rows", [r["text"] for r in new["rows"]], ["sleep 800   running · general-purpose subagent", "sleep 900   running"])
check("new layout selected", new["selected"], 0)
old = uitasks.parse_list(LIST_OLD)
check("old layout count", old["count"], 4)
check("old layout active rows exclude 'Earlier'", len(old["rows"]), 4)
check("old layout sections", [r["section"] for r in old["rows"]], ["Shells", "Shells", "Background agents", "Scheduled"])
check("parse_list with no list dialog returns no rows instead of raising", uitasks.parse_list(EMPTY)["rows"], [])
check("parse_list on a detail view returns no rows", uitasks.parse_list(DETAIL)["rows"], [])
det = uitasks.parse_detail(DETAIL)
check("detail command joins wrapped lines", det["command"], "sleep 900 && echo done")
check("detail status and subagent", (det["status"], det["subagent"]), ("running", "general-purpose subagent"))

# ---------------------------------------------------------------- loop flags (prompts to investigate, not verdicts)
H = 3600
check("pgrep -f loop self-matches",
      bgcheck.classify('until ! pgrep -f "make renders"; do sleep 30; done', "S", 0, H, False, 900), ["LOOP", "PGREP-F"])
check("while pgrep -f", "PGREP-F" in bgcheck.classify('while pgrep -f "make renders"; do sleep 30; done', "S", 0, H, False, 900), True)
check("pgrep --full", "PGREP-F" in bgcheck.classify('while pgrep --full "make renders"; do sleep 30; done', "S", 0, H, False, 900), True)
check("marker wait with no failure exit",
      bgcheck.classify("until [ -f tmp/done ]; do sleep 5; done", "S", 0, H, False, 900), ["LOOP", "NO-EXIT"])
check("marker wait written with test", bgcheck.classify("while ! test -f done; do sleep 5; done", "S", 0, H, False, 900), ["LOOP", "NO-EXIT"])
check("marker wait written with [[ ]]", bgcheck.classify("until [[ -e done ]]; do sleep 5; done", "S", 0, H, False, 900), ["LOOP", "NO-EXIT"])
check("marker wait bounded by the job pid is not NO-EXIT",
      bgcheck.classify("until [ -f tmp/done ] || ! kill -0 4242; do sleep 5; done", "S", 0, H, False, 900), ["LOOP"])
check("marker wait under timeout is not NO-EXIT",
      bgcheck.classify("timeout 600 bash -c 'until [ -f tmp/done ]; do sleep 5; done'", "S", 0, H, False, 900), ["LOOP"])
check("an --until argument is not a loop", bgcheck.classify("python3 run.py --until 5 ; echo", "S", 5, H, False, 900), [])
check("a loop after another command", bgcheck.classify("cd x && while true; do sleep 1; done", "S", 0, H, False, 900), ["LOOP"])
check("idle leaf", bgcheck.classify("tail -f run.log", "S", 0, H, True, 900), ["IDLE"])
check("a parent waiting on a child is not idle", bgcheck.classify("make renders", "S", 0, H, False, 900), [])
check("sleep itself is not flagged idle", bgcheck.classify("sleep 900", "S", 0, H, True, 900), [])
check("zombie", bgcheck.classify("[sh] <defunct>", "Z", 0, 10, True, 900), ["ZOMBIE"])
check("shell wrapper body", bgcheck.body("/bin/bash -c source snap.sh && eval 'make renders' < /dev/null"), "'make renders' < /dev/null")
check("a command that merely contains 'eval ' is left whole", bgcheck.body("python3 -c retrieval eval 5"), "python3 -c retrieval eval 5")
check("claude process: native, helper, npm install",
      (bgcheck.is_claude("/home/u/.local/bin/claude --resume x"), bgcheck.is_claude("node claude-helper.js"),
       bgcheck.is_claude("node /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js")), (True, False, True))
with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(__file__))) as td:
    big = os.path.join(td, "big.log")
    with open(big, "w") as fh:
        fh.write("x\n" * 100000 + "the last line\n")
    check("last line of a large log, read from its tail", bgcheck.last_lines(big)[-1], "the last line")
    check("an unreadable log path is reported, not raised", bgcheck.last_lines(td)[0].startswith("(cannot read"), True)

# ---------------------------------------------------------------- tmux command construction
check("local argv", panelib.Tmux("main").argv("send-keys", "-t", "a:1", "Enter"), ["tmux", "-L", "main", "send-keys", "-t", "a:1", "Enter"])
check("remote argv quotes once",
      panelib.Tmux("main", "h.example").argv("capture-pane", "-t", "f.o bench:1"),
      ["ssh", "-o", "BatchMode=yes", "h.example", "tmux -L main capture-pane -t 'f.o bench:1'"])
check("the ; between two tmux commands survives ssh quoting",
      panelib.Tmux(None, "h.example").argv("display-message", "-p", ";", "capture-pane")[-1], "tmux display-message -p ';' capture-pane")
try:
    panelib.Tmux().key("%1", "x")
    raise AssertionError("sending x must be refused")
except ValueError:
    check("refuses to send x", True, True)
try:
    panelib.Tmux(None, "-oProxyCommand=evil")
    raise AssertionError("a host starting with - must be refused")
except ValueError:
    check("refuses a host that looks like an option", True, True)


class RecordingTmux(panelib.Tmux):
    def __init__(self):
        super().__init__()
        self.calls = []

    def run(self, *args, stdin=None):
        self.calls.append(args)
        return ""


rec = RecordingTmux()
rec.paste("%1", "a")
rec.paste("%1", "b")
names = [c[2] for c in rec.calls if c[0] == "load-buffer"]
check("each paste uses its own buffer name", len(set(names)), 2)
check("paste targets the buffer it loaded", [c[c.index("-b") + 1] for c in rec.calls if c[0] == "paste-buffer"], names)


# ---------------------------------------------------------------- a scripted pane for the control flow
class FakeClock(panelib.Clock):
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class FakePane:
    """Reacts to keys the way Claude Code 2.1.332 was seen to. Keys sent where the real
    UI would do damage are recorded in `damage`."""

    def __init__(self, rows=(), transcript=("● earlier reply",), suggestion="", old_layout=False):
        self.rows, self.transcript, self.suggestion = list(rows), list(transcript), suggestion
        self.old_layout = old_layout
        self.box, self.working, self.in_mode, self.agents, self.bare_total = "", False, False, [], False
        self.focus, self.dialog, self.selected, self.prompt = False, None, 0, False
        self.keys, self.pastes, self.damage, self.submitted = [], [], [], []
        self.close_lag = 0          # look() calls a closing dialog stays drawn for
        self._closing = None
        self.on_paste = None        # called after a paste lands: the person or the UI interferes
        self.swallow_enter = False  # the Enter key is lost
        self.eat_submit = False     # Enter empties the box but nothing is run or echoed
        self.compact_after = None   # look() calls until an accepted /compact finishes
        self.fail_on_key = None     # raise when this key is sent (a tmux failure mid-run)
        self.grey_prefix = ""       # text of the person's that the UI happens to draw dim
        self.chip = False           # the box shows a paste as "[Pasted text #1 +0 lines]"
        self.no_dialog = False      # Enter on the focused footer opens nothing

    # --- what tmux would be asked
    def resolve(self, target):
        return "%7"

    def run(self, *args, stdin=None):
        return "4242 1700000000\n"

    def capture(self, target, colour=False, history=0):
        return self.render()

    def look(self, pane):
        if self._closing is not None:
            self._closing -= 1
            if self._closing < 0:
                self.dialog, self.focus, self._closing = None, False, None
        if self.compact_after is not None:
            self.compact_after -= 1
            if self.compact_after < 0:
                self.transcript.append("  ⎿  Compacted")
                self.working, self.compact_after = False, None
        return self.in_mode, self.render()

    def paste(self, pane, text):
        self.pastes.append(text)
        if self.in_mode or self.dialog or self.prompt:
            self.damage.append("paste outside the input box")
            return
        self.box += text
        if self.on_paste:
            self.on_paste(self)

    def key(self, pane, key):
        self.keys.append(key)
        if key == self.fail_on_key:
            raise RuntimeError("tmux: server exited unexpectedly")
        if self.in_mode:
            self.damage.append(f"{key} sent into copy mode")
        elif self.prompt:
            self.damage.append(f"{key} answered a permission prompt")
        elif key == "Escape":
            if self.dialog and self._closing is None:
                self._closing = self.close_lag
            elif self.dialog:
                self.damage.append("second Escape while the first was still closing the dialog: interrupts the turn")
            else:
                self.damage.append("Escape with no dialog open: interrupts the turn")
        elif self.dialog == "list":
            if key == "Down":
                self.selected = min(self.selected + 1, len(self.rows) - 1)
            elif key == "Up":
                self.selected = max(self.selected - 1, 0)
            elif key == "Enter":
                if self.rows[self.selected][0] != "Shells":
                    self.damage.append("Enter on a non-shell row: effect unknown")
                self.dialog = "detail"
        elif self.dialog == "detail":
            if key == "Left":
                self.dialog = "list"
        elif key == "Down" and not self.focus:
            self.focus = True
        elif key == "Up":
            self.focus = False
        elif key == "Enter" and self.focus and self.no_dialog:
            pass
        elif key == "Enter" and self.focus:
            self.dialog, self.selected = ("detail" if len(self.rows) == 1 else "list"), 0
        elif key == "Enter" and self.eat_submit:
            self.box = ""
        elif key == "Enter" and not self.swallow_enter and self.box:
            if self.grey_prefix:
                self.damage.append("Enter submitted the person's text together with the message")
            self.submitted.append(self.box)
            self.transcript.append(f"❯ {self.box}")
            if self.box.startswith("/compact"):
                self.working, self.compact_after = True, 3
            self.box = ""

    # --- what the screen shows
    def render(self):
        t = list(self.transcript)
        if self.prompt:
            return "\n".join(t + ["  Do you want to proceed?", "  ❯ 1. Yes", "    2. No"])
        if self.dialog == "list":
            head = f"{len(self.rows)} background tasks" if self.old_layout else f"{len(self.rows)} shells"
            body, sec = ["  Background", f"  {head}", ""], None
            for i, (section, text) in enumerate(self.rows):
                if self.old_layout and section != sec:
                    body.append(f"  {section}")
                    sec = section
                mark = "❯" if i == self.selected else " "
                body.append(f"  {mark} {text}   running" if self.old_layout else f"  {mark} ● {text}   running")
            body += ["", "      Earlier in this session (0)", "", "  ↑/↓ to navigate · x to stop · Enter to view · Esc to close"]
            return "\n".join(t + [DRULE] + body)
        if self.dialog == "detail":
            text = self.rows[self.selected][1]
            return "\n".join(t + [DRULE, "  A description", "  shell", "", "  Status:    running", "  Runtime:   14s",
                                  f"  Command:   {text}", "", "  Output", "  No output yet", "",
                                  "  ← to go back · x to stop · Enter/Space to close · Esc to close"])
        if self.compact_after is not None:
            t.append("✻ Compacting conversation… (3s)")
        if self.box or self.grey_prefix:
            shown = "[Pasted text #1 +0 lines]" if (self.chip and self.box) else self.box
            line = f"{R}❯\xa0{DIM}{self.grey_prefix}\x1b[22m{shown}{INV} {RESET}"
        elif self.suggestion:
            line = f"{R}❯\xa0{INV}{self.suggestion[0]}\x1b[0;2m{self.suggestion[1:]}{RESET}"
        else:
            line = f"{R}❯\xa0{INV} {RESET}"
        foot = "  ⏵⏵ auto mode on"
        if self.rows:
            foot += f" · {len(self.rows)} background tasks" if (self.old_layout or self.bare_total) else f" · {len(self.rows)} shells"
        if self.working:
            foot += " · esc to interrupt"
        if self.rows or self.agents:
            foot += " · enter to view tasks" if self.focus else " · ↓ to manage"
        panel = ["", "  ● main"] + [f"  ◯ general-purpose  {a}" for a in self.agents] if self.agents else []
        return "\n".join(t + [RULE, line, RULE + R, "  user@host:/some/dir", foot] + panel)


def quiet(fn, *args):
    """Run a script's run() with its output captured; returns (exit code, output)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = fn(*args, FakeClock())
    return code, buf.getvalue()


# ---------------------------------------------------------------- pane_send.py
def send(pane, *argv):
    return quiet(pane_send.run, pane_send.parse(["t:1", *argv]), pane)


MSG = "from the other session: the data is at tmp/out.json"
p = FakePane(suggestion="try this")
check("send: happy path", (send(p, "--text", MSG)[0], p.submitted, p.keys), (0, [MSG], ["Enter"]))

p = FakePane()
p.box = "half a thought"
check("send: the person's text is in the box: nothing typed", (send(p, "--text", MSG)[0], p.pastes, p.keys, p.box), (2, [], [], "half a thought"))

p = FakePane()
p.in_mode = True
check("send: copy mode: nothing typed", (send(p, "--text", MSG)[0], p.pastes, p.keys), (2, [], []))

p = FakePane()
p.prompt = True
check("send: permission prompt on screen: nothing typed", (send(p, "--text", MSG)[0], p.pastes, p.keys), (2, [], []))

p = FakePane()
p.working = True
check("send: mid-turn refuses without --queue", (send(p, "--text", MSG)[0], p.pastes), (2, []))
p = FakePane()
p.working = True
check("send: mid-turn with --queue sends", (send(p, "--text", MSG, "--queue")[0], p.submitted), (0, [MSG]))

p = FakePane()
p.on_paste = lambda q: setattr(q, "box", "delete the " + q.box)  # the person typed first, in the gap
code, out = send(p, "--text", MSG)
check("send: the person typed in the gap: Enter withheld, exit 4", (code, p.keys, p.submitted), (4, [], []))
check("send: ... and the message says nothing was submitted", "Enter was withheld" in out, True)

p = FakePane()
p.on_paste = lambda q: setattr(q, "prompt", True)  # a permission prompt popped up after the paste
check("send: a prompt appeared after the paste: Enter withheld", (send(p, "--text", MSG)[0], p.keys, p.damage), (4, [], []))

p = FakePane()
p.on_paste = lambda q: setattr(q, "in_mode", True)
check("send: copy mode entered after the paste: Enter withheld", (send(p, "--text", MSG)[0], p.keys), (4, []))

p = FakePane()
p.swallow_enter = True
check("send: Enter not accepted: exit 3", (send(p, "--text", MSG)[0], p.keys, p.submitted), (3, ["Enter"], []))

p = FakePane()
check("send: --no-enter fills and stops", (send(p, "--text", MSG, "--no-enter")[0], p.keys, p.box), (0, [], MSG))

p = FakePane()
check("send: newlines become spaces", (send(p, "--text", "a\nb\n")[0], p.submitted), (0, ["a b"]))
p = FakePane()
check("send: an empty message is an error", (send(p, "--text", "  \n")[0], p.pastes), (1, []))
p = FakePane()
check("send: --read sends nothing", (send(p, "--read")[0], p.pastes, p.keys), (0, [], []))
for bad in (["--read", "--text", "x"], [], ["--text", "a", "--file", "b"]):
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            pane_send.parse(["t:1", *bad])
        raise AssertionError(f"arguments {bad} must be rejected")
    except SystemExit:
        check(f"send: arguments {bad} rejected", True, True)

# ---------------------------------------------------------------- pane_compact.py
def compact(pane, *argv):
    return quiet(pane_compact.run, pane_compact.parse(["t:1", "--wait-idle", "20", *argv]), pane)


p = FakePane(suggestion="wait for it")
check("compact: happy path", (compact(p, "--keep", "the role")[0], p.submitted, p.keys), (0, ["/compact the role"], ["Enter"]))

p = FakePane(rows=[("Shells", "sleep 900")])
check("compact: a background shell (the script itself, when self-compacting) does not block", compact(p)[0], 0)

p = FakePane()
p.agents = ["reviewing · since 10:26 PM"]
code, out = compact(p)
check("compact: a sub-agent is running: nothing typed", (code, p.pastes, p.keys, "sub-agent" in out), (2, [], [], True))
p = FakePane()
p.agents = ["reviewing · since 10:26 PM"]
check("compact: --ignore-agents overrides", compact(p, "--ignore-agents")[0], 0)

p = FakePane(rows=[("Shells", "a"), ("Background agents", "b")])
p.bare_total = True
check("compact: a bare 'N background tasks' total could hide an agent: nothing typed", (compact(p)[0], p.pastes), (2, []))

p = FakePane()
p.working = True
check("compact: mid-turn: nothing typed", (compact(p)[0], p.pastes), (2, []))
p = FakePane()
p.box = "theirs"
check("compact: the person's text: nothing typed", (compact(p)[0], p.pastes, p.box), (2, [], "theirs"))
p = FakePane()
p.in_mode = True
check("compact: copy mode: nothing typed", (compact(p)[0], p.pastes), (2, []))

p = FakePane()
p.on_paste = lambda q: setattr(q, "box", "and also " + q.box)
check("compact: the person typed in the gap: Enter withheld, exit 3", (compact(p)[0], p.keys, p.submitted), (3, [], []))
p = FakePane()
p.on_paste = lambda q: setattr(q, "prompt", True)
check("compact: a prompt appeared after the paste: Enter withheld", (compact(p)[0], p.keys, p.damage), (3, [], []))
p = FakePane()
p.on_paste = lambda q: setattr(q, "working", True)
check("compact: a turn started while typing: Enter withheld", (compact(p)[0], p.keys), (3, []))

p = FakePane(transcript=["❯ /compact earlier", "  ⎿  Compacted", "  I am compacting the notes now", "● Compacting is what I did"])
p.swallow_enter = True
check("compact: Enter lost, with an old 'Compacted' and the word 'compacting' on screen: exit 4, not started",
      (compact(p)[0], p.keys), (4, ["Enter"]))
p = FakePane(transcript=["❯ /compact earlier", "  ⎿  Compacted"])
p.eat_submit = True
check("compact: the box emptied but nothing new was echoed: an old 'Compacted' is not a finish", compact(p)[0], 4)
p = FakePane(transcript=["❯ /compact earlier", "  ⎿  Compacted"])
check("compact: a second compaction is verified against its own echo", compact(p)[0], 0)
p = FakePane()
p.swallow_enter = True
code, out = compact(p, "--timeout", "10")
check("compact: never started with a short --timeout is still 'did not start'", (code, "did not start" in out), (4, True))


# ---------------------------------------------------------------- uitasks.py
def ui(pane):
    with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(__file__))) as state:
        code, out = quiet(uitasks.run, uitasks.parse(["--pane", "t:1", "--state-dir", state]), pane)
    return code, out


TWO = [("Shells", "sleep 800"), ("Shells", "sleep 900")]
p = FakePane(rows=TWO)
code, out = ui(p)
check("ui: two rows, every key in order",
      (code, p.keys), (0, ["Down", "Enter", "Enter", "Left", "Down", "Enter", "Left", "Escape"]))
check("ui: dialog closed, nothing damaged", (p.dialog, p.damage), (None, []))
check("ui: both commands read", ('"command": "sleep 800"' in out, '"command": "sleep 900"' in out), (True, True))

p = FakePane(rows=[("Shells", "sleep 900")])
check("ui: one task opens its detail view directly", (ui(p)[0], p.keys, p.dialog, p.damage), (0, ["Down", "Enter", "Escape"], None, []))

p = FakePane(rows=TWO, transcript=["  Background", "  Status: all good", "  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)",
                                   "  enter to view tasks", "  Esc to close"])
check("ui: the same words in the transcript change nothing", (ui(p)[0], p.keys.count("Escape"), p.dialog, p.damage), (0, 1, None, []))

p = FakePane(rows=TWO)
p.close_lag = 30  # the dialog stays drawn for 3 s after Escape
check("ui: a slow redraw gets ONE Escape", (ui(p)[0], p.keys.count("Escape"), p.damage), (0, 1, []))

p = FakePane(rows=[("Shells", "make renders"), ("Background agents", "Review the parser"), ("Scheduled", "43 * * * * check")], old_layout=True)
code, out = ui(p)
check("ui: old layout: only the shell row is opened", (code, p.keys, p.damage), (0, ["Down", "Enter", "Enter", "Left", "Escape"], []))
check("ui: ... and the others are listed as not opened", out.count('"section": "Background agents"') >= 2, True)

class ShiftingPane(FakePane):
    """The first shell finishes just after its detail view is left: every row moves up one."""

    def key(self, pane, key):
        super().key(pane, key)
        if key == "Left" and len(self.rows) == 3:
            self.rows.pop(0)
            self.selected = 0


p = ShiftingPane(rows=[("Shells", "make A"), ("Shells", "make B"), ("Background agents", "Review the parser")], old_layout=True)
code, out = ui(p)
check("ui: the list shifts mid-walk: no Enter on the row that moved into place",
      (code, p.keys, p.damage), (3, ["Down", "Enter", "Enter", "Left", "Escape"], []))
check("ui: ... no detail filed under another row's name, and the reason is given",
      ("Review the parser" in out.split('"details"')[1].split('"not_opened"')[0], "the task list changed" in out), (False, True))

p = ShiftingPane(rows=[("Shells", "make A"), ("Shells", "make B"), ("Shells", "make C")])
code, out = ui(p)
check("ui: the list shifts mid-walk (all shells): stops, even though the next row is a shell",
      (code, p.keys, p.damage), (3, ["Down", "Enter", "Enter", "Left", "Escape"], []))

p = FakePane(rows=TWO)
p.fail_on_key = "Left"
try:
    ui(p)
    raise AssertionError("the tmux failure must propagate")
except RuntimeError:
    check("ui: a failure mid-run still closes the dialog", (p.keys[-1], p.dialog, p.damage), ("Escape", None, []))

p = FakePane(rows=TWO)
p.box = "typing"
check("ui: the person's text: no key sent", (ui(p)[0], p.keys), (2, []))
p = FakePane(rows=TWO)
p.in_mode = True
check("ui: copy mode: no key sent", (ui(p)[0], p.keys), (2, []))
p = FakePane(rows=[], transcript=["  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)"])
check("ui: 'to manage' only in the transcript: no key sent", (ui(p)[0], p.keys), (2, []))
p = FakePane(rows=TWO)
p.dialog = "list"
check("ui: a dialog the person already has open is left alone", (ui(p)[0], p.keys, p.dialog), (2, [], "list"))
p = FakePane(rows=TWO)
p.prompt = True
check("ui: permission prompt: no key sent", (ui(p)[0], p.keys), (2, []))


# ---------------------------------------------------------------- second review: should-fix items
# A long paste is shown as a "[Pasted text #N]" chip: its content cannot be checked.
p = FakePane()
p.chip = True
code, out = send(p, "--text", MSG)
check("send: the box shows a paste chip: Enter withheld", (code, p.keys, "placeholder" in out), (4, [], True))
p = FakePane()
check("send: a message long enough to become a chip is refused before typing",
      (send(p, "--text", "word " * 200)[0], p.pastes, p.keys), (1, [], []))
p = FakePane()
p.chip = True
check("compact: a chip in the box: Enter withheld", (compact(p, "--keep", "the handoff file")[0], p.keys), (3, []))
p = FakePane()
check("compact: --keep too long is refused before typing", (compact(p, "--keep", "word " * 200)[0], p.pastes), (1, []))

# Control characters would end the bracketed paste and arrive as keys (Escape, Ctrl-C).
for name, bad in (("ESC", "hello\x1b[201~ world"), ("Ctrl-C", "hello\x03world"), ("DEL", "a\x7fb"), ("C1", "a\x9bb")):
    p = FakePane()
    check(f"send: {name} in the message: refused, nothing typed", (send(p, "--text", bad)[0], p.pastes, p.keys), (1, [], []))
p = FakePane()
check("compact: ESC in --keep: refused, nothing typed", (compact(p, "--keep", "keep\x1bthis")[0], p.pastes, p.keys), (1, [], []))
p = FakePane()
check("send: tabs and newlines are still just spaces", (send(p, "--text", "a\tb\nc")[0], p.submitted), (0, ["a b c"]))

# The check before Enter must ignore colour: text of the person's that the colour
# heuristic took for a suggestion is still in the box next to the message.
p = FakePane()
p.grey_prefix = "their draft "
code, out = send(p, "--text", MSG)
check("send: the person's text drawn dim: typed, but Enter withheld", (code, p.pastes, p.keys, p.damage), (4, [MSG], [], []))
p = FakePane()
p.grey_prefix = "their draft "
check("compact: the person's text drawn dim: Enter withheld", (compact(p)[0], p.keys, p.damage), (3, [], []))

# A turn is running whenever a spinner line sits above the box, whatever the footer shows.
SPIN = "✻ Thinking… (12s · esc to interrupt)"
check("working: spinner above the box, footer cut before 'esc to int'",
      panelib.is_working(screen(f"{R}❯\xa0", above="✻ Thinking… (12s)", foot=("  ⏵⏵ auto mode on · 2 shells · esc t…",))), True)
check("working: a two-word spinner above the box, no hint in the footer",
      panelib.is_working(screen(f"{R}❯\xa0", above="✽ Compacting conversation… (3s)")), True)
check("working: the spinner glyph can be the reply bullet (seen live on 2.1.332)",
      panelib.is_working(screen(f"{R}❯\xa0", above="● Forming… (59s · ↓ 6.3k tokens · thinking)")), True)
check("working: minutes and seconds", panelib.is_working(screen(f"{R}❯\xa0", above="✻ Thinking… (1m 12s · esc to interrupt)")), True)
check("idle: column-0 lines with an ellipsis but no elapsed time are not spinners",
      [panelib.is_working(screen(f"{R}❯\xa0", above=l)) for l in ("⏺ Done… the files are written", "※ recap: … next: tests", "! ls…")],
      [False, False, False])
check("idle: a finished-turn line is not a spinner", panelib.is_working(screen(f"{R}❯\xa0", above="✻ Cooked for 2m 3s")), False)
check("idle: a reply or tool line with an ellipsis is not a spinner",
      (panelib.is_working(screen(f"{R}❯\xa0", above="● Thinking… about it")),
       panelib.is_working(screen(f"{R}❯\xa0", above="❯ Wait… what"))), (False, False))
check("idle: an indented spinner-like line is transcript", panelib.is_working(screen(f"{R}❯\xa0", above="  " + SPIN)), False)

# uitasks: Escape only while a dialog is open, also on the way out after a failure.
p = FakePane(rows=TWO)
p.no_dialog = True
check("ui: Enter opened nothing: no Escape on the way out, and focus is handed back with Up",
      (ui(p)[0], p.keys, p.damage, p.focus), (3, ["Down", "Enter", "Up"], [], False))

# A live input box means no dialog, whatever the footer says.
check("dialog: 'Esc to close' in the footer under a live input box is not a dialog",
      panelib.dialog_open(screen(f"{R}❯\xa0", foot=("  user@host:/dir", "  press Esc to close"))), False)

# Only a Compacted line BELOW the last echoed /compact counts.
old = "\n".join(["❯ /compact first", "  ⎿  Compacted", "● a reply", "❯ /compact second", RULE, f"{R}❯\xa0", RULE, FOOT])
check("compact marks: an earlier compaction's result does not finish this one", pane_compact.marks(old)[2], False)
check("compact marks: a result under the last echo does",
      pane_compact.marks(old.replace("❯ /compact second", "❯ /compact second\n  ⎿  Compacted"))[2], True)


# ---------------------------------------------------------------- third review: the focused task footer
# After Down the footer has focus ("enter to view tasks"): Enter opens the Background
# dialog instead of submitting the input box.
p = FakePane(rows=TWO)
p.focus = True
code, out = send(p, "--text", MSG)
check("send: the task footer has focus: nothing typed", (code, p.pastes, p.keys, "footer has focus" in out), (2, [], [], True))
p = FakePane(rows=TWO)
p.focus = True
check("compact: the task footer has focus: nothing typed", (compact(p)[0], p.pastes, p.keys), (2, [], []))


def focus_footer(pane):
    pane.focus = True


p = FakePane(rows=TWO)
p.on_paste = focus_footer  # the person presses Down between the check and the paste
check("send: the footer took focus in the gap: Enter withheld", (send(p, "--text", MSG)[0], p.keys, p.dialog), (4, [], None))
p = FakePane(rows=TWO)
p.on_paste = focus_footer
check("compact: the footer took focus in the gap: Enter withheld", (compact(p)[0], p.keys, p.dialog), (3, [], None))


class EnterOpensSomething(FakePane):
    """Enter does not submit: something without an input box takes over the screen."""

    def key(self, pane, key):
        self.keys.append(key)
        if key == "Enter":
            self.prompt = True


p = EnterOpensSomething()
code, out = send(p, "--text", MSG)
check("send: no input box after Enter is not 'sent'", (code, p.submitted, f"sent {len(MSG)} chars" in out), (3, [], False))


# ---------------------------------------------------------------- third review: remaining items
class EnterRewritesBox(FakePane):
    """Enter accepts a completion instead of submitting: the box changes, nothing is sent."""

    def key(self, pane, key):
        self.keys.append(key)
        if key == "Enter":
            self.box += "/README.md "


p = EnterRewritesBox()
code, out = send(p, "--text", "reply in @marketplace")
check("send: Enter changed the box without submitting: not 'sent'", (code, p.submitted, "NOT CONFIRMED" in out), (3, [], True))

wrapped = "\n".join(["❯ /compact keep the list of", "  Compacted results and the handoff", RULE, f"{R}❯\xa0", RULE, FOOT])
check("compact marks: the echoed --keep text wrapping onto a line that starts 'Compacted' is not a result",
      pane_compact.marks(wrapped)[2], False)

for name, bad in (("zero-width space", "a\u200bb"), ("right-to-left override", "a\u202eb")):
    p = FakePane()
    check(f"send: {name} in the message: refused, nothing typed", (send(p, "--text", bad)[0], p.pastes), (1, []))


def exit_code(fn, argv):
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn(argv)
    except SystemExit as e:
        return e.code
    return None


check("bad arguments exit 1, never 2 (2 means 'refused, nothing typed')",
      (exit_code(pane_send.parse, ["t:1"]), exit_code(pane_send.parse, ["t:1", "--read", "--history", "-5"]),
       exit_code(pane_compact.parse, []), exit_code(uitasks.parse, ["--no-such-option"])), (1, 1, 1, 1))

p = FakePane()
p.fail_on_key = "Enter"
code, out = send(p, "--text", MSG)
check("send: tmux fails after the paste: says the text was typed", (code, "was typed" in out), (1, True))
p = FakePane()
p.fail_on_key = "Enter"
code, out = compact(p)
check("compact: tmux fails after the paste: says the command was typed", (code, "was typed" in out), (1, True))

with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(__file__))) as state:
    old_umask = os.umask(0o022)
    try:
        quiet(uitasks.run, uitasks.parse(["--pane", "t:1", "--state-dir", state]), FakePane(rows=TWO))
    finally:
        os.umask(old_umask)
    pane_dirs = [os.path.join(state, d) for d in os.listdir(state)]
    check("ui: the per-pane snapshot directory is private (it holds full command lines)",
          [oct(os.stat(d).st_mode & 0o777) for d in pane_dirs], ["0o700"])


# ---------------------------------------------------------------- fourth review: one Up, never two
class TypesAfterDown(FakePane):
    """The person starts typing right after Down, and Up's change of focus is drawn
    very late. A second Up would land in the focused input box and recall history."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.lag = None

    def key(self, pane, key):
        if key == "Up":
            self.keys.append(key)
            if not self.focus or self.lag is not None:
                self.damage.append("Up sent into the input box: recalls the previous message over the person's text")
            else:
                self.lag = 60  # looks: longer than the 3 s unfocus() itself waits
            return
        super().key(pane, key)
        if key == "Down":
            self.box = "typing now"

    def look(self, pane):
        out = super().look(pane)
        if self.lag is not None:
            self.lag -= 1
            if self.lag < 0:
                self.focus, self.lag = False, None
        return out


p = TypesAfterDown(rows=TWO)
check("ui: the person typed after Down and the redraw lags: exactly one Up", (ui(p)[0], p.keys, p.damage, p.box), (3, ["Down", "Up"], [], "typing now"))


check("footer focus: seen in a footer cut short by a narrow pane",
      (panelib.footer_focused(screen(f"{R}❯\xa0", foot=("  ⏵⏵ auto mode on · 2 shells · enter to vie…",))),
       panelib.why_not_send(False, screen(f"{R}❯\xa0", foot=("  ⏵⏵ auto mode on · 2 shells · enter to vie…",))) is None), (True, False))
check("footer focus: not read from the transcript", panelib.footer_focused(screen(f"{R}❯\xa0", above="  enter to view tasks")), False)


class BrokenCapture(FakePane):
    """Every look after the paste fails in a way that is not a tmux error."""

    def look(self, pane):
        if self.pastes:
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        return super().look(pane)


p = BrokenCapture()
code, out = send(p, "--text", MSG)
check("send: any failure after the paste says the text was typed", (code, "was typed" in out, p.keys), (1, True, []))
p = BrokenCapture()
code, out = compact(p)
check("compact: any failure after the paste says the command was typed", (code, "was typed" in out, p.keys), (1, True, []))


# ---------------------------------------------------------------- fifth review: agent descriptions are not footer state
p = FakePane(rows=TWO)
p.agents = ["enter to validate the parser · since 10:26 PM"]
check("footer focus: an agent row that says 'enter to v…' is not the footer", panelib.footer_focused(p.render()), False)
code, out = ui(p)
check("ui: ... so no Up is sent into the input box on the way out", (code, p.keys.count("Up"), p.damage), (0, 0, []))
p = FakePane(rows=TWO)
p.agents = ["esc to interrupt the build · since 10:26 PM", "3 background tasks to manage"]
check("working / task count: agent rows are not read as footer state either",
      (panelib.is_working(p.render()), panelib.footer_task_count(p.render()), panelib.footer_has(p.render(), "to manage")), (False, 2, True))


p = FakePane(rows=TWO)
p.agents = ["Move center to viewport · since 10:26 PM"]
check("footer focus: '…center to v…' in an agent row is not the footer either", panelib.footer_focused(p.render()), False)
check("agent panel: a status line that is only a branch name is not the panel",
      (panelib.agent_panel(screen(f"{R}❯\xa0", foot=("  ⎇ main", FOOT))), panelib.background_agents(screen(f"{R}❯\xa0", foot=("  ⎇ main", FOOT)))),
      ([], False))


class ShiftsWhileNavigating(FakePane):
    """A shell finishes while the selection is being moved to the next row."""

    def key(self, pane, key):
        super().key(pane, key)
        if key == "Down" and self.dialog == "list" and len(self.rows) == 3:
            self.rows.pop(0)


p = ShiftsWhileNavigating(rows=[("Shells", "make A"), ("Shells", "make B"), ("Shells", "make C")])
code, out = ui(p)
check("ui: the list shifts during navigation: no Enter on whatever is selected now",
      (code, p.keys, p.damage), (3, ["Down", "Enter", "Enter", "Left", "Down", "Escape"], []))

WRAPPED_LIST = "\n".join(["● earlier reply", DRULE, "  Background", "  2 shells", "",
                          "  ❯ ● uv run --no-project a_script_with_a_very_long_name.py --and --many",
                          "      --more --options   running", "    ● sleep 900   running", "",
                          "  ↑/↓ to navigate · x to stop · Enter to view · Esc to close"])
got = uitasks.parse_list(WRAPPED_LIST)
check("list: a row wrapped onto a second line is one row, not two",
      (got["count"], len(got["rows"]), got["selected"], got["rows"][0]["text"].endswith("--more --options   running")), (2, 2, 0, True))

for first in ("!", "#"):
    p = FakePane()
    check(f"send: a message starting with {first!r} would switch the input mode: refused, nothing typed",
          (send(p, "--text", first + " ls")[0], p.pastes), (1, []))


# ---------------------------------------------------------------- sixth review: wrapped lines under "Earlier"
def earlier(*lines):
    return "\n".join(["● earlier reply", DRULE, "  Background", "  2 shells", "", "  ❯ ● sleep 800   running", "    ● sleep 900   running", "",
                      "      Earlier in this session (1)", *lines, "", "  ↑/↓ to navigate · x to stop · Enter to view · Esc to close"])


got = uitasks.parse_list(earlier("    ● uv run a_long_script.py --with --many", "        --more --options   completed"))
check("list: a finished row that wraps is not joined to a running row",
      [r["text"] for r in got["rows"]], ["sleep 800   running", "sleep 900   running"])
got = uitasks.parse_list(earlier("      make docs   completed"))
check("list: a finished row drawn without a status dot does not crash", (got["count"], len(got["rows"])), (2, 2))


DIRTY = screen(f"{R}❯\xa0", foot=("  ● main", "  ⏵⏵ auto mode on · 2 shells · esc to interrupt · enter to view tasks"))
check("agent panel: a status line '● main' ABOVE the mode line is not the panel head",
      (panelib.agent_panel(DIRTY), panelib.is_working(DIRTY), panelib.footer_focused(DIRTY), panelib.why_not_send(False, DIRTY) is None),
      ([], True, True, False))
p = FakePane(rows=TWO)
p.agents = ["reviewing · since 10:26 PM"]
check("agent panel: the real panel is still found", (panelib.agent_panel(p.render()), panelib.background_agents(p.render())),
      (["◯ general-purpose  reviewing · since 10:26 PM"], True))
check("footer count: with an input box and nothing under it, the transcript is not read",
      panelib.footer_task_count("\n".join(["  told it: 7 background tasks · ↓ to manage", RULE, f"{R}❯\xa0", RULE])), None)


# ---------------------------------------------------------------- seventh review: the panel's other lines
# From the 2.1.332 bundle: more than five agents end in a "↓ N more" row, a nested
# sub-agent's row starts with a tree connector, a scrolled panel's head carries "↑ N more".
MODE = "  ⏵⏵ auto mode on · 2 shells · ↓ to manage"
SIX = ["  ● main"] + [f"  ◯ general-purpose  task {i} · since 10:2{i} PM" for i in range(5)] + ["  ↓ 1 more"]
for name, panel, n in (
        ("six agents, '↓ 1 more' row", SIX, 6),
        ("a nested sub-agent, '└ ◯' row", ["  ● main", "  ◯ general-purpose  outer · since 10:26 PM", "    └ ◯ Explore  inner · since 10:27 PM"], 2),
        ("a scrolled panel, head '● main  ↑ 2 more'", ["  ● main  ↑ 2 more", "  ◯ general-purpose  third · since 10:26 PM"], 1),
        ("a line this script has never seen", ["  ● main", "  ◯ general-purpose  one · since 10:26 PM", "  something new"], 1)):
    s = screen(f"{R}❯\xa0", foot=("  user@host:/dir", MODE, *panel))
    check(f"agent panel: {name}: agents seen, agent rows not footer",
          (len([r for r in panelib.agent_panel(s) if "more" not in r.split()[-1:]]) >= 1, panelib.background_agents(s),
           any("since" in l for l in panelib.footer_lines(s)), panelib.footer_has(s, "to manage")), (True, True, False, True))
loud = screen(f"{R}❯\xa0", foot=("  user@host:/dir", MODE, "  ● main",
                                   *[f"  ◯ general-purpose  enter to view the logs {i} · esc to interrupt it" for i in range(5)], "  ↓ 1 more"))
check("agent panel: six agents whose descriptions quote footer phrases", (panelib.footer_focused(loud), panelib.is_working(loud)), (False, False))


class SixAgents(FakePane):
    def render(self):
        out = super().render()
        return out + "\n  ↓ 1 more" if (self.agents and not self.dialog and not self.prompt) else out


p = SixAgents()
p.agents = [f"task {i} · since 10:2{i} PM" for i in range(5)]
check("compact: six sub-agents running ('↓ 1 more'): nothing typed", (compact(p)[0], p.pastes), (2, []))

# The status line above the mode line is the person's own text; a footer phrase counts
# only as a whole "·"-separated item, the way the UI writes it.
for name, status, mode in (("'enter to view' in a status line", "  Press enter to view logs", FOOT),
                           ("'…center to view' in a status line", "  ~/src/center to view  main", FOOT),
                           ("'esc to interrupt' in a status line", "  job: esc to interrupt", FOOT)):
    s = screen(f"{R}❯\xa0", foot=(status, mode))
    check(f"footer: {name} is not UI state", (panelib.footer_focused(s), panelib.is_working(s)), (False, False))
s = screen(f"{R}❯\xa0", foot=("  user@host:/dir", "  ⏵⏵ auto mode on (shift+tab to cycle) · esc to interrupt · enter to view tasks"))
check("footer: the real items are still seen", (panelib.footer_focused(s), panelib.is_working(s)), (True, True))

MIXED = "\n".join(["● earlier reply", DRULE, "  Background", "  1 shell, 1 monitor", "", "  ❯ ● sleep 800   running", "    ● watch the log   running", "",
                   "  ↑/↓ to navigate · x to stop · Enter to view · Esc to close"])
got = uitasks.parse_list(MIXED)
check("list: an untitled list that is not only shells has no openable rows",
      (len(got["rows"]), [r["section"] in uitasks.OPENABLE for r in got["rows"]]), (2, [False, False]))


# ---------------------------------------------------------------- eighth review: the parenthesised footer hint
# The 2.1.332 bundle has a second footer form behind a server-side flag: the hint in
# parentheses straight after the task count, "4 shells (enter to view tasks)".
PAREN_FOCUS = screen(f"{R}❯\xa0", foot=("  user@host:/dir", "  ⏵⏵ auto mode on · 4 shells (enter to view tasks)"))
PAREN_IDLE = screen(f"{R}❯\xa0", foot=("  user@host:/dir", "  ⏵⏵ auto mode on · 4 shells (↓ to manage)"))
PAREN_BUSY = screen(f"{R}❯\xa0", foot=("  user@host:/dir", "  ⏵⏵ auto mode on · 4 shells (↓ to manage) (esc to interrupt)"))
check("footer: the parenthesised hint form is read",
      (panelib.footer_focused(PAREN_FOCUS), panelib.why_not_send(False, PAREN_FOCUS) is None, panelib.footer_focused(PAREN_IDLE),
       panelib.footer_has(PAREN_IDLE, "to manage"), panelib.footer_task_count(PAREN_IDLE), panelib.is_working(PAREN_BUSY)),
      (True, False, False, True, 4, True))


class ParenFooter(FakePane):
    def render(self):
        return super().render().replace(" · enter to view tasks", " (enter to view tasks)").replace(" · ↓ to manage", " (↓ to manage)")


p = ParenFooter(rows=TWO)
p.focus = True
check("send: parenthesised footer with focus: nothing typed", (send(p, "--text", MSG)[0], p.pastes, p.keys), (2, [], []))
p = ParenFooter(rows=TWO)
p.focus = True
check("compact: parenthesised footer with focus: nothing typed", (compact(p)[0], p.pastes, p.keys), (2, [], []))
p = ParenFooter(rows=TWO)
check("ui: parenthesised footer: a normal run", (ui(p)[0], p.keys, p.damage),
      (0, ["Down", "Enter", "Enter", "Left", "Down", "Enter", "Left", "Escape"], []))
p = ParenFooter(rows=TWO)
p.no_dialog = True
check("ui: parenthesised footer, Enter opened nothing: focus handed back", (ui(p)[0], p.keys, p.focus), (3, ["Down", "Enter", "Up"], False))

with tempfile.TemporaryDirectory(dir=os.path.dirname(os.path.abspath(__file__))) as state:
    args = uitasks.parse(["--pane", "t:1", "--state-dir", state])
    quiet(uitasks.run, args, FakePane(rows=TWO))
    for f in pathlib.Path(state).glob("*/*.json"):
        f.write_text("{ not json")
    time.sleep(1.1)  # the snapshot name has one-second resolution
    code, out = quiet(uitasks.run, args, FakePane(rows=TWO))
    check("ui: an unreadable previous snapshot does not hide this run's result", (code, "self-check ok" in out, "not compared" in out), (0, True, True))

print(f"\nall {N_CHECKS} checks passed")
