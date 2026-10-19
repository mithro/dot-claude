# dot-claude

Personal [Claude Code](https://claude.com/claude-code) plugin marketplace.

## Setup

```bash
claude plugin marketplace add mithro/dot-claude
```

Then enable plugins per-machine:

```bash
claude plugin enable agent-debugger@mithro-personal
claude plugin enable hook-block-tmp-creation@mithro-personal
claude plugin enable my-conventions@mithro-personal
# etc.
```

### Keeping Claude Code off `/tmp`

The hook and conventions only steer the model. Claude Code itself puts its
per-session temp tree — including the scratchpad the system prompt tells the
model to use — under `$TMPDIR/claude-<uid>/`, and the Bash tool does not set
`$TMPDIR` for the commands it runs. On machines where `/tmp` is a RAM-backed
tmpfs, move both on disk in `~/.claude/settings.json`:

```json
"env": {
  "CLAUDE_CODE_TMPDIR": "/home/tim/.claude-tmp",
  "TMPDIR": "/home/tim/.claude-tmp"
}
```

Keep `<dir>/claude-<uid>` within 44 bytes: longer paths overflow the AF_UNIX
socket limit and child processes silently fall back to `/tmp`. Nothing clears
this directory on reboot, so add your own retention (e.g. systemd-tmpfiles).

## Plugins

### Agents (19)

Specialized agents for various development tasks:

| Plugin | Description |
|--------|-------------|
| `agent-accessibility-tester` | WCAG 2.1 compliance, semantic HTML, ARIA, keyboard nav |
| `agent-api-designer` | REST API design, DRF, OpenAPI, versioning |
| `agent-backend-architect` | Scalable API design, microservices, distributed systems |
| `agent-celery-expert` | Async task debugging, retry strategies, queue management |
| `agent-code-reviewer` | Code quality, security vulnerabilities, best practices |
| `agent-data-scientist` | SQL optimization, Django ORM, data visualization, Pandas |
| `agent-debugger` | Root cause analysis, systematic debugging, profiling |
| `agent-deployment-engineer` | Production deployment, zero-downtime, WSGI/ASGI |
| `agent-devops-engineer` | CI/CD, Docker, GitHub Actions, infrastructure as code |
| `agent-django-developer` | Django 5.2+, REST APIs, async views, Celery |
| `agent-documentation-writer` | API docs, docstrings, architecture docs |
| `agent-error-detective` | Error patterns, stack traces, Sentry integration |
| `agent-performance-engineer` | Profiling, caching, async performance, optimization |
| `agent-postgres-pro` | PostgreSQL 17, JSONB, full-text search, query tuning |
| `agent-python-pro` | Modern Python 3.11+, type safety, async programming |
| `agent-security-auditor` | OWASP Top 10, dependency scanning, security review |
| `agent-solution-researcher` | Multi-approach evaluation, trade-off analysis |
| `agent-sre-engineer` | Monitoring, observability, incident response, SLOs |
| `agent-test-specialist` | Django/pytest, browser testing, test coverage |

### Hooks (7)

Enforcement hooks for SSH, git, and command safety:

| Plugin | Description |
|--------|-------------|
| `hook-allow-ssh` | Auto-allows SSH/scp/rsync to configured hosts (eliminates permission prompts) |
| `hook-block-tmp-creation` | Blocks file creation in `/tmp/`, incl. indirect use (`VAR=/tmp/…`, `--out /tmp/…`, `-v /tmp/…:`, `cd /tmp`) (use project-local `tmp/`) |
| `hook-block-stderr-to-null` | Blocks `2>/dev/null` (keep diagnostic output visible) |
| `hook-block-ssh-hash-hostnames` | Blocks SSH `-H` flag and `HashKnownHosts` (keep known_hosts readable) |
| `hook-block-ssh-unsafe-options` | Blocks `StrictHostKeyChecking=no` and `UserKnownHostsFile=/dev/null` |
| `hook-block-inline-scripts` | Blocks `python -c` and heredocs (write to a file first) |
| `hook-safe-force-push` | Blocks bare `git push --force` (use `git safe-force-push <branch>`) |

### Productivity (3)

| Plugin | Description |
|--------|-------------|
| `my-conventions` | Personal coding conventions: Python/uv, ISO dates, small commits, Apache 2.0, etc. |
| `github-repo-setup` | GitHub repository configuration skill and tag ruleset script |
| `google-sheets` | Google Sheets layout skill (`creating-google-sheets`) and `sheetcheck.py` column-fit / lint tool |

## Structure

```
dot-claude/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog (28 plugins)
├── marketplace/
│   ├── agent-*/                  # 19 agent plugins
│   ├── hook-*/                   # 7 hook plugins
│   ├── my-conventions/           # Coding conventions (SessionStart hook)
│   └── github-repo-setup/       # GitHub config skill + scripts
├── settings.json                 # Repo-level permissions
├── CLAUDE.md                     # Repo description
├── GitHub.md                     # Reference: GitHub setup commands
└── LICENSE                       # Apache 2.0
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.

## Author

Tim 'mithro' Ansell
