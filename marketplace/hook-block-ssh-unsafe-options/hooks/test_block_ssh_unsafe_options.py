#!/usr/bin/env python3
"""Tests for block_ssh_unsafe_options.py.

Runs the hook as a subprocess exactly as hooks.json does (python3 <script>)
and asserts on the decision, the fields used, and fail-open behaviour.
"""

import json
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent / "block_ssh_unsafe_options.py"

# Built by concatenation so the live hook does not deny writing this file.
SHKC_NO = "StrictHostKeyChecking" + " no"
UKHF_NULL = "UserKnownHostsFile" + " /dev/null"


def run(payload):
    return subprocess.run(["python3", str(HOOK)], input=payload,
                          capture_output=True, text=True)


def hook(tool_name, tool_input):
    proc = run(json.dumps({"tool_name": tool_name, "tool_input": tool_input}))
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def decision(tool_name, tool_input):
    out = hook(tool_name, tool_input)
    return out.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


def bash(command):
    return decision("Bash", {"command": command})


# --- command line: both ssh option spellings ---------------------------------

@pytest.mark.parametrize("command", [
    "ssh -o StrictHostKeyChecking=no host",
    "ssh -oStrictHostKeyChecking=no host",
    "ssh -o 'StrictHostKeyChecking no' host",
    'ssh -o "StrictHostKeyChecking no" host',
    "ssh -o UserKnownHostsFile=/dev/null host",
    "ssh -o 'UserKnownHostsFile /dev/null' host",
    "scp -o StrictHostKeyChecking=no file host:/tmp/",
    "ssh -o stricthostkeychecking=NO host",       # case-insensitive
    # 2026-11-01 review: synonyms and spellings ssh accepts
    "ssh -o StrictHostKeyChecking=off host",
    "ssh -o StrictHostKeyChecking=false host",
    "ssh -o=StrictHostKeyChecking=no host",       # readconf tolerates a leading =
    "ssh -4oStrictHostKeyChecking=no host",       # clustered short flags
    "ssh -o GlobalKnownHostsFile=/dev/null host",
    "ssh -o 'UserKnownHostsFile=/dev/null' host",
    "ssh -tto StrictHostKeyChecking=no host",
    "sftp -o StrictHostKeyChecking=no host",
    "sudo ssh -o StrictHostKeyChecking=no host",
    "GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no' git fetch",
    "rsync -e 'ssh -o UserKnownHostsFile=/dev/null' a host:/tmp/",
    "/usr/bin/ssh -o StrictHostKeyChecking=no host",
])
def test_denies_unsafe_cli_options(command):
    assert bash(command) == "deny", command


@pytest.mark.parametrize("line", [
    "StrictHostKeyChecking" + "=no",
    "StrictHostKeyChecking" + " off",
    "StrictHostKeyChecking" + " false",
    "StrictHostKeyChecking" + " no # until the lab is rekeyed",
    "StrictHostKeyChecking" + "\tno",
    "UserKnownHostsFile" + "=/dev/null",
    "GlobalKnownHostsFile" + " /dev/null",
])
def test_denies_config_spellings(line):
    assert decision("Write", {
        "file_path": "/home/tim/.ssh/config",
        "content": f"Host x\n    {line}\n",
    }) == "deny", line


def test_allows_edit_that_keeps_existing_unsafe_line_as_context():
    """Editing a neighbouring line must not re-deny an option that was already there."""
    assert decision("Edit", {
        "file_path": "/home/tim/.ssh/config",
        "old_string": f"Host lab\n    {SHKC_NO}\n    User root\n",
        "new_string": f"Host lab\n    {SHKC_NO}\n    User tim\n",
    }) == "allow"


def test_denies_edit_that_adds_a_second_unsafe_line():
    assert decision("Edit", {
        "file_path": "/home/tim/.ssh/config",
        "old_string": f"Host lab\n    {SHKC_NO}\n",
        "new_string": f"Host lab\n    {SHKC_NO}\n    {UKHF_NULL}\n",
    }) == "deny"


@pytest.mark.parametrize("command", [
    "ssh -o StrictHostKeyChecking=accept-new host",
    "ssh -o StrictHostKeyChecking=yes host",
    "ssh -o StrictHostKeyChecking=ask host",
    "ssh -o UserKnownHostsFile=~/.ssh/known_hosts_project host",
    "ssh host",
    "grep -r StrictHostKeyChecking=no docs/",     # not an ssh -o option
    # round-2 review: an audit grep whose flag cluster ends in o
    "grep -rno StrictHostKeyChecking=no .",
    "grep -o 'UserKnownHostsFile /dev/null' ~/.ssh/config",
])
def test_allows_safe_cli_options(command):
    assert bash(command) == "allow", command


# --- files: only ssh config files are in scope -------------------------------

def test_denies_write_of_ssh_config_with_strict_no():
    assert decision("Write", {
        "file_path": "/home/tim/.ssh/config",
        "content": f"Host x\n    {SHKC_NO}\n",
    }) == "deny"


def test_denies_edit_of_system_ssh_config_with_dev_null():
    assert decision("Edit", {
        "file_path": "/etc/ssh/ssh_config",
        "old_string": "Host *",
        "new_string": f"Host *\n    {UKHF_NULL}",
    }) == "deny"


def test_denies_ssh_config_dropin():
    assert decision("Write", {
        "file_path": "/home/tim/.ssh/config.d/lab",
        "content": f"{SHKC_NO}\n",
    }) == "deny"


def test_allows_docs_that_mention_the_option():
    """Markdown/code that discusses the option is not an ssh config file."""
    assert decision("Write", {
        "file_path": "/home/tim/notes/ssh-notes.md",
        "content": f"Never do this:\n\n{SHKC_NO}\n",
    }) == "allow"


def test_allows_commented_out_option_in_ssh_config():
    assert decision("Write", {
        "file_path": "/home/tim/.ssh/config",
        "content": f"# {SHKC_NO}\n",
    }) == "allow"


def test_allows_accept_new_in_ssh_config():
    assert decision("Write", {
        "file_path": "/home/tim/.ssh/config",
        "content": "StrictHostKeyChecking accept-new\n",
    }) == "allow"


def test_other_tools_are_ignored():
    assert hook("Read", {"file_path": "/home/tim/.ssh/config"}) == {}


# --- what the model and the user each receive ------------------------------

def test_deny_reason_reaches_the_model():
    out = hook("Bash", {"command": "ssh -o StrictHostKeyChecking=no host"})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "accept-new" in reason
    assert out["systemMessage"]


# --- fail open, but visibly ------------------------------------------------

def test_bad_input_fails_open_with_visible_error():
    proc = run("this is not json")
    assert proc.returncode == 1
    assert proc.stdout.strip() == ""
    assert "block_ssh_unsafe_options" in proc.stderr
