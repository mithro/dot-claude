## About this repo

This is a personal Claude Code plugin marketplace (`mithro-personal`).

### Setup

```
claude plugin marketplace add mithro/dot-claude
```

### Structure

- `.claude-plugin/marketplace.json` — Marketplace catalog
- `marketplace/` — Plugin source directories
- `settings.json` — Permission allow rules and machine-specific config
- `GitHub.md` — Reference: GitHub repository setup commands (also available as `github-setup` skill)

### Plugins

- `agent-*` — 21 specialized agents (code-reviewer, debugger, django-developer, etc.)
- `hook-*` — 9 hooks (allow-ssh, block /tmp, stderr, SSH hash, SSH unsafe options, force-push, inline scripts, gitconfig safe.directory, megacommits)
- `my-conventions` — Universal coding conventions (Python/uv, dates, commits, etc.)
- `github-repo-setup` — GitHub repository configuration tools and skills
- `google-sheets` — Google Sheets layout conventions skill + `sheetcheck.py` (column fit from data, lint)

### Hooks: conventions

- Every hook has a `hooks/test_*.py`; run them all with `uv run run_hook_tests.py`.
- A deny must put its explanation in `hookSpecificOutput.permissionDecisionReason` — that is the only field Claude Code shows to the model. `systemMessage` is rendered to the user only; the model never sees it.
- Fail open *visibly*: on a hook bug, print a traceback to stderr and exit 1 (non-blocking error, shown to the user). Never exit 0 with `{}` on an exception — that hides the bug.
