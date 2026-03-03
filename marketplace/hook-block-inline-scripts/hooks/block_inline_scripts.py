#!/usr/bin/env python3
"""PreToolUse hook: block inline code that requires escaping/quoting.

Blocks patterns where code is embedded in a command line in ways that
require shell escaping or quoting — `python -c "..."`, unquoted heredocs
(`<< EOF` where variables expand), and double-quoted heredocs (`<<"EOF"`).

Allows:
  - Single-quoted heredocs (`<<'EOF'`) — no expansion, no escaping needed
  - $(cat <<'EOF' ...) — used for commit messages and PR bodies
  - Normal script execution (`uv run python3 ./script.py`)
"""

import json
import re
import sys


DENY_PYTHON_C = """\u274c **`python -c` blocked by hook**

Inline `python -c "..."` requires shell escaping of quotes, backslashes,
and special characters. This is fragile and error-prone.

Long inline commands also break permission auto-allow rules (e.g.
`Bash(uv:*)`) because the entire command becomes a single complex string
that can't be matched by simple prefix patterns.

**Write it to a file instead:**
```bash
# 1. Use the Write tool to create the script
# 2. Then execute it:
uv run python3 ./tmp/my_script.py
# 3. Clean up when done
```"""

DENY_UNQUOTED_HEREDOC = """\u274c **Unquoted/double-quoted heredoc blocked by hook**

Heredocs without single-quoted delimiters perform variable expansion
and require escaping of `$`, backticks, and backslashes inside the body.

Long inline commands also break permission auto-allow rules (e.g.
`Bash(git commit:*)`) because the entire command becomes a single complex
string that can't be matched by simple prefix patterns.

**Use a single-quoted delimiter instead:**
```bash
# BAD  — variables expand, escaping needed:
command << EOF
$variable gets expanded
EOF

# GOOD — no expansion, no escaping:
command <<'EOF'
$variable stays literal
EOF
```

Or write the content to a file first using the Write tool."""


# --- Patterns ---

# python -c / python3 -c (with optional uv run prefix)
PYTHON_DASH_C = re.compile(
    r'(?:uv\s+run\s+)?python[23]?\s+-c\s',
)

# Heredoc with single-quoted delimiter — SAFE, allow these
# Matches: <<'EOF', << 'EOF', <<-'EOF', <<- 'MARKER'
# Requires << to be preceded by whitespace or start-of-string
SAFE_HEREDOC = re.compile(
    r"(?:^|\s)<<-?\s*'(\w+)'",
    re.MULTILINE,
)

# Any heredoc operator (to find ones that aren't single-quoted)
# Matches: << EOF, <<EOF, <<"EOF", <<-EOF, <<- "EOF", etc.
# Requires << to be preceded by whitespace or start-of-string
# (avoids matching << inside quoted strings like echo "use << for")
ANY_HEREDOC = re.compile(
    r'(?:^|\s)(<<-?\s*"?\w)',
    re.MULTILINE,
)


def find_unsafe_heredocs(command):
    """Check if command has heredocs that aren't single-quoted.

    Returns True if there are unsafe (unquoted or double-quoted) heredocs.
    """
    # Find all heredoc positions
    all_heredocs = list(ANY_HEREDOC.finditer(command))
    if not all_heredocs:
        return False

    # Find all safe (single-quoted) heredoc positions
    safe_positions = {m.start() for m in SAFE_HEREDOC.finditer(command)}

    # If any heredoc start position isn't in the safe set, it's unsafe
    for m in all_heredocs:
        if m.start() not in safe_positions:
            return True

    return False


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

    # Check for python -c (always blocked)
    if PYTHON_DASH_C.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_PYTHON_C,
        }))
        return

    # Check for unsafe heredocs (unquoted or double-quoted delimiters)
    if find_unsafe_heredocs(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": DENY_UNQUOTED_HEREDOC,
        }))
        return

    # No match — allow
    print(json.dumps({}))


if __name__ == "__main__":
    main()
