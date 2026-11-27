#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Claude Code status line: the logged-in claude.ai account, then user@host:cwd.

Prints e.g. `(me@mith.ro) tim@x1c-work:/home/tim/local`. The working directory
comes from the session JSON on stdin (workspace.current_dir, then cwd).

Claude Code pipes session JSON to a status line command on stdin, but that
JSON does not carry the account. The login is stored in ~/.claude.json (or
$CLAUDE_CONFIG_DIR/.claude.json) under "oauthAccount", so read it from there.
The file is re-read on every refresh, so a /login to another account shows up
at once.

Each account gets its own colour so a glance tells them apart. Known accounts
are pinned: hashing just three emails onto a colour wheel collides too easily
(claude@wafer.space and claude@mith.ro land 8 degrees apart). Any other
account is hashed onto FALLBACK_COLOURS, which shares no colour with the
pinned ones, so a new account can never pass for a known one.
"""

import hashlib
import json
import os
import pathlib
import pwd
import socket
import sys

# Shown in place of any part (account, user, host, directory) we cannot find.
UNKNOWN = "???"

# xterm-256 colour numbers.
PINNED_COLOURS = {
    "me@mith.ro": 42,  # green
    "claude@wafer.space": 39,  # blue
    "claude@mith.ro": 208,  # orange
}
FALLBACK_COLOURS = [141, 204, 220, 51, 170, 118]  # purple pink yellow cyan magenta lime


def colour_for(email: str) -> int:
    email = email.lower()
    if email in PINNED_COLOURS:
        return PINNED_COLOURS[email]
    # sha256, not hash(): Python randomises str hashes per process.
    digest = hashlib.sha256(email.encode()).digest()
    return FALLBACK_COLOURS[int.from_bytes(digest[:4], "big") % len(FALLBACK_COLOURS)]


def coloured(email: str) -> str:
    return f"\033[38;5;{colour_for(email)}m({email})\033[0m"


def config_file() -> pathlib.Path:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        return pathlib.Path(config_dir) / ".claude.json"
    return pathlib.Path.home() / ".claude.json"


def session_cwd(session_json: str) -> str:
    """The session's working directory, from the JSON Claude Code pipes in.

    Falls back to our own cwd (Claude Code starts us in the session's) when
    the JSON is missing, malformed or lacks the field.
    """
    try:
        session = json.loads(session_json)
    except json.JSONDecodeError:
        session = None
    if isinstance(session, dict):
        workspace = session.get("workspace")
        if isinstance(workspace, dict) and workspace.get("current_dir"):
            return workspace["current_dir"]
        if session.get("cwd"):
            return session["cwd"]
    try:
        return os.getcwd()
    except OSError:  # e.g. the directory was deleted under us
        return UNKNOWN


def current_user() -> str:
    """What `whoami` prints: the name of the effective uid, ignoring $USER."""
    try:
        return pwd.getpwuid(os.geteuid()).pw_name or UNKNOWN
    except KeyError:  # uid with no passwd entry
        return UNKNOWN


def short_hostname() -> str:
    """What `hostname -s` prints: the hostname up to the first dot."""
    try:
        return socket.gethostname().split(".")[0] or UNKNOWN
    except OSError:
        return UNKNOWN


def prompt_part(cwd: str) -> str:
    """user@host:cwd, coloured like the Debian bash prompt."""
    return (
        f"\033[01;32m{current_user()}@{short_hostname()}\033[00m"
        f":\033[01;34m{cwd}\033[00m"
    )


def account_part() -> str:
    try:
        account = json.loads(config_file().read_text()).get("oauthAccount") or {}
    except (OSError, json.JSONDecodeError, AttributeError):
        account = {}
    email = account.get("emailAddress")
    # An unknown account is uncoloured, so it cannot pass for a real one.
    return coloured(email) if email else f"({UNKNOWN})"


def main() -> int:
    # Always read stdin to the end so Claude Code never blocks writing to us.
    cwd = session_cwd(sys.stdin.read())
    print(f"{account_part()} {prompt_part(cwd)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
