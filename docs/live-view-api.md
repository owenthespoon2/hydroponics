# Live view API (`firmware/timelapse-cam/live_view.py`)

Home LAN only: binds 0.0.0.0 with no login. Default port 8000.

## Endpoints

### `GET /`
The page (`web/index.html`), `text/html`.

### `GET /stream`
MJPEG, `multipart/x-mixed-replace; boundary=frame`, one JPEG per part. Use as an `<img src>`.

### `GET /temp`
```json
{"probes": {"28-000000d3a8fa": 15.12, "28-000000000002": null}}
```
`null` = no valid reading.

### `GET /api/readings?since=<ISO time>&limit=<n>`
The local reading log (`reading_log.py`). A background thread samples the probes and relay 1 once a minute into `readings.db` (next to `live_view.py`, not in git) and keeps 7 days, oldest dropped first. The Hub calls this when it comes back after Owen's PC was off and stores what it missed.

`since` (optional): ISO 8601 with an offset (`Z` allowed; encode `+` as `%2B`). Only samples strictly after it are returned, oldest first. `limit`: 1–1000 (default 1000).
```json
{"samples": [{"ts": "2026-11-19T10:34:00+00:00", "probes": {"28-000000000001": 21.4}, "heater_on": false}],
 "more": false, "oldest": "2026-11-12T10:35:00+00:00", "keep_days": 7}
```
`ts` is whole seconds, UTC, and identifies the sample (asking twice returns the same `ts`). `heater_on` is left out when the relay state was unknown. `more: true` means ask again with `since` = the last `ts`. Bad `since` gives `400`; `503` if the log could not be opened.

### `GET /api/camera/settings`
```json
{"schema": [{"key": "fov", "label": "Field of view", "type": "choice",
             "choices": ["full", "crop"], "default": "full"}],
 "values": {"fov": "full", "framerate": 15, "hflip": false}}
```
`type` is `choice`, `int`, `float` or `bool`; numbers carry `min`, `max`, `step`.

### `POST /api/camera/settings`
Request: any partial of the values.
```json
{"framerate": 10, "hflip": true}
```
Success `200`, and the stream restarts with the new settings:
```json
{"values": {"fov": "full", "framerate": 10, "hflip": true}}
```
Bad key or value `400`:
```json
{"error": "framerate: must be between 1 and 30"}
```

### `POST /api/device/shutdown` and `POST /api/device/reboot`
Request body must be exactly confirmed:
```json
{"confirm": true}
```
Reply `202` (sent before the action runs, about 1 s later; the camera is stopped first):
```json
{"status": "shutting_down"}
```
or `{"status": "rebooting"}`. A missing or false `confirm` gives `400 {"error": "..."}`.
`GET` on these paths gives `405`. Only the two fixed commands in `device_actions.py` can run.

### `GET /api/relay`
Relay 1 status (default GPIO 5, active-low, driven with `pinctrl`):
```json
{"on": true, "auto_off_in_s": 540, "pin": 5, "active_low": true, "max_on_s": 600}
```
`auto_off_in_s` is `null` when the relay is off.

### `POST /api/relay`
Request:
```json
{"on": true}
```
Success `200` with the status object above. A body that is not `{"on": true|false}` gives `400 {"error": "..."}`. If `pinctrl` fails: `500 {"error": "..."}` and the relay is reported as off.

Safety: the relay is switched off at start, on exit (normal, Ctrl+C, SIGTERM), before a reboot or shutdown, and by itself after `--relay-max-on` seconds (default 600). Options: `--relay-pin`, `--relay-active-high`, `--relay-max-on`.
On the website this maps to `heating_enable` / `heating_disable` in `docs/device-api.md` (that file is not edited here).

## Porting to another website

* The page is `web/index.html` plus the `API_BASE` constant at the top of its script. Every fetch and the stream URL use it, so point it at another origin (or a proxy) to move the page.
* The settings form is built from `SCHEMA` (via `GET /api/camera/settings`); no setting names are hard-coded in the page. Adding a setting to `camera_settings.SCHEMA` adds it to the form.
* On the public website the Pi connects out only (see `docs/device-api.md`); the website cannot call these HTTP endpoints. The controls therefore become device commands the Pi picks up.

Proposed device commands (**PROPOSED**; the owner must add them to `docs/device-api.md` first, this project does not edit that file):

| Command | Args |
|---|---|
| `set_camera_settings` | a settings partial, same shape as the `POST /api/camera/settings` body |
| `device_reboot` | none |
| `device_shutdown` | none |

The Pi side would validate with `camera_settings.validate` and run `device_actions.run_action`, the same code the HTTP routes use.
