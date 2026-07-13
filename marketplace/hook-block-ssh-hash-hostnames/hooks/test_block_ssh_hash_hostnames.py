#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Self-contained tests for block_ssh_hash_hostnames.py.

Feeds crafted PreToolUse JSON payloads to the hook as a subprocess and
asserts the deny/allow decision for each. Exits 0 on success, 1 on failure.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "block_ssh_hash_hostnames.py"

# Built via concatenation so the live hook doesn't deny writing this test
# file itself (it scans Write/Edit content for this literal string).
HASH_YES = "HashKnownHosts" + " " + "yes"

failures: list[str] = []


def run_hook(tool_name: str, tool_input: dict) -> dict:
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"hook exited {proc.returncode}:\n{proc.stderr}")
    return json.loads(proc.stdout)


def decision(result: dict) -> str:
    return result.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


def check(name: str, expected: str, tool_name: str, tool_input: dict) -> None:
    result = run_hook(tool_name, tool_input)
    actual = decision(result)
    status = "PASS" if actual == expected else "FAIL"
    print(f"{status}: {name} (expected {expected}, got {actual})")
    if actual != expected:
        failures.append(f"{name}: expected {expected}, got {actual}\n  {tool_input}")


def bash(name: str, expected: str, command: str) -> None:
    check(name, expected, "Bash", {"command": command})


# --- -H in the remote command run BY ssh must be allowed -------------------

bash(
    "ipmitool -H inside quoted remote command",
    "allow",
    "ssh -o ConnectTimeout=20 asus-bmc 'ipmitool -I lanplus -H 192.168.66.2"
    " -U root -P 0penBmc -N 5 chassis status 2>&1 | head -n 6'",
)
bash(
    "-H in unquoted remote command",
    "allow",
    "ssh asus-bmc ipmitool -H 192.168.66.2 chassis status",
)
bash(
    "-H in remote command after options taking values",
    "allow",
    "ssh -i ~/.ssh/id_ed25519 -p 2222 host 'ipmitool -H 10.0.0.1 power status'",
)
bash(
    "remote command merely mentioning HashKnownHosts",
    "allow",
    "ssh host 'grep HashKnownHosts /etc/ssh/ssh_config'",
)

# --- -H given to ssh itself (or other ssh tools) must stay blocked ---------

bash("bare ssh -H before destination", "deny", "ssh -H host uptime")
bash("ssh -H combined with other flags", "deny", "ssh -4H host uptime")
bash("sudo ssh -H", "deny", "sudo ssh -H host uptime")
bash("ssh-keyscan -H", "deny", "ssh-keyscan -H github.com")
bash("ssh-keyscan -H after other args", "deny", "ssh-keyscan -t rsa -H github.com")
bash("ssh-keygen -H", "deny", "ssh-keygen -H -f ~/.ssh/known_hosts")
bash(
    "ssh-keyscan -H in second pipeline command",
    "deny",
    "echo start && ssh-keyscan -H github.com >> known_hosts",
)
bash(
    "ssh-keyscan -H inside command substitution",
    "deny",
    "echo $(ssh-keyscan -H github.com)",
)
bash(
    "ssh-keyscan -H inside backticks",
    "deny",
    "echo `ssh-keyscan -H github.com`",
)
bash(
    "ssh tool with -H run remotely via ssh",
    "deny",
    "ssh host 'ssh-keyscan -H internal >> ~/.ssh/known_hosts'",
)

# --- HashKnownHosts option handling -----------------------------------------

bash(
    "ssh -o HashKnownHosts=yes",
    "deny",
    "ssh -o HashKnownHosts=yes host uptime",
)
bash(
    "ssh -oHashKnownHosts=yes (attached value)",
    "deny",
    "ssh -oHashKnownHosts=yes host uptime",
)
bash(
    "ssh -o HashKnownHosts=no is fine",
    "allow",
    "ssh -o HashKnownHosts=no host uptime",
)

# --- non-ssh commands are never the hook's business -------------------------

bash("plain ipmitool -H locally", "allow", "ipmitool -H 192.168.66.2 chassis status")
bash("grep -H is unrelated", "allow", "grep -H pattern file.txt")

# --- file edits: only ssh config files are in scope --------------------------

check(
    "Write enabling hashing in ~/.ssh/config",
    "deny",
    "Write",
    {"file_path": "/home/tim/.ssh/config", "content": HASH_YES + "\n"},
)
check(
    "Write enabling hashing in /etc/ssh/ssh_config",
    "deny",
    "Write",
    {"file_path": "/etc/ssh/ssh_config", "content": HASH_YES + "\n"},
)
check(
    "Write disabling hashing in ~/.ssh/config",
    "allow",
    "Write",
    {"file_path": "/home/tim/.ssh/config", "content": "HashKnownHosts no\n"},
)
check(
    "Edit with commented-out hashing in ~/.ssh/config",
    "allow",
    "Edit",
    {"file_path": "/home/tim/.ssh/config", "new_text": "# " + HASH_YES + "\n"},
)
check(
    "Write mentioning the option in a non-ssh-config file",
    "allow",
    "Write",
    {"file_path": "/home/tim/project/test_hook.py", "content": HASH_YES + "\n"},
)

print()
if failures:
    print(f"{len(failures)} FAILURE(S):")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)
print("All tests passed.")
sys.exit(0)
