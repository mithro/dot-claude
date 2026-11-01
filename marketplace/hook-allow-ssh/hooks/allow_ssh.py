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
    "permit-root-access": true
  }
]

Fields:
  - host (required): hostname or IP
  - user (optional): if specified, only allow SSH as this user
  - permit-root-access (optional, default false): whether to auto-allow
    root-level access. This gates both logging in as root (ssh root@host)
    and running sudo on the remote host (ssh user@host sudo cmd), since
    both give full root access.

Auto-allows:
  - ssh [flags] [user@]host command
  - ssh [flags] -l user host command
  - scp file [user@]host:/tmp/path  (tmp dirs only)
  - rsync file [user@]host:/tmp/path  (tmp dirs only)
  - any of the above piped into read-only local filters (grep, awk, head...)

Never auto-allows anything that would run or write something LOCALLY
without a prompt:
  - a second command (`;`, `&`, `&&`, `||`, newline, `$( )`, backticks)
  - a redirection outside quotes (`>`, `>>`, `<`)
  - a pipe into anything other than a known read-only filter (`| bash`,
    `| xargs rm`, `| tee file`)
  - ssh options whose value the LOCAL client executes or that load an
    arbitrary config: -o ProxyCommand/LocalCommand/PermitLocalCommand/
    KnownHostsCommand/Include/Match, and -F <config>
Operators inside the quoted remote command run on the remote host and are fine.

Returns {} (no opinion) for everything else, falling through to normal
permission prompting.

Output protocol: an allow carries permissionDecisionReason (shown to the user
in the transcript) naming the matched host, so it is clear why no prompt
appeared. If the hook itself fails it exits 1 with a traceback on stderr: a
non-blocking error that falls back to normal prompting but is visible, rather
than silently passing.
"""

import json
import os
import re
import shlex
import sys
import traceback

CONFIG_PATH = os.path.expanduser('~/.claude/ssh-allowed-hosts.json')
CONFIG_DISPLAY = '~/.claude/ssh-allowed-hosts.json'

# SSH flags that take an argument (the next token)
SSH_FLAGS_WITH_ARG = set('bcDEeFIiJLlmOopQRSwWo')

# SSH flags that do NOT take an argument
SSH_FLAGS_NO_ARG = set('46AaCfGgKkMNnqsTtVvXxYy')

# Local commands a pipeline may feed ssh output into. Anything else (bash, sh,
# python, xargs, tee, ...) can execute or write locally, so it is not auto-allowed.
PIPE_FILTERS = {
    'grep', 'egrep', 'fgrep', 'rg', 'awk', 'gawk', 'sed', 'head', 'tail',
    'sort', 'uniq', 'wc', 'cut', 'tr', 'cat', 'less', 'more', 'jq', 'column',
    'nl', 'tac', 'fold', 'fmt', 'paste', 'strings', 'hexdump', 'xxd', 'od',
}

# ssh -o options whose value the LOCAL client executes, or that pull in a
# config file / matching block which can set those.
LOCAL_EXEC_OPTIONS = re.compile(
    r'^\s*(ProxyCommand|LocalCommand|PermitLocalCommand|KnownHostsCommand|Include|Match)\b',
    re.IGNORECASE,
)


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


def has_local_exec_ssh_option(tokens):
    """True if ssh's own options (before the destination) can run a LOCAL command.

    -o ProxyCommand=... / -oProxyCommand=... (and the other LOCAL_EXEC_OPTIONS)
    are executed by the local ssh client; -F loads an arbitrary config file
    that can set any of them.
    """
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == '--' or not token.startswith('-') or token == '-':
            return False
        flag_str = token[1:]
        if flag_str[0] == 'F':
            return True
        if flag_str[0] == 'o':
            value = flag_str[1:]
            if not value:
                i += 1
                value = tokens[i] if i < len(tokens) else ''
            if LOCAL_EXEC_OPTIONS.match(value):
                return True
            i += 1
            continue
        if len(flag_str) == 1 and flag_str in SSH_FLAGS_WITH_ARG:
            i += 2  # skip the flag's separate value token
            continue
        i += 1
    return False


def has_local_exec_copy_option(tokens):
    """True if scp/rsync options name a LOCAL program to run or a config to load.

    rsync -e / --rsh and scp -S choose the "remote shell" program, which runs
    locally; -o <LOCAL_EXEC_OPTIONS> and -F behave as for ssh. Options may
    appear after operands, so the whole token list is scanned.
    """
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == '--':
            return False
        if not token.startswith('-') or token == '-':
            i += 1
            continue
        if token.startswith('--'):
            if token.startswith('--rsh'):
                return True
            i += 1
            continue
        flag_str = token[1:]
        if 'e' in flag_str or flag_str[0] in 'SF':
            return True
        if flag_str[0] == 'o':
            value = flag_str[1:]
            if not value:
                i += 1
                value = tokens[i] if i < len(tokens) else ''
            if LOCAL_EXEC_OPTIONS.match(value):
                return True
        i += 1
    return False


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


def split_pipeline(command):
    """Split a command on unquoted `|` into pipeline segments.

    Returns None if the command contains any other unquoted shell operator,
    because each of those lets something run or be written LOCALLY alongside
    the ssh invocation:
      ; & && || newline   -> a second local command
      $( ) and backticks  -> a local command substitution (also inside "...")
      > >> <              -> a local file is created/overwritten/read
    Operators inside single quotes (or non-expanding parts of double quotes)
    are part of the remote command and are left alone.
    """
    segments = []
    current = []
    in_single = False
    in_double = False
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        nxt = command[i + 1] if i + 1 < n else ''
        if in_single:
            if ch == "'":
                in_single = False
            current.append(ch)
        elif in_double:
            if ch == '\\':
                current.append(ch)
                if nxt:
                    current.append(nxt)
                    i += 1
            elif ch == '"':
                in_double = False
                current.append(ch)
            elif ch == '`' or (ch == '$' and nxt == '('):
                return None  # command substitution expands inside double quotes
            else:
                current.append(ch)
        else:
            if ch == "'":
                in_single = True
                current.append(ch)
            elif ch == '"':
                in_double = True
                current.append(ch)
            elif ch == '\\':
                current.append(ch)
                if nxt:
                    current.append(nxt)
                    i += 1
            elif ch == '|':
                if nxt == '|':
                    return None
                segments.append(''.join(current))
                current = []
            elif ch in ';&\n`<>':
                return None
            elif ch == '$' and nxt == '(':
                return None
            else:
                current.append(ch)
        i += 1
    segments.append(''.join(current))
    return segments


def has_shell_operators(command):
    """True if the command chains, substitutes or redirects outside quotes."""
    return split_pipeline(command) is None


def is_readonly_filter(segment):
    """True if a pipeline segment is a known read-only local filter."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    if not tokens:
        return False
    cmd = tokens[0].rsplit('/', 1)[-1]
    if cmd not in PIPE_FILTERS:
        return False
    if cmd == 'sed' and any(
        t == '--in-place' or (t.startswith('-i') and not t.startswith('--'))
        for t in tokens[1:]
    ):
        return False  # sed -i edits a local file
    return True


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


