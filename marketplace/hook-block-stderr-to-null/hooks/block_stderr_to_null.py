#!/usr/bin/env python3
"""PreToolUse hook: block commands that silence stderr.

Stderr contains valuable diagnostic information — errors, warnings, and
unexpected conditions. Suppressing it hides problems and makes debugging harder.

Blocked forms (all of them discard stderr):
    cmd 2>/dev/null            (also 2>"/dev/null", cmd>/dev/null 2>&1 ...)
    cmd >/dev/null 2>&1        (stdout to null, then stderr onto it)
    cmd &>/dev/null            (bash shorthand for both streams)
    cmd >&/dev/null
    cmd 2>&-                   (closes stderr)

Allowed: `cmd >/dev/null` (stdout only), `cmd 2>&1 | tee log`, `cmd 2>err.log`,
`cmd 2>&1 >/dev/null` (stderr ends up on the original stdout, still visible),
and the text `2>/dev/null` inside quotes (a commit message, a grep pattern),
which the shell never parses as a redirection. A `$( )` inside double quotes
does run, so its contents are still checked.

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


# A quoted /dev/null is still /dev/null: normalise before stripping quotes.
QUOTED_DEV_NULL = re.compile(r"""(['"])/dev/null\1""")

# 2>/dev/null, 2> /dev/null (but not 12>/dev/null: that is fd 12)
STDERR_TO_NULL = re.compile(r"(?<!\d)2>\s*/dev/null")

# &>/dev/null, &>>/dev/null, >&/dev/null — both streams
BOTH_TO_NULL = re.compile(r"(?<!\d)(?:&>>?|>&)\s*/dev/null")

# >/dev/null ... 2>&1 within the same simple command: stdout goes to null and
# stderr is then pointed at (null) stdout. The stdout redirect is `>` with no
# fd (not preceded by a digit, `&` or another `>`) or an explicit `1>`.
# `[^|;&\n]*` keeps the match inside one command so `a >/dev/null && b 2>&1`
# is not caught.
STDOUT_NULL_THEN_DUP = re.compile(
    r"(?:(?<!\d)1|(?<![\d&>]))>>?\s*/dev/null[^|;&\n]*\s2>&1"
)

# 2>&- closes stderr outright
CLOSE_STDERR = re.compile(r"(?<!\d)2>&-")

PATTERNS = [STDERR_TO_NULL, BOTH_TO_NULL, STDOUT_NULL_THEN_DUP, CLOSE_STDERR]

DENY_MESSAGE = """🚫 **Silencing stderr is blocked by hook**

The command discards stderr (`2>/dev/null`, `>/dev/null 2>&1`, `&>/dev/null` \
or `2>&-`), which hides important diagnostic information.

**What to do instead:**
- Let stderr flow normally so diagnostic information is visible
- If you need to handle errors, capture stderr to a file for inspection (`2>err.log`)
- If output is noisy, filter specific known-safe messages (`2>&1 | grep -v ...`) \
rather than suppressing all of stderr
- Discarding only stdout (`>/dev/null`) is fine"""


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
    does run: those are kept verbatim. The quote characters themselves stay.
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


def silences_stderr(command):
    text = strip_quoted(QUOTED_DEV_NULL.sub('/dev/null', command))
    return any(p.search(text) for p in PATTERNS)


def main():
    input_data = json.load(sys.stdin)

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = input_data.get("tool_input", {}).get("command", "")
    if silences_stderr(command):
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
