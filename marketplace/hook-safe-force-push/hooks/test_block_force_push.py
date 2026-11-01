#!/usr/bin/env python3
"""Tests for block_force_push.py.

Runs the hook as a subprocess exactly as hooks.json does (python3 <script>)
and asserts on the decision, the fields used, and fail-open behaviour.
"""

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent / "block_force_push.py"


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


# --- every direct force push is denied, with or without a branch -----------

@pytest.mark.parametrize("command", [
    "git push --force",
    "git push -f",
    "git push --force-with-lease",
    "git push origin --force",
    "git push --force origin main",
    "git push -uf origin main",
    "git push --force-with-lease=main origin main",
    "git push origin +main",                   # refspec force push
    "git push origin +HEAD:main",
    "git push origin feature +main",
    "cd repo && git push -f origin main",
])
def test_denies_force_push(command):
    assert decision(command) == "deny", command


# --- ordinary pushes and the safe wrappers are allowed ---------------------

@pytest.mark.parametrize("command", [
    "git push",
    "git push origin main",
    "git push -u origin feature",
    "git push --follow-tags",
    "git push --dry-run origin main",
    "git push origin HEAD:refs/heads/main",
    "git push origin :old-branch",              # delete, not force
    "git safe-force-push main",
    "git safe-force-push origin main",
    "git safe-force-push-lease origin main",
    "git fetch origin +refs/heads/*:refs/remotes/origin/*",  # + in a fetch refspec
])
def test_allows_safe_pushes(command):
    assert decision(command) == "allow", command


def test_non_bash_tool_is_ignored():
    assert hook("Write", {"file_path": "/x", "content": "git push -f"}) == {}


# --- what the model and the user each receive ------------------------------

def test_deny_reason_reaches_the_model():
    out = hook("Bash", {"command": "git push --force origin main"})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "safe-force-push" in reason
    assert out["systemMessage"]


def test_refspec_deny_names_the_plus_form():
    out = hook("Bash", {"command": "git push origin +main"})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "+" in reason and "refspec" in reason.lower()


# --- fail open, but visibly ------------------------------------------------

def test_bad_input_fails_open_with_visible_error():
    proc = run("this is not json")
    assert proc.returncode == 1
    assert proc.stdout.strip() == ""
    assert "block_force_push" in proc.stderr
