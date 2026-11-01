#!/usr/bin/env python3
"""PreToolUse hook: block unsafe SSH host verification options.

Blocks:
  - StrictHostKeyChecking=no  (disables host key verification entirely)
  - UserKnownHostsFile=/dev/null  (discards learned host keys)

in both `-o Option=value` and `-o 'Option value'` command-line spellings, and
as directives written to SSH config files (~/.ssh/*, /etc/ssh/*, *ssh_config*).
Writes to other files that merely mention the options (docs, code, tests) are
not the hook's business.

These are commonly used together to blindly accept any host key, which
defeats SSH's protection against man-in-the-middle attacks.

Allows:
  - StrictHostKeyChecking=accept-new  (accept first-seen keys, reject changes)
  - StrictHostKeyChecking=yes / ask  (strict verification)
  - UserKnownHostsFile=<any real path>  (any file that isn't /dev/null)

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


DENY_STRICT_HOST_KEY = """❌ **`StrictHostKeyChecking no` blocked by hook**

Setting `StrictHostKeyChecking` to `no` disables SSH host key verification
entirely — any host key is silently accepted, even if it has changed.
This defeats SSH's protection against man-in-the-middle attacks.

**Use `accept-new` instead:**
```
# Command line:
ssh -o StrictHostKeyChecking=accept-new user@host

# SSH config:
StrictHostKeyChecking accept-new
```

`accept-new` accepts keys for hosts seen for the first time, but rejects
changed keys for previously-seen hosts — much safer than `no`."""

DENY_KNOWN_HOSTS_DEV_NULL = """❌ **`UserKnownHostsFile /dev/null` blocked by hook**

Setting `UserKnownHostsFile` to `/dev/null` discards all learned host keys,
so SSH can never detect a changed (potentially compromised) host key.
This is usually paired with `StrictHostKeyChecking no` to silently accept
everything — defeating SSH's MITM protection.

**Remove this option** and let SSH use its default known_hosts file.
If you need a separate known_hosts file, point it to a real path:
```
ssh -o UserKnownHostsFile=~/.ssh/known_hosts_project user@host
```"""


# --- Command-line patterns ---
# ssh accepts both `-o Option=value` and `-o 'Option value'`; the quote is
# optional and the value may be separated by `=` or whitespace.

STRICT_HOST_KEY_NO_CLI = re.compile(
    r"""-o\s*['"]?StrictHostKeyChecking[\s=]+no\b""",
    re.IGNORECASE,
)

KNOWN_HOSTS_DEV_NULL_CLI = re.compile(
    r"""-o\s*['"]?UserKnownHostsFile[\s=]+/dev/null\b""",
    re.IGNORECASE,
)

# --- Config file patterns (directive per line, whitespace separated) ---

STRICT_HOST_KEY_NO_CONF = re.compile(
    r'^\s*StrictHostKeyChecking\s+no\s*$',
    re.MULTILINE | re.IGNORECASE,
)

KNOWN_HOSTS_DEV_NULL_CONF = re.compile(
    r'^\s*UserKnownHostsFile\s+/dev/null\s*$',
    re.MULTILINE | re.IGNORECASE,
)

# Only SSH config files are in scope for Write/Edit: ~/.ssh/..., /etc/ssh/...,
# anything named *ssh_config* (incl. drop-in directories).
SSH_CONFIG_PATH = re.compile(r'(^|/)(\.ssh/|etc/ssh/)|(^|/)ssh_config')


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


def check_bash_command(command):
    """Return a denial message if the command uses unsafe SSH options, else None."""
    if STRICT_HOST_KEY_NO_CLI.search(command):
        return DENY_STRICT_HOST_KEY
    if KNOWN_HOSTS_DEV_NULL_CLI.search(command):
        return DENY_KNOWN_HOSTS_DEV_NULL
    return None


def check_file_content(tool_input):
    """Return a denial message if an SSH config write/edit adds unsafe options."""
    if not SSH_CONFIG_PATH.search(tool_input.get('file_path', '') or ''):
        return None

    # new_string (Edit tool) or content (Write tool)
    text = tool_input.get('new_string', '') or tool_input.get('content', '') or ''

    # Comment lines are harmless
    non_comment = [line for line in text.splitlines() if not line.lstrip().startswith('#')]
    filtered = '\n'.join(non_comment)

    if STRICT_HOST_KEY_NO_CONF.search(filtered):
        return DENY_STRICT_HOST_KEY
    if KNOWN_HOSTS_DEV_NULL_CONF.search(filtered):
        return DENY_KNOWN_HOSTS_DEV_NULL
    return None


def main():
    input_data = json.load(sys.stdin)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {}) or {}
    reason = None

    if tool_name == 'Bash':
        reason = check_bash_command(tool_input.get('command', '') or '')
    elif tool_name in ('Edit', 'Write'):
        reason = check_file_content(tool_input)

    if reason:
        deny(reason)
    else:
        allow()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Fail open, but visibly: exit 1 is a non-blocking hook error whose
        # stderr Claude Code shows to the user. Exit 0 with `{}` would hide the bug.
        print(f"{Path(__file__).name}: hook failed, allowing the tool call:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
