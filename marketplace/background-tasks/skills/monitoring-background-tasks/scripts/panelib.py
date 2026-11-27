"""Shared helpers for reading and driving a Claude Code TUI through tmux.

Everything that decides "is it safe to press a key" lives here so the scripts
agree, and so it can be unit-tested against saved screens (test_bgtasks.py).

A pane is addressed by a tmux target (`%53`, `session:window`, `session:window.pane`),
optionally on a named socket (`-L main`) and optionally on another host over ssh.
Scripts that send keys resolve the target ONCE to a pane id (`Tmux.resolve`) and use
that id from then on, so a window or pane switch cannot redirect later keys.

How a screen is read (verified on Claude Code 2.1.332):

  * Claude Code draws its own structure at column 0: the rule lines around the input
    box, the `❯` prompt, the rule above a dialog. Transcript text, including tool
    output that happens to contain the same words or a picture of another pane, is
    indented. So only column-0 rules count, and only the LAST one anchors anything.
  * Input box: `rule / ❯ line(s) / rule`, where the closing rule is the last column-0
    rule on screen. The lines below it are the footer (status line, mode line, agent
    panel). The few lines above it hold the spinner.
  * Dialog: everything below the last column-0 rule, when that block ends in a hint
    line containing "Esc to close".
"""
from __future__ import annotations

import argparse
import os
import re
import secrets
import shlex
import subprocess
import sys
import time
import unicodedata

ANSI = re.compile(r"\x1b\[[0-9;:]*m")
OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")  # hyperlinks, titles (BEL or ST terminated)
SGR = re.compile(r"\x1b\[([0-9;:]*)m")
PROMPT = "❯"
RULE = "─"
PASTED = re.compile(r"\[Pasted text #\d+[^\]]*\]")  # what the box shows for a long paste
MAX_MESSAGE = 400  # characters; see clean_message


class ArgParser(argparse.ArgumentParser):
    """Bad arguments exit 1. argparse's own exit status is 2, which these scripts use
    for "refused, nothing was typed"."""

    def error(self, message: str):
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


class Clock:
    """Time, replaceable in tests so wait loops run instantly."""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class Tmux:
    """Run tmux commands locally or on another host, never through a shell string we build by hand."""

    def __init__(self, socket: str | None = None, host: str | None = None):
        if host and host.startswith("-"):
            raise ValueError(f"host {host!r} looks like an option")
        self.socket, self.host = socket, host

    def argv(self, *args: str) -> list[str]:
        cmd = ["tmux"] + (["-L", self.socket] if self.socket else []) + list(args)
        if self.host:
            # ssh joins its arguments with spaces and hands them to the remote shell,
            # so quote once, here, with shlex.
            return ["ssh", "-o", "BatchMode=yes", self.host, shlex.join(cmd)]
        return cmd

    def run(self, *args: str, stdin: str | None = None) -> str:
        try:
            r = subprocess.run(self.argv(*args), input=stdin, capture_output=True, text=True)
        except FileNotFoundError as e:
            raise RuntimeError(f"cannot run {self.argv(*args)[0]!r}: {e}") from e
        if r.returncode != 0:
            raise RuntimeError(f"{' '.join(self.argv(*args))!r} failed ({r.returncode}): {r.stderr.strip()}")
        return r.stdout

    def resolve(self, target: str) -> str:
        """The pane id (`%N`) that `target` means right now."""
        out = self.run("display-message", "-p", "-t", target, "#{pane_id}").strip()
        if not re.fullmatch(r"%\d+", out):
            raise RuntimeError(f"tmux target {target!r} did not resolve to a pane (got {out!r})")
        return out

    def capture(self, target: str, colour: bool = False, history: int = 0) -> str:
        args = ["capture-pane", "-p", "-t", target]
        if colour:
            args.append("-e")
        if history:
            args += ["-S", f"-{history}"]
        return self.run(*args)

    def look(self, pane: str) -> tuple[bool, str]:
        """(pane is in copy/view mode, colour capture), from ONE tmux invocation.

        `capture-pane` reads the application's screen even while the person has the pane
        scrolled back in copy mode, so a capture alone looks safe; but `send-keys` would
        then go to copy mode, not to Claude Code. Every check before a key uses this."""
        out = self.run("display-message", "-p", "-t", pane, "#{pane_in_mode}", ";",
                       "capture-pane", "-p", "-e", "-t", pane)
        first, _, screen = out.partition("\n")
        if first.strip() not in ("0", "1"):
            raise RuntimeError(f"unexpected tmux reply for {pane}: {first!r}")
        return first.strip() == "1", screen

    def key(self, target: str, key: str) -> None:
        if key in ("x", "X"):
            raise ValueError("refusing to send 'x': in the Background dialog it stops the selected task")
        self.run("send-keys", "-t", target, key)

    def paste(self, target: str, text: str) -> None:
        """Put text into the pane's input without any shell or tmux key-name interpretation.
        The buffer name is unique per call: two scripts pasting at once must not swap texts."""
        buf = f"claude-bgtasks-{os.getpid()}-{secrets.token_hex(4)}"
        self.run("load-buffer", "-b", buf, "-", stdin=text)
        try:
            self.run("paste-buffer", "-p", "-d", "-b", buf, "-t", target)
        except RuntimeError:
            try:  # do not leave the message behind in a named buffer on the tmux server
                self.run("delete-buffer", "-b", buf)
            except RuntimeError:
                pass
            raise


