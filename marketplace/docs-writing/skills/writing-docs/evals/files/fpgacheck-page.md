---
type: how-to
owner: tools team
reader: someone with a board on a Pi who wants to check its wiring
review: 2026-12-01
---

# Using fpgacheck

fpgacheck is our tool for checking that an FPGA board is wired correctly to its Raspberry Pi. It was written in
2025 to replace the old shell scripts and is now the standard way to verify a board. It supports the Acorn,
the Arty A7 and the Fomu, and currently 14 tests.

## Installation

Installing is easy. Just add our apt repository and install the package:

```
curl -fsSL https://apt.example.org/key.gpg | sudo tee /etc/apt/keyrings/example.gpg
sudo apt update && sudo apt install fpgacheck
```

## Running

1. Run `fpgacheck`.
2. It will detect the board automatically (it reads the HAT EEPROM, falls back to USB vendor IDs, and finally
   to a JTAG scan, unless `--board` is given, in which case detection is skipped; detection takes about 2 s).
3. Read the output.

## Options

`--board NAME` forces the board type. `--json` prints machine-readable output. `--quiet` suppresses everything
except failures. `--publish` uploads the result to the fleet server (needs a token in ~/.fpgacheck/token; ask
the ops team for one). `-v` is verbose.

## How detection works

Detection first reads the HAT EEPROM over I2C on GPIO 0 and 1. If no HAT is present, it enumerates USB devices
and matches vendor IDs against a table in `fpgacheck/boards.py`. If that also fails it does a JTAG IDCODE scan on
the default pins. This order was chosen because the EEPROM read is passive and cannot disturb a running design,
whereas a JTAG scan toggles TCK.

## Reading the result

A passing run prints `PASS` and the board's label. A failing run prints each failing test with a hint. For
example a swapped UART shows `uart-loopback FAIL: no echo (TX and RX swapped?)`. See the test list in the
README for all 14 tests.

Note: on a Pi 5, you must run with sudo, otherwise the GPIO chip can't be opened.

Note: the `--publish` option is not yet available for the Fomu.

## Next

- The README
- The test list
- The fleet server docs
- How to wire an Acorn
- How to wire an Arty
- Reporting a bug
