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
import re
import sys

# --- Bash command patterns that create files in /tmp ---

# Redirects: > /tmp/..., >> /tmp/..., 2> /tmp/..., &> /tmp/...
REDIRECT_TO_TMP = re.compile(r'[0-9&]*>{1,2}\s*"?/tmp/')

# tee /tmp/... (with optional flags)
TEE_TO_TMP = re.compile(r'\btee\s+(-[a-zA-Z]+\s+)*/tmp/')

# cp/mv ... /tmp/... (the .+\s ensures there's a source arg before /tmp dest)
CP_MV_TO_TMP = re.compile(r'\b(cp|mv)\b.+\s"?/tmp/')

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
    CP_MV_TO_TMP,
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

    # mktemp: deny if present without a custom non-/tmp directory
    if MKTEMP_PRESENT.search(command):
        if not MKTEMP_CUSTOM_DIR.search(command):
            return make_deny(DENY_MESSAGE)

    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input -- allow the operation
        print(make_allow())
        return

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
    main()
