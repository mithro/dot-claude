#!/usr/bin/env python3
"""PreToolUse hook: block megacommits, encourage small logical commits.

Intercepts `git commit` and measures what would actually be committed. If the
change is larger than the thresholds (too many files, or too many added lines),
the commit is blocked with guidance to split it into smaller, logical commits.

Why: small, focused commits produce a clean, reviewable history and make it
easy to review, revert, cherry-pick, and bisect. "Megacommits" bundle unrelated
changes together, are hard to review, and are painful to partially undo.

Escape hatch for legitimately large commits (vendored deps, generated code,
bulk renames, initial imports): prefix the command with ALLOW_MEGACOMMIT=1, e.g.
    ALLOW_MEGACOMMIT=1 git commit -m "vendor: import upstream library"

Thresholds are configurable via environment variables:
    MEGACOMMIT_MAX_FILES   (default 15)
    MEGACOMMIT_MAX_LINES   (default 400)   # added lines; lockfiles excluded

The hook FAILS OPEN: any error (not a repo, parse failure, git error) allows
the commit, so it never blocks legitimate work because of its own bugs.
"""

import json
import os
import re
import shlex
import subprocess
import sys


DEFAULT_MAX_FILES = 15
DEFAULT_MAX_LINES = 400

OVERRIDE_TOKEN = "ALLOW_MEGACOMMIT=1"

# Detects a `git commit` invocation. The negative lookahead prevents matching
# `git commit-tree` / `git commit-graph` (which are followed by `-` or a word
# char) while still matching `git commit`, `git commit -m`, `git commit --amend`.
COMMIT_RE = re.compile(r"\bgit\s+commit(?![\w-])")

# Short option letters that consume the rest of the cluster (or the next token)
# as their VALUE. Once one of these is seen in a `-xyz` cluster, remaining
# characters are a value, not flags — so we must stop scanning for `-a`.
VALUE_TAKING_SHORT_OPTS = frozenset("mcCFS")

# Filenames whose line churn is ignored (still counted as a changed file).
# These are generated or lock files that are legitimately large and would
# otherwise dominate the line count and cause false positives.
IGNORED_LINE_PATTERNS = [
    re.compile(p)
    for p in (
        r"(^|/)package-lock\.json$",
        r"(^|/)npm-shrinkwrap\.json$",
        r"(^|/)yarn\.lock$",
        r"(^|/)pnpm-lock\.yaml$",
        r"(^|/)uv\.lock$",
        r"(^|/)poetry\.lock$",
        r"(^|/)Pipfile\.lock$",
        r"(^|/)Cargo\.lock$",
        r"(^|/)Gemfile\.lock$",
        r"(^|/)composer\.lock$",
        r"(^|/)go\.sum$",
        r"(^|/)flake\.lock$",
        r"(^|/)[^/]+\.lock$",  # generic *.lock
        r"\.min\.js$",
        r"\.min\.css$",
        r"\.map$",  # source maps
    )
]


def allow():
    """Emit the allow decision (empty object) and exit."""
    print(json.dumps({}))


def deny(message):
    """Emit a deny decision with a user-facing message and exit."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                },
                "systemMessage": message,
            }
        )
    )


def int_env(name, default):
    """Read a non-negative int from the environment, falling back to default."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        return default
    return value if value >= 0 else default


def parse_commit_invocation(command):
    """Inspect the command for the first `git commit` and return (all_mode, cd_dir).

    all_mode: True when -a / --all is present (commits all tracked modified
              files, not just the staged ones), which changes how we measure.
    cd_dir:   directory from a leading `cd <dir> &&` so we measure the right
              repo; None when absent.

    Best-effort and quote-aware via shlex; returns (False, None) if the command
    cannot be tokenized.
    """
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        return (False, None)

    cd_dir = None
    if len(tokens) >= 2 and tokens[0] == "cd":
        cd_dir = tokens[1]

    control_ops = {"&&", "||", ";", "|", "&"}
    all_mode = False

    i = 0
    while i < len(tokens) - 1:
        if tokens[i] == "git" and tokens[i + 1] == "commit":
            j = i + 2
            while j < len(tokens) and tokens[j] not in control_ops:
                token = tokens[j]
                if token == "--":
                    break  # end of options; pathspecs follow
                if token == "--all":
                    all_mode = True
                elif token.startswith("-") and not token.startswith("--"):
                    for ch in token[1:]:
                        if ch == "a":
                            all_mode = True
                            break
                        if ch in VALUE_TAKING_SHORT_OPTS:
                            break  # rest of cluster is this option's value
                j += 1
            break
        i += 1

    return (all_mode, cd_dir)


