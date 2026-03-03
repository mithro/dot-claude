#!/usr/bin/env python3
"""SessionStart hook: inject personal coding conventions as advisory rules.

Outputs JSON with additionalContext containing all advisory coding
conventions. These are soft rules (not enforced by hooks) that guide
Claude's behaviour.
"""

import json

CONVENTIONS = r"""## Personal Coding Conventions

These conventions apply to all projects unless overridden by project-specific rules.

### Python & Tooling
- You **really, really, suck** at writing bash/shell as you always get the escaping wrong. You thus **MUST** use python (which you get right more often) for anything which has more than two commands, loops, if statements or command substitutions.
- **ALWAYS** use `uv` for all Python commands by default. Use `uv run` to execute Python scripts and `uv pip` for package management. Never use plain `python`, `python3`, or `pip` commands - always prefix with `uv`.

### Date Formats
- **NEVER** use American-style date formats. This includes ANY format that puts month before day, whether numeric (MM/DD/YYYY, 11/29/2025) or written ("November 29, 2025", "November 29"). **ALWAYS** use either ISO 8601 format (YYYY-MM-DD) or day-first formats ("29 November 2025", "29 Nov 2025", DD/MM/YYYY). American date ordering is ambiguous and confusing to the rest of the world.

### Git & Commits
- **ALWAYS** make small, discrete commits as you work. Don't wait until the end to commit everything at once. Each logical unit of work (adding a file, fixing a bug, implementing a feature) should be its own commit. This creates a clean, understandable git history and makes it easier to review, revert, or cherry-pick changes.
- **NEVER** use `git push --force` or `git push --force-with-lease` directly. **ALWAYS** use the safe wrapper commands that require explicit branch names: `git safe-force-push <branch>` or `git safe-force-push-lease <branch>`.

### Licensing
- When selecting a license, choose Apache 2.0 license unless strong reasons otherwise. If you believe a different license would be more appropriate, ask the user first before selecting an alternative.

### Verification & Thoroughness
- **Never** take short cuts like reading only parts of files or making assumptions about the state of things. **Never** jump to conclusions, make sure to verify any assumption that you are making. **ALWAYS** carefully double check all your work. **Always** provide detailed proof for any claim you make, such as quotes directly from official sources (with verification that the quote actually exists on the source page), command output or test programs which verify your claims.

### Temporary Files
- **NEVER** create files in `/tmp/`. Use a project-local `tmp/` directory instead (e.g. `mkdir -p ./tmp`). **ALWAYS** clean up any tmp files when done.

### SSH
- **NEVER** use the `-H` flag with `ssh-keyscan`, `ssh-keygen`, or other SSH tools. The `-H` flag hashes hostnames and addresses, making `known_hosts` files unreadable. Also **never** set `HashKnownHosts` to `yes` in SSH config files — use `HashKnownHosts no` or omit it entirely.

### Stderr
- **NEVER** redirect stderr to `/dev/null` (i.e. `2>/dev/null`). Stderr output contains valuable diagnostic information that must always be visible.

### Git Worktrees
- When creating, managing, or cleaning up git worktrees, **ALWAYS** use the `superpowers:using-git-worktrees` skill first. This ensures proper directory selection, .gitignore verification, and safety checks.
- **NEVER delete worktrees outside standard locations**: Worktrees located outside of `.worktrees/` or `~/.config/superpowers/worktrees/` are **user-created workspaces** and must never be deleted or removed without explicit user permission.

### System PATH
- **`/usr/sbin` not in user PATH**: On most Linux systems, `/usr/sbin` is only in root's PATH, not regular users'. Tools like `bridge`, `iptables`, `nft`, `tc`, and other system administration utilities live there. When running these commands (e.g., over SSH as a non-root user), use `sudo` which includes `/usr/sbin` in its PATH.

### GitHub
- When creating or configuring new GitHub repositories, use the `github-setup` skill for standard repository settings and configuration commands."""


def main():
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": CONVENTIONS.strip(),
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
