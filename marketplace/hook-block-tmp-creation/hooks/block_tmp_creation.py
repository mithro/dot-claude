#!/usr/bin/env python3
"""PreToolUse hook: block file creation in /tmp.

Claude should use a project-local tmp/ directory instead of /tmp, which is
often a RAM-backed tmpfs and triggers permission prompts. This hook enforces
that rule by denying clear file-creation patterns targeting /tmp -- including
indirect ones (VAR=/tmp/..., --out /tmp/..., -v /tmp/...:, cd /tmp/...) -- and
silently allowing ambiguous or read-only cases (letting the normal permission
system handle those).
"""

import json
import os
import re
import shlex
import sys
import traceback

# --- Bash command patterns that create files in /tmp ---

# Redirects: > /tmp/..., >> /tmp/..., 2> /tmp/..., &> /tmp/...
REDIRECT_TO_TMP = re.compile(r'[0-9&]*>{1,2}\s*"?/tmp/')

# tee /tmp/... (with optional flags)
TEE_TO_TMP = re.compile(r'\btee\s+(-[a-zA-Z]+\s+)*/tmp/')

# cp/mv are checked per simple command by cp_mv_to_tmp() below: only a /tmp
# DESTINATION counts (copying out of /tmp is a read), and the command is split
# quote- and substitution-aware so `cp "$(ls | head -1)" /tmp/x` is one command.
COPY_COMMANDS = {'cp', 'mv'}
COPY_WRAPPERS = {'sudo', 'env', 'nice', 'nohup', 'command'}
COPY_OPTS_WITH_ARG = {'-S', '--suffix', '-t', '--target-directory'}

# mkdir /tmp/... (with optional flags)
MKDIR_TMP = re.compile(r'\bmkdir\s+(-[a-zA-Z]+\s+)*"?/tmp/')

# touch /tmp/... (with optional flags)
TOUCH_TMP = re.compile(r'\btouch\s+(-[a-zA-Z]+\s+)*"?/tmp/')

# --- Indirect writes: a /tmp path handed to something that writes there later ---

# VAR=/tmp/..., export TMPDIR=/tmp, OUT="/tmp/run1" ./build.sh
ASSIGN_TMP = re.compile(
    r'(?:^|[\s;&|(])(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*=["\']?/tmp(?:/|["\'\s;&|)]|$)'
)

# --out /tmp/..., --progress-dir=/tmp/..., -o /tmp/a.out
# (long options only when named like an output location, or in --opt=/tmp form,
# so read-only `ls -la /tmp/x` / `du -sh /tmp/x` stay allowed; --exclude,
# --include and --filter take match patterns, not paths to write)
OPTION_TO_TMP = re.compile(
    r'--[\w-]*(?:out|dir|resume|progress|work|cache|log|dest|target|prefix|tmp|temp|save|root|path)'
    r'[\w-]*\s+["\']?/tmp/'
    r'|--(?!(?:exclude|include|filter)\b)[\w-]+=["\']?/tmp/'
    r'|(?:^|\s)-o\s*["\']?/tmp/'
)

# docker/podman -v /tmp/...:/x, --volume=/tmp/...:/x, --mount ...,src=/tmp/...
MOUNT_FROM_TMP = re.compile(
    r'(?:\s-v|--volume)[\s=]+["\']?/tmp/[^\s:]*:'
    r'|--mount[\s=]+\S*(?:src|source)=["\']?/tmp/'
)

# cd /tmp/... (everything after writes there via relative paths)
CD_TO_TMP = re.compile(r'\b(?:cd|pushd)\s+["\']?/tmp(?:/|["\'\s;&|)]|$)')

# mktemp detection: present in command
MKTEMP_PRESENT = re.compile(r'\bmktemp\b')
# mktemp with -p or --tmpdir pointing to a non-/tmp directory
MKTEMP_CUSTOM_DIR = re.compile(r'\bmktemp\b.*(?:-p\s+|--tmpdir[= ])(?!"?/tmp)(?!/tmp)')

BASH_CREATION_PATTERNS = [
    REDIRECT_TO_TMP,
    TEE_TO_TMP,
    MKDIR_TMP,
    TOUCH_TMP,
    ASSIGN_TMP,
    OPTION_TO_TMP,
    MOUNT_FROM_TMP,
    CD_TO_TMP,
]

