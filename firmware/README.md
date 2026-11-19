# 💻 Firmware & Automation Scripts

This directory houses software modules for **Phase 2 (Raspberry Pi)** and **Phase 3 (ESP32)** automation.

## Reading the probe (`pi-thermostat/`)
* `python3 read_temp.py` prints `<probe id>  <°C>` every 2 s (Ctrl+C to stop).
* `--once` prints one round and exits; `--interval N` changes the delay.
* Exit code 1 if no `28-*` probe is found (check wiring / 1-Wire overlay).
* A bad CRC, the 85 °C power-on value or a reading outside -10..60 °C shows `no reading`.
* Tests (any machine): `python -m pytest firmware/pi-thermostat/tests/test_ds18b20.py -q`

## Live camera view (`timelapse-cam/`)
* On the Pi: `python3 live_view.py` (`--port N`, default 8000). Needs `rpicam-vid`; no installs.
* On the PC open `http://hydro-pi.local:8000` (stream plus probe reading, refreshed every 5 s).
* Home LAN only: binds 0.0.0.0 with no login. Ctrl+C stops it and the camera.
* Tests (any machine): `python -m pytest firmware/timelapse-cam/tests/test_live_view.py -q`

## Planned Modules

### 1. `pi-thermostat/`
* Python daemon reading `/sys/bus/w1/devices/28-*/w1_slave` (DS18B20 1-Wire interface).
* Controls the relay on `GPIO 5` (pin 29, active-low) with hysteresis (`ON <= 20.0°C`, `OFF >= 24.0°C`) and failsafe max-runtime watchdog.
* Exposes a lightweight Flask / Node-RED web endpoint over **Tailscale** for remote monitoring and manual override.

### 2. `timelapse-cam/`
* `cron`-scheduled `rpicam-still` capture every 60 minutes during the 12-hour grow-light window.
* Automatic daily stitching into an MP4 growth time-lapse via `ffmpeg`.

### 3. `esp32-nodes/`
* Future wireless MQTT / HTTP sensor nodes for multi-reservoir EC/pH monitoring and automated top-up pumps in Phase 3.
