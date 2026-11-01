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
    and running sudo/su/doas/pkexec on the remote host, since all give
    full root access.

Auto-allows:
  - ssh [safe flags] [user@]host [command]
  - scp [safe flags] LOCAL... [user@]host:/tmp/path   (uploads to tmp dirs only)
  - rsync [safe flags] LOCAL... [user@]host:/tmp/path (uploads to tmp dirs only)
  - any of the above piped into read-only local filters (grep, head, jq...)

Security model: an auto-allow skips the permission prompt entirely, so this
hook is a WHITELIST. Anything it does not positively recognise falls through
to normal prompting (returns {}), including:
  - any unquoted shell operator other than `|` (`;` `&` `&&` `||` newline
    `$( )` backticks) and any redirection (`>` `>>` `<`): a second local
    command or a local file
  - `|` into anything but a fixed set of filters that cannot write or execute
    (so no awk/sed/sort/xargs/bash), named bare or as /usr/bin/x or /bin/x
  - ssh/scp flags outside a small known-harmless set (e.g. -F -E -I -S -J -W
    -L -R -D -M -X are refused) and `-o` names outside a known-harmless set
    (ProxyCommand, LocalCommand, PKCS11Provider, UserKnownHostsFile, HostName,
    ProxyJump... are refused)
  - rsync options with local side effects (--rsh/-e, --log-file, --*-batch,
    --remove-source-files, --daemon, --config, --server/--sender)
  - a leading VAR=value or `env` (PATH=, LD_PRELOAD=, SUDO_ASKPASS= change how
    the local binary runs); sudo/nice/nohup/command wrappers are accepted
  - -l / -o User disagreeing with user@host (ssh honours -l; refuse the
    ambiguity rather than check the wrong user against the config)
  - scp/rsync where the remote is not the single final operand (a download
    writes an arbitrary LOCAL path), or whose remote path escapes tmp via `..`
Operators inside the quoted remote command run on the remote host and are fine.

