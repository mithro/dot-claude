---
name: launching-nested-chrome
description: Use when an agent needs its own Chrome to drive a website (CDP or the Claude in Chrome extension) on a Linux desktop without disturbing the user's Chrome, using the Chrome profile of the Claude account Claude Code is logged into - e.g. portals needing the user's login, sites where the user must sign in or paste a password, or when remote debugging is refused on the default profile.
---

# Launching a nested Chrome

## Overview

Run a second Chrome on its own Xephyr X display, using a **copy** of the
Chrome profile named after the Claude Code account. The user sees one
window they can click and paste into; nothing else touches their desktop,
their real profile or Chrome sync.

`nested_chrome.py` (next to this file) does all of it. Read its `--help`
before improvising: each flag and exclusion fixes a real failure.

## Quick reference

```bash
S=<this skill dir>/nested_chrome.py
uv run python -I $S profiles              # * marks the profile to copy
uv run python -I $S start https://site/   # prints DISPLAY and CDP port
uv run python -I $S status
uv run python -I $S stop
uv run <this skill dir>/cdp_eval.py --port <port> --url site 'document.title'
DISPLAY=:<n> import -window root -resize 60% shot.png   # look at it
```

## Choosing the profile

- The Claude account is `claude auth status` → `email`.
- The profile to copy is the one whose **name** is that email and which is
  **not signed in to Chrome** (`chrome-signin=-`). That one profile holds the
  Claude extension signed in as that account, so the copy pairs with this
  Claude Code session.
- The script refuses a profile signed in to Chrome. A copy would clone its
  sync identity (sync device, GCM registrations) and fight the real one.
- No such profile? Ask the user to create one: Chrome profile menu → Add →
  *Continue without an account*, name it the Claude account's email,
  install Claude in Chrome and sign it in. Or use `start --fresh`: the
  user installs the extension from the Web Store inside the nested window
  and signs in there. Never fall back to a profile of another account.
- The copy carries that profile's website logins (e.g. Google). That is
  the point, but say so to the user.

## Rules

| Do | Why |
|---|---|
| Use the script's copy (`~/.config/chrome-nested-<account>`), never the real user-data-dir | Chrome ≥136 refuses `--remote-debugging-port` on the default dir, and a shared dir opens tabs in the user's running Chrome |
| Keep the default password store (no `--password-store=basic`) | Copied cookies are encrypted with the desktop keyring key; `basic` silently logs everything out |
| Leave `--ozone-platform=x11` and unset `WAYLAND_DISPLAY` | Otherwise Chrome opens on the Wayland desktop, not in Xephyr |
| Let the user type passwords; the clipboard bridge carries their paste both ways | Never ask for credentials in chat |
| Re-copy only with `start --refresh` | It deletes logins made inside the nested browser |
| Stop with `stop` (process groups it started) | Never `pkill chrome` - that kills the user's browser |
| Take the CDP port from `start` or `status`, every time | Chrome picks a free port per start. A guessed or remembered port may belong to another browser, and `cdp_eval.py` would run there with its cookies |

## Driving it

- **CDP** (`cdp_eval.py`, port 127.0.0.1 only): `fetch()` from the page
  carries its cookies, so read the site's JSON endpoints instead of scraping.
  Use real input (`Input.dispatchMouseEvent`) for widgets that ignore
  scripted `.click()`.
- **Claude in Chrome**: two browsers now run the extension. Call
  `list_connected_browsers` then `select_browser` for the nested one.
- No window manager runs in Xephyr: `xdotool windowactivate` fails; use
  `xdotool mousemove X Y click 1` (DISPLAY=:<n>).

## Common mistakes

- **Testing paste with the user's real clipboard.** The nested window is
  on their screen; pasting shows whatever they copied. Ask the user to copy
  a harmless word and paste it. Automated test only with their OK: save the
  clipboard (check `xclip -o -t TARGETS`; it may be an image), use a dummy
  string, restore after `stop`.
- **Forgetting what the bridge exposes.** It carries text only, both ways:
  a password the user copies sits in the nested clipboard where the agent
  can read it, and a copy inside the nested window replaces the user's
  clipboard. The CDP port has no authentication from other local processes.
- **Logins missing after the first copy.** The profile is copied while the
  real Chrome may be writing it (`start` warns when it is running). If the
  nested browser comes up logged out, close the real Chrome and run
  `start --refresh`.
- **Typing lost right after launch.** Wait for the page to load and click
  into the field again before concluding paste is broken.