def plain(screen: str) -> str:
    return ANSI.sub("", OSC.sub("", screen))


def is_rule(line: str) -> bool:
    """A rule line drawn by the UI: starts at column 0 (transcript text is indented)."""
    s = plain(line)
    return s.startswith(RULE) and s.count(RULE) >= 20


def clean_message(text: str) -> str:
    """`text` as one line, ready to paste into an input box. Raises ValueError for text
    that cannot be typed safely:

      * Control characters. tmux writes a buffer's bytes raw between the bracketed-paste
        markers, so an embedded ESC [ 201 ~ would end the paste early and the bytes after
        it (an Escape, a Ctrl-C) would arrive as keys.
      * Invisible format characters (zero-width space, direction overrides): the input
        box may not show them, so the check before Enter could not match.
      * More than MAX_MESSAGE characters. Claude Code shows a long paste as a
        "[Pasted text #N]" placeholder, and then nothing can check that the box holds
        this message and only this message.

    Tabs and newlines become single spaces (a newline would submit early)."""
    text = re.sub(r"\s+", " ", text).strip()
    bad = sorted({c for c in text if unicodedata.category(c) in ("Cc", "Cf")})
    if bad:
        raise ValueError("the message contains control or invisible format characters ("
                         + ", ".join(f"U+{ord(c):04X}" for c in bad) + "); remove them")
    if len(text) > MAX_MESSAGE:
        raise ValueError(f"the message is {len(text)} characters (limit {MAX_MESSAGE}): write it to a file the "
                         "other session can read and send a one-line pointer to it")
    return text


def squash(text: str) -> str:
    """Text with ALL whitespace removed, for comparing what was pasted with what the
    input box shows (the box re-wraps long text, sometimes mid-word)."""
    return re.sub(r"\s+", "", text.replace("\xa0", " "))


# ---- colour: telling the UI's grey suggestion from text the person typed

class _Sgr:
    """Foreground colour and dim, tracked across a whole capture. tmux emits colour
    changes only when they change, so the state carries over line breaks."""

    def __init__(self) -> None:
        self.dim, self.fg, self.inverse = False, None, False

    def feed(self, params: str) -> None:
        items = params.split(";") if params else ["0"]
        i = 0
        while i < len(items):
            it = items[i]
            if ":" in it:  # 38:5:N or 38:2::R:G:B in one item
                sub = [x for x in it.split(":") if x != ""]
                if sub and sub[0] == "38" and len(sub) >= 3:
                    self.fg = ("256", sub[2]) if sub[1] == "5" else ("rgb", tuple(sub[-3:]))
                i += 1
                continue
            try:
                n = int(it or 0)
            except ValueError:
                i += 1
                continue
            if n == 0:
                self.dim, self.fg, self.inverse = False, None, False
            elif n == 7:
                self.inverse = True
            elif n == 27:
                self.inverse = False
            elif n == 2:
                self.dim = True
            elif n == 22:
                self.dim = False
            elif 30 <= n <= 37 or 90 <= n <= 97:
                self.fg = ("basic", str(n))
            elif n == 39:
                self.fg = None
            elif n in (38, 48, 58):
                mode = items[i + 1] if i + 1 < len(items) else ""
                if mode == "5":
                    if n == 38 and i + 2 < len(items):
                        self.fg = ("256", items[i + 2])
                    i += 2
                elif mode == "2":
                    if n == 38 and i + 4 < len(items):
                        self.fg = ("rgb", tuple(items[i + 2:i + 5]))
                    i += 4
            i += 1

    @property
    def grey(self) -> bool:
        if self.dim:
            return True
        if self.fg is None:
            return False
        kind, val = self.fg
        try:
            if kind == "basic":
                return val == "90"
            if kind == "256":
                return int(val) == 8 or 237 <= int(val) <= 251
            r, g, b = (int(c) for c in val)
            return max(r, g, b) - min(r, g, b) <= 24 and 60 <= r <= 190
        except ValueError:
            return False


