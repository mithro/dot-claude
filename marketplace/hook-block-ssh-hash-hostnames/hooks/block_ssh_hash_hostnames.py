#!/usr/bin/env python3
"""PreToolUse hook: Block SSH hostname hashing.

Blocks the -H flag on ssh-keyscan, ssh-keygen, and other SSH tools,
and blocks HashKnownHosts=yes in SSH config files. We want proper
hostnames, not hashed versions.

For ssh itself, only ssh's own options are checked: everything after the
destination is the remote command, which is checked recursively as its own
shell command (so `ssh host 'ipmitool -H ...'` is fine, but both
`ssh -H host` and `ssh host 'ssh-keyscan -H ...'` are blocked).

Wrappers are looked through: sudo/env/nice/nohup/timeout/xargs/..., `bash -c
'...'`, and a leading VAR=value whose value is itself an ssh command
(GIT_SSH_COMMAND='ssh -o HashKnownHosts=yes').
"""

from __future__ import annotations

import json
import re
import shlex
import sys
import traceback
from pathlib import Path

SSH_TOOLS = {'ssh', 'ssh-keyscan', 'ssh-keygen', 'ssh-copy-id', 'ssh-add'}

# Wrappers that may precede the real command -> the wrapper's own options that
# consume the next token.
PREFIX_CMDS: dict[str, set[str]] = {
    'sudo': {'-u', '-g', '-C', '-D', '-R', '-T', '-U', '-h', '-p', '-r', '-t'},
    'doas': {'-u', '-C'},
    'env': {'-u', '-C', '-S', '--unset', '--chdir', '--split-string'},
    'nice': {'-n'},
    'nohup': set(),
    'command': set(),
    'time': {'-f', '-o'},
    'stdbuf': {'-i', '-o', '-e'},
    'xargs': {'-n', '-I', '-P', '-L', '-s', '-d', '-E', '-a', '-l',
              '--max-args', '--max-procs', '--max-lines', '--replace',
              '--delimiter', '--arg-file', '--max-chars'},
    'timeout': {'-k', '-s', '--kill-after', '--signal'},
}
# Wrappers that take positional arguments before the command (timeout DURATION).
PREFIX_POSITIONALS = {'timeout': 1}

# Shells whose -c argument is a command string of its own.
SHELLS = {'bash', 'sh', 'zsh', 'dash', 'ksh'}

# ssh client options that consume a following argument (OpenSSH 9.x).
SSH_ARG_OPTS = set('BbcDEeFIiJLlmOopQRSWw')

# Tokens that end one simple command and start another.
COMMAND_SEPARATORS = {'&&', '||', '|', '|&', ';', ';;', '&', '(', ')'}

# ssh accepts yes/true/1 for boolean options.
HASH_OPTION_ENABLED = re.compile(r'HashKnownHosts[\s=]+(yes|true|1)\b', re.IGNORECASE)

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


def strip_wrapper(name: str, tokens: list[str]) -> list[str]:
    """Drop a wrapper's own options (and positionals) to reach the wrapped command."""
    arg_opts = PREFIX_CMDS[name]
    while tokens and tokens[0].startswith('-') and tokens[0] != '-':
        opt = tokens[0]
        tokens = tokens[1:]
        if opt in arg_opts and tokens:
            tokens = tokens[1:]
    return tokens[PREFIX_POSITIONALS.get(name, 0):]


def check_simple_command(tokens: list[str]) -> str | None:
    tokens = list(tokens)
    while tokens:
        head = tokens[0].rsplit('/', 1)[-1]
        if '=' in tokens[0] and not tokens[0].startswith('-'):
            # Leading VAR=value: the value may itself be an ssh command line
            # (GIT_SSH_COMMAND='ssh -o HashKnownHosts=yes').
            reason = check_bash_command(tokens[0].split('=', 1)[1])
            if reason:
                return reason
            tokens = tokens[1:]
        elif head in PREFIX_CMDS:
            tokens = strip_wrapper(head, tokens[1:])
        else:
            break
    if not tokens:
        return None
    tool_name = tokens[0].rsplit('/', 1)[-1]
    if tool_name in SHELLS and '-c' in tokens[1:]:
        script_index = tokens.index('-c', 1) + 1
        if script_index < len(tokens):
            return check_bash_command(tokens[script_index])
        return None
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

    def enabled_lines(text: str) -> int:
        # Comment lines don't count (SSH config uses # for comments).
        return sum(
            1 for line in (text or '').splitlines()
            if not line.lstrip().startswith('#') and HASH_OPTION_ENABLED.search(line)
        )

    if 'new_string' in tool_input:  # Edit tool: deny only if the edit ADDS one
        added = enabled_lines(tool_input.get('new_string', '')) > enabled_lines(
            tool_input.get('old_string', ''))
    else:  # Write tool
        added = enabled_lines(tool_input.get('content', '')) > 0

    if added:
        return (
            "BLOCKED: Do not set HashKnownHosts to yes.\n"
            "This hashes hostnames making known_hosts unreadable.\n"
            "Use 'HashKnownHosts no' or omit the setting."
        )
    return None


def deny(message: str) -> None:
    """permissionDecisionReason is what the model sees; systemMessage is for the user."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
        "systemMessage": message,
    }))


def allow() -> None:
    print(json.dumps({}))


def main():
    input_data = json.load(sys.stdin)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {}) or {}
    reason = None

    if tool_name == 'Bash':
        reason = check_bash_command(tool_input.get('command', '') or '')
    elif tool_name in ('Edit', 'Write'):
        reason = check_file_edit(tool_input)

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
