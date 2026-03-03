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

- `agent-*` — 19 specialized agents (code-reviewer, debugger, django-developer, etc.)
- `hook-*` — 6 enforcement hooks (block /tmp, stderr, SSH hash, SSH unsafe options, force-push, inline scripts)
- `my-conventions` — Universal coding conventions (Python/uv, dates, commits, etc.)
- `github-repo-setup` — GitHub repository configuration tools and skills
