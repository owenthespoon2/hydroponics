# HYDROPONICS — ACTIVE BOARD (MAX 60 LINES)

## RULES (details in CLAUDE.md and docs/KIT-RULES.md)
- Code runs on the Pi 4 (Raspberry Pi OS, Python 3.13, aarch64). Standard library only unless the task says otherwise. Task sessions run on Windows and never touch the Pi: test against a fake sysfs folder.
- One test file: `python -m pytest <file> -q`. No other check command yet.
- Never commit tokens, Wi-Fi details, IP addresses or hostnames other than `hydro-pi`.

## ACTIVE QUEUE (one task per session)
- [ ] **T1:** [model:sonnet] [effort:low] DS18B20 reader + test CLI. New `firmware/pi-thermostat/ds18b20.py`: `find_probes(base="/sys/bus/w1/devices")` returns probe ids (folders starting `28-`); `read_c(probe_id, base=...)` reads `<base>/<id>/temperature` (millidegrees, int) and falls back to `w1_slave` (needs `YES` on line 1, value after `t=` on line 2); returns float °C or `None` on missing file, bad CRC, or the power-on value 85000. Discard readings outside -10..60 °C as `None`. New `firmware/pi-thermostat/read_temp.py`: prints `<probe id>  <°C to 2 dp>` for every probe every `--interval` seconds (default 2), `--once` prints one round and exits, exit code 1 with a clear message if no probes are found. New `firmware/pi-thermostat/tests/test_ds18b20.py` using `tmp_path` fake folders (both file formats, CRC NO, 85000, missing probe, out of range). Add a 5-line usage section to `firmware/README.md`. Done when `python -m pytest firmware/pi-thermostat/tests/test_ds18b20.py -q` passes.

## WAITING ON HARDWARE (supervisor moves these up)
- DONE 2026-11-19: probe wired (GPIO 4, adapter board), `28-000000d3a8fa` reads ~15 °C on the Pi. SSH key login works for the supervisor.
- Camera test, then relay bench test (active-low or high?) before any thermostat code.

## Known failures (not yours)
- none
