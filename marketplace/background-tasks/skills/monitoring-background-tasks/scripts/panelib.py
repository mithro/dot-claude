"""Shared helpers for reading and driving a Claude Code TUI through tmux.

Everything that decides "is it safe to press a key" lives here so the scripts
agree, and so it can be unit-tested against saved screens (test_panelib.py).

A pane is addressed by a tmux target (`%53`, `session:window`, `session:window.pane`),
optionally on a named socket (`-L main`) and optionally on another host over ssh.
"""
from __future__ import annotations

import re
import shlex
import subprocess

ANSI = re.compile(r"\x1b\[[0-9;:]*m")
PROMPT = "❯"  # ❯
RULE = "─"  # ─


class Tmux:
    """Run tmux commands locally or on another host, never through a shell string we build by hand."""

    def __init__(self, socket: str | None = None, host: str | None = None):
        self.socket, self.host = socket, host

    def argv(self, *args: str) -> list[str]:
        cmd = ["tmux"] + (["-L", self.socket] if self.socket else []) + list(args)
        if self.host:
            # ssh joins its arguments with spaces and hands them to the remote shell,
            # so quote once, here, with shlex.
            return ["ssh", "-o", "BatchMode=yes", self.host, shlex.join(cmd)]
        return cmd

    def run(self, *args: str, stdin: str | None = None) -> str:
        r = subprocess.run(self.argv(*args), input=stdin, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"{' '.join(self.argv(*args))!r} failed ({r.returncode}): {r.stderr.strip()}")
        return r.stdout

    def capture(self, target: str, colour: bool = False, history: int = 0) -> str:
        args = ["capture-pane", "-p", "-t", target]
        if colour:
            args.append("-e")
        if history:
            args += ["-S", f"-{history}"]
        return self.run(*args)

    def key(self, target: str, key: str) -> None:
        if key in ("x", "X"):
            raise ValueError("refusing to send 'x': in the Background dialog it stops the selected task")
        self.run("send-keys", "-t", target, key)

    def paste(self, target: str, text: str) -> None:
        """Put text into the pane's input without any shell or tmux key-name interpretation."""
        buf = "claude-bgtasks"
        self.run("load-buffer", "-b", buf, "-", stdin=text)
        self.run("paste-buffer", "-p", "-d", "-b", buf, "-t", target)


OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\\\)")  # hyperlinks, titles


def plain(screen: str) -> str:
    return ANSI.sub("", OSC.sub("", screen))


def is_rule(line: str) -> bool:
    s = plain(line).strip()
    return s.startswith(RULE) and s.count(RULE) >= 20


def _visible_default_colour(segment: str) -> str:
    """Text of `segment` that is NOT dim/grey. Claude Code draws its own suggestions
    (ghost text) dim or grey; text the person typed is in the default colour."""
    out, grey = [], False
    for tok in re.split(r"(\x1b\[[0-9;:]*m)", segment):
        if tok.startswith("\x1b["):
            codes = [c for c in re.split(r"[;:]", tok[2:-1])]
            if codes in (["0"], [""], ["39"], ["22"]) or "0" == codes[0]:
                grey = False
            if "2" in codes[:1] or "90" in codes:
                grey = True
            if codes[:2] == ["38", "5"] and len(codes) >= 3 and (codes[2] == "8" or codes[2].isdigit() and 237 <= int(codes[2]) <= 251):
                grey = True
            if codes[:2] == ["38", "2"] and len(codes) >= 5:
                try:
                    r, g, b = (int(c) for c in codes[2:5])
                    if max(r, g, b) - min(r, g, b) <= 24 and 60 <= r <= 190:
                        grey = True
                except ValueError:
                    pass
        elif not grey:
            out.append(tok)
    return "".join(out)


def input_box(colour_screen: str) -> str | None:
    """What the person has typed in the input box, or "" if it is empty, or None if no
    input box is on screen (a dialog, a permission prompt, a shell, a crashed session).

    The box is the block that starts with a `❯` line directly below a rule line and runs
    to the next rule line. Earlier `❯` lines higher up are past messages, not the box.
    Pass a capture taken WITH colour (`capture-pane -e`); without colour a grey
    suggestion is indistinguishable from typed text and is reported as typed.
    """
    lines = colour_screen.splitlines()
    for i in range(len(lines) - 1, 0, -1):
        if not plain(lines[i]).lstrip().startswith(PROMPT):
            continue
        above = next((lines[j] for j in range(i - 1, -1, -1) if plain(lines[j]).strip()), "")
        if not is_rule(above):
            continue
        parts = [lines[i].split(PROMPT, 1)[1]]
        for l in lines[i + 1:]:
            if is_rule(l):
                break
            parts.append(l)
        else:
            return None  # no closing rule: not an input box
        text = " ".join(_visible_default_colour(p) for p in parts)
        return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
    return None


def status_tail(screen: str, n: int = 8) -> list[str]:
    return [l for l in plain(screen).splitlines() if l.strip()][-n:]


def is_working(screen: str) -> bool:
    """A turn is in progress (a message sent now is queued, not read at once)."""
    return any("esc to interrupt" in l for l in status_tail(screen))


def has_input_box(colour_screen: str) -> bool:
    return input_box(colour_screen) is not None


def list_open(screen: str) -> bool:
    """The Background tasks LIST dialog is open."""
    p = plain(screen)
    return bool(re.search(r"^\s*Background\s*$", p, re.M)) and "Esc to close" in "\n".join(status_tail(p, 3))


def detail_open(screen: str) -> bool:
    """One task's DETAIL view is open. With a single background task, Enter on the
    footer opens this directly and the list is never shown."""
    p = plain(screen)
    return bool(re.search(r"^\s*Status:\s", p, re.M)) and "Esc to close" in "\n".join(status_tail(p, 3))


def dialog_open(screen: str) -> bool:
    """Any Background tasks dialog (list or detail) is open, so Escape closes it
    instead of interrupting the turn."""
    return list_open(screen) or detail_open(screen)


def footer_task_count(screen: str) -> int | None:
    """The task count in the footer, if shown. Claude Code versions word it differently:
    'N background tasks', or a breakdown such as '1 shell · 2 agents' (summed here)."""
    for l in reversed(status_tail(screen, 4)):
        if "to manage" not in l and "background task" not in l:
            continue
        m = re.search(r"(\d+) background tasks?", l)
        if m:
            return int(m.group(1))
        parts = re.findall(r"(\d+) (?:shell|agent|monitor|task|scheduled|teammate)s?\b", l)
        if parts:
            return sum(int(p) for p in parts)
    return None
