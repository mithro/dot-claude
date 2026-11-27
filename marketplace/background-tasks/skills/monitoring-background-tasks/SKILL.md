---
name: monitoring-background-tasks
description: Use when starting, waiting on, checking or reporting on background work in Claude Code - Bash run_in_background shells, Monitors, sub-agents, scheduled/cron check-ins, long-running jobs, CI runs - and when reading or driving a Claude Code TUI through tmux (capture-pane, send-keys), your own pane or another session's. Trigger on "is it still running", "N background tasks", "give status updates every X minutes", "check on the sub-agents", "set up a regular check", "talk to the claude session in tmux window Y", "/compact the other sessions", stuck or accumulating background tasks, wait loops, pgrep, sleep loops, or before writing "all healthy" about anything you did not just inspect.
---

# Monitoring background tasks

## Overview

Background work fails quietly: a wait loop that can never exit, a job detached from the
process tree, a monitor that only fires on success. A check that looks only at what you
expect to see reports "all healthy" while broken tasks pile up.

**Core principle: account for every process and every task by hand, against two independent
views (the process tree and the UI), and never let a script or a filter make the judgement.**

Scripts are in `scripts/` beside this file; run each with `uv run --no-project <script>`.
Every one has `--help`. They capture and flag; you judge.

## Starting background work so it can finish

| Do | Never |
|---|---|
| `run_in_background` and let the harness notify you on exit | `while pgrep -f "<cmd>"; do sleep; done` — the pattern is in the loop's own command line, so `pgrep` always matches and the loop never exits |
| Send all output to a log file (`cmd >> run.log 2>&1`), then read the log | `cmd \| grep …` / `\| tail` on the live output: it discards the progress and error lines and leaves a monitor nothing to read |
| A wait that exits on success **or** failure **or** deadline: marker file OR job PID gone (`kill -0`) OR `timeout` | `until [ -f done ]; do sleep; done` — no exit when the job dies; a new one gets stacked on every tool timeout |
| A Monitor whose filter covers every terminal state (success, failure, cancel, timeout) | A monitor that matches only the success line. Silence is not success |
| `gh run watch`, or a poll for progress with a stall limit | A fixed timeout on work whose duration you cannot predict: poll for change, give up only after no progress |
| Keep stderr | `2>/dev/null` |

A wait that can always end, run with `run_in_background` and re-armed while the job lives
(the `timeout` is the reporting cadence, so each expiry is your cue to report):

```bash
timeout 300 bash -c 'p=$(cat tmp/job.pid); until [ -f tmp/job.done ] || ! kill -0 "$p"; do sleep 15; done'; \
  if [ -f tmp/job.done ]; then echo DONE; elif kill -0 "$(cat tmp/job.pid)"; then echo STILL-RUNNING; else echo DIED; fi; tail -n 20 tmp/job.log
```

Say the same in every sub-agent brief: how to wait (as above), log to a file, never search
the whole filesystem, and leave no background command running when reporting back.

## Waiting and reporting

- **Wait and report automatically.** Never ask "want me to wait?". Launch, state the expected
  duration, arm one notifier, then report when it fires.
- **Do not poke.** With a notifier armed, do not re-read a quiet log every few seconds. Look
  mid-flight only when a notification fires, the expected duration is clearly exceeded, or
  the person asks. Slow is not stuck: give graceful shutdowns and seek-bound jobs their time
  before escalating, and never cancel or SIGKILL out of impatience.
- **Do not go silent.** Report progress on a cadence, each time with remaining time **and**
  finish clock-time. A cadence the person states wins; otherwise use the tiers in
  `references/reporting-cadence.md`. Before every status report, check every background
  shell and sub-agent you have open, and say which are healthy.
- **Recurring checks follow the work.** Create the check-in (cron/scheduled) the moment
  background work starts or resumes; delete it when a check finds nothing running. A stale
  status display is a defect; so is a check-in left running over nothing.
- **A coordinator stays responsive.** If other sessions depend on you, nothing over about
  5 seconds runs in your foreground.

## The health check

1. `bgcheck.py --dir <project dir> --log '<log glob>'` — the whole descendant tree of this
   session's `claude` process, unfiltered, plus processes detached from it (reparented
   `nohup`/`setsid` jobs are invisible to the tree and are exactly what wait loops wait on).
