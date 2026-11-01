#!/usr/bin/env python3
"""Tests for block_inline_scripts.py.

Runs the hook as a subprocess exactly as hooks.json does (python3 <script>)
and asserts on the decision, the fields used, and fail-open behaviour.
"""

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent / "block_inline_scripts.py"


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


# --- inline python: denied however it is spelled ---------------------------

@pytest.mark.parametrize("command", [
    'python -c "print(1)"',
    "python3 -c 'print(1)'",
    "python3.13 -c 'print(1)'",
    "/usr/bin/python3 -c 'print(1)'",
    'uv run python -c "print(1)"',
    "uv run python -I -c 'print(1)'",          # flag between python and -c
    "uv run --no-project python -I -c 'x'",
    "python3 -u -B -c 'print(1)'",
    # 2026-11-01 review
    "python3 -c'print(1)'",                    # no space after -c
    "uv run python@3.12 -c 'print(1)'",        # uv interpreter spelling
    'echo "$(python3 -c \'print(1)\')"',       # $( ) inside double quotes still runs
])
def test_denies_inline_python(command):
    assert decision(command) == "deny", command


# --- unquoted / double-quoted heredocs: denied -----------------------------

@pytest.mark.parametrize("command", [
    "cat << EOF\nhello $USER\nEOF",
    "cat <<EOF\nhello\nEOF",
    'cat <<"EOF"\nhello\nEOF',
    "cat <<-EOF\n\thello\nEOF",
])
def test_denies_expanding_heredocs(command):
    assert decision(command) == "deny", command


# --- legitimate forms: allowed ---------------------------------------------

@pytest.mark.parametrize("command", [
    "cat <<'EOF'\nhello $USER\nEOF",
    "git commit -m \"$(cat <<'EOF'\nfix: thing\nEOF\n)\"",
    "uv run python3 ./tmp/my_script.py",
    "python3 -m pytest -c pytest.ini",         # -c belongs to pytest, not python
    "python3 script.py -c config.toml",        # -c is the script's own option
    "pip install -c constraints.txt pkg",
    # 2026-11-01 review: text inside quotes is neither an interpreter nor a heredoc
    'git commit -m "fix python -c handling"',
    "echo 'write <<EOF'",
    "grep -n 'python -c' hooks.py",
])
def test_allows_scripts_and_quoted_heredocs(command):
    assert decision(command) == "allow", command


def test_non_bash_tool_is_ignored():
    assert hook("Write", {"file_path": "/x", "content": "python -c 'x'"}) == {}


# --- what the model and the user each receive ------------------------------

def test_python_c_reason_reaches_the_model():
    out = hook("Bash", {"command": "python3 -c 'print(1)'"})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "python -c" in reason
    assert "Write" in reason                   # tells the model what to do instead
    assert out["systemMessage"]


def test_heredoc_reason_reaches_the_model():
    out = hook("Bash", {"command": "cat << EOF\nx\nEOF"})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "<<'EOF'" in reason
    assert out["systemMessage"]


# --- fail open, but visibly ------------------------------------------------

def test_bad_input_fails_open_with_visible_error():
    proc = run("this is not json")
    assert proc.returncode == 1
    assert proc.stdout.strip() == ""
    assert "block_inline_scripts" in proc.stderr
