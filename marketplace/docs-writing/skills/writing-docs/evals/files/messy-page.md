# Relay HAT

The relay HAT is a 4-channel relay board that sits on the Raspberry Pi's 40-pin header. It is currently used on
five of our Pi 4 hosts and three Pi 5 hosts to switch the bench lamps and the fan. We have 9 of them in the lab.

![relay HAT](relay-hat.png) ![relay HAT (dark)](relay-hat-dark.png)

The HAT has 4 relays (K1 to K4), each driven by a GPIO through a ULN2003 driver. The relays are rated 10 A at
250 V AC. Each relay has a screw terminal block with COM, NO and NC. The HAT is powered from the Pi's 5 V rail
so you don't need a separate supply (Sources: the vendor wiki page, our measurement of 85 mA with all four
relays on, 2026-09-30).

## GPIO mapping

K1 is on GPIO 26, K2 on GPIO 20, K3 on GPIO 21 and K4 on GPIO 19. Note that these are the BCM numbers, not the
header pin numbers (pins 37, 38, 40 and 35 respectively). The relays are active-high. On the old revision 1.0
boards the mapping was different (K1 was on GPIO 4); we don't have any of those any more I think.

## Setting it up

First you just need to simply seat the HAT on the header. Make sure it's the right way round (the terminal
blocks should point away from the Pi's USB ports). Then install the packages: `sudo apt install python3-gpiozero`
and `pip install relayhat` (our package, see the repo). Then run `relayhat test` which clicks each relay in
turn; you should hear four clicks. If you don't hear clicks check the HAT is seated properly, and please note
that the HAT won't work on a Pi 5 without the `lgpio` backend (TODO: document how to install it). In order to
switch a relay from Python, use `RelayHAT().set(1, True)`.

For the screw terminals, you will need a 2.5 mm flat screwdriver, 18 AWG wire, ferrules (optional but
recommended), and the load's cable. Strip 7 mm, insert into the NO terminal and COM, tighten to 0.5 Nm.

## Future: Pi 5 support

We are working on native Pi 5 support (the gpiozero backend currently throws on a Pi 5, see issue #17). Coming
soon. Also planned: a web page to click relays.

## Where the facts come from

- Vendor wiki: https://example.com/relay-hat/wiki (the pin mapping, the relay ratings)
- Our measurement log, 2026-09-30: current draw
- The ULN2003 datasheet (TI, SLRS027)

## Troubleshooting

If a relay clicks but the load doesn't switch, the wire is probably in NC instead of NO. If nothing clicks at
all, the HAT might not be seated, or you may be on a Pi 5 (see above). If the Pi reboots when a relay switches,
the 5 V supply is probably too weak; use a 3 A supply.
