#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Self-contained tests for block_gitconfig_safe_directory.py.

Runs the hook as a subprocess with crafted PreToolUse JSON payloads and
asserts the deny/allow decision for each. Exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "block_gitconfig_safe_directory.py"

failures: list[str] = []


def run(payload: dict) -> dict:
    result = subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout or "{}")


def expect(payload: dict, *, deny: bool, label: str) -> None:
    out = run(payload)
    decision = out.get("hookSpecificOutput", {}).get("permissionDecision")
    got_deny = decision == "deny"
    want = "deny" if deny else "allow"
    got = "deny" if got_deny else "allow"
    if got_deny == deny:
        print(f"  OK   [{want:5}] {label}")
    else:
        failures.append(f"FAIL  expected={want} got={got}: {label}\n      output={out!r}")
        print(f"  FAIL [{want:5}] {label}  (got {got})")


def bash(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def write(path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit(path: str, old: str, new: str) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": path, "old_string": old, "new_string": new},
    }


print("Bash — must BLOCK:")
expect(bash("git config --add safe.directory /home/tim/repo"), deny=True, label="git config --add safe.directory <path>")
expect(bash("git config --global --add safe.directory /"), deny=True, label="--global --add safe.directory /")
expect(bash("git config --global safe.directory '*'"), deny=True, label="--global safe.directory '*' (no --add)")
expect(bash("git config safe.directory /opt/foo"), deny=True, label="git config safe.directory <path>")
expect(bash("cd /home && git config --global --add safe.directory /opt"), deny=True, label="chained && add")
expect(bash("git config --unset other.thing && git config --add safe.directory /"), deny=True, label="unset other; then add safe (chained)")
expect(bash("git -c color.ui=never config --global --add safe.directory /"), deny=True, label="git with -c flag then add safe")
expect(bash("git -C /repo config --add safe.directory /"), deny=True, label="git -C <path> config add safe")

print("\nBash — must ALLOW:")
expect(bash("git config --unset safe.directory /home/tim/repo"), deny=False, label="--unset safe.directory")
expect(bash("git config --global --unset-all safe.directory"), deny=False, label="--unset-all safe.directory")
expect(bash("git config --global --remove-section safe"), deny=False, label="--remove-section safe")
expect(bash("git config --get safe.directory"), deny=False, label="--get safe.directory")
expect(bash("git config --get-all safe.directory"), deny=False, label="--get-all safe.directory")
expect(bash("git config --list"), deny=False, label="--list (read all)")
expect(bash("git config --list | grep safe"), deny=False, label="grep for safe in --list output")
expect(bash("git config user.name foo"), deny=False, label="unrelated git config key")
expect(bash("git status"), deny=False, label="unrelated git command")
expect(bash("ls -la /home"), deny=False, label="non-git command")
expect(bash("echo 'safe.directory' > /tmp/note"), deny=False, label="echo string mentioning safe.directory (no git config)")

print("\nWrite — must BLOCK:")
expect(write("/home/tim/.gitconfig", "[safe]\n\tdirectory = /\n"), deny=True, label="Write ~/.gitconfig with [safe]")
expect(write("/home/tim/github/mithro/rcfiles/git/gitconfig", "[user]\n[safe]\n\tdirectory = /\n"), deny=True, label="Write rcfiles git/gitconfig with [safe]")
expect(write("/home/tim/proj/.git/config", "[safe]\n\tdirectory = .\n"), deny=True, label="Write .git/config with [safe]")
expect(write("/home/tim/.config/git/config", "[safe]\n\tdirectory = .\n"), deny=True, label="Write XDG git/config with [safe]")
expect(write("/etc/gitconfig", "[safe]\n\tdirectory = /\n"), deny=True, label="Write /etc/gitconfig with [safe]")

print("\nWrite — must ALLOW:")
expect(write("/home/tim/.gitconfig", "[user]\n\tname = Tim\n"), deny=False, label="Write gitconfig without safe content")
expect(write("/home/tim/README.md", "Add a `[safe]` section like:\n\n    safe.directory = /\n"), deny=False, label="Write docs that mention safe.directory")
expect(write("/home/tim/notes/about-gitconfig.md", "[safe] is dangerous"), deny=False, label="Write doc whose name has 'gitconfig' substring")
expect(write("/home/tim/.gitignore", "[safe]\n"), deny=False, label="Write .gitignore (not a gitconfig)")

print("\nEdit — must BLOCK:")
expect(edit("/home/tim/.gitconfig", "[user]\nname = Tim\n", "[user]\nname = Tim\n[safe]\n\tdirectory = /\n"), deny=True, label="Edit introduces [safe] (0 -> 2 references)")
expect(
    edit(
        "/home/tim/.gitconfig",
        "[safe]\n\tdirectory = /\n",
        "[safe]\n\tdirectory = /\n\tdirectory = /home/tim\n",
    ),
    deny=True,
    label="Edit grows safe.directory count (1 -> 1, but section still grows)",
)
expect(edit("/home/tim/foo/.git/config", "", "[safe]\n\tdirectory = .\n"), deny=True, label="Edit on .git/config introduces [safe]")
expect(edit("/home/tim/.config/git/config", "", "[safe]\n\tdirectory = .\n"), deny=True, label="Edit on XDG config introduces [safe]")
expect(
    edit(
        "/home/tim/.gitconfig",
        "[safe]\n\tdirectory = /\n[user]\nname = X\n",
        "[safe]\n\tdirectory = /\n\tdirectory = /home/tim\n[user]\nname = X\n",
    ),
    deny=True,
    label="Edit appends second 'directory =' line under existing [safe] (file form)",
)
expect(
    write(
        "/home/tim/.gitconfig",
        "[user]\n\tname = X\n[safe]\n\tdirectory = /home\n\tdirectory = /opt\n",
    ),
    deny=True,
    label="Write gitconfig with [safe] containing only file-form 'directory =' lines",
)

print("\nEdit — must ALLOW:")
expect(
    edit(
        "/home/tim/.gitconfig",
        "[safe]\n\tdirectory = /\n[user]\nname = X\n",
        "[user]\nname = X\n",
    ),
    deny=False,
    label="Edit removes entire [safe] section",
)
expect(
    edit(
        "/home/tim/.gitconfig",
        "[safe]\n\tdirectory = /\n\tdirectory = /\n\tdirectory = /home/tim\n",
        "[safe]\n\tdirectory = /home/tim\n",
    ),
    deny=False,
    label="Edit dedupes duplicate safe.directory entries (count drops)",
)
expect(edit("/home/tim/.gitconfig", "name = old\n", "name = new\n"), deny=False, label="Edit unrelated section of gitconfig")
expect(edit("/home/tim/docs/safe.md", "", "[safe] section discussion"), deny=False, label="Edit non-gitconfig doc that mentions [safe]")
expect(edit("/home/tim/README.md", "", "Use `git config --add safe.directory /path` if needed"), deny=False, label="Edit README mentioning command (not a gitconfig)")

print("\nMalformed input — must ALLOW (don't break Claude on bad input):")
result = subprocess.run(["python3", str(HOOK)], input=b"not json", capture_output=True, check=True)
out = json.loads(result.stdout or "{}")
if out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
    failures.append("FAIL  malformed JSON should not deny")
    print("  FAIL malformed input not allowed through")
else:
    print("  OK   malformed input passes through")

print()
if failures:
    print(f"FAILED — {len(failures)} test(s):")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)
print("All tests passed.")
