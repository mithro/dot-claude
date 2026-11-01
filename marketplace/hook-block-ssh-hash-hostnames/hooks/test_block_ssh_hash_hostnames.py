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
    "ssh -o ConnectTimeout=20 bmc-host 'ipmitool -I lanplus -H 192.0.2.10"
    " -U root -P <password> -N 5 chassis status 2>&1 | head -n 6'",
)
bash(
    "-H in unquoted remote command",
    "allow",
    "ssh bmc-host ipmitool -H 192.0.2.10 chassis status",
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
bash(
    "ssh -o HashKnownHosts=true (ssh accepts true as yes)",
    "deny",
    "ssh -o HashKnownHosts=true host uptime",
)

# --- 2026-11-01 review: common wrappers around the ssh tool -----------------

bash("xargs ssh-keyscan -H", "deny", "echo github.com | xargs ssh-keyscan -H")
bash("xargs -n1 ssh-keyscan -H", "deny", "cat hosts | xargs -n 1 ssh-keyscan -H")
bash("timeout N ssh-keyscan -H", "deny", "timeout 5 ssh-keyscan -H github.com")
bash("timeout -k 1 N ssh-keyscan -H", "deny", "timeout -k 1 5 ssh-keyscan -H github.com")
bash("bash -c 'ssh-keyscan -H'", "deny", "bash -c 'ssh-keyscan -H github.com'")
bash("sh -c with ssh -o HashKnownHosts=yes", "deny", "sh -c 'ssh -o HashKnownHosts=yes host'")
bash(
    "GIT_SSH_COMMAND carrying HashKnownHosts=yes",
    "deny",
    "GIT_SSH_COMMAND='ssh -o HashKnownHosts=yes' git fetch",
)
bash("timeout around a clean ssh", "allow", "timeout 5 ssh host uptime")
bash("xargs around a clean ssh-keyscan", "allow", "echo github.com | xargs ssh-keyscan -t ed25519")

# --- non-ssh commands are never the hook's business -------------------------

bash("plain ipmitool -H locally", "allow", "ipmitool -H 192.0.2.10 chassis status")
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
    {"file_path": "/home/tim/.ssh/config", "old_string": "Host *",
     "new_string": "Host *\n# " + HASH_YES + "\n"},
)
check(
    "Edit adding hashing to ~/.ssh/config (Edit tool field is new_string)",
    "deny",
    "Edit",
    {"file_path": "/home/tim/.ssh/config", "old_string": "Host *",
     "new_string": "Host *\n    " + HASH_YES + "\n"},
)
check(
    "Write mentioning the option in a non-ssh-config file",
    "allow",
    "Write",
    {"file_path": "/home/tim/project/test_hook.py", "content": HASH_YES + "\n"},
)
check(
    "Write enabling hashing with 'true' in ~/.ssh/config",
    "deny",
    "Write",
    {"file_path": "/home/tim/.ssh/config", "content": "HashKnownHosts" + " true\n"},
)
check(
    "Edit of a neighbouring line keeps an existing HashKnownHosts yes as context",
    "allow",
    "Edit",
    {"file_path": "/home/tim/.ssh/config",
     "old_string": "Host *\n    " + HASH_YES + "\n    User root\n",
     "new_string": "Host *\n    " + HASH_YES + "\n    User tim\n"},
)
check(
    "Edit adding a second HashKnownHosts yes is still denied",
    "deny",
    "Edit",
    {"file_path": "/home/tim/.ssh/config",
     "old_string": "Host *\n    " + HASH_YES + "\n",
     "new_string": "Host *\n    " + HASH_YES + "\nHost lab\n    " + HASH_YES + "\n"},
)

# --- output protocol ---------------------------------------------------------

result = run_hook("Bash", {"command": "ssh-keyscan -H host"})
reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
if "-H" in reason:
    print("PASS: deny reason is in permissionDecisionReason (shown to the model)")
else:
    failures.append(f"deny reason missing from permissionDecisionReason: {result!r}")
    print("FAIL: deny reason is in permissionDecisionReason")

proc = subprocess.run([sys.executable, str(HOOK)], input="not json",
                      capture_output=True, text=True)
if proc.returncode == 1 and not proc.stdout.strip() and "block_ssh_hash_hostnames" in proc.stderr:
    print("PASS: malformed input fails open visibly (exit 1, error on stderr)")
else:
    failures.append(
        f"malformed input: exit={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr[:200]!r}"
    )
    print("FAIL: malformed input fails open visibly")

print()
if failures:
    print(f"{len(failures)} FAILURE(S):")
    for f in failures:
        print(f"  {f}")
    sys.exit(1)
print("All tests passed.")
sys.exit(0)
