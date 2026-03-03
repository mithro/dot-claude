#!/usr/bin/env python3
"""PreToolUse hook: Block SSH hostname hashing.

Blocks the -H flag on ssh-keyscan, ssh-keygen, and other SSH tools,
and blocks HashKnownHosts=yes in SSH config files. We want proper
hostnames, not hashed versions.
"""

import json
import re
import sys


def check_bash_command(command: str) -> str | None:
    """Check if a bash command uses SSH hostname hashing.

    Returns a reason string if blocked, None if allowed.
    """
    # Split on common shell operators to find individual commands
    # This handles: cmd1 && cmd2, cmd1 || cmd2, cmd1 | cmd2, cmd1; cmd2
    # Also handles $() and backtick subshells (imperfectly, but good enough)
    simple_commands = re.split(r'&&|\|\||\||;|`|\$\(', command)

    for simple_cmd in simple_commands:
        simple_cmd = simple_cmd.strip()

        # Strip leading sudo/env/nice etc.
        while True:
            match = re.match(r'^(?:sudo|env|nice|nohup|command)\s+', simple_cmd)
            if match:
                simple_cmd = simple_cmd[match.end():]
            else:
                break

        # Check if this is an SSH tool command
        cmd_match = re.match(r'^(ssh-keyscan|ssh-keygen|ssh-copy-id|ssh-add|ssh)\b', simple_cmd)
        if not cmd_match:
            continue

        tool_name = cmd_match.group(1)

        # Now check for -H flag in this specific command's arguments
        # Parse the rest of the command after the tool name
        rest = simple_cmd[cmd_match.end():]

        # Look for -H as a standalone flag or combined with other short flags
        # Examples: -H, -tH, -Ht, -tHr
        if re.search(r'(?:^|\s)-[a-zA-Z]*H[a-zA-Z]*\b', rest):
            return (
                f"BLOCKED: '{tool_name}' with -H flag hashes hostnames.\n"
                f"Remove the -H flag to keep proper hostnames."
            )

        # Also check for HashKnownHosts in -o options
        if re.search(r'HashKnownHosts', rest):
            return (
                f"BLOCKED: '{tool_name}' with HashKnownHosts option hashes hostnames.\n"
                f"Use -o HashKnownHosts=no or omit the option entirely."
            )

    return None


def check_file_edit(tool_input: dict) -> str | None:
    """Check if a file edit adds HashKnownHosts yes/1.

    Returns a reason string if blocked, None if allowed.
    """
    # Check new_text (Edit tool) or content (Write tool)
    text = tool_input.get('new_text', '') or tool_input.get('content', '')

    for line in text.splitlines():
        # Skip comment lines (SSH config uses # for comments)
        if line.lstrip().startswith('#'):
            continue
        if re.search(r'HashKnownHosts\s+(yes|1)\b', line):
            return (
                "BLOCKED: Do not set HashKnownHosts to yes.\n"
                "This hashes hostnames making known_hosts unreadable.\n"
                "Use 'HashKnownHosts no' or omit the setting."
            )

    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't read input, allow the operation
        print(json.dumps({}))
        return

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    reason = None

    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        reason = check_bash_command(command)

    elif tool_name in ('Edit', 'Write', 'MultiEdit'):
        reason = check_file_edit(tool_input)

    if reason:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
            },
            "systemMessage": reason,
        }
        print(json.dumps(result))
    else:
        print(json.dumps({}))


if __name__ == '__main__':
    main()
