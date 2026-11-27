#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Claude Code status line: show the email of the logged-in claude.ai account.

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


def main() -> int:
    # Drain the session JSON so Claude Code never blocks writing to us.
    sys.stdin.read()

    path = config_file()
    try:
        account = json.loads(path.read_text()).get("oauthAccount") or {}
    except (OSError, json.JSONDecodeError) as e:
        # Visible in the status line rather than a silent blank.
        print(f"account unknown ({path}: {e.__class__.__name__})")
        return 0

    email = account.get("emailAddress")
    print(coloured(email) if email else "not logged in to claude.ai")
    return 0


if __name__ == "__main__":
    sys.exit(main())
