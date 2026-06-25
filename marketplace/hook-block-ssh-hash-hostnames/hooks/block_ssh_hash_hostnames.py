#!/usr/bin/env python3
"""PreToolUse hook: Block SSH hostname hashing.

Blocks the -H flag on ssh-keyscan, ssh-keygen, and other SSH tools,
and blocks HashKnownHosts=yes in SSH config files. We want proper
hostnames, not hashed versions.
"""

import json
import re
import shlex
import sys


def extract_ssh_own_args(rest: str) -> str:
    """For 'ssh [options] hostname [command]', extract only the [options] part.

    Returns a string containing only ssh's own options (before the hostname),
    so we can check for -H without matching flags in the remote command
    (e.g. curl -H for HTTP headers).

    For parse failures (e.g. unmatched quotes from command splitting),
    returns the full string as a safe fallback — may give false positives
    but won't miss real -H usage.
    """
    try:
        tokens = shlex.split(rest)
    except ValueError:
        # shlex can't parse (e.g. unmatched quote) — fall back to full string
        return rest

    # SSH options that require a following argument value
    opts_with_args = set('bcDEeFIiJLlmOopQRSWw')

    option_parts = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == '--':
            # Explicit end of options
            break
        if token.startswith('-') and len(token) > 1:
            option_parts.append(token)
            # In combined flags like -vi, the last char determines
            # whether the next token is consumed as an argument
            flag_chars = token[1:]
            if flag_chars and flag_chars[-1] in opts_with_args:
                # Next token is the option's argument value
                if i + 1 < len(tokens):
                    option_parts.append(tokens[i + 1])
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        else:
            # First non-option token is the hostname — stop here.
            # Everything after is the remote command.
            break

    return ' '.join(option_parts)


def split_shell_commands(command: str) -> list[str]:
    """Split a command string on shell operators, respecting quotes.

    Splits on: && || | ; ` $(
    Does NOT split when these operators appear inside single or double quotes.
    """
    parts = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    n = len(command)

    while i < n:
        c = command[i]

        if in_single_quote:
            # Inside single quotes, everything is literal except closing '
            current.append(c)
            if c == "'":
                in_single_quote = False
            i += 1
        elif in_double_quote:
            # Inside double quotes, backslash can escape certain chars
            if c == '\\' and i + 1 < n:
                current.append(c)
                current.append(command[i + 1])
                i += 2
            elif c == '"':
                current.append(c)
                in_double_quote = False
                i += 1
            else:
                current.append(c)
                i += 1
        else:
            # Outside quotes — check for quote starts and operators
            if c == "'":
                in_single_quote = True
                current.append(c)
                i += 1
            elif c == '"':
                in_double_quote = True
                current.append(c)
                i += 1
            elif c == '\\' and i + 1 < n:
                current.append(c)
                current.append(command[i + 1])
                i += 2
            elif command[i:i+2] == '&&':
                parts.append(''.join(current))
                current = []
                i += 2
            elif command[i:i+2] == '||':
                parts.append(''.join(current))
                current = []
                i += 2
            elif command[i:i+2] == '$(':
                parts.append(''.join(current))
                current = []
                i += 2
            elif c == '|':
                parts.append(''.join(current))
                current = []
                i += 1
            elif c == ';':
                parts.append(''.join(current))
                current = []
                i += 1
            elif c == '`':
                parts.append(''.join(current))
                current = []
                i += 1
            else:
                current.append(c)
                i += 1

    parts.append(''.join(current))
    return parts


def check_bash_command(command: str) -> str | None:
    """Check if a bash command uses SSH hostname hashing.

    Returns a reason string if blocked, None if allowed.
    """
    # Split on shell operators respecting quotes, so operators inside
    # quoted strings (e.g. ssh host 'cmd1 | cmd2') are not treated as pipes
    simple_commands = split_shell_commands(command)

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

        # Parse the rest of the command after the tool name
        rest = simple_cmd[cmd_match.end():]

        # For 'ssh', only check flags before the hostname — everything
        # after the hostname is the remote command, where -H could belong
        # to another tool (e.g. curl -H for HTTP headers).
        # For ssh-keyscan/ssh-keygen/etc., check all arguments.
        if tool_name == 'ssh':
            args_to_check = extract_ssh_own_args(rest)
        else:
            args_to_check = rest

        # Look for -H as a standalone flag or combined with other short flags
        # Examples: -H, -tH, -Ht, -tHr
        if re.search(r'(?:^|\s)-[a-zA-Z]*H[a-zA-Z]*\b', args_to_check):
            return (
                f"BLOCKED: '{tool_name}' with -H flag hashes hostnames.\n"
                f"Remove the -H flag to keep proper hostnames."
            )

        # Also check for HashKnownHosts in -o options
        if re.search(r'HashKnownHosts', args_to_check):
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
