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
"""

import json
import os
import pathlib
import sys


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

    print(account.get("emailAddress") or "not logged in to claude.ai")
    return 0


if __name__ == "__main__":
    sys.exit(main())
