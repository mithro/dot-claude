#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Self-contained tests for block_megacommits.py.

Builds throwaway git repos under a project-local tmp/ directory, feeds crafted
PreToolUse JSON payloads to the hook as a subprocess, and asserts the deny/allow
decision for each. Cleans up after itself. Exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "block_megacommits.py"
GIT_ID = ["-c", "user.email=test@example.com", "-c", "user.name=Test"]

# Project-local scratch root (never /tmp, per house rules); cleaned up at exit.
SCRATCH_BASE = Path.cwd() / "tmp"
SCRATCH_BASE.mkdir(parents=True, exist_ok=True)
RUN_DIR = Path(tempfile.mkdtemp(prefix="megacommit-test-", dir=SCRATCH_BASE))

failures: list[str] = []


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {args} failed:\n{proc.stderr}")
    return proc


def new_repo(initial_commit: bool = True) -> str:
    repo = tempfile.mkdtemp(dir=RUN_DIR)
    git(repo, "init", "-q")
    if initial_commit:
        write_lines(repo, "README", 1)
        git(repo, "add", "README")
        git(repo, *GIT_ID, "commit", "-q", "-m", "seed")
    return repo


def write_lines(repo: str, name: str, n: int) -> None:
    path = os.path.join(repo, name)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        f.writelines(f"line {i}\n" for i in range(n))


def invoke(command: str, cwd: str, tool_name: str = "Bash") -> str:
    payload = {
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "cwd": cwd,
    }
    result = subprocess.run(
        ["python3", str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        check=True,
    )
    out = json.loads(result.stdout or "{}")
    return out.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


def expect(command: str, cwd: str, *, deny: bool, label: str, tool_name: str = "Bash") -> None:
    decision = invoke(command, cwd, tool_name=tool_name)
    want = "deny" if deny else "allow"
    got_deny = decision == "deny"
    if got_deny == deny:
        print(f"  OK   [{want:5}] {label}")
    else:
        got = "deny" if got_deny else "allow"
        failures.append(f"expected={want} got={got}: {label}")
        print(f"  FAIL [{want:5}] {label}  (got {got})")


def many_files(repo: str, count: int) -> None:
    names = [f"f{i}.py" for i in range(count)]
    for n in names:
        write_lines(repo, n, 1)
    git(repo, "add", *names)


try:
    print("Must BLOCK:")

    r = new_repo()
    many_files(r, 20)
    expect("git commit -m 'many files'", r, deny=True, label="20 staged files")

    r = new_repo()
    write_lines(r, "big.py", 500)
    git(r, "add", "big.py")
    expect("git commit -m 'big'", r, deny=True, label="500 added lines in one file")

    r = new_repo()
    write_lines(r, "README", 600)  # modify tracked file, leave unstaged
    expect("git commit -am 'all'", r, deny=True, label="-am sweeps large unstaged tracked change")

    print("\nMust ALLOW:")

    r = new_repo()
    write_lines(r, "a.py", 10)
    write_lines(r, "b.py", 10)
    git(r, "add", "a.py", "b.py")
    expect("git commit -m 'small'", r, deny=False, label="small staged commit (2 files)")

    r = new_repo()
    many_files(r, 15)
    expect("git commit -m 'boundary'", r, deny=False, label="exactly 15 files (at limit)")

    r = new_repo()
    many_files(r, 20)
    expect("ALLOW_MEGACOMMIT=1 git commit -m 'vendored'", r, deny=False, label="override token bypasses block")

    r = new_repo()
    write_lines(r, "README", 600)  # large unstaged tracked change, NOT staged
    expect("git commit -m 'refactor a lot of all the things'", r, deny=False,
           label="no -a ignores unstaged; 'a'/'all' in message not parsed as -a")

    r = new_repo()
    write_lines(r, "uv.lock", 1000)
    git(r, "add", "uv.lock")
    expect("git commit -m 'lock'", r, deny=False, label="lockfile line churn ignored (1 file)")

    r = new_repo()
    many_files(r, 20)
    expect("git status", r, deny=False, label="non-commit git command")
    expect("git commit -m x", r, deny=False, label="non-Bash tool", tool_name="Write")
    expect("git commit-tree HEAD^{tree} -m x", r, deny=False, label="git commit-tree is not a commit")

    r = new_repo()
    many_files(r, 20)
    git_dir = git(r, "rev-parse", "--git-dir").stdout.strip()
    git_dir = git_dir if os.path.isabs(git_dir) else os.path.join(r, git_dir)
    with open(os.path.join(git_dir, "MERGE_HEAD"), "w") as f:
        f.write("0" * 40 + "\n")
    expect("git commit -m 'merge'", r, deny=False, label="merge in progress (legitimately large)")

    r = new_repo(initial_commit=False)
    many_files(r, 20)
    expect("git commit -m 'import'", r, deny=False, label="initial commit, no HEAD")

    nonrepo = tempfile.mkdtemp(dir=RUN_DIR)
    expect("git commit -m x", nonrepo, deny=False, label="not a git repository")

    r = new_repo()
    write_lines(r, "doomed.py", 600)
    git(r, "add", "doomed.py")
    git(r, *GIT_ID, "commit", "-q", "-m", "add doomed")
    git(r, "rm", "-q", "doomed.py")
    expect("git commit -m 'remove'", r, deny=False, label="large deletion, no additions")

    r = new_repo()
    expect("git commit --amend -m 'reword'", r, deny=False, label="amend with nothing newly staged")

    print("\nMalformed input — must ALLOW (don't break Claude on bad input):")
    result = subprocess.run(["python3", str(HOOK)], input=b"not json", capture_output=True, check=True)
    out = json.loads(result.stdout or "{}")
    if out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
        failures.append("malformed JSON should not deny")
        print("  FAIL malformed input not allowed through")
    else:
        print("  OK   malformed input passes through")

finally:
    shutil.rmtree(RUN_DIR, ignore_errors=True)

print()
if failures:
    print(f"FAILED — {len(failures)} test(s):")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)
print("All tests passed.")
