# dot-claude

Personal [Claude Code](https://claude.com/claude-code) plugin marketplace.

## Setup

```bash
claude plugin marketplace add github:mithro/dot-claude
```

Then enable plugins per-machine:

```bash
claude plugin enable agent-debugger@mithro-personal
claude plugin enable hook-block-tmp-creation@mithro-personal
claude plugin enable my-conventions@mithro-personal
# etc.
```

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

### Hooks (4)

Enforcement hooks that deny dangerous operations:

| Plugin | Description |
|--------|-------------|
| `hook-block-tmp-creation` | Blocks file creation in `/tmp/` (use project-local `tmp/`) |
| `hook-block-stderr-to-null` | Blocks `2>/dev/null` (keep diagnostic output visible) |
| `hook-block-ssh-hash-hostnames` | Blocks SSH `-H` flag and `HashKnownHosts` (keep known_hosts readable) |
| `hook-safe-force-push` | Blocks bare `git push --force` (use `git safe-force-push <branch>`) |

### Productivity (2)

| Plugin | Description |
|--------|-------------|
| `my-conventions` | Personal coding conventions: Python/uv, ISO dates, small commits, Apache 2.0, etc. |
| `github-repo-setup` | GitHub repository configuration skill and tag ruleset script |

## Structure

```
dot-claude/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace catalog (25 plugins)
├── marketplace/
│   ├── agent-*/                  # 19 agent plugins
│   ├── hook-*/                   # 4 hook enforcement plugins
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
