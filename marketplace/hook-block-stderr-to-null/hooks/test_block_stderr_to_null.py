#!/usr/bin/env python3
"""Tests for block_stderr_to_null.py.

Runs the hook as a subprocess exactly as hooks.json does (python3 <script>)
and asserts on the decision, the fields used, and fail-open behaviour.
"""

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent / "block_stderr_to_null.py"


def run(payload):
    return subprocess.run(["python3", str(HOOK)], input=payload,
                          capture_output=True, text=True)


def hook(tool_name, tool_input):
    proc = run(json.dumps({"tool_name": tool_name, "tool_input": tool_input}))
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def decision(command):
    out = hook("Bash", {"command": command})
    return out.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


# --- forms that silence stderr: all must be denied -------------------------

@pytest.mark.parametrize("command", [
    "ls 2>/dev/null",
    "ls 2> /dev/null",
    "ls >/dev/null 2>&1",
    "ls > /dev/null 2>&1",
    "ls 1>/dev/null 2>&1",
    "ls >>/dev/null 2>&1",
    "ls &>/dev/null",
    "ls &>>/dev/null",
    "ls >&/dev/null",
    "ls 2>&-",
    "make 2>/dev/null | tail",
    "cmd1 && cmd2 2>/dev/null",
    # 2026-11-01 review
    'ls 2>"/dev/null"',
    "ls 2>'/dev/null'",
    "ls>/dev/null 2>&1",             # no space before the operator
    "ls&>/dev/null",
    'echo "$(ls 2>/dev/null)"',      # $( ) inside double quotes still runs
])
def test_denies_silenced_stderr(command):
    assert decision(command) == "deny", command


# --- forms that keep stderr visible: all must be allowed -------------------

@pytest.mark.parametrize("command", [
    "ls >/dev/null",                 # stdout only
    "ls 2>&1 | tee build.log",       # stderr merged into the pipe
    "ls 2>&1 >/dev/null",            # stderr goes to the ORIGINAL stdout (visible)
    "ls 2>err.log",                  # captured to a file
    "ls >/dev/null && other 2>&1",   # 2>&1 belongs to a different command
    "ls >/dev/null; other 2>&1",
    "grep -r foo . 2>&1 | head",
    # 2026-11-01 review: text inside quotes is not a redirection
    'git commit -m "stop using 2>/dev/null"',
    "grep -rn '2>/dev/null' marketplace/",
    'echo "2>/dev/null is bad"',
    "ls 12>/dev/null",               # fd 12, not stderr
])
def test_allows_visible_stderr(command):
    assert decision(command) == "allow", command


def test_non_bash_tool_is_ignored():
    assert hook("Write", {"file_path": "/x", "content": "2>/dev/null"}) == {}


# --- what the model and the user each receive ------------------------------

def test_deny_reason_reaches_the_model():
    """permissionDecisionReason is the field Claude Code shows to the model."""
    out = hook("Bash", {"command": "ls 2>/dev/null"})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "/dev/null" in reason
    assert "instead" in reason.lower()


def test_deny_also_tells_the_user():
    out = hook("Bash", {"command": "ls 2>/dev/null"})
    assert out["systemMessage"]


# --- fail open, but visibly ------------------------------------------------

def test_bad_input_fails_open_with_visible_error():
    """Non-JSON stdin: exit 1 (non-blocking), nothing on stdout, error on stderr."""
    proc = run("this is not json")
    assert proc.returncode == 1
    assert proc.stdout.strip() == ""
    assert "block_stderr_to_null" in proc.stderr
