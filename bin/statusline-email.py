#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Claude Code status line: user@host:cwd, then the logged-in claude.ai account.

Prints e.g. `tim@x1c-work:/home/tim/local me@mith.ro`. The working directory
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

import getpass
import hashlib
import json
import os
import pathlib
import socket
import sys

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
    return f"\033[38;5;{colour_for(email)}m{email}\033[0m"


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
    return os.getcwd()


def prompt_part(cwd: str) -> str:
    """user@host:cwd, coloured like the Debian bash prompt."""
    user = getpass.getuser()
    host = socket.gethostname().split(".")[0]
    return f"\033[01;32m{user}@{host}\033[00m:\033[01;34m{cwd}\033[00m"


def account_part() -> str:
    path = config_file()
    try:
        account = json.loads(path.read_text()).get("oauthAccount") or {}
    except (OSError, json.JSONDecodeError) as e:
        # Visible in the status line rather than a silent blank.
        return f"account unknown ({path}: {e.__class__.__name__})"

    email = account.get("emailAddress")
    return coloured(email) if email else "not logged in to claude.ai"


def main() -> int:
    # Always read stdin to the end so Claude Code never blocks writing to us.
    cwd = session_cwd(sys.stdin.read())
    print(f"{prompt_part(cwd)} {account_part()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
