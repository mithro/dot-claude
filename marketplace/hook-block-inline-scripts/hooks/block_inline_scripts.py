#!/usr/bin/env python3
"""PreToolUse hook: block inline code that requires escaping/quoting.

Blocks patterns where code is embedded in a command line in ways that
require shell escaping or quoting — `python -c "..."` (with any interpreter
flags before `-c`, e.g. `python -I -c`), unquoted heredocs (`<< EOF` where
variables expand), and double-quoted heredocs (`<<"EOF"`).

Allows:
  - Single-quoted heredocs (`<<'EOF'`) — no expansion, no escaping needed
  - $(cat <<'EOF' ...) — used for commit messages and PR bodies
  - Normal script execution (`uv run python3 ./script.py`)
  - The text `python -c` or `<<EOF` inside quotes (a commit message, a grep
    pattern): the shell never parses it. A `$( )` inside double quotes does
    run, so its contents are still checked.

Out of scope (by design, keep the rule narrow): other interpreters' inline
forms such as `bash -c`, `node -e`, `perl -e`, and python flags that take a
value before `-c` (`python -X dev -c ...`, `python -W ignore -c ...`).

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


DENY_PYTHON_C = """❌ **`python -c` blocked by hook**

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

DENY_UNQUOTED_HEREDOC = """❌ **Unquoted/double-quoted heredoc blocked by hook**

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


# --- Patterns (applied to the command with quoted text blanked out) --------

# python -c, with any number of boolean interpreter flags in between:
#   python -c, python3 -c, python3.13 -c, /usr/bin/python3 -c,
#   uv run python -I -c, uv run python@3.12 -c, python3 -u -B -c, python3 -c'...',
#   python3 -cprint(1)  (python takes everything glued to -c as the code)
# The -c must be the interpreter's own flag; `python3 -m pytest -c x` is
# pytest's -c (the non-flag `pytest` ends the interpreter's options).
PYTHON_DASH_C = re.compile(
    r"(?:^|[\s/(`])python(?:[23](?:\.\d+)?|@[\d.]+)?\s+(?:-[A-Za-z]+\s+)*-c(?!=)",
)

# Heredoc with single-quoted delimiter — SAFE, allow these. Quoted text has
# been blanked, so <<'EOF' appears as <<'' here.
# Requires << to be preceded by whitespace or start-of-string
SAFE_HEREDOC = re.compile(
    r"(?:^|\s)<<-?\s*'\w*'",
    re.MULTILINE,
)

# Any heredoc operator (to find ones that aren't single-quoted)
# Matches: << EOF, <<EOF, <<"EOF", <<-EOF, <<- "EOF", etc. (not <<< here-strings)
ANY_HEREDOC = re.compile(
    r"""(?:^|\s)<<-?\s*(?:["']|\w)""",
    re.MULTILINE,
)


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


def strip_quoted(command):
    """Blank out quoted text that the shell never parses as syntax.

    Single-quoted spans are emptied. Double-quoted spans are emptied too,
    unless they contain a command substitution (`$(` or a backtick), which
    does run: those are kept verbatim. The quote characters themselves stay,
    so `<<'EOF'` and `<<"EOF"` remain distinguishable from `<<EOF`.
    """
    out = []
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if ch == '\\':
            out.append(command[i:i + 2])
            i += 2
            continue
        if ch in '\'"':
            quote = ch
            j = i + 1
            while j < n:
                if quote == '"' and command[j] == '\\':
                    j += 2
                    continue
                if command[j] == quote:
                    break
                j += 1
            inner = command[i + 1:j]
            if quote == '"' and ('$(' in inner or '`' in inner):
                out.append(quote + inner + quote)
            else:
                out.append(quote + quote)
            i = j + 1
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def find_unsafe_heredocs(text):
    """True if the (quote-stripped) command has heredocs that aren't single-quoted."""
    all_heredocs = list(ANY_HEREDOC.finditer(text))
    if not all_heredocs:
        return False

    safe_positions = {m.start() for m in SAFE_HEREDOC.finditer(text)}
    return any(m.start() not in safe_positions for m in all_heredocs)


def main():
    input_data = json.load(sys.stdin)

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = input_data.get("tool_input", {}).get("command", "")
    text = strip_quoted(command)

    if PYTHON_DASH_C.search(text):
        deny(DENY_PYTHON_C)
        return

    if find_unsafe_heredocs(text):
        deny(DENY_UNQUOTED_HEREDOC)
        return

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