def allowed_reason(command, config):
    """Return a short reason string if the command should be auto-allowed, else None.

    Only auto-allows a single ssh/scp/rsync invocation, optionally piped into
    read-only local filters. See split_pipeline() for what disqualifies a
    command.
    """
    if not command:
        return None

    segments = split_pipeline(command)
    if segments is None:
        return None

    # Every downstream pipeline stage must be a harmless local filter.
    for segment in segments[1:]:
        if not is_readonly_filter(segment):
            return None

    try:
        tokens = shlex.split(segments[0].strip())
    except ValueError:
        return None

    tokens = strip_privilege_prefixes(tokens)
    if not tokens:
        return None

    cmd = tokens[0]
    args = tokens[1:]

    if cmd == 'ssh':
        if has_local_exec_ssh_option(args):
            return None

        result = parse_ssh_command(args)
        if result is None:
            return None

        user, host, remote_cmd = result
        entry = find_allowed_host(config, host, user)
        if entry is None:
            return None

        # Check if this command requires root-level access:
        # either logging in as root, or sudo anywhere in the remote command.
        remote_str = ' '.join(remote_cmd)
        uses_sudo = bool(re.search(r'\bsudo\b', remote_str))
        needs_root = user == 'root' or uses_sudo
        if needs_root and not entry.get('permit-root-access', False):
            return None

        target = f'{user}@{host}' if user else host
        return f'hook-allow-ssh: ssh {target} is listed in {CONFIG_DISPLAY}'

    elif cmd in ('scp', 'rsync'):
        if has_local_exec_copy_option(args):
            return None

        targets = parse_scp_rsync_targets(args)
        if not targets:
            return None

        names = []
        for user, host, path in targets:
            entry = find_allowed_host(config, host, user)
            if entry is None:
                return None
            if user == 'root' and not entry.get('permit-root-access', False):
                return None
            if not is_tmp_path(path):
                return None
            names.append(f'{user}@{host}' if user else host)

        return (f'hook-allow-ssh: {cmd} to {", ".join(sorted(set(names)))} '
                f'(tmp paths only) is listed in {CONFIG_DISPLAY}')

    return None


def check_command(command, config):
    """True if the command should be auto-allowed, False otherwise."""
    return allowed_reason(command, config) is not None


def make_allow(reason):
    """Return a permission-granting response.

    For "allow", permissionDecisionReason is shown to the user (not the model),
    which is what we want: it explains why no permission prompt appeared.
    """
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        },
    })


def make_pass():
    """Return an empty response (no opinion — pass through to normal prompting)."""
    return json.dumps({})


def main():
    input_data = json.load(sys.stdin)

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

    reason = allowed_reason(command, config)
    if reason:
        print(make_allow(reason))
    else:
        print(make_pass())


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Fail open (fall back to normal prompting), but visibly: exit 1 is a
        # non-blocking hook error whose stderr Claude Code shows to the user.
        print(f"{os.path.basename(__file__)}: hook failed, falling back to prompting:",
              file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
