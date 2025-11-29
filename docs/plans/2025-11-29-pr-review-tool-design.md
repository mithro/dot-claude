# PR Review Tool Design

**Date:** 2025-11-29
**Status:** Draft - needs evaluation during development

## Problem Statement

When AI assists with reviewing large PRs (50+ comments), it tends to:
- Get overwhelmed by the volume
- Start skimming and batching to "be efficient"
- Accumulate context until quality degrades
- Miss duplicates and make inconsistent decisions

## Goals

1. Process PR review comments one-by-one without AI fatigue
2. Prevent context overflow in the orchestrating AI
3. Enable duplicate detection across many comments
4. Track decisions and apply them consistently
5. Sync resolutions back to GitHub

## Solution Overview

A Python CLI tool + Claude Code slash command that:
- Downloads and decomposes PR comments into atomic items
- Uses fresh sub-agents for each evaluation (no fatigue)
- Keeps orchestrator deliberately ignorant of details (no overflow)
- Stores rich context as files sub-agents can read on-demand
- Tracks all decisions for duplicate detection and consistency

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Slash Command                            │
│              (Orchestrator - minimal context)               │
│                                                             │
│  ┌─────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ pr-review│───▶│ Evaluator   │───▶│ User        │        │
│  │ brief   │    │ Sub-agent   │    │ Decision    │        │
│  └─────────┘    └─────────────┘    └─────────────┘        │
│       │                                   │                 │
│       │              ┌─────────────┐      │                 │
│       │              │ Fixer       │◀─────┘                 │
│       │              │ Sub-agent   │  (if "fix it")        │
│       │              └─────────────┘                        │
│       │                     │                               │
│       ▼                     ▼                               │
│  ┌─────────┐          ┌─────────┐                          │
│  │ pr-review│         │ pr-review│                          │
│  │ decide  │          │ decide  │                          │
│  └─────────┘          │ fixed   │                          │
│                       └─────────┘                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │     .pr-review/         │
              │  ├── data/ (JSON)       │
              │  └── context/ (Markdown)│
              └─────────────────────────┘
```

### Key Principle: Orchestrator Ignorance

The orchestrator (main Claude session running the slash command) should **never see full details**. It only sees:
- Progress: "I042/52"
- Brief: "src/views.py:142 | Use async"
- Sub-agent conclusion: "Recommend FIX, high confidence"
- User decision

All detailed analysis happens in isolated sub-agents that:
- Start fresh (no accumulated fatigue)
- Get full context via files (not polluting orchestrator)
- Return only conclusions

## CLI Interface

```bash
# Initialize: download, decompose, detect project tooling
pr-review init <pr-url>

# Orchestrator commands (MINIMAL output)
pr-review brief              # "#I042/52 | C018 | file:line | one-liner"
pr-review status             # "47/52 items, 12/18 comments resolved"

# Context generation (writes to files, not stdout)
pr-review context evaluate   # Writes .pr-review/context/current-eval.md
pr-review context fix        # Writes .pr-review/context/current-fix.md

# Decision recording
pr-review decide <status> [--reason "..."] [--commit <sha>] [--of <item>]
# Statuses: fixed, ignored, obsolete, deferred, duplicate

# GitHub sync
pr-review sync               # Minimize/resolve comments on GitHub

# Issue management
pr-review link-issue <item> <issue-number>
```

## Data Model

### Directory Structure

```
.pr-review/
├── data/                           # Machine-readable (CLI only)
│   ├── state.json                  # Progress, current index
│   ├── project-config.json         # Detected tooling
│   ├── comments/
│   │   └── C001.json ... C018.json
│   └── items/
│       └── I001.json ... I052.json
│
└── context/                        # AI-readable (sub-agents)
    ├── index.md                    # Quick reference for scanning
    ├── pr-summary.md               # What this PR is about
    ├── project.md                  # Tooling commands
    ├── current-eval.md             # Generated for evaluator
    ├── current-fix.md              # Generated for fixer
    └── comments/
        ├── C001/
        │   ├── comment.md          # Original comment
        │   └── items/
        │       └── I001/
        │           ├── item.md     # The actionable item
        │           └── resolution.md  # Decision + reasoning
        └── C002/
            ├── comment.md
            └── items/
                ├── I002/
                │   ├── item.md
                │   └── resolution.md
                ├── I003/
                │   └── item.md     # No resolution = pending
                └── I004/
                    └── item.md
