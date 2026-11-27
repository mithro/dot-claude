#!/usr/bin/env python3
"""Run a private Chrome inside a nested Xephyr display for an agent to drive.

The browser uses a copy of the Chrome profile whose name is the Claude
account Claude Code is logged into, never the user's real profile. It runs
on its own X display, so no window appears on the desktop, and a clipboard
bridge lets the user copy on the desktop and paste in the nested browser
(and back).

    nested_chrome.py profiles               list profiles, mark the match
    nested_chrome.py start [URL ...]        copy profile if needed, launch
    nested_chrome.py status                 show what is running
    nested_chrome.py stop                   stop Chrome, bridge and Xephyr
    nested_chrome.py clipbridge HOST NESTED internal: the clipboard bridge

Linux/X11 only (works on a Wayland desktop through XWayland). Needs Xephyr,
xclip and google-chrome.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

CHROME_DIR = os.path.expanduser("~/.config/google-chrome")
CLAUDE_EXT = "fcoeoabgfenejglbffodgkkbkcdhcgfn"  # Claude in Chrome
NATIVE_HOST = "com.anthropic.claude_code_browser_extension.json"
STATE_FILE = "nested-chrome.json"
# Text that must be in the command line of each process the state file names.
PROCESS_MARK = {"xephyr": "Xephyr", "clipbridge": "clipbridge", "chrome": "chrome"}

# Profile parts never copied: caches (large, rebuilt), the open tabs of the
# real browser, sync and push-messaging identities (a clone would share the
# real profile's sync device and GCM registrations) and installed web apps
# (Chrome would write .desktop launchers for them into the user's desktop).
COPY_EXCLUDE = {
    "Cache", "Code Cache", "GPUCache", "DawnGraphiteCache", "DawnWebGPUCache",
    "Sessions", "Sync Data", "GCM Store", "Web Applications",
    "LOCK", "SingletonLock", "SingletonSocket", "SingletonCookie",
}


def claude_account():
    out = subprocess.run(["claude", "auth", "status"], capture_output=True,
                         text=True, check=True).stdout
    return json.loads(out)["email"]


def chrome_profiles():
    state = json.load(open(os.path.join(CHROME_DIR, "Local State")))
    for pdir, info in state["profile"]["info_cache"].items():
        path = os.path.join(CHROME_DIR, pdir)
        yield {
            "dir": pdir,
            "name": info.get("name", ""),
            # Non-empty only when the profile is signed in to Chrome itself
            # (the identity Chrome sync uses), not just to websites.
            "chrome_account": info.get("user_name", ""),
            "claude_ext": os.path.isdir(os.path.join(path, "Extensions", CLAUDE_EXT)),
        }


def slug(account):
    return re.sub(r"[^a-z0-9]+", "-", account.lower()).strip("-")


def nested_dir(account):
    return os.path.expanduser(f"~/.config/chrome-nested-{slug(account)}")


def pick_profile(account, wanted=None):
    profiles = list(chrome_profiles())
    if wanted:
        matches = [p for p in profiles if p["dir"] == wanted]
    else:
        matches = [p for p in profiles if account.lower() in (p["name"].lower(), p["chrome_account"].lower())]
        # The user's own synced profile often has the same account; prefer
        # the copyable one (named after the account, not signed in to Chrome).
        copyable = [p for p in matches if not p["chrome_account"]]
        matches = copyable or matches
    if len(matches) != 1:
        sys.exit(f"error: {len(matches)} Chrome profiles match {wanted or account!r}; "
                 "run `profiles` and pass --profile DIR, or --fresh for an empty profile")
    p = matches[0]
    if p["chrome_account"]:
        sys.exit(f"error: profile {p['dir']!r} is signed in to Chrome as {p['chrome_account']} "
                 "(Chrome sync). A copy would clone its sync identity. Use a profile that is "
                 "not signed in to Chrome, or --fresh.")
    if not p["claude_ext"]:
        print(f"warning: profile {p['dir']!r} does not have the Claude in Chrome extension", file=sys.stderr)
    return p


def copy_profile(src, dest):
    def ignore(d, names):
        top = os.path.abspath(d) == os.path.abspath(src)
        return [n for n in names if (top and n in COPY_EXCLUDE) or n.startswith("Singleton")]
    shutil.copytree(src, os.path.join(dest, "Default"), ignore=ignore, symlinks=True,
                    ignore_dangling_symlinks=True, dirs_exist_ok=False)


def harden_prefs(build, dest):
    """Prefs that keep the nested browser quiet and unlinked."""
    path = os.path.join(build, "Default", "Preferences")
    prefs = json.load(open(path)) if os.path.exists(path) else {}
    def put(dotted, value):
        node = prefs
        *parents, leaf = dotted.split(".")
        for k in parents:
            node = node.setdefault(k, {})
        node[leaf] = value
    put("signin.allowed", False)                 # no Chrome sign-in, so no sync
    put("signin.allowed_on_next_startup", False)
    put("profile.default_content_setting_values.notifications", 2)  # host desktop popups
    put("download.prompt_for_download", False)   # file dialogs can open via the host portal
    put("download.default_directory", os.path.join(dest, "Downloads"))
    put("session.restore_on_startup", 5)         # start on the new tab page
    put("browser.has_seen_welcome_page", True)
    os.makedirs(os.path.join(build, "Downloads"), exist_ok=True)
    json.dump(prefs, open(path, "w"))


def install_native_host(dest):
    """Chrome reads native-messaging manifests from <user-data-dir>/NativeMessagingHosts,
    so the Claude extension in the copy needs its own copy to reach Claude Code."""
    src = os.path.join(CHROME_DIR, "NativeMessagingHosts", NATIVE_HOST)
    if os.path.exists(src):
        os.makedirs(os.path.join(dest, "NativeMessagingHosts"), exist_ok=True)
        shutil.copy2(src, os.path.join(dest, "NativeMessagingHosts", NATIVE_HOST))


def free_display(start=40):
    n = start
    while os.path.exists(f"/tmp/.X11-unix/X{n}") or os.path.exists(f"/tmp/.X{n}-lock"):
        n += 1
    return n


def spawn(cmd, env=None, log=None):
    out = open(log, "ab") if log else subprocess.DEVNULL
    return subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=out,
                            stderr=subprocess.STDOUT, start_new_session=True).pid


def boot_id():
    return open("/proc/sys/kernel/random/boot_id").read().strip()


def proc_start(pid):
    """Start time (clock ticks since boot) of a live process, else None."""
    try:
        stat = open(f"/proc/{pid}/stat").read()
    except OSError:
        return None
    # The command name (field 2) may contain spaces and brackets.
    fields = stat.rsplit(")", 1)[1].split()
    return None if fields[0] == "Z" else int(fields[19])


def proc_cmdline(pid):
    try:
        return open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="replace")
    except OSError:
        return ""


def alive(state, key):
    """Is the process `start` recorded under `key` still running?

    A pid alone is not enough: the state file outlives a reboot or crash,
    and the pid may since have gone to an unrelated process that `stop`
    would then kill. So the process must also look like ours (command
    line) and have started when ours did (same boot, same start time).
    Reads /proc rather than kill(pid, 0), which raises PermissionError for
    another user's process."""
    pid = state.get(key)
    start = proc_start(pid)
    if start is None or PROCESS_MARK[key] not in proc_cmdline(pid):
        return False
    if "starts" not in state:  # written by a version that recorded pids only
        return True
    return state.get("boot_id") == boot_id() and state["starts"].get(key) == start


