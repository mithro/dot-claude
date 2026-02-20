#!/usr/bin/env python3
"""PreToolUse hook: block inline code execution in Bash commands.

Blocks patterns like `python -c "..."`, heredocs piping to interpreters,
and similar inline program embedding. Forces writing code to a file first
and then executing it, which avoids escaping nightmares and is easier to
debug.

Allows:
  - git commit -m "$(cat <<'EOF'...)" — commit message heredocs
  - gh pr create --body "$(cat <<'EOF'...)" — PR body heredocs
  - echo/printf into files (simple data, not programs)
"""

import json
import re
import sys


DENY_MESSAGE = """\u274c **Inline script blocked by hook**

You tried to embed code directly in the command line. This is fragile
and leads to escaping bugs. **Write it to a file first**, then run it.

**Instead of:**
```bash
python3 -c "import json; print(json.dumps(...))"
```

**Do this:**
```bash
# 1. Use the Write tool to create the script file
# 2. Then execute it:
uv run python3 ./tmp/my_script.py
```

**Instead of heredocs:**
```bash
python3 << 'EOF'
import json
print("hello")
EOF
```

**Do this:**
```bash
# 1. Use the Write tool to create the script file
# 2. Then execute it:
uv run python3 ./tmp/my_script.py
```

Remember to clean up temporary files when done."""


# --- Patterns to BLOCK ---

# python -c / python3 -c (with optional uv run prefix)
PYTHON_DASH_C = re.compile(
    r'(?:uv\s+run\s+)?python[23]?\s+-c\s',
)

# Heredoc feeding into an interpreter or command
# Matches: python3 <<, bash <<, sh <<, node <<, ruby <<, perl <<
# But NOT: $(cat << which is the commit/PR message pattern
HEREDOC_TO_INTERPRETER = re.compile(
    r'(?<!cat\s)(?<!\$\(cat\s)'  # not preceded by "cat " or "$(cat "
    r'\b(?:python[23]?|bash|sh|node|ruby|perl|php)\b'
    r'.*<<-?\s*[\'"]?\w',
)

# Bare heredoc at start of pipeline or after pipe
# e.g.: cat << 'EOF' | python3
HEREDOC_PIPE_TO_INTERPRETER = re.compile(
    r'<<-?\s*[\'"]?\w+[\'"]?\b'
    r'.*\|\s*(?:python[23]?|bash|sh|node|ruby|perl|php)\b',
)

# General heredoc usage (except the $(cat << pattern used for messages)
# This catches: anything << EOF that isn't inside $(cat <<
GENERAL_HEREDOC = re.compile(
    r'(?<!\$\(cat\s)<<-?\s*[\'"]?\w+[\'"]?',
)


# --- Patterns to ALLOW (checked first) ---

# $(cat <<'EOF' ... EOF) — used for git commit -m and gh pr create --body
COMMIT_HEREDOC = re.compile(
    r'\$\(cat\s+<<',
)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({}))
        return

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({}))
        return

    command = input_data.get("tool_input", {}).get("command", "")

    # Check for python -c (always blocked, even inside $(cat <<))
    if PYTHON_DASH_C.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_MESSAGE,
        }))
        return

    # If the ONLY heredocs are inside $(cat <<), allow
    if COMMIT_HEREDOC.search(command):
        # Strip out all $(cat << ... EOF\n) blocks, then check if any
        # heredocs remain
        stripped = COMMIT_HEREDOC.sub('', command)
        if not GENERAL_HEREDOC.search(stripped):
            print(json.dumps({}))
            return

    # Check for heredocs piped to interpreters
    if HEREDOC_TO_INTERPRETER.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_MESSAGE,
        }))
        return

    if HEREDOC_PIPE_TO_INTERPRETER.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_MESSAGE,
        }))
        return

    # Check for general heredoc usage
    if GENERAL_HEREDOC.search(command):
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