```

### Terminology

- **Comment**: Raw GitHub entity (review comment or PR comment)
- **Item**: Atomic actionable thing extracted from a comment
- One comment → 1 or more items (decomposition)
- Each item gets evaluated and decided independently
- Comment resolved on GitHub when ALL its items are resolved

### Index Structure

`context/index.md` provides:
- PR summary and progress
- Items grouped by category (async, error-handling, types, etc.)
- Enough detail for duplicate detection
- Keywords index for searching

Sub-agents scan the index, then read specific `resolution.md` files if they need more detail.

## GitHub Integration

### Operations

| Operation | Method |
|-----------|--------|
| Fetch PR metadata | `gh api repos/{owner}/{repo}/pulls/{pr}` |
| Fetch review comments | `gh api repos/{owner}/{repo}/pulls/{pr}/comments` |
| Fetch PR comments | `gh api repos/{owner}/{repo}/issues/{pr}/comments` |
| Minimize comment | `gh api graphql` (minimizeComment mutation) |
| Create issue | `gh issue create` |

### Status to Minimize Reason Mapping

| Our Status | GitHub Minimize Reason |
|------------|------------------------|
| FIXED | RESOLVED |
| IGNORED | OFF_TOPIC |
| OBSOLETE | OUTDATED |
| DEFERRED | RESOLVED |
| DUPLICATE | DUPLICATE |

## Prompt Templates

### Briefing (Quality Instructions)

All sub-agents receive:
- "Bet your life on it" quality standard
- Infinite time/resources mindset
- No skimming, no batching, no assumptions
- Verify everything, show your work
- Research improvements

### Evaluator Prompt

Receives:
- Briefing
- Current item details
- Code context
- Pointers to index.md and resolution files

Returns:
- Summary (2-3 sentences)
- Analysis (what was checked)
- Already fixed? (yes/no with evidence)
- Duplicate? (which item, why)
- Recommendation (FIXED/OBSOLETE/DUPLICATE/IGNORE/FIX/DEFER)
- Confidence (High/Medium/Low)
- Reasoning

### Fixer Prompt

Receives:
- Briefing
- Item details
- Recommendation from evaluator
- Project tooling commands

Returns:
- What changed
- Files modified
- Commit SHA
- Verification done

## Workflow

### Initialization

```
pr-review init <url>
├── Fetch PR metadata
├── Fetch all comments (review + PR)
├── Decompose general comments into items
├── Detect project tooling (or ask)
├── Generate initial context/ files
└── Report: "X comments, Y items to review"
```

### Main Loop

```
For each item (chronologically):
1. pr-review brief → orchestrator sees one line
2. pr-review context evaluate → writes file
3. Task(evaluator) → reads file, returns conclusion
4. Present to user with AskUserQuestion
5. User decides
6. If "fix":
   a. pr-review context fix → writes file
   b. Task(fixer) → makes changes, commits
   c. Verify commit exists
7. pr-review decide <status> → records, advances
8. Repeat
```

### Completion

```
pr-review sync
├── For each resolved comment:
│   ├── Add reply explaining resolution
│   └── Minimize with appropriate reason
└── Report summary
```

## Decision Statuses

| Status | Meaning | Action |
|--------|---------|--------|
| FIXED | Issue was addressed | Record commit, resolve on GitHub |
| IGNORED | Valid but won't fix | Record reason, minimize as OFF_TOPIC |
| OBSOLETE | No longer relevant | Record reason, minimize as OUTDATED |
| DEFERRED | Fix later | Create/link issue, minimize as RESOLVED |
| DUPLICATE | Same as previous item | Apply previous decision, minimize as DUPLICATE |

## Open Questions

Things to evaluate during development:

1. **Index detail level**: Is the category-grouped table enough for duplicate detection?
2. **Decomposition accuracy**: How well can AI split general comments into items?
3. **Project detection**: What tooling patterns should we detect?
4. **Sub-agent prompts**: Will evaluator/fixer prompts produce consistent results?
5. **Context file format**: Is the markdown structure optimal for sub-agents?
6. **Sync timing**: Should we sync after each comment or batch at end?

## Implementation Notes

- Use `uv` for all Python commands
- Use `gh` CLI for GitHub API (authenticated via user's gh auth)
- Store in project's `.pr-review/` directory (gitignored)
- Support resume: persist state, can stop and continue later
- Chronological processing order
