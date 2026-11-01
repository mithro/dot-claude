#!/usr/bin/env python3
"""PreToolUse hook: block direct git force pushes.

Blocks every direct force push, wherever the flag sits in the command:
    git push --force [remote] [branch]
    git push [remote] [branch] --force
    git push --force-with-lease[=...] ...
    git push -f / -uf / -vf ...
    git -C repo push --force
    git push <remote> +<refspec>        (a leading + forces that refspec)

The safe wrappers, which require an explicit branch name, are allowed:
    git safe-force-push <branch>
    git safe-force-push-lease <branch>

The command is split into simple commands (quote-aware, at `&&` `||` `|` `;`
`&` and newlines) and each `git [global options] push ...` is examined on its
own, so `git safe-force-push x && git push --force` is still caught and
`git commit -m "never git push --force"` is not.

Output protocol: a deny carries the explanation in
hookSpecificOutput.permissionDecisionReason (the field Claude Code shows to the
model) and repeats it in systemMessage (shown to the user). If the hook itself
fails it exits 1 with a traceback on stderr: a non-blocking error that lets the
tool call proceed but is visible, rather than silently approving.
"""

import json
import shlex
import sys
import traceback
from pathlib import Path


DENY_MESSAGE = """❌ **Direct force-push blocked by hook**

You attempted a direct force push: `git push --force`, `--force-with-lease`,
`-f`, or a refspec with a leading `+` (e.g. `git push origin +main`, which
force-updates that ref).

**Use the safe wrapper commands instead:**
```bash
# Force push a specific branch
git safe-force-push <branch>
git safe-force-push <remote> <branch>

# Force push with lease for a specific branch
git safe-force-push-lease <branch>
git safe-force-push-lease <remote> <branch>
```

**Why:** bare `git push --force` can push ALL matching branches and overwrite
other people's work on shared branches. The safe wrappers require an explicit
branch name, so every force push is deliberate and scoped."""

# Tokens that end one simple command and start another.
COMMAND_SEPARATORS = {'&&', '||', '|', '|&', ';', ';;', '&', '(', ')'}

# Wrappers that may precede the real command.
WRAPPERS = {'sudo', 'env', 'nice', 'nohup', 'command', 'time'}

# git global options that consume the next token (git -C <dir> push ...).
GIT_GLOBAL_WITH_ARG = {
    '-C', '-c', '--git-dir', '--work-tree', '--namespace', '--super-prefix',
    '--config-env',
}

FORCE_LONG_OPTIONS = {'--force', '--force-with-lease'}
SAFE_WRAPPERS = {'safe-force-push', 'safe-force-push-lease'}


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


def split_simple_commands(command):
    """Split a shell command into simple commands (lists of tokens).

    Quote-aware via shlex; `(`/`)` and the usual control operators separate
    commands, and a token starting with a backtick starts a new one.
    """
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError:
        # Unbalanced quotes: the shell would reject it too.
        return []

    commands = []
    current = []
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


def git_subcommand(tokens):
    """Return (subcommand, args) if tokens are `[wrapper...] git [global opts] <sub> ...`."""
    i = 0
    while i < len(tokens) and (
        tokens[i] in WRAPPERS
        or ('=' in tokens[i] and not tokens[i].startswith('-'))
    ):
        i += 1
    if i >= len(tokens) or tokens[i].rsplit('/', 1)[-1] != 'git':
        return None
    i += 1
    while i < len(tokens) and tokens[i].startswith('-'):
        i += 2 if tokens[i] in GIT_GLOBAL_WITH_ARG else 1
    if i >= len(tokens):
        return None
    return tokens[i], tokens[i + 1:]


def push_args_force(args):
    """True if the arguments of `git push` force-update anything."""
    for tok in args:
        if tok in FORCE_LONG_OPTIONS or tok.startswith('--force-with-lease='):
            return True
        if tok.startswith('-') and not tok.startswith('--') and 'f' in tok[1:]:
            return True
        if tok.startswith('+'):
            return True
    return False


def is_force_push(command):
    for tokens in split_simple_commands(command):
        parsed = git_subcommand(tokens)
        if parsed is None:
            continue
        sub, args = parsed
        if sub in SAFE_WRAPPERS:
            continue
        if sub == 'push' and push_args_force(args):
            return True
    return False


def main():
    input_data = json.load(sys.stdin)

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = input_data.get("tool_input", {}).get("command", "")
    if is_force_push(command):
        deny(DENY_MESSAGE)
    else:
        allow()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open, but visibly: exit 1 is a non-blocking hook error whose
        # stderr Claude Code shows to the user. Exit 0 with `{}` would hide the bug.
        print(f"{Path(__file__).name}: hook failed, allowing the tool call:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