def load_state(dest):
    try:
        return json.load(open(os.path.join(dest, STATE_FILE)))
    except FileNotFoundError:
        return None


def save_state(dest, state):
    with open(os.path.join(dest, STATE_FILE), "w") as f:
        json.dump(state, f)


def stop_recorded(dest, state):
    """Stop what the state file recorded and remove it, whatever happens."""
    try:
        for k in ("chrome", "clipbridge", "xephyr"):  # Chrome first so it saves its profile
            if not alive(state, k):
                continue
            try:
                os.killpg(state[k], signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                continue
            for _ in range(50):
                if not alive(state, k):
                    break
                time.sleep(0.1)
            else:
                print(f"warning: {k} (pid {state[k]}) did not exit after SIGTERM", file=sys.stderr)
    finally:
        try:
            os.remove(os.path.join(dest, STATE_FILE))
        except FileNotFoundError:
            pass


def devtools_active_port(dest):
    """(port, websocket path) Chrome wrote once its CDP server was listening."""
    try:
        port, ws_path = open(os.path.join(dest, "DevToolsActivePort")).read().split()[:2]
        return int(port), ws_path
    except (OSError, ValueError):
        return None


def cdp_up(port, ws_path):
    """Version info from the CDP server on `port`, only if it is our Chrome.

    Anything can answer on a local port - another browser that had it first,
    say - and evaluating JavaScript there would run in the wrong browser with
    its cookies. Our Chrome is the one whose browser websocket path matches
    the DevToolsActivePort file in our own user-data-dir."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            version = json.load(r)
    except (OSError, ValueError):
        return None
    if not ws_path or not version.get("webSocketDebuggerUrl", "").endswith(ws_path):
        return None
    return version


def cmd_profiles(args):
    account = args.account or claude_account()
    print(f"Claude Code account: {account}\n")
    for p in chrome_profiles():
        match = account.lower() in (p["name"].lower(), p["chrome_account"].lower())
        mark = ("x" if p["chrome_account"] else "*") if match else " "
        print(f"{mark} {p['dir']:<12} name={p['name']!r:<24} "
              f"chrome-signin={p['chrome_account'] or '-':<26} claude-ext={'yes' if p['claude_ext'] else 'no'}")
    print("\n* = the Claude account's profile; `start` copies it."
          "\nx = the Claude account, but signed in to Chrome (sync): never copied."
          "\nNo *? Create a profile without Chrome sign-in named after the account, or use --fresh.")


def cmd_start(args):
    account = args.account or claude_account()
    dest = nested_dir(account)
    state = load_state(dest)
    if state and alive(state, "chrome"):
        sys.exit(f"already running: DISPLAY=:{state['display']} CDP port {state['port']} ({dest})")
    if state:
        # Chrome is gone (closed or crashed) but its Xephyr and clipboard
        # bridge may live on. Starting again without stopping them would
        # orphan both, the bridge still copying the user's clipboard.
        print("cleaning up the previous run (Chrome had exited)")
        stop_recorded(dest, state)

    if args.refresh and os.path.isdir(dest):
        shutil.rmtree(dest)
    if not os.path.isdir(dest):
        # Build beside the final name and rename, so a failed copy never
        # leaves a half profile that the next start would reuse.
        p = None if args.fresh else pick_profile(account, args.profile)
        tmp = dest + ".partial"
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(os.path.join(tmp, "Default") if args.fresh else tmp)
        if p:
            if os.path.lexists(os.path.join(CHROME_DIR, "SingletonLock")):
                print("warning: Chrome is running, so the copy may catch a database mid-write. "
                      "If logins are missing in the nested browser, close Chrome and "
                      "run `start --refresh`.", file=sys.stderr)
            print(f"copying profile {p['dir']!r} ({p['name']}) -> {dest}")
            copy_profile(os.path.join(CHROME_DIR, p["dir"]), tmp)
        harden_prefs(tmp, dest)
        install_native_host(tmp)
        os.rename(tmp, dest)

    w, h = args.size.split("x")
    display = free_display()
    host = os.environ.get("DISPLAY", ":0")
    state = {"account": account, "display": display, "port": None, "ws_path": None,
             "boot_id": boot_id(), "starts": {}}

    def record(key, pid):
        # Saved after every spawn, so `stop` can always find what was started.
        state[key] = pid
        state["starts"][key] = proc_start(pid)
        save_state(dest, state)

    record("xephyr", spawn(["Xephyr", f":{display}", "-screen", args.size, "-title",
                            f"Nested Chrome ({account}) :{display}", "-resizeable", "-no-host-grab"],
                           log=os.path.join(dest, "xephyr.log")))
    for _ in range(50):
        if os.path.exists(f"/tmp/.X11-unix/X{display}"):
            break
        time.sleep(0.2)
    else:
        stop_recorded(dest, state)
        sys.exit(f"error: Xephyr :{display} did not start; see {dest}/xephyr.log")

    # Without WAYLAND_DISPLAY (and with --ozone-platform=x11) Chrome cannot
    # open its window on a Wayland desktop instead of the nested display.
    env = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"}
    env["DISPLAY"] = f":{display}"
    record("clipbridge", spawn([sys.executable, os.path.abspath(__file__), "clipbridge", host, f":{display}"],
                               log=os.path.join(dest, "clipbridge.log")))
    # Port 0: Chrome picks a free port and writes it to DevToolsActivePort in
    # its user-data-dir. A fixed port that something else already holds does
    # not stop Chrome starting; the other listener would just answer for it.
    active_port_file = os.path.join(dest, "DevToolsActivePort")
    if os.path.exists(active_port_file):
        os.remove(active_port_file)  # left by the previous run
    record("chrome", spawn(["google-chrome", f"--user-data-dir={dest}", "--profile-directory=Default",
                            "--ozone-platform=x11", "--disable-sync",
                            "--no-first-run", "--no-default-browser-check",
                            "--window-position=0,0", f"--window-size={w},{h}",
                            f"--remote-debugging-port={args.port or 0}",
                            "--remote-debugging-address=127.0.0.1",
                            *args.urls], env=env, log=os.path.join(dest, "chrome.log")))
    for _ in range(60):
        active = devtools_active_port(dest)
        if active and cdp_up(*active):
            break
        time.sleep(0.5)
    else:
        sys.exit("error: Chrome did not open its CDP port"
                 + (f" (is port {args.port} already in use?)" if args.port else "")
                 + f"; see {dest}/chrome.log, then run `stop`")
    state["port"], state["ws_path"] = active
    save_state(dest, state)
    print(f"running: account={account} DISPLAY=:{display} CDP=http://127.0.0.1:{state['port']} dir={dest}")


def cmd_status(args):
    account = args.account or claude_account()
    dest = nested_dir(account)
    state = load_state(dest)
    if not state:
        sys.exit(f"not started ({dest})")
    for k in ("xephyr", "clipbridge", "chrome"):
        pid = state.get(k)
        print(f"{k:<10} pid {pid if pid else '-':<8} {'running' if alive(state, k) else 'stopped'}")
    port = state.get("port")
    if "ws_path" in state:
        v = alive(state, "chrome") and port and cdp_up(port, state["ws_path"])
    else:  # state from a version that could not tell whose port it was
        v = None
    print(f"display    :{state['display']}\ncdp        {port or '-'} {v['Browser'] if v else 'down'}")


def cmd_stop(args):
    account = args.account or claude_account()
    dest = nested_dir(account)
    state = load_state(dest)
    if not state:
        sys.exit(f"not started ({dest})")
    stop_recorded(dest, state)
    print("stopped")


def clip_get(display):
    try:
        r = subprocess.run(["xclip", "-o", "-selection", "clipboard", "-t", "UTF8_STRING"],
                           env={**os.environ, "DISPLAY": display}, capture_output=True, timeout=3)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.returncode == 0 and r.stdout else None


def clip_put(display, data, selections):
    for sel in selections:
        try:
            subprocess.run(["xclip", "-i", "-selection", sel], input=data,
                           env={**os.environ, "DISPLAY": display}, timeout=3)
        except subprocess.TimeoutExpired:
            pass  # one missed copy must not end the bridge; the next poll retries


def cmd_clipbridge(args):
    """Copy text clipboard changes both ways, polling twice a second.

    Uses xclip on the host display too: on a GNOME Wayland desktop the
    compositor keeps the XWayland clipboard in step, whereas wl-paste there
    has to flash a window to get focus."""
    host, nested = args.host, args.nested
    sock = f"/tmp/.X11-unix/X{nested.lstrip(':')}"
    last_host = last_nested = None
    while os.path.exists(sock):
        h, n = clip_get(host), clip_get(nested)
        if h and h != last_host:
            last_host = h
            if h != n:
                clip_put(nested, h, ("clipboard", "primary"))  # Ctrl+V and middle-click
                n = h
            last_nested = n
        elif n and n != last_nested:
            last_nested = n
            if n != h:
                clip_put(host, n, ("clipboard",))
            last_host = n
        time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", help="Claude account (default: from `claude auth status`)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profiles").set_defaults(fn=cmd_profiles)
    s = sub.add_parser("start")
    s.add_argument("--profile", help="Chrome profile directory to copy, e.g. 'Profile 2'")
    s.add_argument("--fresh", action="store_true", help="empty profile: in the nested window, install Claude in Chrome from the Web Store and sign it in")
    s.add_argument("--refresh", action="store_true", help="delete the copy (and logins made in it) and copy again")
    s.add_argument("--size", default="1500x950")
    s.add_argument("--port", type=int, help="fixed CDP port (default: a free port Chrome picks; `start` prints it)")
    s.add_argument("urls", nargs="*")
    s.set_defaults(fn=cmd_start)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("stop").set_defaults(fn=cmd_stop)
    c = sub.add_parser("clipbridge")
    c.add_argument("host")
    c.add_argument("nested")
    c.set_defaults(fn=cmd_clipbridge)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