def run_git(repo_dir, args):
    """Run a git subcommand in repo_dir; return CompletedProcess (or None)."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def resolve_git_dir(repo_dir):
    """Return the absolute path to the repo's .git dir, or None if not a repo."""
    result = run_git(repo_dir, ["rev-parse", "--git-dir"])
    if result is None or result.returncode != 0:
        return None
    git_dir = result.stdout.strip()
    if not git_dir:
        return None
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(repo_dir, git_dir)
    return git_dir


def operation_in_progress(git_dir):
    """True if a merge/cherry-pick/revert is in progress (legitimately large)."""
    return any(
        os.path.exists(os.path.join(git_dir, marker))
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD")
    )


def has_head(repo_dir):
    """True if the repo has at least one commit (HEAD resolves)."""
    result = run_git(repo_dir, ["rev-parse", "--verify", "--quiet", "HEAD"])
    return result is not None and result.returncode == 0


def line_count_ignored(path):
    """True if a path's line churn should be excluded (lock/generated files)."""
    return any(pattern.search(path) for pattern in IGNORED_LINE_PATTERNS)


def measure(repo_dir, all_mode):
    """Return (files_changed, added_lines) for what the commit would include.

    Staged changes use `git diff --cached`; with -a/--all we compare the whole
    working tree against HEAD (what `git commit -a` actually records). Binary
    files contribute no line count; lock/generated files are counted as files
    but their line churn is ignored.
    """
    diff_args = ["diff", "--numstat", "--no-color"]
    diff_args.append("HEAD" if all_mode else "--cached")

    result = run_git(repo_dir, diff_args)
    if result is None or result.returncode != 0:
        return None

    files_changed = 0
    added_lines = 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, _deleted, path = parts[0], parts[1], "\t".join(parts[2:])
        files_changed += 1
        if added == "-":  # binary file
            continue
        if line_count_ignored(path):
            continue
        try:
            added_lines += int(added)
        except ValueError:
            pass

    return (files_changed, added_lines)


def build_deny_message(files_changed, added_lines, max_files, max_lines):
    reasons = []
    if files_changed > max_files:
        reasons.append(f"**{files_changed} files** changed (limit {max_files})")
    if added_lines > max_lines:
        reasons.append(f"**{added_lines} added lines** (limit {max_lines})")
    reason_text = " and ".join(reasons)

    return f"""❌ **Megacommit blocked by hook**

This commit is too large: {reason_text}.

Large commits bundle unrelated changes together, are hard to review, and are
painful to revert or cherry-pick. Split this into smaller, logical commits —
one self-contained change each.

**How to split it up:**
```bash
git reset                 # unstage everything (keeps your changes)
git add -p                # stage one logical change interactively
git commit -m "..."       # commit it, then repeat for the next change
```

**If this commit is genuinely one logical unit** (vendored dependency,
generated code, bulk rename, initial import), override the hook:
```bash
ALLOW_MEGACOMMIT=1 git commit -m "..."
```

Thresholds are configurable via MEGACOMMIT_MAX_FILES / MEGACOMMIT_MAX_LINES."""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        allow()
        return

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        allow()
        return

    # Not a commit -> nothing to do.
    if not COMMIT_RE.search(command):
        allow()
        return

    # Explicit override.
    if OVERRIDE_TOKEN in command:
        allow()
        return

    all_mode, cd_dir = parse_commit_invocation(command)

    repo_dir = input_data.get("cwd") or os.getcwd()
    if cd_dir:
        repo_dir = cd_dir if os.path.isabs(cd_dir) else os.path.join(repo_dir, cd_dir)

    git_dir = resolve_git_dir(repo_dir)
    if git_dir is None:
        allow()  # not a git repo we can measure
        return

    # Merge/cherry-pick/revert commits are legitimately large.
    if operation_in_progress(git_dir):
        allow()
        return

    # Initial commit (project import) is legitimately large.
    if not has_head(repo_dir):
        allow()
        return

    measured = measure(repo_dir, all_mode)
    if measured is None:
        allow()  # could not measure -> don't block
        return

    files_changed, added_lines = measured
    max_files = int_env("MEGACOMMIT_MAX_FILES", DEFAULT_MAX_FILES)
    max_lines = int_env("MEGACOMMIT_MAX_LINES", DEFAULT_MAX_LINES)

    if files_changed > max_files or added_lines > max_lines:
        deny(build_deny_message(files_changed, added_lines, max_files, max_lines))
        return

    allow()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # fail open: never block a commit due to a hook bug
        allow()
