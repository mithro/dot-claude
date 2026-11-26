# Reading your own Background tasks dialog through tmux

Your list of background tasks and the UI's list drift apart. The UI is the second,
independent view to reconcile against. `scripts/uitasks.py` does everything below; this
page is what it does and why, so you can check its work or do it by hand when a Claude
Code update changes the screens.

Verified on Claude Code 2.1.332 (2026-11-26). An earlier layout (seen 2026-11-24) is noted
where it differs. **Expect this to change between versions: look at the captured screen
before trusting any key sequence here.**

## The screens

**Footer**, last line of the pane, while tasks exist:

    ⏵⏵ auto mode on · 2 shells · esc to interrupt · ↓ to manage

Earlier wording: `N background tasks · ↓ to manage`. No `to manage` means no tasks (or an
unexpected screen): send nothing.

**Down** focuses the footer; it then reads `enter to view tasks`. **Up** gives focus back.

**Enter** opens one of two things:

- With **two or more** tasks, the list:

      Background
      2 shells

      ❯ ● sleep 800   running
        ● sleep 900   running

          Earlier in this session (0)

      ↑/↓ to navigate · x to stop · Enter to view · Esc to close

  The earlier layout had a `N background tasks` header and titled sections: *Shells*,
  *Background agents*, *Scheduled*, then *Earlier in this session*.
- With **exactly one** task, that task's detail view directly. There is no list.

**Enter** on a row opens its detail view:

      <description>
      shell

      Status:   running
      Runtime:  14s
      Command:  sleep 900

      Output
      No output yet

      ← to go back · x to stop · Enter/Space to close · Esc to close

**Left** returns to the list. **Escape** closes the dialog.

## Rules

1. Capture with `-e` first. Act only if the input box is on screen and empty (grey text is a
   suggestion; default-colour text is the person's).
2. One key at a time; confirm the expected screen before the next.
3. `Escape` only while the list or a detail view is visibly open. Outside them it interrupts
   the turn you are running.
4. Never send `x`.
5. "Closed" means the footer shows `to manage` again, not merely that the dialog text is gone
   from a half-redrawn screen.
6. Afterwards: dialog closed, input box unchanged. If a run fails after `Enter` was sent,
   capture the pane and close the dialog yourself before doing anything else.

## What the count includes

The count covers background shells, background agents, scheduled (cron) jobs and monitors.
It does **not** include a sub-agent's current foreground tool call, which looks identical to
a background shell in `ps`. MCP servers are also direct children of `claude` and are not
tasks. That is why "children of `claude`" and "N" differ, and why each difference has to be
explained from the commands rather than counted.

## What the script records

- Raw screens, one file per step, in
  `~/.local/state/claude-bgtasks/<pane>/<stamp>-screens/`. One directory per pane: a shared
  one makes the diff compare against another session.
- A JSON snapshot: footer count, header, every row, the detail view of every active row.
- A diff against the previous snapshot. "Identical" is flagged so a stale capture is noticed.
- Self-checks (exit 3): footer count = header count = parsed rows; every row's detail read;
  dialog closed; input box unchanged. Exit 2 means it declined to touch the pane.

**Every run, compare the raw screens with the JSON by eye.** A self-check only proves the
script agrees with itself.
