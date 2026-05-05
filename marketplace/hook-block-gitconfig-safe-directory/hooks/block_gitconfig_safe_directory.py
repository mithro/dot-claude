#!/usr/bin/env python3
"""PreToolUse hook: block adding [safe]/safe.directory entries to gitconfigs.

`safe.directory` (CVE-2022-24765 mitigation) protects git from running hooks
out of repositories in directories owned by other users. Adding entries —
especially `safe.directory = /` or `safe.directory = *` — disables that
protection. The right fix for "dubious ownership" warnings is almost always
to fix file ownership, not to add a safe entry.

This hook blocks:
  - Bash:  `git config ... safe.directory ...` segments that don't include
           a removal/read flag (--unset, --unset-all, --remove-section,
           --get, --get-all, --get-regexp, --list, --edit, --show-*).
  - Edit:  Edits to a gitconfig file where the new_string introduces or
           grows the count of `[safe]`/`safe.directory` references.
  - Write: Writes to a gitconfig file whose content contains `[safe]` or
           `safe.directory`.

It allows:
  - Removing entries (`git config --unset safe.directory`,
    `--remove-section safe`).
  - Reading (`git config --get safe.directory`, `--list`).
  - Editing/Writing non-gitconfig files even if their content discusses
    `safe.directory` (so docs and code-review aren't false-positived).
  - Edits whose new_string has fewer occurrences than old_string (dedupe
    or removal).

Hooks fire on every matching tool call, so this script uses python3 (not
uv) for fast cold-start, and depends only on the stdlib.
"""

import json
import re
import sys


# A path is treated as a gitconfig if its basename is one of the canonical
# names. Matches both ~/.gitconfig (dotfile) and rcfiles/git/gitconfig (no dot),
# repo-local .git/config, the XDG location, and /etc/gitconfig.
GITCONFIG_PATH = re.compile(
    r"(?:^|/)(?:\.?gitconfig|\.git/config|\.config/git/config)$"
)

# gitconfig section header, e.g. `[safe]` or `[safe "name"]`.
SECTION_HEADER = re.compile(r'^\s*\[(\w+)(?:\s+"[^"]*")?\]', re.IGNORECASE)

# A bare `directory =` key (file-format), valid under [safe] section.
BARE_DIRECTORY_KEY = re.compile(r"^\s*directory\s*=", re.IGNORECASE)

# Dotted-form reference: `safe.directory` (used by `git config` CLI and
# `git config --list` output).
DOTTED_SAFE_DIRECTORY = re.compile(r"\bsafe\.directory\b", re.IGNORECASE)

# Shell separators for splitting a Bash command into segments. We treat each
# segment independently so that `git config --unset X && git config --add
# safe.directory Y` correctly blocks only the second segment.
SHELL_SEP = re.compile(r"\s*(?:&&|\|\||\||;|\n)\s*")

# A `git config` invocation. We allow optional git-level flags between
# `git` and `config` (e.g. `git -C /repo -c color.ui=never config ...`).
GIT_CONFIG = re.compile(
    r"\bgit\b(?:\s+-[A-Za-z]\S*(?:\s+\S+)?|\s+--[A-Za-z][\w-]*(?:[= ]\S+)?)*\s+config\b"
)

SAFE_DIRECTORY_REF = re.compile(r"\bsafe\.directory\b")

# Flags that make a `git config safe.directory ...` invocation safe (read or
# remove). `--edit` opens an editor, which is user-driven, so allow.
READ_OR_REMOVE = re.compile(
    r"--(?:unset|unset-all|remove-section|get|get-all|get-regexp"
    r"|list|edit|show-origin|show-scope)\b"
)


DENY_MESSAGE = """❌ **Adding [safe]/safe.directory to gitconfig is blocked**

You attempted to add a `[safe]` section or `safe.directory` entry to a
gitconfig file. **This is almost never the right fix.**

**Why blocked:** `safe.directory` (CVE-2022-24765 mitigation) prevents git
from running hooks out of repositories owned by other users. Adding
entries — especially `safe.directory = /` or `safe.directory = *` —
disables that protection. The "dubious ownership" warning means an
ownership/permission mismatch needs fixing, not bypassing.

**What to do instead:**
1. Inspect the actual mismatch:
   ```
   ls -la <repo>/.git
   id
   stat <repo>
   ```
2. Fix file ownership at the source:
   ```
   sudo chown -R "$USER:$USER" <repo>
   ```
3. If the repo lives on a filesystem mounted with non-matching uids
   (e.g. NTFS, SMB, NFS), remount it with appropriate uid/gid options
   rather than persisting a `safe.directory` entry.
4. If you legitimately need a one-shot bypass for a single command in a
   short-lived environment (CI runner, container, foreign checkout):
   ```
   git -c safe.directory=<exact-path> <command>
   ```
   This is per-invocation and scoped — never use `/` or `*`.

**Removal is not blocked.** To clean up existing entries:
```
git config --global --unset-all safe.directory
git config --global --remove-section safe
```
"""


def make_deny(message: str) -> str:
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
        },
        "systemMessage": message,
    })


def make_allow() -> str:
    return json.dumps({})


def is_gitconfig_path(path: str) -> bool:
    if not path:
        return False
    if path == "/etc/gitconfig":
        return True
    return bool(GITCONFIG_PATH.search(path))


def count_safe(content: str) -> int:
    """Count safe-related references in gitconfig-format content.

    Counts (section-aware):
      - `[safe]` section headers
      - bare `directory = ...` key lines that appear within a `[safe]` section
      - any `safe.directory` dotted-form reference (anywhere; appears in
        `git config --list` output and in some inline contexts)
    """
    if not content:
        return 0
    section = ""
    count = 0
    for line in content.splitlines():
        m = SECTION_HEADER.match(line)
        if m:
            section = m.group(1).lower()
            if section == "safe":
                count += 1
            continue
        if section == "safe" and BARE_DIRECTORY_KEY.match(line):
            count += 1
        if DOTTED_SAFE_DIRECTORY.search(line):
            count += 1
    return count


def has_safe_content(content: str) -> bool:
    return count_safe(content) > 0


def find_blocked_bash_segment(command: str) -> str | None:
    """Return the first command segment that adds/sets safe.directory, else None."""
    if not command:
        return None
    for segment in SHELL_SEP.split(command):
        if not GIT_CONFIG.search(segment):
            continue
        if not SAFE_DIRECTORY_REF.search(segment):
            continue
        if READ_OR_REMOVE.search(segment):
            continue
        return segment
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print(make_allow())
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool_name == "Bash":
        if find_blocked_bash_segment(tool_input.get("command", "")):
            print(make_deny(DENY_MESSAGE))
            return

    elif tool_name == "Write":
        path = tool_input.get("file_path", "")
        if is_gitconfig_path(path) and has_safe_content(tool_input.get("content", "") or ""):
            print(make_deny(DENY_MESSAGE))
            return

    elif tool_name == "Edit":
        path = tool_input.get("file_path", "")
        if is_gitconfig_path(path):
            old_count = count_safe(tool_input.get("old_string", ""))
            new_count = count_safe(tool_input.get("new_string", ""))
            if new_count > old_count:
                print(make_deny(DENY_MESSAGE))
                return

    print(make_allow())


if __name__ == "__main__":
    main()
