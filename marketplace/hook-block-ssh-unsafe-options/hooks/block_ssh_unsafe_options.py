#!/usr/bin/env python3
"""PreToolUse hook: block unsafe SSH host verification options.

Blocks:
  - StrictHostKeyChecking=no  (disables host key verification entirely)
  - UserKnownHostsFile=/dev/null  (discards learned host keys)

These are commonly used together to blindly accept any host key, which
defeats SSH's protection against man-in-the-middle attacks.

Allows:
  - StrictHostKeyChecking=accept-new  (accept first-seen keys, reject changes)
  - StrictHostKeyChecking=yes / ask  (strict verification)
  - UserKnownHostsFile=<any real path>  (any file that isn't /dev/null)
"""

import json
import re
import sys


DENY_STRICT_HOST_KEY = """\u274c **`StrictHostKeyChecking no` blocked by hook**

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

DENY_KNOWN_HOSTS_DEV_NULL = """\u274c **`UserKnownHostsFile /dev/null` blocked by hook**

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

# -o StrictHostKeyChecking=no (with or without space after -o)
# Matches: -o StrictHostKeyChecking=no, -oStrictHostKeyChecking=no
STRICT_HOST_KEY_NO_CLI = re.compile(
    r'-o\s*StrictHostKeyChecking\s*=\s*no\b',
    re.IGNORECASE,
)

# -o UserKnownHostsFile=/dev/null (with or without space after -o)
KNOWN_HOSTS_DEV_NULL_CLI = re.compile(
    r'-o\s*UserKnownHostsFile\s*=\s*/dev/null\b',
    re.IGNORECASE,
)

# --- Config file patterns ---

# StrictHostKeyChecking no  (SSH config format uses space, not =)
STRICT_HOST_KEY_NO_CONF = re.compile(
    r'^\s*StrictHostKeyChecking\s+no\s*$',
    re.MULTILINE | re.IGNORECASE,
)

# UserKnownHostsFile /dev/null  (SSH config format)
KNOWN_HOSTS_DEV_NULL_CONF = re.compile(
    r'^\s*UserKnownHostsFile\s+/dev/null\s*$',
    re.MULTILINE | re.IGNORECASE,
)


def check_bash_command(command: str) -> str | None:
    """Check if a bash command uses unsafe SSH options.

    Returns a denial message if blocked, None if allowed.
    """
    if STRICT_HOST_KEY_NO_CLI.search(command):
        return DENY_STRICT_HOST_KEY

    if KNOWN_HOSTS_DEV_NULL_CLI.search(command):
        return DENY_KNOWN_HOSTS_DEV_NULL

    return None


def check_file_content(tool_input: dict) -> str | None:
    """Check if a file write/edit adds unsafe SSH options.

    Returns a denial message if blocked, None if allowed.
    """
    # Check new_string (Edit tool) or content (Write tool)
    text = tool_input.get('new_string', '') or tool_input.get('content', '')

    # Filter out comment lines before checking
    non_comment_lines = []
    for line in text.splitlines():
        if not line.lstrip().startswith('#'):
            non_comment_lines.append(line)
    filtered = '\n'.join(non_comment_lines)

    if STRICT_HOST_KEY_NO_CONF.search(filtered):
        return DENY_STRICT_HOST_KEY

    if KNOWN_HOSTS_DEV_NULL_CONF.search(filtered):
        return DENY_KNOWN_HOSTS_DEV_NULL

    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({}))
        return

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    reason = None

    if tool_name == 'Bash':
        reason = check_bash_command(tool_input.get('command', ''))

    elif tool_name in ('Edit', 'Write'):
        reason = check_file_content(tool_input)

    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": reason,
        }))
    else:
        print(json.dumps({}))


if __name__ == '__main__':
    main()
