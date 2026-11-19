# Heating project: warm water, unattended, before 14 December

**Goal:** keep the plant's root zone warm and steady with a thermostat-controlled heater while I'm in England for about 3 weeks from **2026-12-14**. It is cold in Niigata and nobody will be here.

**Hard deadline:** 2026-12-14. A heater left running unattended has to be proven first, not hoped for.

## Plan
A Raspberry Pi reads a DS18B20 waterproof probe in a water bath around the jar and switches a 5 V USB heater through a relay. Hysteresis stops the relay chattering. The wiring is in [wiring-diagrams.md](wiring-diagrams.md), the parts in [bill-of-materials.md](bill-of-materials.md), and the planned code in [../firmware/README.md](../firmware/README.md).

## Proposed milestones (working back from the 14th, adjust freely)
| Target | Milestone | Done |
| :--- | :--- | :--- |
| 2026-11-26 | Probe reads correctly on the Pi (1-Wire enabled); temperature logged | [ ] |
| 2026-12-01 | Relay and heater tested on the bench in a bucket of water, with the Pi switching it | [ ] |
| 2026-12-05 | Thermostat script running as a service: hysteresis, max-runtime watchdog, restarts on boot | [ ] |
| 2026-12-06 | Real setup running with the plant: bath, jar, cover, heater, probe | [ ] |
| 2026-12-06 to 12-12 | **7-day soak test** in the real setup. Watch the temperature log. No manual tweaks. | [ ] |
| 2026-12-10 | Decide the fallback if the soak test is not clean (see below) | [ ] |
| 2026-12-12 | Remote access works from my phone off the home Wi-Fi (Tailscale). A camera photo arrives. | [ ] |
| 2026-12-13 | Final check: water level, heater submerged, cover on, power strip secure | [ ] |
| 2026-12-14 | Fly | [ ] |

## Failure cases to test, not assume
1. **Pi crashes or hangs while the relay is on.** What does the relay do? The heater's own cutoff is the last line of defence. Confirm what its listing actually claims and test it, because I have not verified it yet.
2. **Wi-Fi drops for hours.** The thermostat must keep working with no network.
3. **Power cut and return.** Everything should come back on its own and not stay stuck off or on.
4. **Water evaporates.** A heater out of water must shut off safely. The bath cover reduces evaporation and the bath depth rule stops floating jars.
5. **Probe falls out of the water or fails.** The script should turn the heater off on an impossible reading, not on.

## Fallback if the heater is not ready
Decide by 2026-12-10. Options: pause the run before leaving, move it somewhere warmer, or ask someone to check in. Write down which was chosen and why in the log.

## Log it
Each stage of this project gets a post on the website (type: `build`) so it lands in [../log/](../log/).
