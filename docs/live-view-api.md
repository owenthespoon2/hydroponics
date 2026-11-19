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
