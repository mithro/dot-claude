#!/usr/bin/env python3
"""PreToolUse hook: auto-allow SSH/scp/rsync to configured hosts.

Reads ~/.claude/ssh-allowed-hosts.json for a list of trusted hosts.
When a Bash command targets a configured host, returns permissionDecision:
"allow" so Claude doesn't prompt for permission.

Config format (~/.claude/ssh-allowed-hosts.json):
[
  {
    "host": "server.example.com",
    "user": "tim",
    "sudo": true
  }
]

Fields:
  - host (required): hostname or IP
  - user (optional): if specified, only allow SSH as this user
  - sudo (optional, default false): whether to auto-allow sudo commands

Auto-allows:
  - ssh [flags] [user@]host command
  - ssh [flags] -l user host command
  - scp file [user@]host:/tmp/path  (tmp dirs only)
  - rsync file [user@]host:/tmp/path  (tmp dirs only)

Returns {} (no opinion) for everything else, falling through to normal
permission prompting.
"""

import json
import os
import re
import shlex
import sys

CONFIG_PATH = os.path.expanduser('~/.claude/ssh-allowed-hosts.json')

# SSH flags that take an argument (the next token)
SSH_FLAGS_WITH_ARG = set('bcDEeFIiJLlmOopQRSwWo')

# SSH flags that do NOT take an argument
SSH_FLAGS_NO_ARG = set('46AaCfGgKkMNnqsTtVvXxYy')


def load_config():
    """Load allowed hosts config. Returns [] on any error."""
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        if not isinstance(config, list):
            return []
        return config
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def find_allowed_host(config, host, user):
    """Check if host/user combination is in the allowed config.

    Returns the config entry if found, None otherwise.
    """
    for entry in config:
        if not isinstance(entry, dict):
            continue
        if entry.get('host') != host:
            continue
        # If entry specifies a user, it must match
        config_user = entry.get('user')
        if config_user is not None and config_user != user:
            continue
        return entry
    return None


def parse_ssh_command(tokens):
    """Parse ssh command tokens to extract host, user, and remote command.

    Returns (user, host, remote_cmd_tokens) or None if parsing fails.

    Handles:
      ssh [options] [user@]hostname [command...]
      ssh [options] -l user hostname [command...]
    """
    i = 0
    user_from_l = None

    # Walk past options
    while i < len(tokens):
        token = tokens[i]

        if not token.startswith('-'):
            # First non-option token is the host
            break

        if token == '--':
            # End of options
            i += 1
            break

        # Handle combined flags like -tt or -vvv
        # And flags with args like -oOption=val or -p22
        flag_str = token[1:]  # strip leading '-'

        # Check if it's a long-ish combined form like -oStrictHostKeyChecking=accept-new
        if len(flag_str) > 1 and flag_str[0] in SSH_FLAGS_WITH_ARG:
            # The rest of the token is the argument to this flag
            if flag_str[0] == 'l':
                user_from_l = flag_str[1:]
            i += 1
            continue

        # Walk through the flag characters
        j = 0
        consumed_arg = False
        while j < len(flag_str):
            ch = flag_str[j]
            if ch in SSH_FLAGS_WITH_ARG:
                # If there are more chars after this, they're the arg value
                if j + 1 < len(flag_str):
                    if ch == 'l':
                        user_from_l = flag_str[j + 1:]
                    consumed_arg = True
                    break
                else:
                    # Next token is the argument
                    i += 1
                    if i < len(tokens):
                        if ch == 'l':
                            user_from_l = tokens[i]
                    consumed_arg = True
                    break
            elif ch in SSH_FLAGS_NO_ARG:
                j += 1
            else:
                # Unknown flag — skip it
                j += 1

        i += 1

        if consumed_arg:
            continue

    if i >= len(tokens):
        # No host found (e.g., ssh -V)
        return None

    # tokens[i] is the hostname (possibly user@host)
    host_token = tokens[i]
    i += 1

    user = user_from_l
    host = host_token

    if '@' in host_token:
        user, host = host_token.split('@', 1)

    # Remaining tokens are the remote command
    remote_cmd = tokens[i:]

    return (user, host, remote_cmd)


def parse_scp_rsync_targets(tokens):
    """Parse scp/rsync tokens to extract remote targets.

    Returns list of (user, host, path) tuples for remote targets.
    Remote targets match the pattern [user@]host:path.
    """
    targets = []
    i = 0

    # Skip options first
    while i < len(tokens):
        token = tokens[i]
        if token == '--':
            i += 1
            break
        if not token.startswith('-'):
            break
        # scp/rsync options that take arguments
        # Common ones: -P port, -i identity, -F config, -e rsh, -o option
        if len(token) == 2 and token[1] in 'PiFeoS':
            i += 2  # skip flag and its argument
            continue
        i += 1

    # Remaining tokens are source(s) and destination
    # Look for remote targets: [user@]host:path
    while i < len(tokens):
        token = tokens[i]
        # Match user@host:path or host:path
        # But not absolute paths like /tmp/foo or relative paths
        # Also not URLs like http://...
        match = re.match(r'^(?:([^@:]+)@)?([^@:/][^@:]*):(.*)$', token)
        if match:
            user = match.group(1)
            host = match.group(2)
            path = match.group(3)
            targets.append((user, host, path))
        i += 1

    return targets


