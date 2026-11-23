# What the Spoon Archive Hub does with this system (as of 21 Nov 2026)

The Hub (Owen's website on his PC, Projects → Hydroponic System 1) is set up and working with the real Pi. This page tells any chat working in this repo what already exists there, so it is not rebuilt here.

## What the Hub already does

- **Pulls from the Pi every 60 s** over the home network / ZeroTier: `GET /temp` and `GET /api/relay` from `timelapse-cam/live_view.py` (port 8000). It stores `water_temp_c`, `heater_on`, `auto_off_in_s` and `max_on_s`. The Pi's address is typed into the Hub, never stored in git.
- **Live tab**: live camera (the Hub proxies `GET /stream`), a ⚙ camera settings pop-up built only from the Pi's `GET /api/camera/settings` schema (so any new setting added here appears there automatically), temperature tiles and chart with hover readout, heater controls, and a table of heating sessions (rise and °C/min).
- **Heater**: the Hub only forwards Owen's On/Off (`POST /api/relay`). The heater logic stays on the Pi, which switches itself off after `max_on_s` (600 s). The Hub warns (phone push) when the probe goes missing, the heater runs 8 min without the water warming, the water is hot while heating, or the heater is on with no temperature.
- **Time-lapse**: the Hub saves a camera frame every 1–60 min (set in the Hub; default 30) and makes videos per grow run or any time range. It can send them to Owen's Telegram and delete the frames once delivery is confirmed.
- **Posts and data**: the Hub writes `log/`, `runs/`, `data/` and the README status block here (unchanged).

## Needs doing here, in this repo (Pi side)

1. **Camera restart bug: fixed (24 Nov 2026).** `Camera.start()` now does everything under its lock (the old gap let a dying process trigger a second `rpicam-vid`), stops every stray `rpicam-vid` of this user before starting, and `_pump()` ignores frames from a replaced process.
2. **Long exposures: done, manual (24 Nov 2026).** `camera_settings.py` has `shutter_ms` (0 = auto, up to 1000 ms) and `gain` (0 = auto, up to 16). The frame rate is lowered so the shutter fits one frame (1000 ms gives 1 fps). They appear in the Hub's camera pop-up by themselves. Still open: switching to night values automatically from frame brightness, and stills longer than 1 s (`rpicam-still`, needs the stream paused).
3. **Heater run length**: `max_on_s` is 600 s; the first real 10-minute run did not warm the water measurably. Raise it on the Pi once the setup is trusted (the Hub reads the new value by itself).