DENY_MESSAGE = """\u274c **/tmp creation blocked by hook**

You attempted to create files in `/tmp/` (or point a tool, variable, mount or `cd` at it). \
This **includes the harness scratchpad** when the system prompt places it under \
`/tmp/claude-<uid>/` — that instruction does not override this rule. \
Use a **project-local directory** instead:

```python
import tempfile, os
tmpdir = os.path.join(os.getcwd(), "tmp")
os.makedirs(tmpdir, exist_ok=True)
# Use tmpdir for your temporary files
# ALWAYS clean up when done
```

Or in bash:
```bash
mkdir -p ./tmp
# Use ./tmp/ instead of /tmp/
# ALWAYS clean up when done
```

**Why:** `/tmp` is often a RAM-backed tmpfs: large scratch output (build trees, \
images, simulation runs) consumes memory, fills it for every other process, and \
vanishes on reboot. It also triggers permission prompts and scatters files outside \
the project. A local `tmp/` directory is on disk, accessible, and contained.

To move Claude Code's own temp dir and the scratchpad off `/tmp`, set \
`CLAUDE_CODE_TMPDIR` and `TMPDIR` in `~/.claude/settings.json` `env` \
(keep `<dir>/claude-<uid>` within 44 bytes)."""


def make_deny(message):
    """Return a deny response with the given message.

    permissionDecisionReason is what Claude sees; systemMessage is shown to the user.
    """
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
        "systemMessage": message,
    })


def make_allow():
    """Return an allow response (empty object = no opinion)."""
    return json.dumps({})


def check_file_path(tool_input):
    """Check if Write/Edit file_path targets /tmp."""
    file_path = tool_input.get("file_path", "")
    if file_path.startswith("/tmp/") or file_path == "/tmp":
        return make_deny(DENY_MESSAGE)
    return None


def split_simple_commands(command):
    """Split on unquoted `|` `;` `&` `(` `)` and newlines.

    Quotes and `$( ... )` substitutions are kept intact, so each piece is one
    simple command as the shell would see it.
    """
    segments = []
    current = []
    quote = None
    depth = 0
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if quote is not None:
            if quote == '"' and ch == '\\':
                current.append(command[i:i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
            current.append(ch)
            i += 1
            continue
        if ch == '\\':
            current.append(command[i:i + 2])
            i += 2
            continue
        if ch in '\'"':
            quote = ch
        elif command.startswith('$(', i):
            depth += 1
            current.append('$(')
            i += 2
            continue
        elif ch == ')' and depth > 0:
            depth -= 1
        elif depth == 0 and ch in '|;&()\n':
            segments.append(''.join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    segments.append(''.join(current))
    return segments


def is_tmp_dest(path):
    return path == '/tmp' or path.startswith('/tmp/')


def cp_mv_to_tmp(segment):
    """True if this simple command is a cp/mv whose destination is in /tmp."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    while tokens and (tokens[0] in COPY_WRAPPERS
                      or ('=' in tokens[0] and not tokens[0].startswith('-'))):
        tokens = tokens[1:]
    if not tokens or tokens[0].rsplit('/', 1)[-1] not in COPY_COMMANDS:
        return False

    operands = []
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--':
            operands.extend(tokens[i + 1:])
            break
        if tok in ('-t', '--target-directory'):
            if i + 1 < len(tokens) and is_tmp_dest(tokens[i + 1]):
                return True
            i += 2
            continue
        if tok.startswith('--target-directory='):
            if is_tmp_dest(tok.split('=', 1)[1]):
                return True
            i += 1
            continue
        if tok in COPY_OPTS_WITH_ARG:
            i += 2
            continue
        if tok.startswith('-') and len(tok) > 1:
            i += 1
            continue
        operands.append(tok)
        i += 1
    return len(operands) >= 2 and is_tmp_dest(operands[-1])


def check_bash(command):
    """Check if a Bash command creates files in /tmp."""
    # Skip commands that contain git commit/tag/notes — any /tmp references
    # are likely in the message text, not actual shell file operations.
    if re.search(r'\bgit\s+(commit|tag|notes)\b', command):
        return None

    # Check each creation pattern
    for pattern in BASH_CREATION_PATTERNS:
        if pattern.search(command):
            return make_deny(DENY_MESSAGE)

    # cp/mv with a /tmp destination, judged one simple command at a time
    if any(cp_mv_to_tmp(segment) for segment in split_simple_commands(command)):
        return make_deny(DENY_MESSAGE)

    # mktemp: deny if present without a custom non-/tmp directory
    if MKTEMP_PRESENT.search(command):
        if not MKTEMP_CUSTOM_DIR.search(command):
            return make_deny(DENY_MESSAGE)

    return None


def main():
    input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Write/Edit: check file_path
    if tool_name in ("Write", "Edit"):
        result = check_file_path(tool_input)
        if result:
            print(result)
            return

    # Bash: check command
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        result = check_bash(command)
        if result:
            print(result)
            return

    # No match -- allow
    print(make_allow())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open, but visibly: exit 1 is a non-blocking hook error whose
        # stderr Claude Code shows to the user. Exit 0 with `{}` would hide the bug.
        print(f"{os.path.basename(__file__)}: hook failed, allowing the tool call:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