def _box(lines: list[str]) -> tuple[int, int, int] | None:
    """(top rule, prompt line, bottom rule) indexes of the input box in plain `lines`."""
    rules = [i for i, l in enumerate(lines) if is_rule(l)]
    if len(rules) < 2:
        return None
    bottom = rules[-1]
    for p in range(bottom - 1, 0, -1):
        if is_rule(lines[p]):
            return None  # nothing between the last two rules is a prompt
        if lines[p].startswith(PROMPT):
            above = next((j for j in range(p - 1, -1, -1) if lines[j].strip()), None)
            if above is not None and is_rule(lines[above]):
                return above, p, bottom
            return None
    return None


def input_box(screen: str) -> str | None:
    """What the person has typed in the input box, or "" if it is empty, or None if no
    input box is on screen (a dialog, a permission prompt, a shell, a crashed session).

    Pass a capture taken WITH colour (`capture-pane -e`): grey or dim text is the UI's
    own suggestion and is left out. Without colour a suggestion is indistinguishable from
    typed text and is reported as typed; `input_box(plain(screen))` is therefore the
    colour-blind reading: every character in the box, whoever put it there.
    """
    raw = OSC.sub("", screen).splitlines()
    span = _box([ANSI.sub("", l) for l in raw])
    if span is None:
        return None
    _, p, bottom = span
    state, out = _Sgr(), []
    cursor, cursor_at, grey_after_cursor = [], None, False
    for i, line in enumerate(raw[:bottom]):
        seen_prompt = i > p
        for tok in re.split(r"(\x1b\[[0-9;:]*m)", line):
            m = SGR.fullmatch(tok)
            if m:
                state.feed(m.group(1))
                continue
            if i < p:
                continue
            if not seen_prompt:
                if PROMPT not in tok:
                    continue
                tok, seen_prompt = tok.split(PROMPT, 1)[1], True
            if state.inverse:
                cursor.append(tok)
                cursor_at = len(out)
            elif state.grey:
                grey_after_cursor = grey_after_cursor or (cursor_at is not None and bool(tok.strip()))
            else:
                out.append(tok)
        if i >= p:
            out.append(" ")
    # The cursor is drawn in inverse video. On an empty box it is an inverse space; over a
    # suggestion it is the suggestion's FIRST LETTER in inverse with the rest grey after it.
    # Any other inverse text (the cursor moved back onto typed text) is the person's.
    under = "".join(cursor)
    typed = "".join(out)
    if under.strip() and not (len(under.strip()) == 1 and grey_after_cursor and not typed.strip()):
        out.insert(cursor_at, under)
    return re.sub(r"\s+", " ", "".join(out).replace("\xa0", " ")).strip()


def has_input_box(screen: str) -> bool:
    return input_box(screen) is not None


# The sub-agent panel under the footer, as Claude Code 2.1.332 draws it:
#     ● main                      head; "● main  ↑ 2 more" when scrolled
#     ◯ general-purpose  <description> · since 10:26 PM
#       └ ◯ Explore  <description>           a nested sub-agent, behind a tree connector
#     ↓ 1 more                               when more than five rows
PANEL_HEAD = re.compile(r"\s*[●◯○◉⏺]\s+main(?:\s+.*)?")
PANEL_ROW = re.compile(r"\s*(?:(?:[├└│]\s*)*[●◯○◉⏺]\s+\S|[↑↓]\s+\d+\s+more\b)")


def _below_box(screen: str) -> tuple[list[str], list[str]]:
    """(footer lines, agent panel rows): the plain non-empty lines below the input box,
    split at the panel's "● main" row. Both empty when there is no input box on screen."""
    lines = plain(screen).splitlines()
    span = _box(lines)
    below = [l for l in lines[span[2] + 1:] if l.strip()] if span else []
    heads = [i for i, l in enumerate(below) if PANEL_HEAD.fullmatch(l)]
    if not heads:
        return below, []
    # The panel is the last thing on screen, so its head is the LAST line that looks
    # like one. Lines after the head that look like panel rows are the panel; any other
    # line after it stays a footer line. That keeps both mistakes safe: a custom status
    # line reading "● main" above the mode line does not hide the mode line, and a panel
    # line this script has never seen does not turn the agent rows back into footer text.
    i = heads[-1]
    after = below[i + 1:]
    return below[:i] + [l for l in after if not PANEL_ROW.match(l)], [l for l in after if PANEL_ROW.match(l)]