2. **Read every line.** No `grep -v`, no allow-list, no "skip the shell wrappers": the
   wrappers are where the wait loops live. For each `LOOP`, state its exit condition and
   whether that can still become true. `IDLE` is a question to answer, not a verdict; a
   parent waiting on a busy child is fine.
3. `uitasks.py` — captures the TUI's Background dialog and the sub-agent panel from your
   own pane. Then compare its saved raw screens with its JSON by eye, and read its diff
   against the last run.
4. **Reconcile.** Every background shell, agent, scheduled job and monitor you know of must
   appear in the UI (footer count, agent panel, dialog rows), and everything the UI shows
   must be one you know of. What the count covers differs between Claude Code versions
   (`references/tmux-own-ui.md`). A sub-agent's current foreground tool call looks the same
   in `ps` but is not a background task; MCP servers are children of `claude` too. Explain
   every difference; never round it away.
5. **Report each task**: what it is, whether it is working, the evidence. Stop leftovers of
   finished work: duplicate waiters, expired monitors, tunnels, claims on shared hardware.
6. **Before killing anything**, write down its exit condition and why that can no longer
   become true. A `LOOP` or `NO-EXIT` flag is a pattern match and is not that reason. Kill
   only what this session or its own sub-agents started, never another session's processes
   and never a job doing real work, and say what you killed.

## tmux

Your pane is `$TMUX_PANE`. Reading is always safe: `tmux capture-pane -p -t "$TMUX_PANE"`
(add `-e` for colour, `-S -80` for scrollback). Sending keys is not.

**Before any key goes to any Claude Code pane:**

1. Capture **with colour**. The input box must be on screen and empty. Grey/dim text after
   `❯` is the UI's suggestion; default-colour text is the person's typing — if it is there,
   send nothing and never clear it. The pane must not be in copy mode
   (`tmux display-message -p -t PANE '#{pane_in_mode}'` prints `0`): a capture looks normal
   while the person is scrolled back, but keys would go to copy mode. The footer must not
   read "enter to view tasks": focus is then on the task footer, and Enter opens the
   Background dialog instead of submitting.
2. Send one key, then confirm on a fresh capture that the screen shows the state that key
   should produce before the next.
3. `Escape` only while a dialog is visibly open: anywhere else it interrupts the running turn.
   Never `x` in the Background dialog (it stops the task). Never `Ctrl-C` to get attention.
4. Type text and `Enter` as separate steps. Before `Enter`, the box must hold exactly what
   you typed and nothing else: if the person typed at the same moment, `Enter` would submit
   their words with yours. After `Enter`, confirm the submit happened. A slash command sent
   without that check is the usual reason "`/compact` never ran".

Read UI state only from where the UI draws it: the input box between the last two rule
lines, the footer below it, a dialog below the last rule line. The transcript above quotes
the same words ("↓ to manage", "Background", "esc to interrupt").

- Driving your own task dialog, key by key: `references/tmux-own-ui.md` (`uitasks.py` does it).
- Reading, messaging, compacting and restarting **other** sessions, locally or over ssh:
  `references/tmux-other-sessions.md` (`pane_send.py`, `pane_compact.py`).
  Both scripts apply the four rules above. If the pane is not safe to type into they type
  nothing and exit 2: `pane_send.py` at once unless given `--wait SECS`, `pane_compact.py`
  after `--wait-idle` (default 600 s). If the box changes under them after typing, they
  withhold `Enter` and leave the text there (`pane_send.py` exit 4, `pane_compact.py`
  exit 3). Either way tell the person; do not clear the box.

When telling the person about another session, name it as host + tmux `session:window` +
window title. A friendly session name or a bare PR number is not somewhere they can switch to.

## Red flags

| Thought | Reality |
|---|---|
| "It's sleeping, so it's idle by design and will end on its own" | Read the exit condition. Sleeping is not healthy. |
| "I'll filter the noise out of `ps` first" | The filter hides the processes you are meant to judge. |
| "My task list says 3, close enough to the UI's 4" | The mismatch is the finding. |
| "The script said self-check ok" | Look at its raw screens. A script that captured the wrong screen also passes. |
| "Empty log after 30 s, something is wrong" | State the expected duration and wait for the notifier. |
| "Nothing has changed, I'll skip this report" | The cadence is the contract. Report, with an ETA. |
| "Text in the box is probably a suggestion" | Check the colour. If unsure, send nothing. |
| "I typed `/compact`, so it compacted" | Require the "Compacting" then "Compacted" markers. |
