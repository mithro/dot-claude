#!/usr/bin/env python3
"""PreToolUse hook: Block SSH hostname hashing.

Blocks the -H flag on ssh-keyscan, ssh-keygen, and other SSH tools,
and blocks HashKnownHosts=yes in SSH config files. We want proper
hostnames, not hashed versions.

For ssh itself, only ssh's own options are checked: everything after the
destination is the remote command, which is checked recursively as its own
shell command (so `ssh host 'ipmitool -H ...'` is fine, but both
`ssh -H host` and `ssh host 'ssh-keyscan -H ...'` are blocked).
"""

import json
import re
import shlex
import sys

SSH_TOOLS = {'ssh', 'ssh-keyscan', 'ssh-keygen', 'ssh-copy-id', 'ssh-add'}

# Wrappers that may precede the real command.
PREFIX_CMDS = {'sudo', 'env', 'nice', 'nohup', 'command'}

# ssh client options that consume a following argument (OpenSSH 9.x).
SSH_ARG_OPTS = set('BbcDEeFIiJLlmOopQRSWw')

# Tokens that end one simple command and start another.
COMMAND_SEPARATORS = {'&&', '||', '|', '|&', ';', ';;', '&', '(', ')'}

HASH_OPTION_ENABLED = re.compile(r'HashKnownHosts[\s=]+(yes|1)\b', re.IGNORECASE)

SSH_CONFIG_PATH = re.compile(r'(^|/)(\.ssh/|etc/ssh/)|(^|/)ssh_config')


def blocked_h(tool_name: str) -> str:
    return (
        f"BLOCKED: '{tool_name}' with -H flag hashes hostnames.\n"
        f"Remove the -H flag to keep proper hostnames."
    )


def blocked_hash_option(tool_name: str) -> str:
    return (
        f"BLOCKED: '{tool_name}' with HashKnownHosts=yes hashes hostnames.\n"
        f"Use -o HashKnownHosts=no or omit the option entirely."
    )


def split_simple_commands(tokens: list[str]) -> list[list[str]]:
    """Split a token stream into simple commands at shell operators.

    Command substitutions also start a new command: `(` is its own token
    (shlex punctuation), while backticks stay glued to the word, so a
    leading backtick is stripped and treated as a command boundary.
    """
    commands: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok in COMMAND_SEPARATORS:
            if current:
                commands.append(current)
                current = []
        elif tok.startswith('`'):
            if current:
                commands.append(current)
            stripped = tok.lstrip('`')
            current = [stripped] if stripped else []
        else:
            current.append(tok)
    if current:
        commands.append(current)
    return commands


def check_ssh_args(args: list[str]) -> str | None:
    """Walk ssh's own options up to the destination.

    The remote command (everything after the destination) runs under a
    remote shell, so it is re-checked as a shell command of its own.
    """
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == '--':
            i += 1
            continue
        if tok.startswith('-') and len(tok) > 1:
            flags = tok[1:]
            j = 0
            while j < len(flags):
                ch = flags[j]
                if ch == 'H':
                    return blocked_h('ssh')
                if ch in SSH_ARG_OPTS:
                    value = flags[j + 1:]
                    if not value:
                        i += 1
                        value = args[i] if i < len(args) else ''
                    if ch == 'o' and HASH_OPTION_ENABLED.search(value):
                        return blocked_hash_option('ssh')
                    break
                j += 1
            i += 1
            continue
        # First non-option token is the destination; the rest is the
        # remote command.
        # One level of quoting was already consumed by the outer parse,
        # so a plain join reproduces what the remote shell will parse.
        remote = args[i + 1:]
        if remote:
            return check_bash_command(' '.join(remote))
        return None
    return None


def check_tool_args(tool_name: str, args: list[str]) -> str | None:
    """Check ssh-keyscan/ssh-keygen/etc, where every arg is the tool's own."""
    for tok in args:
        if tok.startswith('-') and not tok.startswith('--'):
            flags = tok[1:].split('=', 1)[0]
            if 'H' in flags:
                return blocked_h(tool_name)
        if HASH_OPTION_ENABLED.search(tok):
            return blocked_hash_option(tool_name)
    return None


def check_simple_command(tokens: list[str]) -> str | None:
    # Strip wrapper commands and leading VAR=VALUE assignments.
    while tokens and (
        tokens[0] in PREFIX_CMDS
        or ('=' in tokens[0] and not tokens[0].startswith('-'))
    ):
        tokens = tokens[1:]
    if not tokens:
        return None
    tool_name = tokens[0].rsplit('/', 1)[-1]
    if tool_name not in SSH_TOOLS:
        return None
    if tool_name == 'ssh':
        return check_ssh_args(tokens[1:])
    return check_tool_args(tool_name, tokens[1:])


def check_bash_command(command: str) -> str | None:
    """Check if a bash command uses SSH hostname hashing.

    Returns a reason string if blocked, None if allowed.
    """
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        # Unbalanced quotes etc. -- the shell would reject it too.
        return None

    for simple_cmd in split_simple_commands(tokens):
        reason = check_simple_command(simple_cmd)
        if reason:
            return reason
    return None


def check_file_edit(tool_input: dict) -> str | None:
    """Check if an SSH config file edit enables HashKnownHosts.

    Returns a reason string if blocked, None if allowed.
    """
    # Only SSH config files are in scope; the option string is harmless
    # in code, docs, or other files.
    file_path = tool_input.get('file_path', '')
    if not SSH_CONFIG_PATH.search(file_path):
        return None

    # Check new_text (Edit tool) or content (Write tool)
    text = tool_input.get('new_text', '') or tool_input.get('content', '')

    for line in text.splitlines():
        # Skip comment lines (SSH config uses # for comments)
        if line.lstrip().startswith('#'):
            continue
        if HASH_OPTION_ENABLED.search(line):
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
