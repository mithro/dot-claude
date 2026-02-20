#!/usr/bin/env python3
"""PreToolUse hook: block unsafe git force-push commands.

Blocks git push --force, git push --force-with-lease, and git push -f
when used without an explicit branch name (which pushes ALL branches).
Users should use the safe wrapper commands instead:
  git safe-force-push <branch>
  git safe-force-push-lease <branch>
"""

import json
import re
import sys


DENY_MESSAGE = """\u274c **Unsafe force-push blocked by hook**

You attempted to use `git push --force` (or `--force-with-lease` / `-f`) which is dangerous
because it can push ALL branches without targeting a specific one.

**Use the safe wrapper commands instead:**
```bash
# Force push a specific branch
git safe-force-push <branch>
git safe-force-push <remote> <branch>

# Force push with lease for a specific branch
git safe-force-push-lease <branch>
git safe-force-push-lease <remote> <branch>
```

**Why:** Bare `git push --force` pushes all matching branches, which can
overwrite other people's work on shared branches. The safe wrappers require
an explicit branch name to prevent accidents."""

# Patterns that match dangerous force-push commands
# We block:
#   git push --force (with or without remote, but no branch)
#   git push --force-with-lease (with or without remote, but no branch)
#   git push -f (short form, always blocked)
#
# We allow:
#   git safe-force-push <branch>
#   git safe-force-push-lease <branch>

FORCE_PUSH_PATTERN = re.compile(
    r'\bgit\s+push\s+'
    r'(?:'
    r'--force(?:-with-lease)?'  # --force or --force-with-lease
    r'|'
    r'-[a-zA-Z]*f[a-zA-Z]*'    # -f or combined flags like -uf
    r')'
)

# Also catch: git push <remote> --force (flag after remote)
FORCE_PUSH_AFTER_REMOTE = re.compile(
    r'\bgit\s+push\s+\S+\s+'
    r'(?:'
    r'--force(?:-with-lease)?'
    r'|'
    r'-[a-zA-Z]*f[a-zA-Z]*'
    r')'
)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input -- allow the operation
        print(json.dumps({}))
        return

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({}))
        return

    command = input_data.get("tool_input", {}).get("command", "")

    # Skip if it's using the safe wrapper commands
    if re.search(r'\bgit\s+safe-force-push', command):
        print(json.dumps({}))
        return

    # Check for force-push patterns
    if FORCE_PUSH_PATTERN.search(command) or FORCE_PUSH_AFTER_REMOTE.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_MESSAGE,
        }))
        return

    # No match -- allow
    print(json.dumps({}))


if __name__ == "__main__":
    main()
