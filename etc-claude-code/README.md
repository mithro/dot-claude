# `/etc/claude-code`

Files installed into `/etc/claude-code/` by `rcfiles/setup.sh` (the `claude`
function). Claude Code on Linux reads `/etc/claude-code/managed-settings.json`
as *managed* (policy) settings: every `claude` process loads it, whatever
`--setting-sources` or the Agent SDK's `settingSources` option says, and it
overrides the user's `~/.claude/settings.json`.

## `managed-settings.json`

Holds only `cleanupPeriodDays`, which is already in `../settings.json`. The
copy here matters for `claude` processes that never read the user settings.

Claude Code deletes transcripts in `~/.claude/projects/` older than
`cleanupPeriodDays` (default 30) when it starts. A tool that runs `claude`
through the Agent SDK with `settingSources: []` never loads `settings.json`,
so its CLI sweeps at the default 30 days.

That happened in 2026. episodic-memory 1.0.15 bundled Agent SDK 0.1.77,
which came with its own Claude Code 2.0.77. Its summariser ran that copy
without user settings on every session start. Between July and October it
deleted every transcript older than 30 days on one laptop, although
`settings.json` said 1095. A test with a 40-day-old and a 10-day-old decoy
transcript reproduced it: the bundled CLI, run with `--setting-sources ""`,
deleted the 40-day one and kept the 10-day one.

episodic-memory 1.6.0 still passes `settingSources: []`. The managed file
keeps the retention period the same for every `claude` process.

`setup.sh` installs this file only if `/etc/claude-code/managed-settings.json`
is missing or already identical. If the installed file differs, it prints a
diff and leaves the file alone.