def footer_lines(screen: str) -> list[str]:
    """The plain lines below the input box that the UI itself writes: status line and
    mode line. The sub-agent panel under them is NOT included: its rows carry each
    agent's description, free text that can contain any footer phrase ("enter to
    validate…", "esc to interrupt the build"). Empty when there is no input box."""
    return _below_box(screen)[0]


def above_box(screen: str, n: int = 6) -> list[str]:
    """The last `n` non-empty plain lines above the input box: where the spinner is."""
    lines = plain(screen).splitlines()
    span = _box(lines)
    return [l for l in lines[:span[0]] if l.strip()][-n:] if span else []


def status_tail(screen: str, n: int = 8) -> list[str]:
    return [l for l in plain(screen).splitlines() if l.strip()][-n:]


# A running turn's spinner line, at column 0: one glyph, a few words ending in an
# ellipsis, then a parenthesis that starts with the elapsed time:
#     ✻ Thinking… (12s · esc to interrupt)
#     ● Forming… (59s · ↓ 6.3k tokens · thinking)      <- the glyph can be the reply bullet
# The elapsed time is what tells it from a reply or a recap that happens to contain an
# ellipsis ("● Done… the files are written"). A finished turn leaves "✻ Cooked for 2m 3s".
# In its first second a spinner may have no time yet; the footer's "esc to int" covers that.
SPINNER_BUSY = re.compile(r"^\S \S+(?: \S+){0,3}… \(\d+[hms]\b")


def _footer_item(screen: str, prefix: str) -> bool:
    """A footer hint starting with `prefix` is on screen. Claude Code 2.1.332 writes a
    hint either as a whole "·"-separated item ("… · 4 shells · enter to view tasks") or,
    behind a server-side flag, in parentheses after the item before it ("… · 4 shells
    (enter to view tasks)"). The status line above the mode line is the person's own
    text and may contain the same words mid-sentence, which is neither form."""
    hint = re.compile(r"(?:^|[·(])\s*" + re.escape(prefix))
    return any(hint.search(l.strip()) for l in footer_lines(screen))


def footer_has(screen: str, phrase: str) -> bool:
    """`phrase` is in the footer below the input box. Never search the whole screen for
    a footer phrase: the transcript quotes them ("↓ to manage" follows every backgrounded
    agent, and this skill's own output mentions them)."""
    return any(phrase in l for l in footer_lines(screen))


def is_working(screen: str) -> bool:
    """A turn is in progress (a message sent now is queued, not read at once).

    With an input box on screen, either sign is enough: "esc to int…" anywhere in the
    footer (however many agent rows follow it), or a spinner line at column 0 just
    above the box. The spinner does not depend on how much of the footer a narrow pane
    left visible. The transcript, which may quote the same words, is never looked at.
    Without an input box (a dialog, or a bare footer string): the last lines of the screen."""
    if not has_input_box(screen):
        return any("esc to int" in l for l in status_tail(screen))
    return _footer_item(screen, "esc to int") or any(SPINNER_BUSY.match(l) for l in above_box(screen))


def agent_panel(screen: str) -> list[str]:
    """The sub-agent rows of the panel under the footer ("● main" then one row each)."""
    return [r.strip() for r in _below_box(screen)[1]]


def background_agents(screen: str) -> bool | None:
    """True if the screen shows a sub-agent of this session still running, False if it
    shows none, None if the footer only gives a total that could include agents.

    Seen on 2.1.332: a spinner line "Waiting for 1 background agent to finish", and an
    agent panel under the footer ("● main" then one "◯ <type> …" row per agent). The
    footer's own count ("2 shells") does not include agents there. The earlier wording
    "N background tasks" does not say what the tasks are."""
    if any(re.match(r"\S Waiting for .*background agent", l) for l in above_box(screen)):
        return True
    foot = footer_lines(screen)
    if agent_panel(screen) or any(re.search(r"\b\d+ (?:background |sub)?agents?\b", l) for l in foot):
        return True
    if any(re.search(r"\d+ background tasks?", l) for l in foot):
        return None
    return False


FOOTER_FOCUSED = "the task footer has focus (someone pressed Down): Enter would open the Background dialog, not submit"


def footer_focused(screen: str) -> bool:
    """Down from an empty input box moves focus to the task footer, which then reads
    "enter to view tasks". Text can still land in the box, but Enter opens the
    Background dialog instead of submitting. Matches a footer cut short by a narrow
    pane ("enter to vie…") too; cut shorter than that, it cannot be told apart."""
    return _footer_item(screen, "enter to v")


