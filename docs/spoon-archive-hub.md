# What the Spoon Archive Hub does with this system (as of 21 Nov 2026)

The Hub (Owen's website on his PC, Projects → Hydroponic System 1) is set up and working with the real Pi. This page tells any chat working in this repo what already exists there, so it is not rebuilt here.

## What the Hub already does

- **Pulls from the Pi every 60 s** over the home network / ZeroTier: `GET /temp` and `GET /api/relay` from `timelapse-cam/live_view.py` (port 8000). It stores `water_temp_c`, `heater_on`, `auto_off_in_s` and `max_on_s`. The Pi's address is typed into the Hub, never stored in git.
- **Live tab**: live camera (the Hub proxies `GET /stream`), a ⚙ camera settings pop-up built only from the Pi's `GET /api/camera/settings` schema (so any new setting added here appears there automatically), temperature tiles and chart with hover readout, heater controls, and a table of heating sessions (rise and °C/min).
- **Heater**: the Hub only forwards Owen's On/Off (`POST /api/relay`). The heater logic stays on the Pi, which switches itself off after `max_on_s` (600 s). The Hub warns (phone push) when the probe goes missing, the heater runs 8 min without the water warming, the water is hot while heating, or the heater is on with no temperature.
- **Time-lapse**: the Hub saves a camera frame every 1–60 min (set in the Hub; default 30) and makes videos per grow run or any time range. It can send them to Owen's Telegram and delete the frames once delivery is confirmed.
- **Posts and data**: the Hub writes `log/`, `runs/`, `data/` and the README status block here (unchanged).

## Needs doing here, in this repo (Pi side)

1. **Camera restart bug (important)**: in `timelapse-cam/live_view.py`, `Camera.restart()` only stops the latest `rpicam-vid`. If an older one is still running, it keeps the camera, so new settings (field of view, resolution, frame rate, flip) silently do nothing, and `_pump()` keeps publishing that old process's frames. Fix: before starting a new process, stop every running `rpicam-vid` (not just `self.proc`), and in `_pump()` only publish frames when `self.proc is proc`. Workaround until then: `sudo systemctl restart hydro-live-view` while the heater is off. The Pi copy has no git; deploy the fixed file from this repo.
2. **Long exposures (optional, for night time-lapses)**: add `shutter` (µs), `gain` and an exposure mode to `camera_settings.py`'s schema and command builder. The camera looks like a v2 (IMX219), which can expose up to about 10 s. A long-exposure still at night needs the stream paused (one camera user at a time). New schema fields show up in the Hub automatically.
3. **Heater run length**: `max_on_s` is 600 s; the first real 10-minute run did not warm the water measurably. Raise it on the Pi once the setup is trusted (the Hub reads the new value by itself).
