## About this repo

This is a `~/.claude` configuration repo (symlinked from `~/github/mithro/dot-claude`). It contains global Claude Code settings, custom agents, and hook enforcement scripts that apply across all projects.

### Structure

- `settings.json` — Permissions, hooks, plugin preferences, and status line config
- `CLAUDE.md` — Global behavioural rules (this file)
- `GitHub.md` — Standard GitHub repository setup commands and settings
- `scripts/` — PreToolUse hook scripts that enforce rules with hard denials
- `agents/` — Custom specialized agents (code-reviewer, debugger, security-auditor, etc.)
- `docs/plans/` — Design documents and implementation plans

---

- You **really, really, suck** at writing bash/shell as you always get the escaping wrong. You thus **MUST** use python (which you get right more often) for anything which has more than two commands, loops, if statements or command subsitutions.
- **ALWAYS** use `uv` for all Python commands by default. Use `uv run` to execute Python scripts and `uv pip` for package management. Never use plain `python`, `python3`, or `pip` commands - always prefix with `uv`.
- **NEVER** create files in `/tmp/`. A PreToolUse hook enforces this and will **deny** any Write, Edit, or Bash command that creates files there. Instead, use a project-local `tmp/` directory (e.g. `mkdir -p ./tmp`). Make sure that you **ALWAYS** cleanup any tmp files. Every file you don't remove causes many cute puppies to die. Do you want to be responsible for killing cute puppies?
- **Never** take short cuts like reading only parts of files or making assumptions about the state of things. **Never** jump to conclusions, make sure to verify any assumption that you are making. **ALWAYS** carefully double check all your work. **Always** provide detailed proof for any claim you make, such as quotes directly from official sources (with verification that the quote actually exists on the source page), command output or test programs which verify your claims (but making sure they actually demonstrate your claim and are not failing for unrelated reasons).
- **NEVER** use `git push --force` or `git push --force-with-lease` directly. **ALWAYS** use the safe wrapper commands that require explicit branch names.
  - **DO** use: `git safe-force-push <branch>` or `git safe-force-push <remote> <branch>`
  - **DO** use: `git safe-force-push-lease <branch>` or `git safe-force-push-lease <remote> <branch>`
  - **DON'T** use: `git push --force` (blocked - pushes all branches!)
  - **DON'T** use: `git push --force <remote>` (blocked - pushes all matching branches!)
  - **DON'T** use: `git push --force-with-lease` (blocked - no branch specified!)
  - **DON'T** use: `git push --force-with-lease <remote>` (blocked - no branch specified!)
  - **DON'T** use: `git push -f` (blocked - short form is dangerous!)
- **ALWAYS** make small, discrete commits as you work. Don't wait until the end to commit everything at once. Each logical unit of work (adding a file, fixing a bug, implementing a feature) should be its own commit. This creates a clean, understandable git history and makes it easier to review, revert, or cherry-pick changes.
- When selecting a license, choose Apache 2.0 license unless strong reasons otherwise. If you believe a different license would be more appropriate, ask the user first before selecting an alternative.
- **NEVER** use American-style date formats. This includes ANY format that puts month before day, whether numeric (MM/DD/YYYY, 11/29/2025) or written ("November 29, 2025", "November 29"). **ALWAYS** use either ISO 8601 format (YYYY-MM-DD) or day-first formats ("29 November 2025", "29 Nov 2025", DD/MM/YYYY). American date ordering is ambiguous and confusing to the rest of the world.
- When creating or configuring new GitHub repositories, refer to `GitHub.md` in this directory for the standard repository settings and configuration commands to apply.
- **Git Worktrees**: When creating, managing, or cleaning up git worktrees, **ALWAYS** use the `superpowers:using-git-worktrees` skill first. This ensures proper directory selection, .gitignore verification, and safety checks.
- **NEVER** use the `-H` flag with `ssh-keyscan`, `ssh-keygen`, or other SSH tools. A PreToolUse hook enforces this and will **deny** the command. The `-H` flag hashes hostnames and addresses, making `known_hosts` files unreadable and unmanageable. We want proper hostnames, not hashed versions. Also **never** set `HashKnownHosts yes` in SSH config files — use `HashKnownHosts no` or omit it entirely.
- **NEVER** redirect stderr to `/dev/null` (i.e. `2>/dev/null`). Stderr output contains valuable diagnostic information — errors, warnings, and unexpected conditions — that must always be visible. Suppressing it hides problems and makes debugging harder.
- **`/usr/sbin` not in user PATH**: On most Linux systems, `/usr/sbin` is only in root's PATH, not regular users'. Tools like `bridge`, `iptables`, `nft`, `tc`, and other system administration utilities live there. When running these commands (e.g., over SSH as a non-root user), use `sudo` (e.g., `sudo bridge link show`) which includes `/usr/sbin` in its PATH. Without `sudo`, you'll get "command not found" even though the binary exists.
- **NEVER delete worktrees outside standard locations**: Worktrees located outside of `.worktrees/` or `~/.config/superpowers/worktrees/` are **user-created workspaces** and must never be deleted or removed without explicit user permission. These directories (e.g., `project-2`, `project-feature-branch`) represent intentional, long-lived workspaces that the user manages manually. Only worktrees within the standard skill-managed locations may be cleaned up as part of normal workflow.