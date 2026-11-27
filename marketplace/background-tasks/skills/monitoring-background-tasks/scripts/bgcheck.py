#!/usr/bin/env python3
"""Background health check: EVERY process this Claude Code session started, unfiltered.

    uv run --no-project bgcheck.py [--dir DIR ...] [--log GLOB ...] [--idle-min 15] [--claude-pid PID]

Prints, and filters nothing out:

1. The full descendant tree of this session's `claude` process (found by walking up from
   this script), with state, elapsed time, CPU time and %CPU, and the command each runs.
2. With --dir: processes OUTSIDE that tree whose command line or working directory is under
   DIR. A job a sub-agent detached (nohup / setsid / systemd-run) is reparented away from
   the tree, and those are exactly what stuck wait loops wait on.
3. With --log: how long ago each matching log file was written, and its last line.
4. The footer of this session's own tmux pane, to reconcile against the tree.

Flags are prompts for you to investigate, never verdicts:
  LOOP      a while/until/sleep loop: read its exit condition and confirm it can still become true
  PGREP-F   a loop on `pgrep -f`: the pattern is in the loop's own command line, so it never exits
  NO-EXIT   a wait on a marker file with no deadline and no check that the job is still alive
  IDLE      a leaf process with no CPU time, alive longer than --idle-min
  ZOMBIE    state Z
  DETACHED  outside the tree with no claude ancestor (section 2 only)

This script makes no health decision and kills nothing. Read every line.

Linux only: it reads `ps -eo …etimes,times…` (procps) and /proc/<pid>/cwd.
The flags are pattern matches on command lines. They miss loops written in other ways
and can fire on commands that merely look like loops, which is why every line is read.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import panelib  # noqa: E402


def read_ps() -> dict[int, dict]:
    rows = {}
    out = subprocess.run(["ps", "-eo", "pid=,ppid=,stat=,etimes=,times=,pcpu=,args="],
                         capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        f = line.split(None, 6)
        if len(f) < 7:
            continue
        pid, ppid, stat, etimes, cpus, pcpu, args = f
        rows[int(pid)] = dict(ppid=int(ppid), stat=stat, et=int(etimes), cpu=int(cpus),
                              pcpu=float(pcpu), args=args)
    return rows


def is_claude(args: str) -> bool:
    """A Claude Code process: the native `claude` binary, or node/bun running its cli.js."""
    a = args.split()
    if not a:
        return False
    if os.path.basename(a[0]) == "claude":
        return True
    return os.path.basename(a[0]) in ("node", "bun") and any(
        os.path.basename(x) == "claude" or "/claude-code/" in x for x in a[1:4])


def body(args: str) -> str:
    """The command a Claude Code shell wrapper actually runs. The wrapper is
    `<shell> -c source <snapshot> && … eval '<command>' …`; anything else is returned whole."""
    m = re.match(r"\S*sh\s+-\w*c\s.*?&&\s+eval\s+(.*)$", args, re.S)
    return m.group(1) if m else args


def classify(cmd: str, stat: str, cpu: int, et: int, is_leaf: bool, idle_s: int) -> list[str]:
    flags = []
    # `while`/`until` as a shell keyword (at the start, or after ; & | ( { a quote or `do`)
    # with a `do` after it; not a word inside an argument such as `--until 5`.
    loop = bool(re.search(r"""(?:^|[;&|({'"]|\bdo\s)\s*(?:while|until)\s.*?[;\n]\s*do\b""", cmd, re.S))
    if loop:
        flags.append("LOOP")
    if re.search(r"\bpgrep\b[^|;&]*\s(?:-\w*f|--full\b)", cmd) and loop:
        flags.append("PGREP-F")
    if loop and re.search(r"(?:\[\[?|\btest)\s+!?\s*-[efs]\s", cmd) and not re.search(r"\btimeout\b|kill -0|/proc/|SECONDS|date \+%s", cmd):
        flags.append("NO-EXIT")
    if cpu == 0 and et > idle_s and is_leaf and not cmd.lstrip().startswith("sleep"):
        flags.append("IDLE")
    if stat.startswith("Z"):
        flags.append("ZOMBIE")
    return flags


def last_lines(path: str, tail_bytes: int = 8192) -> list[str]:
    """The non-empty lines in the last few KB of a file (logs can be gigabytes)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, os.path.getsize(path) - tail_bytes))
            return fh.read().decode(errors="replace").strip().splitlines()
    except OSError as e:
        return [f"(cannot read: {e})"]


def fmt(s: int) -> str:
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", action="append", default=[], help="also list processes outside the tree with cmdline or cwd under DIR")
    ap.add_argument("--log", action="append", default=[], help="glob of log files to report freshness for")
    ap.add_argument("--idle-min", type=int, default=15)
    ap.add_argument("--claude-pid", type=int, help="check this claude process instead of the one this script runs under")
    a = ap.parse_args()
    if not sys.platform.startswith("linux"):
        sys.exit("bgcheck.py needs Linux (procps `ps -eo etimes,times` and /proc); "
                 "on this system list the tree by hand, e.g. `ps -axo pid,ppid,stat,etime,time,command`")

    rows = read_ps()
    me = os.getpid()
    root = a.claude_pid or me
    if not a.claude_pid:
        while root in rows and not is_claude(rows[root]["args"]):
            root = rows[root]["ppid"]
    if root not in rows or not is_claude(rows[root]["args"]):
        sys.exit("no `claude` ancestor found; pass --claude-pid PID")

    skip, p = set(), me  # our own call chain is not background work
    while p in rows and p != root:
        skip.add(p)
        p = rows[p]["ppid"]
    skip |= {pid for pid, r in rows.items() if r["ppid"] == me}

    kids: dict[int, list[int]] = {}
    for pid, r in rows.items():
        kids.setdefault(r["ppid"], []).append(pid)

    total = flagged = loops = 0

    def walk(pid: int, depth: int) -> None:
        nonlocal total, flagged, loops
        for c in sorted(kids.get(pid, [])):
            if c in skip:
                walk(c, depth)
                continue
            r = rows[c]
            b = body(r["args"])
            fl = classify(b, r["stat"], r["cpu"], r["et"], not kids.get(c), a.idle_min * 60)
            total += 1
            loops += "LOOP" in fl
            flagged += bool(set(fl) - {"LOOP"})
            print(f"{'  ' * depth}{c} {r['stat']:4} et={fmt(r['et'])} cpu={fmt(r['cpu'])} "
                  f"{r['pcpu']:4.0f}% [{' '.join(fl)}] {b}")
            walk(c, depth + 1)

    print(f"== 1. Session claude pid {root}: every descendant, nothing filtered ==")
    walk(root, 1)
    direct = [c for c in kids.get(root, []) if c not in skip]
    print(f"\n{total} processes, {loops} LOOP (check each exit condition by hand), {flagged} with another flag.")
    print(f"{len(direct)} direct children of claude (background shells, plus MCP servers and any sub-agent's "
          f"current foreground tool call; tell them apart by reading the commands).")

    if a.dir:
        dirs = [os.path.realpath(os.path.expanduser(d)) for d in a.dir]

        def session_of(pid: int) -> int | None:
            n = 0
            while pid in rows and pid > 1 and n < 64:
                if is_claude(rows[pid]["args"]):
                    return pid
                pid, n = rows[pid]["ppid"], n + 1
            return None

        print(f"\n== 2. Processes OUTSIDE the tree with cmdline or cwd under {', '.join(dirs)} ==")
        found = 0
        for pid, r in sorted(rows.items()):
            if pid in skip or pid == me:
                continue
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except OSError:
                cwd = ""
            if not any(d in r["args"] or cwd == d or cwd.startswith(d + "/") for d in dirs):
                continue
            owner = session_of(pid)
            if owner == root:
                continue
            found += 1
            where = "DETACHED (no claude ancestor)" if owner is None else f"under another claude session, pid {owner}"
            print(f"  {pid} ppid={r['ppid']} {r['stat']:4} et={fmt(r['et'])} cpu={fmt(r['cpu'])} {r['pcpu']:4.0f}% [{where}] cwd={cwd}\n      {r['args']}")
        print(f"{found} such processes. Account for each: is it yours, is it working, does anything wait on it?")
    else:
        print("\n== 2. (skipped: pass --dir DIR to find jobs detached from the tree) ==")

    if a.log:
        print("\n== 3. Logs ==")
        now = time.time()
        mtimes = {}
        for g in a.log:
            for p in glob.glob(os.path.expanduser(g), recursive=True):
                try:
                    if os.path.isfile(p):
                        mtimes[p] = os.stat(p).st_mtime
                except OSError:  # deleted between the glob and the stat
                    pass
        paths = sorted(mtimes, key=mtimes.get, reverse=True)
        for p in paths:
            lines = last_lines(p)
            print(f"  {(now - mtimes[p]) / 60:8.1f} min ago  {p}\n      last: {(lines[-1] if lines else '(empty)')[:200]}")
        if not paths:
            print("  no file matched")

    pane = os.environ.get("TMUX_PANE")
    print(f"\n== 4. UI footer of this session's pane ({pane}) ==")
    screen = None
    if pane:
        try:
            screen = panelib.Tmux().capture(pane)
        except RuntimeError as e:
            print(f"  the UI cannot be read ({e}); say so in the report.")
    else:
        print("  not running inside tmux: the UI cannot be read; say so in the report.")
    if screen is not None:
        for l in panelib.status_tail(screen, 12):
            print("  " + l.rstrip()[:200])
        n = panelib.footer_task_count(screen)
        print(f"  footer count: {n if n is not None else 'not shown (open the dialog with uitasks.py)'}")
        for row in panelib.agent_panel(screen):
            print(f"  agent panel: {row}")
        print("  Reconcile: every background shell, agent, scheduled job and monitor you know of must appear in the UI "
              "(footer count, agent panel, Background dialog), and everything the UI shows must be one you know of.")


if __name__ == "__main__":
    main()
