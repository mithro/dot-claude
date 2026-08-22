---
name: netgear-switches
description: Use when inspecting or changing Netgear switches on the Welland/Monarto network (ports, VLANs, PVIDs, PoE, LLDP, MACs, sensors, management IP) — explains the shared `netgear` MCP server, the inventory, credentials, per-model backend quirks and the safety rules for writes.
---

# Netgear switches (Welland / Monarto)

The `netgear` MCP server (tools `list_switches`, `get_ports`, `get_vlans`,
`get_pvids`, `get_macs`, `get_lldp`, `get_sensors`, `get_poe`, `get_mgmt_ip`,
`snapshot`, `identify`, `get_device`, and the write tools `set_port_enabled`,
`set_poe`, `cycle_poe`, `clear_poe_fault`, `set_pvid`, `set_vlan_membership`,
`create_vlan`, `delete_vlan`, `set_mgmt_ip`, `upload_certificate*`) is
`ngsw-mcp` from **python-netgear-switch-library** (Debian package
`python3-netgear-switch-library`, installed from the site apt-proxy).

## How the server runs (ten64-welland, as `tim`)

- **One shared process for every Claude session**, socket-activated:
  `ngsw-mcp.socket` listens on `127.0.0.1:8765`; the first connection starts
  `ngsw-mcp-proxy.service` → `ngsw-mcp.service` (`ngsw-mcp --transport
  streamable-http` on `:8766`). After 15 min idle the proxy exits and
  `StopWhenUnneeded=` stops the server. Nothing runs when nobody is using it.
- Units: `~/.config/systemd/user/ngsw-mcp.{socket,service}`,
  `ngsw-mcp-proxy.service`. Troubleshoot with
  `systemctl --user status ngsw-mcp.socket ngsw-mcp.service` and
  `journalctl --user -u ngsw-mcp.service`.
- Inventory: `~/.config/ngsw/inventory.toml` (`NGSW_INVENTORY`). **Always
  address switches by inventory name** (`switch="m4300-24x"`), not ad-hoc
  host+model. `list_switches` tells you the names. Passwords are never on
  disk: each is a `!~/.config/ngsw/get-cred.sh <host>` secret spec that asks
  gdoc2netcfg (`sudo -n`) at the moment it is needed. Never print one.
- The same inventory drives the CLI:
  `ngsw --config ~/.config/ngsw/inventory.toml --switch <name> <cmd>`
  (e.g. `ports`, `vlans`, `lldp`, `nsdp-device`, `show`).

## Fleet facts (measured, 2026-08-22; see inventory comments)

| Inventory name(s) | Model / registry key | Backends that work |
|---|---|---|
| `s3300-1`, `s3300-2` | S3300-52X (`gsm7228ps`, alias `s3300`) | SNMP `public` is read **and write**; CLI is **telnet on port 60000** (no ssh); HTTP. |
| `m4300-24x`, `m4300-16x-poe-s1/2/3` | M4300 FASTPATH | SNMP `public` read; writes: no write community in gdoc2netcfg → use `backend="ssh"` (admin + web password) or HTTP. |
| `gsm7252ps-s1/2/3` | GSM7252PS FASTPATH | SNMP `public` **read-only** (`noAccess` on set); writes via `backend="ssh"`. "s2" in conversation means `gsm7252ps-s2`, not `m4300-16x-poe-s2`. |
| `gs110emx1/2/3` | GS110EMX (Plus) | HTTP web UI primarily; NSDP from `br-net`. |
| `poe-micro1/2/3` | GS105PE (Plus; only `poe-micro3` confirmed) | NSDP (`br-net`) + HTTP. |
| `m7300`, `xs748t` | registry `m7300`/`xs748t` | did not answer SNMP `public` on 2026-08-22 — check before assuming. |
| `gs728tpp-monarto` | GS728TPP (Monarto, via wg tunnel) | SNMP/HTTP. |

`protected_ports` in the inventory are the LLDP-measured inter-switch, router
(ten64/OpenWrt) and tweed links; writes to them fail without `force=true`.
Switches that were unreachable during the sweep (`s3300-2`, `m4300-16x-poe-s1/-s3`,
`gsm7252ps-s3`) have **no** protected ports yet — be doubly careful there.

## Rules for writes (non-negotiable)

1. **Read first.** `get_ports`/`get_vlans`/`get_lldp` on the target before any
   write; never change a port whose LLDP neighbour is a switch, the router or
   a server unless the user explicitly names it.
2. **Writes need `force=true` only when the user has asked for that exact
   change** on that exact port/VLAN. `force` is not a retry knob.
3. **Never leave a device changed by accident:** record prior state, make the
   change, re-read to prove it. Use throwaway VLAN ids 4001–4008 for
   experiments; touch only link-down ports with an empty/`'empty'` description.
4. **Never persist config** (`write memory` / save) on a switch during testing
   — the library does not, and you must not either over the CLI backend.
5. **Pick the backend deliberately** when it matters (`backend="ssh"` for
   FASTPATH writes); an unsupported combination returns
   `{"unsupported": true, ...}` — that is an honest answer, not a retry cue.
   Never "fall back" to another protocol to make a call look successful.
6. A failure is something *you* did (wrong backend, credential, ordering,
   protected port) until the device's own output proves otherwise.

## When the server misbehaves

- `systemctl --user is-active ngsw-mcp.socket` must be `active`; if not:
  `systemctl --user enable --now ngsw-mcp.socket`.
- Stuck server: `systemctl --user stop ngsw-mcp-proxy.service ngsw-mcp.service`
  (the next MCP call restarts it).
- After upgrading `python3-netgear-switch-library`, stop the service the same
  way so the next connection picks up the new code.