def is_tmp_path(path):
    """Check if a remote path is within a tmp directory.

    Allows:
      /tmp/...     — absolute tmp
      tmp/...      — relative ~/tmp/
      /var/tmp/... — system tmp

    Empty path (host:) is NOT allowed — that's the home directory.
    """
    if not path:
        return False
    return (
        path.startswith('/tmp/')
        or path == '/tmp'
        or path.startswith('tmp/')
        or path == 'tmp'
        or path.startswith('/var/tmp/')
        or path == '/var/tmp'
    )


def extract_first_command(command):
    """Extract individual commands from a shell command string.

    Splits on shell operators (&&, ||, |, ;) and returns all simple
    commands. Also handles $() and backtick subshells by splitting on them.
    """
    # Split on shell operators
    parts = re.split(r'&&|\|\||[|;]|`|\$\(', command)
    return [p.strip() for p in parts if p.strip()]


def strip_privilege_prefixes(tokens):
    """Strip leading privilege/environment wrapper commands.

    Removes: sudo, env, nice, nohup, command, etc.
    """
    privilege_cmds = {'sudo', 'env', 'nice', 'nohup', 'command'}
    while tokens:
        if tokens[0] in privilege_cmds:
            tokens = tokens[1:]
            # Skip sudo flags like -u user, -i, etc.
            while tokens and tokens[0].startswith('-'):
                flag = tokens[0]
                tokens = tokens[1:]
                # sudo flags that take an argument
                if flag in ('-u', '-g', '-C', '-D', '-R', '-T'):
                    if tokens:
                        tokens = tokens[1:]
            continue
        # env VAR=val ... — skip variable assignments
        if tokens[0] and '=' in tokens[0] and not tokens[0].startswith('-'):
            # Could be env FOO=bar cmd — skip the assignment
            # But only if it looks like VAR=val (starts with letter/underscore)
            if re.match(r'^[A-Za-z_]\w*=', tokens[0]):
                tokens = tokens[1:]
                continue
        break
    return tokens


def check_command(command, config):
    """Check a single bash command against the allowed hosts config.

    Returns True if the command should be auto-allowed, False otherwise.
    """
    # Split into simple commands and check each
    simple_commands = extract_first_command(command)

    for simple_cmd in simple_commands:
        try:
            tokens = shlex.split(simple_cmd)
        except ValueError:
            # Malformed shell quoting — don't auto-allow
            return False

        if not tokens:
            continue

        tokens = strip_privilege_prefixes(tokens)
        if not tokens:
            continue

        cmd = tokens[0]
        args = tokens[1:]

        if cmd == 'ssh':
            result = parse_ssh_command(args)
            if result is None:
                continue

            user, host, remote_cmd = result
            entry = find_allowed_host(config, host, user)
            if entry is None:
                # Host not in config — don't auto-allow
                return False

            # Check if remote command uses sudo
            remote_stripped = strip_privilege_prefixes(list(remote_cmd))
            # The original remote_cmd had sudo if stripping changed it
            uses_sudo = (list(remote_cmd) != remote_stripped)
            if uses_sudo and not entry.get('sudo', False):
                return False

        elif cmd in ('scp', 'rsync'):
            targets = parse_scp_rsync_targets(args)
            if not targets:
                # No remote targets found — not an SSH operation
                continue

            for user, host, path in targets:
                entry = find_allowed_host(config, host, user)
                if entry is None:
                    return False
                if not is_tmp_path(path):
                    return False

        else:
            # Not an ssh/scp/rsync command — don't auto-allow the whole thing
            # But also don't block — it might be piped with an ssh command.
            # We only auto-allow if ALL ssh/scp/rsync parts are allowed.
            continue

    # Only auto-allow if we found at least one ssh/scp/rsync command
    # and none of them were disallowed
    has_ssh_cmd = False
    for simple_cmd in simple_commands:
        try:
            tokens = shlex.split(simple_cmd)
        except ValueError:
            return False
        if not tokens:
            continue
        tokens = strip_privilege_prefixes(tokens)
        if tokens and tokens[0] in ('ssh', 'scp', 'rsync'):
            has_ssh_cmd = True
            break

    return has_ssh_cmd


def make_allow():
    """Return a permission-granting response."""
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        },
    })


def make_pass():
    """Return an empty response (no opinion — pass through to normal prompting)."""
    return json.dumps({})


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print(make_pass())
        return

    tool_name = input_data.get('tool_name', '')
    if tool_name != 'Bash':
        print(make_pass())
        return

    command = input_data.get('tool_input', {}).get('command', '')
    if not command:
        print(make_pass())
        return

    config = load_config()
    if not config:
        print(make_pass())
        return

    if check_command(command, config):
        print(make_allow())
    else:
        print(make_pass())


if __name__ == '__main__':
    main()
