#!/usr/bin/env python3
"""PreToolUse hook: block commands that redirect stderr to /dev/null.

Stderr contains valuable diagnostic information — errors, warnings, and
unexpected conditions. Suppressing it hides problems and makes debugging harder.
"""

import json
import re
import sys


PATTERN = re.compile(r"2>\s*/dev/null")

DENY_MESSAGE = """🚫 **Stderr redirection to /dev/null is blocked**

You attempted to use `2>/dev/null` which hides important diagnostic information.

**What to do instead:**
- Let stderr flow normally so diagnostic information is visible
- If you need to handle errors, capture stderr to a variable or file for inspection
- If output is noisy, filter specific known-safe messages rather than suppressing all of stderr"""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input — allow the operation
        print(json.dumps({}))
        return

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({}))
        return

    command = input_data.get("tool_input", {}).get("command", "")
    if PATTERN.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_MESSAGE,
        }))
        return

    # No match — allow
    print(json.dumps({}))


if __name__ == "__main__":
    main()