Output protocol: an allow carries permissionDecisionReason (shown to the user
in the transcript) naming the matched host, so it is clear why no prompt
appeared. If the hook itself fails it exits 1 with a traceback on stderr: a
non-blocking error that falls back to normal prompting but is visible, rather
than silently passing.
"""

import json
import os
import posixpath
import re
import shlex
import sys
import traceback

CONFIG_PATH = os.path.expanduser('~/.claude/ssh-allowed-hosts.json')
CONFIG_DISPLAY = '~/.claude/ssh-allowed-hosts.json'

# --- ssh client flags -------------------------------------------------------
# Known-harmless flags only. Anything else (-D -E -F -I -J -L -M -O -R -S -W
# -w -X -Y -f -g ...) means "no opinion": it binds/forwards local ports, loads
# a local config/library, writes a local file, runs a local program or talks
# to a host other than the destination.
SSH_SAFE_FLAGS_NO_ARG = set('46AaCGKkNnqsTtVvx')
SSH_SAFE_FLAGS_WITH_ARG = set('bBceilmopQ')

# scp flags (BSD getopt: options precede operands). Note scp -l is a bandwidth
# limit, not a user.
SCP_SAFE_FLAGS_NO_ARG = set('346ABCOpqRrTv')
SCP_SAFE_FLAGS_WITH_ARG = set('cilPo')

# `-o Name=value` names that have no local side effect beyond the connection
# itself. Compared case-insensitively. Notably absent: ProxyCommand,
# LocalCommand, PermitLocalCommand, KnownHostsCommand, Include, Match,
# PKCS11Provider, SecurityKeyProvider, XAuthLocation, UserKnownHostsFile,
# GlobalKnownHostsFile, ControlPath, ControlMaster, IdentityAgent,
# LocalForward, RemoteForward, DynamicForward, StreamLocalBindUnlink,
# HostName, HostKeyAlias, ProxyJump.
SAFE_SSH_OPTIONS = {name.lower() for name in (
    'AddKeysToAgent', 'BatchMode', 'CheckHostIP', 'Ciphers',
    'ClearAllForwardings', 'Compression', 'ConnectTimeout',
    'ConnectionAttempts', 'ExitOnForwardFailure', 'ForwardAgent',
    'GSSAPIAuthentication', 'HashKnownHosts', 'HostKeyAlgorithms',
    'IdentitiesOnly', 'IdentityFile', 'KbdInteractiveAuthentication',
    'KexAlgorithms', 'LogLevel', 'MACs', 'NumberOfPasswordPrompts',
    'PasswordAuthentication', 'Port', 'PreferredAuthentications',
    'PubkeyAcceptedAlgorithms', 'PubkeyAuthentication', 'RequestTTY',
    'SendEnv', 'ServerAliveCountMax', 'ServerAliveInterval', 'SetEnv',
    'StrictHostKeyChecking', 'TCPKeepAlive', 'UpdateHostKeys', 'User',
    'VerifyHostKeyDNS',
)}

# --- rsync options ----------------------------------------------------------
# rsync (popt) accepts options anywhere. Long options with a local side effect
# (prefix match, since several take =value or have -format variants):
RSYNC_UNSAFE_LONG_PREFIXES = (
    '--rsh', '--log-file', '--write-batch', '--only-write-batch',
    '--read-batch', '--remove-source-files', '--daemon', '--config',
    '--server', '--sender', '--files-from', '--dparam',
)
# Long options that take a separate argument when written without '='.
RSYNC_LONG_WITH_SEPARATE_ARG = {
    '--exclude', '--include', '--filter', '--exclude-from', '--include-from',
    '--max-size', '--min-size', '--timeout', '--bwlimit', '--chmod', '--chown',
    '--block-size', '--compress-level', '--temp-dir', '--backup-dir',
    '--suffix', '--partial-dir', '--out-format', '--log-format',
    '--compare-dest', '--copy-dest', '--link-dest', '--max-delete',
    '--modify-window', '--port', '--sockopts', '--address', '--contimeout',
    '--rsync-path', '--remote-option', '--usermap', '--groupmap', '--checksum-choice',
    '--info', '--debug', '--stderr', '--iconv', '--skip-compress',
}
# Short rsync options that consume the next token when written alone
# ('-e' is refused outright: it names a local program to run).
RSYNC_SHORT_WITH_ARG = set('BTfM')

# --- pipelines --------------------------------------------------------------
# Local commands a pipeline may feed ssh output into: programs that can
# neither execute anything nor write a file. awk, sed, sort, uniq, xxd, less,
# more, tee, xargs and every interpreter are deliberately absent.
PIPE_FILTERS = {
    'grep', 'egrep', 'fgrep', 'rg', 'head', 'tail', 'wc', 'cut', 'tr', 'cat',
    'jq', 'column', 'nl', 'tac', 'fold', 'fmt', 'strings', 'hexdump', 'od',
}
PIPE_FILTER_DIRS = ('/usr/bin/', '/bin/')

# Remote operand: [user@]host:path (not an absolute/relative local path, not a URL)
REMOTE_OPERAND = re.compile(r'^(?:([^@:]+)@)?([^@:/][^@:]*):(.*)$')

# Remote commands that escalate to root
ROOT_ESCALATION = re.compile(r'\b(sudo|su|doas|pkexec)\b')


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
    """Return the config entry for host/user, or None."""
    for entry in config:
        if not isinstance(entry, dict):
            continue
        if entry.get('host') != host:
            continue
        config_user = entry.get('user')
        if config_user is not None and config_user != user:
            continue
        return entry
    return None


def split_option(value):
    """Split an -o value into (name, value).

    ssh's readconf accepts `Name=value`, `Name value`, and tolerates a leading
    `=` or whitespace (`-o=ProxyCommand=x` sets ProxyCommand).
    """
    value = value.lstrip(' \t=')
    m = re.match(r'([^\s=]+)[\s=]*(.*)$', value, re.DOTALL)
    if not m:
        return '', ''
    return m.group(1), m.group(2).strip()


def walk_options(tokens, no_arg, with_arg):
    """Walk BSD-getopt style options (ssh/scp) up to the first operand.

    Returns (index_of_first_operand, user_from_options) or None if any flag is
    outside the safe sets, any -o name is outside SAFE_SSH_OPTIONS, or an
    argument is missing. Short flags may be clustered (`-tF cfg`, `-4oOpt=v`),
    so every character of a cluster is checked.
    """
    i = 0
    user_opt = None
    while i < len(tokens):
        token = tokens[i]
        if token == '--':
            i += 1
            break
        if not token.startswith('-') or token == '-':
            break
        flags = token[1:]
        j = 0
        while j < len(flags):
            ch = flags[j]
            if ch in no_arg:
                j += 1
                continue
            if ch in with_arg:
                value = flags[j + 1:]
                if not value:
                    i += 1
                    if i >= len(tokens):
                        return None
                    value = tokens[i]
                if ch == 'l' and with_arg is SSH_SAFE_FLAGS_WITH_ARG:
                    user_opt = value
                elif ch == 'o':
                    name, val = split_option(value)
                    if name.lower() not in SAFE_SSH_OPTIONS:
                        return None
                    if name.lower() == 'user':
                        user_opt = val
                break
            return None  # unknown or unsafe flag
        i += 1
    return i, user_opt


def resolve_user(user_at, user_opt):
    """Combine user@ and -l / -o User. ssh honours the option; refuse conflicts."""
    if user_opt is None:
        return user_at, True
    if user_at is not None and user_at != user_opt:
        return None, False
    return user_opt, True


def parse_ssh_command(tokens):
    """Parse ssh args into (user, host, remote_cmd_tokens), or None.

    None means: unsafe/unknown flag, no destination, or -l/-o User conflicts
    with user@host.
    """
    walked = walk_options(tokens, SSH_SAFE_FLAGS_NO_ARG, SSH_SAFE_FLAGS_WITH_ARG)
    if walked is None:
        return None
    i, user_opt = walked
    if i >= len(tokens):
        return None  # no host (e.g. ssh -V)

    host_token = tokens[i]
    remote_cmd = tokens[i + 1:]

    user_at = None
    host = host_token
    if '@' in host_token:
        user_at, host = host_token.split('@', 1)
    if not host or host.startswith('-'):
        return None

    user, ok = resolve_user(user_at, user_opt)
    if not ok:
        return None
    return (user, host, remote_cmd)


def split_remote_operand(token):
    """Return (user, host, path) if token is [user@]host:path, else None."""
    if '://' in token:
        return ('', token, '')  # rsync://... is remote too; never allowed
    m = REMOTE_OPERAND.match(token)
    if not m:
        return None
    return (m.group(1), m.group(2), m.group(3))


def parse_scp_operands(tokens):
    """scp: walk options, return (operands, user_from_options) or None."""
    walked = walk_options(tokens, SCP_SAFE_FLAGS_NO_ARG, SCP_SAFE_FLAGS_WITH_ARG)
    if walked is None:
        return None
    i, user_opt = walked
    return tokens[i:], user_opt


def parse_rsync_operands(tokens):
    """rsync: skip/validate options anywhere, return operands or None."""
    operands = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == '--':
            operands.extend(tokens[i + 1:])
            break
        if token.startswith('--'):
            name = token.split('=', 1)[0]
            if name.startswith(RSYNC_UNSAFE_LONG_PREFIXES):
                return None
            if name in RSYNC_LONG_WITH_SEPARATE_ARG and '=' not in token:
                i += 2
                continue
            i += 1
            continue
        if token.startswith('-') and token != '-':
            flags = token[1:]
            if 'e' in flags:
                return None  # -e: local remote-shell program
            if flags[-1] in RSYNC_SHORT_WITH_ARG:
                i += 2
                continue
            i += 1
            continue
        operands.append(token)
        i += 1
    return operands


def parse_scp_rsync_targets(tokens):
    """Remote targets ([user@]host:path) among scp/rsync operands.

    Kept for callers/tests that only want the remote operands; the direction
    check lives in copy_target().
    """
    targets = []
    for token in tokens:
        if token.startswith('-'):
            continue
        parsed = split_remote_operand(token)
        if parsed is not None and '://' not in token:
            targets.append(parsed)
    return targets


def copy_target(operands):
    """The single remote destination of an upload, or None.

    Only `LOCAL... [user@]host:path` is recognised: the last operand must be
    remote and every earlier one local. A remote source would write to an
    arbitrary LOCAL path.
    """
    if len(operands) < 2:
        return None
    for operand in operands[:-1]:
        if split_remote_operand(operand) is not None:
            return None
    target = split_remote_operand(operands[-1])
    if target is None or '://' in operands[-1]:
        return None
    return target


def is_tmp_path(path):
    """True if a remote path (after normalising `..`) is within a tmp directory.

    Allows /tmp/..., tmp/... (home-relative), /var/tmp/.... The empty path
    (host:) is the home directory and is NOT allowed.
    """
    if not path:
        return False
    norm = posixpath.normpath(path)
    if norm.startswith('..') or norm == '.':
        return False
    return (
        norm.startswith('/tmp/')
        or norm == '/tmp'
        or norm.startswith('tmp/')
        or norm == 'tmp'
        or norm.startswith('/var/tmp/')
        or norm == '/var/tmp'
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
    """True if a pipeline segment is a known filter that cannot write or execute.

    The program must be a bare name in PIPE_FILTERS or that name under
    /usr/bin or /bin, so `./grep` (a file Claude could have just written) is
    refused.
    """
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    if not tokens:
        return False
    prog = tokens[0]
    if '/' in prog:
        if not any(prog == d + name for d in PIPE_FILTER_DIRS for name in PIPE_FILTERS):
            return False
        prog = prog.rsplit('/', 1)[-1]
    return prog in PIPE_FILTERS


def strip_privilege_prefixes(tokens):
    """Strip sudo/nice/nohup/command wrappers.

    Returns None (refuse) for `env` or any leading VAR=value assignment:
    PATH=, LD_PRELOAD=, SUDO_ASKPASS=... change which local code runs.
    """
    # wrapper -> its flags that consume the next token
    wrappers = {
        'sudo': {'-u', '-g', '-C', '-D', '-R', '-T', '-U', '-h', '-p', '-r', '-t'},
        'nice': {'-n'},
        'nohup': set(),
        'command': set(),
    }
    while tokens:
        head = tokens[0]
        if head == 'env' or re.match(r'^[A-Za-z_]\w*=', head):
            return None
        if head not in wrappers:
            break
        tokens = tokens[1:]
        while tokens and tokens[0].startswith('-'):
            flag = tokens[0]
            tokens = tokens[1:]
            if flag in wrappers[head] and tokens:
                tokens = tokens[1:]
    return tokens


def allowed_reason(command, config):
    """Return a short reason string if the command should be auto-allowed, else None."""
    if not command:
        return None

    segments = split_pipeline(command)
    if segments is None:
        return None

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
        result = parse_ssh_command(args)
        if result is None:
            return None
        user, host, remote_cmd = result
        entry = find_allowed_host(config, host, user)
        if entry is None:
            return None

        needs_root = user == 'root' or bool(ROOT_ESCALATION.search(' '.join(remote_cmd)))
        if needs_root and not entry.get('permit-root-access', False):
            return None

        target = f'{user}@{host}' if user else host
        return f'hook-allow-ssh: ssh {target} is listed in {CONFIG_DISPLAY}'

    if cmd in ('scp', 'rsync'):
        user_opt = None
        if cmd == 'scp':
            parsed = parse_scp_operands(args)
            if parsed is None:
                return None
            operands, user_opt = parsed
        else:
            operands = parse_rsync_operands(args)
            if operands is None:
                return None

        target = copy_target(operands)
        if target is None:
            return None
        user_at, host, path = target
        user, ok = resolve_user(user_at, user_opt)
        if not ok:
            return None

        entry = find_allowed_host(config, host, user)
        if entry is None:
            return None
        if user == 'root' and not entry.get('permit-root-access', False):
            return None
        if not is_tmp_path(path):
            return None

        name = f'{user}@{host}' if user else host
        return (f'hook-allow-ssh: {cmd} upload to {name}:{path} '
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
