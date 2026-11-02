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


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, TypeError):
        return False


def load_state(dest):
    try:
        return json.load(open(os.path.join(dest, STATE_FILE)))
    except FileNotFoundError:
        return None


def cdp_up(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            return json.load(r)
    except OSError:
        return None


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
    if state and alive(state.get("chrome")):
        sys.exit(f"already running: DISPLAY=:{state['display']} CDP port {state['port']} ({dest})")

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
            print(f"copying profile {p['dir']!r} ({p['name']}) -> {dest}")
            copy_profile(os.path.join(CHROME_DIR, p["dir"]), tmp)
        harden_prefs(tmp, dest)
        install_native_host(tmp)
        os.rename(tmp, dest)

    w, h = args.size.split("x")
    display = free_display()
    port = args.port or 9300 + display
    host = os.environ.get("DISPLAY", ":0")
    xephyr = spawn(["Xephyr", f":{display}", "-screen", args.size, "-title",
                    f"Nested Chrome ({account}) :{display}", "-resizeable", "-no-host-grab"],
                   log=os.path.join(dest, "xephyr.log"))
    for _ in range(50):
        if os.path.exists(f"/tmp/.X11-unix/X{display}"):
            break
        time.sleep(0.2)
    else:
        sys.exit(f"error: Xephyr :{display} did not start; see {dest}/xephyr.log")

    # Without WAYLAND_DISPLAY (and with --ozone-platform=x11) Chrome cannot
    # open its window on a Wayland desktop instead of the nested display.
    env = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"}
    env["DISPLAY"] = f":{display}"
    bridge = spawn([sys.executable, os.path.abspath(__file__), "clipbridge", host, f":{display}"],
                   log=os.path.join(dest, "clipbridge.log"))
    chrome = spawn(["google-chrome", f"--user-data-dir={dest}", "--profile-directory=Default",
                    "--ozone-platform=x11", "--disable-sync",
                    "--no-first-run", "--no-default-browser-check",
                    "--window-position=0,0", f"--window-size={w},{h}",
                    f"--remote-debugging-port={port}", "--remote-debugging-address=127.0.0.1",
                    *args.urls], env=env, log=os.path.join(dest, "chrome.log"))
    json.dump({"account": account, "display": display, "port": port, "xephyr": xephyr,
               "clipbridge": bridge, "chrome": chrome}, open(os.path.join(dest, STATE_FILE), "w"))
    for _ in range(60):
        if cdp_up(port):
            break
        time.sleep(0.5)
    else:
        sys.exit(f"error: Chrome CDP port {port} not up; see {dest}/chrome.log")
    print(f"running: account={account} DISPLAY=:{display} CDP=http://127.0.0.1:{port} dir={dest}")


def cmd_status(args):
    account = args.account or claude_account()
    dest = nested_dir(account)
    state = load_state(dest)
    if not state:
        sys.exit(f"not started ({dest})")
    for k in ("xephyr", "clipbridge", "chrome"):
        print(f"{k:<10} pid {state[k]:<8} {'running' if alive(state[k]) else 'stopped'}")
    v = cdp_up(state["port"])
    print(f"display    :{state['display']}\ncdp        {state['port']} {v['Browser'] if v else 'down'}")


def cmd_stop(args):
    account = args.account or claude_account()
    dest = nested_dir(account)
    state = load_state(dest)
    if not state:
        sys.exit(f"not started ({dest})")
    for k in ("chrome", "clipbridge", "xephyr"):  # Chrome first so it saves its profile
        if alive(state[k]):
            os.killpg(state[k], signal.SIGTERM)
            for _ in range(50):
                if not alive(state[k]):
                    break
                time.sleep(0.1)
    os.remove(os.path.join(dest, STATE_FILE))
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
        subprocess.run(["xclip", "-i", "-selection", sel], input=data,
                       env={**os.environ, "DISPLAY": display}, timeout=3)


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
    s.add_argument("--port", type=int, help="CDP port (default 9300 + display number)")
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
