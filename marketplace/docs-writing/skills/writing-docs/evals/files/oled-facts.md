# Facts gathered for the OLED page (engineer's notes, not a page)

Board: 0.96" SSD1306 OLED module, 128x64, I2C, 4-pin header labelled on the silkscreen: GND, VCC, SCL, SDA
(in that order, GND nearest the module's mounting hole). Runs at 3.3 V. I2C address 0x3C (measured with
i2cdetect on 2026-10-14 on a Raspberry Pi 4 Model B, Raspberry Pi OS Bookworm 64-bit).

Host: Raspberry Pi 4 Model B. 40-pin header: pin 1 is 3V3 (square pad, nearest the SD card end, on the
inside row). Pin 3 = GPIO 2 (SDA1), pin 5 = GPIO 3 (SCL1), pin 6 = GND. The I2C bus is off by default: enable
with `sudo raspi-config nonint do_i2c 0` (0 = enable) then reboot, or add `dtparam=i2c_arm=on` to
/boot/firmware/config.txt.

Wiring (4 female-female jumper wires, any colours; we used black/red/yellow/blue):
  module GND  -> header pin 6 (GND)
  module VCC  -> header pin 1 (3V3)   NOT pin 2 or 4 (those are 5 V and will damage the module)
  module SCL  -> header pin 5 (GPIO 3)
  module SDA  -> header pin 3 (GPIO 2)

Check: `sudo i2cdetect -y 1` prints a grid with `3c` in row 30, column c. Needs `i2c-tools`
(`sudo apt install i2c-tools`).

Test: `pip install luma.oled` then the example script from the luma.oled README
(https://github.com/rm-hull/luma.oled) shows "Hello World" on the display.

Common faults seen on the bench:
  - i2cdetect shows nothing: I2C not enabled, or SDA/SCL swapped (the two middle wires).
  - Display stays dark but i2cdetect sees 3c: VCC on a 5 V pin burned the regulator (module needs replacing),
    or the contrast is 0 in the script.
  - i2cdetect prints "Error: Could not open file /dev/i2c-1": I2C not enabled (reboot after enabling).

Photos available in photos/: oled-front.jpg (module face up, header at the bottom), oled-header.jpg (close-up
of the 4-pin header with the silkscreen readable), pi4-header-corner.jpg (the Pi 4 header with pin 1's square
pad visible), wired.jpg (the four jumpers in place, module face up). There is no photo of the i2cdetect output.

Future: we plan to support the SH1106 variant (issue #42). The old page said "five modules in the lab"; we now
have eight.

Sources: module datasheet (Solomon Systech SSD1306 rev 1.1), Raspberry Pi documentation "GPIO and the 40-pin
header", the luma.oled README.
