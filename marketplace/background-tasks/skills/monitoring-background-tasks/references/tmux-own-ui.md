# Reading your own Background tasks dialog through tmux

Your list of background tasks and the UI's list drift apart. The UI is the second,
independent view to reconcile against. `scripts/uitasks.py` does everything below; this
page is what it does and why, so you can check its work or do it by hand when a Claude
Code update changes the screens.

Verified on Claude Code 2.1.332 (2026-11-26). An earlier layout (seen 2026-11-24) is noted
where it differs. **Expect this to change between versions: look at the captured screen
before trusting any key sequence here.**

## The screens

**Footer**, below the input box, while tasks exist:

    ⏵⏵ auto mode on · 2 shells · esc to interrupt · ↓ to manage

Other wordings seen: `N background tasks · ↓ to manage`, `1 shell · /tasks to see subagents
· ↓ to manage`, and `↓ to manage` with no count when only a sub-agent is running. A status
line may sit between the input box and this line. No `to manage` in the footer means no
tasks (or an unexpected screen): send nothing. The transcript also contains `↓ to manage`
(after every backgrounded agent), so look only below the input box.

**Agent panel**, under the footer, while sub-agents run:

      ● main
      ◯ general-purpose  waiting on 1 shell · <description> · since 10:26 PM

With several agents this pushes the footer line well above the bottom of the pane.

**Down** focuses the footer; it then reads `enter to view tasks`. **Up** gives focus back.

**Enter** opens one of two things:

- With **two or more** tasks, the list:

      Background
      2 shells

      ❯ ● sleep 800   running
        ● sleep 900   running

          Earlier in this session (0)

      ↑/↓ to navigate · x to stop · Enter to view · Esc to close

  On 2.1.332 this list holds shells only. A shell started by a sub-agent is in it, marked
  `running · general-purpose subagent`; the sub-agents themselves are in the agent panel.
  The earlier layout had a `N background tasks` header and titled sections: *Shells*,
  *Background agents*, *Scheduled*, then *Earlier in this session*.
- With **exactly one** task, that task's detail view directly. There is no list.

A dialog replaces the input box: it is everything below the last rule line that starts at
column 0, and its last line is the key hint ending `Esc to close`.

**Enter** on a row opens its detail view:

      <description>
      shell

      Status:   running
      Runtime:  14s
      Command:  sleep 900

      Output
      No output yet

      ← to go back · x to stop · Enter/Space to close · Esc to close

A shell started by a sub-agent has a `Subagent:` line as well. **Left** returns to the
list. **Escape** closes the whole dialog, from the list or from a detail view.

What **Enter** does on an agent, scheduled or monitor row (earlier layout) was never
captured. `uitasks.py` lists those rows and does not open them.

The list is live: when a task finishes, the rows below it move up. `uitasks.py` compares the
list with its first reading before every row's **Enter** and stops (exit 3) if any row
differs, because the selected position may now hold a different row. Run it again.

## Rules

1. Capture with `-e` first. Act only if the pane is not in copy mode and the input box is on
   screen and empty (grey text is a suggestion; default-colour text is the person's).
2. One key at a time; confirm the expected screen on a fresh capture before the next. To move
   the selection, send one `Down` or `Up` and check that `❯` moved.
3. `Escape` only while a dialog is visibly open below the last rule line. Outside one it
   interrupts the turn you are running. One `Escape` closes it: send it once and wait for the
   dialog to go. Send another only if a fresh capture, seconds later, still shows the dialog.
4. Never send `x`.
5. "Closed" means the input box is drawn again, not merely that the dialog text is gone
   from a half-redrawn screen.
6. Afterwards: dialog closed, input box unchanged. If a run fails after `Enter` was sent,
   capture the pane and close the dialog yourself before doing anything else.

## What the count includes

It depends on the version, so read the wording:

- `2 shells` (2.1.332): background shells only, including shells that sub-agents started.
  Sub-agents are not counted; they are the rows of the agent panel.
- `N background tasks` (earlier, and sometimes still shown): shells, background agents,
  scheduled (cron) jobs and monitors together.

Neither includes a sub-agent's current foreground tool call, which looks identical to a
background shell in `ps`. MCP servers are also direct children of `claude` and are not
tasks. That is why "children of `claude`" and "N" differ, and why each difference has to be
explained from the commands rather than counted.

## What the script records

- Raw screens, one file per step, in
  `~/.local/state/claude-bgtasks/<pane>/<stamp>-screens/`. One directory per pane: a shared
  one makes the diff compare against another session.
- A JSON snapshot: footer count, header, every row, the detail view of every shell row, the
  rows it did not open, and the agent panel.
- A diff against the previous snapshot. "Identical" is flagged so a stale capture is noticed.
  Pane ids start again when the tmux server restarts, so a snapshot from another server is
  not compared.
- Self-checks (exit 3): footer count = header count = parsed rows; every shell row's detail
  read; dialog closed; input box unchanged. Exit 2 means it declined to touch the pane.
- If it fails after opening the dialog, it still closes the dialog before reporting.

**Every run, compare the raw screens with the JSON by eye.** A self-check only proves the
script agrees with itself.