def why_not_send(in_mode: bool, screen: str, allow_working: bool = False) -> str | None:
    """Why nothing may be typed into this pane now, or None if it is safe.
    `screen` must be a colour capture taken together with `in_mode` (`Tmux.look`)."""
    if in_mode:
        return "the pane is in copy mode (the person is scrolling back); keys would not reach Claude Code"
    box = input_box(screen)
    if box is None:
        return "no Claude Code input box on screen (a dialog, a permission prompt, or not a Claude session)"
    if box:
        return f"the person has text in the input box: {box!r}"
    if footer_focused(screen):
        return FOOTER_FOCUSED
    if is_working(screen) and not allow_working:
        return "the session is mid-turn"
    return None


def confirm_typed(tm: Tmux, pane: str, text: str, clock: Clock, timeout: float = 4.0) -> tuple[bool, str, str]:
    """After a paste, before Enter: (ok, last colour screen, reason when not ok).

    ok only when the input box holds exactly `text` and nothing else, read WITHOUT
    regard to colour. That catches the person typing between the check and the paste
    (their text and ours would be submitted together), a dialog or permission prompt
    that appeared meanwhile (Enter would answer it), and any typed text the colour
    heuristic took for a suggestion. Focus on the task footer is not ok either (Enter
    would open the Background dialog). A "[Pasted text #N]" placeholder is never ok:
    it hides what it stands for, which could be the person's own paste."""
    end = clock.now() + timeout
    while True:
        in_mode, screen = tm.look(pane)
        got = input_box(plain(screen))
        if not in_mode and got is not None and squash(got) == squash(text) and not footer_focused(screen):
            return True, screen, ""
        if clock.now() >= end:
            break
        clock.sleep(0.3)
    if in_mode:
        return False, screen, "the pane went into copy mode"
    if got is None:
        return False, screen, "the input box is gone (a dialog or permission prompt appeared)"
    if not got:
        return False, screen, "the text did not appear in the input box"
    if footer_focused(screen):
        return False, screen, FOOTER_FOCUSED
    if PASTED.search(got):
        return False, screen, ("the input box shows a pasted-text placeholder, which cannot be checked "
                               f"against the message: {got!r}")
    return False, screen, f"the input box holds something other than the message: {got!r}"


def dialog_lines(screen: str) -> list[str] | None:
    """The plain lines of an open dialog, or None. A dialog is the block below the last
    column-0 rule whose last line is a key hint containing "Esc to close"; while one is
    open there is no input box. Words like "Background" or "Status:" higher up, in the
    transcript, are not looked at."""
    lines = plain(screen).splitlines()
    if _box(lines) is not None:
        return None
    rules = [i for i, l in enumerate(lines) if is_rule(l)]
    if not rules:
        return None
    block = lines[rules[-1] + 1:]
    last = next((l for l in reversed(block) if l.strip()), "")
    return block if "Esc to close" in last else None


def list_open(screen: str) -> bool:
    """The Background tasks LIST dialog is open."""
    d = dialog_lines(screen)
    return d is not None and next((l.strip() for l in d if l.strip()), "") == "Background"


def detail_open(screen: str) -> bool:
    """One task's DETAIL view is open. With a single background task, Enter on the
    footer opens this directly and the list is never shown."""
    d = dialog_lines(screen)
    return d is not None and not list_open(screen) and any(re.match(r"\s*Status:\s", l) for l in d)


def dialog_open(screen: str) -> bool:
    """A dialog that Escape closes is open (the Background list, a detail view, or
    another one with the same "Esc to close" hint), so Escape will not interrupt a turn."""
    return dialog_lines(screen) is not None


def footer_task_count(screen: str) -> int | None:
    """The task count in the footer, if shown. Claude Code versions word it differently:
    'N background tasks', or a breakdown such as '2 shells' (summed here). On 2.1.332
    the breakdown leaves sub-agents out; they are listed in the panel under the footer."""
    for l in reversed(footer_lines(screen) if has_input_box(screen) else status_tail(screen, 4)):
        if "to man" not in l and "background task" not in l and "to view tasks" not in l:
            continue
        m = re.search(r"(\d+) background tasks?", l)
        if m:
            return int(m.group(1))
        parts = re.findall(r"(\d+) (?:shell|agent|monitor|task|scheduled|teammate)s?\b", l)
        if parts:
            return sum(int(p) for p in parts)
    return None
