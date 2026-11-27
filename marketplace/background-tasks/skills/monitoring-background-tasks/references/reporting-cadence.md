# Progress reporting cadence

A cadence the person states for the task wins ("every 45 minutes", "every 60 seconds").
A project's own instructions win next. Otherwise:

| Expected duration | Report at least every |
|---|---|
| under 10 minutes | 60 seconds |
| under 4 hours | 5 minutes |
| 4 hours or more | 15 minutes |

- Estimate the duration up front (pending bytes ÷ throughput, items ÷ rate) to pick the tier.
- Each iteration of a repeated job is its own task: a fast pass inside a long sequence still
  gets the fast cadence.
- Never drift coarser than the tier, and never skip a report because nothing changed.

## Every report carries

1. Progress as a number (count, bytes, percent), not an adjective.
2. **Remaining time and the finish clock-time**, recomputed each report from observed
   throughput: anchor a `(value, timestamp)` start point and extrapolate. A fixed anchor
   averages out noise. If an early estimate proves short, re-arm at the tighter tier.
3. The state of every other background shell, monitor and sub-agent you have open — checked,
   not remembered — and what was stopped as a leftover.
4. For long multi-session work: current priorities, what is consuming effort, what is being
   waited on, and what is next.

## Driving it

- Capture the job's full output to a log file and have a background Monitor read **the log**,
  never the live pipe.
- Prefer a time-capped waiter (wakes at the cadence **or** when the job ends) that you
  re-arm while the job continues, over a fire-once-at-completion waiter, for anything
  longer than one cadence interval.
- Keep at most one progress monitor per job. Stop duplicates and expired ones.
- Scheduled check-ins are session-only: recreate them after a restart, pause them when the
  work pauses, and recreate them the moment work resumes.
- Dispatching a sub-agent counts: say so when it starts and when it returns, and check on it
  at the cadence in between. Sub-agents that background a long command often end their turn
  "waiting" and never resume; check the job yourself and tell them the result.

## Not impatience

Reporting on a cadence is not the same as poking. Between reports, leave the job alone. A
progress figure that does not move for many minutes can be normal for seek-bound or
single-large-item work; say what you see and the expected duration rather than declaring a
stall, and do not cancel, restart or SIGKILL without evidence that the exit condition can
no longer be reached.
