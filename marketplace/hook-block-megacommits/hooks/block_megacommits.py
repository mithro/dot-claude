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
import traceback


DEFAULT_MAX_FILES = 15
DEFAULT_MAX_LINES = 400

OVERRIDE_TOKEN = "ALLOW_MEGACOMMIT=1"

# Detects a `git commit` invocation, allowing git's global options in between
# (`git -C /repo commit`, `git -c x=y commit`, `git --no-pager commit`). The
# negative lookahead prevents matching `git commit-tree` / `git commit-graph`
# (which are followed by `-` or a word char) while still matching `git commit`,
# `git commit -m`, `git commit --amend`.
COMMIT_RE = re.compile(
    r"\bgit(?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+commit(?![\w-])"
)

# git global options that consume the next token.
GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                       "--super-prefix", "--config-env"}

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
    """Emit a deny decision.

    permissionDecisionReason is what the model sees; systemMessage is for the user.
    """
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": message,
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
    """Inspect the command for the first `git commit`; return (all_mode, cd_dir, c_dir).

    all_mode: True when -a / --all is present (commits all tracked modified
              files, not just the staged ones), which changes how we measure.
    cd_dir:   directory from a leading `cd <dir> &&` so we measure the right
              repo; None when absent.
    c_dir:    directory from `git -C <dir> commit`; None when absent.

    Best-effort and quote-aware via shlex; returns (False, None, None) if the
    command cannot be tokenized.
    """
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        return (False, None, None)

    cd_dir = None
    if len(tokens) >= 2 and tokens[0] == "cd":
        cd_dir = tokens[1]

    control_ops = {"&&", "||", ";", "|", "&"}
    all_mode = False
    c_dir = None

    i = 0
    while i < len(tokens) - 1:
        if tokens[i] == "git":
            # Skip git's global options to find the subcommand.
            k = i + 1
            while k < len(tokens) and tokens[k].startswith("-"):
                if tokens[k] == "-C" and k + 1 < len(tokens):
                    c_dir = tokens[k + 1]
                k += 2 if tokens[k] in GIT_GLOBAL_WITH_ARG else 1
            if k >= len(tokens) or tokens[k] != "commit":
                i = k
                continue
            j = k + 1
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

    return (all_mode, cd_dir, c_dir)


def run_git(repo_dir, args):
    """Run a git subcommand in repo_dir; return CompletedProcess (or None).

    Up to three git calls per hook run must fit the 10 s hook timeout in
    hooks.json, hence 3 s each.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=3,
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
    input_data = json.load(sys.stdin)

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

    all_mode, cd_dir, c_dir = parse_commit_invocation(command)

    repo_dir = input_data.get("cwd") or os.getcwd()
    for sub_dir in (cd_dir, c_dir):
        if sub_dir:
            sub_dir = os.path.expanduser(sub_dir)
            repo_dir = sub_dir if os.path.isabs(sub_dir) else os.path.join(repo_dir, sub_dir)

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
    except Exception:
        # Fail open (never block a commit because of a hook bug), but visibly:
        # exit 1 is a non-blocking hook error whose stderr Claude Code shows to
        # the user. Exit 0 with `{}` would hide the bug.
        print(f"{os.path.basename(__file__)}: hook failed, allowing the commit:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
