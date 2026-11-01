#!/usr/bin/env python3
"""PreToolUse hook: block direct git force pushes.

Blocks every direct force push, with or without an explicit branch:
    git push --force [remote] [branch]
    git push --force-with-lease[=...] [remote] [branch]
    git push -f / -uf ...
    git push <remote> +<refspec>        (a leading + forces that refspec)

The safe wrappers, which require an explicit branch name, are allowed:
    git safe-force-push <branch>
    git safe-force-push-lease <branch>

Output protocol: a deny carries the explanation in
hookSpecificOutput.permissionDecisionReason (the field Claude Code shows to the
model) and repeats it in systemMessage (shown to the user). If the hook itself
fails it exits 1 with a traceback on stderr: a non-blocking error that lets the
tool call proceed but is visible, rather than silently approving.
"""

import json
import re
import sys
import traceback
from pathlib import Path


DENY_MESSAGE = """❌ **Direct force-push blocked by hook**

You attempted a direct force push: `git push --force`, `--force-with-lease`,
`-f`, or a refspec with a leading `+` (e.g. `git push origin +main`, which
force-updates that ref).

**Use the safe wrapper commands instead:**
```bash
# Force push a specific branch
git safe-force-push <branch>
git safe-force-push <remote> <branch>

# Force push with lease for a specific branch
git safe-force-push-lease <branch>
git safe-force-push-lease <remote> <branch>
```

**Why:** bare `git push --force` can push ALL matching branches and overwrite
other people's work on shared branches. The safe wrappers require an explicit
branch name, so every force push is deliberate and scoped."""

# --force / --force-with-lease / -f (incl. combined short flags like -uf)
# directly after `git push`
FORCE_PUSH_PATTERN = re.compile(
    r'\bgit\s+push\s+'
    r'(?:'
    r'--force(?:-with-lease)?'
    r'|'
    r'-[a-zA-Z]*f[a-zA-Z]*'
    r')'
)

# The same flags after a remote: git push origin --force
FORCE_PUSH_AFTER_REMOTE = re.compile(
    r'\bgit\s+push\s+\S+\s+'
    r'(?:'
    r'--force(?:-with-lease)?'
    r'|'
    r'-[a-zA-Z]*f[a-zA-Z]*'
    r')'
)

# A refspec with a leading +: git push origin +main / +HEAD:main.
# `[^|;&\n]*` keeps the match inside the same simple command.
PLUS_REFSPEC = re.compile(r'\bgit\s+push\b[^|;&\n]*\s\+\S')

SAFE_WRAPPER = re.compile(r'\bgit\s+safe-force-push')


def deny(message):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
        "systemMessage": message,
    }))


def allow():
    print(json.dumps({}))


def is_force_push(command):
    if SAFE_WRAPPER.search(command):
        return False
    return bool(
        FORCE_PUSH_PATTERN.search(command)
        or FORCE_PUSH_AFTER_REMOTE.search(command)
        or PLUS_REFSPEC.search(command)
    )


def main():
    input_data = json.load(sys.stdin)

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = input_data.get("tool_input", {}).get("command", "")
    if is_force_push(command):
        deny(DENY_MESSAGE)
    else:
        allow()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open, but visibly: exit 1 is a non-blocking hook error whose
        # stderr Claude Code shows to the user. Exit 0 with `{}` would hide the bug.
        print(f"{Path(__file__).name}: hook failed, allowing the tool call:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
