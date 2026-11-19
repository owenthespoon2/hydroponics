# Device API: the contract between the Pi and my website

The Pi sends data to my website and picks up a few allowed commands. This file is the contract. The website and the Pi agent are both built against it, so change this file first and the code second.

**Status:** draft v1. Nothing is built yet. The website builds the server side and a fake-device simulator first, so it can be tested before the Pi exists.

## Principles
1. **The Pi connects out. Nothing connects in.** The Pi makes outbound HTTPS requests to the website. No ports are opened on my home router. This works behind any home network.
2. **Safety lives on the device, never on the website.** The heater control loop and its hard limits run on the device (see [heating-project.md](heating-project.md)). The website can ask for changes inside safe bounds. It can never override a limit. If the website, the network, or the Pi's agent fails, the heater keeps behaving safely on its own.
3. **No free-form shell.** The website never sends arbitrary commands. Only the allow-list below.
4. **Offline is normal.** The Pi buffers data when the network is down and sends it later. Re-sent data must not create duplicates.
5. **Additive changes only** within a version. Unknown fields are ignored, never rejected.

## Base and auth
- Base URL: `https://<my-site>/api/hydroponics/device/v1`
- Header: `Authorization: Bearer <device-token>`
- One token per device, stored only on the device (an environment file that is not in git). The server stores only a hash. A token can be revoked without affecting anything else.
- HTTPS only. Reject plain HTTP.
- Timestamps: ISO 8601 with an offset, e.g. `2026-11-19T19:30:00+09:00`. The site displays in Asia/Tokyo.

## `POST /readings`: sensor data
The Pi samples about once a minute and sends a batch about every 5 minutes. Buffer up to 7 days offline.

```json
{
  "schema_version": 1,
  "device_id": "hydro-pi",
  "sent_at": "2026-11-19T19:35:00+09:00",
  "samples": [
    {
      "ts": "2026-11-19T19:34:00+09:00",
      "water_temp_c": 21.4,
      "water_temp_2_c": 21.6,
      "heater_on": true,
      "setpoint_c": 22.0,
      "controller_ok": true,
      "pi_cpu_temp_c": 48.2
    }
  ]
}
```
- Every field except `ts` is optional. A missing field means "not measured", never zero.
- `water_temp_c` is the control probe. `water_temp_2_c` is the independent monitoring probe.
- A sample is identified by `(device_id, ts)`. Sending the same sample twice is a no-op, not an error.
- Response: `200 {"accepted": N, "duplicates": M}`.

## `POST /events`: things worth noticing
```json
{ "device_id": "hydro-pi", "ts": "2026-11-19T19:40:00+09:00",
  "level": "warning", "code": "probe_missing", "message": "Control probe returned no reading for 5 minutes" }
```
- `level`: `info` | `warning` | `critical`.
- Suggested codes: `boot`, `probe_missing`, `probe_disagree`, `over_temp`, `under_temp`, `heater_stuck_on`, `controller_reset`, `power_restored`, `camera_error`.

## `POST /photos`: camera
`multipart/form-data` with fields `file` (JPEG), `ts`, `kind` (`timelapse` | `daily` | `on_demand`), `camera_id`.
- Max 5 MB. The device resizes before sending (long edge 1600 px).
- Response: `200 {"id": "...", "url": "..."}`.

## `GET /commands/next`: allowed commands
The Pi polls about every 30 seconds. The server returns the oldest pending command, or `204` if none.

```json
{ "id": "cmd_01H...", "issued_at": "2026-11-19T19:50:00+09:00", "expires_at": "2026-11-19T20:00:00+09:00",
  "command": "set_setpoint", "args": { "value_c": 22.5 } }
```
The Pi then reports the outcome with `POST /commands/{id}/result` (`{"status": "done" | "rejected" | "failed", "detail": "..."}`).

### The complete allow-list (v1)
| Command | Args | Rule |
| :--- | :--- | :--- |
| `capture_photo` | none | Take a photo now and upload it. |
| `set_setpoint` | `value_c` | The device clamps to its own limits (default 18.0 to 26.0 °C) and rejects values outside them. |
| `heating_disable` | none | Turn the heater off and hold it off. Always allowed. |
| `heating_enable` | none | Allowed only if the device's own checks pass. The device may reject it. |
| `report_status` | none | Send a full status snapshot as an event. |
| `send_logs` | `lines` (max 200) | Send the last lines of the agent log as an event. |

- Commands expire (default 10 minutes). The device ignores expired commands and never replays them.
- A command is acted on once. The `id` is idempotent.
- Anything not on this list is rejected by both the server and the device.

## Alerts (the website's job)
While I'm away, the website should tell me when something is wrong:
- no data from the device for **30 minutes**
- `water_temp_c` above **28 °C** or below **15 °C**
- any `critical` event
- the two probes disagreeing by more than **3 °C** for 10 minutes

## Data kept
- **Website database:** every sample and event, every photo.
- **GitHub (`data/`):** a daily batch of readings downsampled to 5-minute rows, committed once a day (not per reading), at `data/YYYY/YYYY-MM.csv` with columns `ts,water_temp_c,water_temp_2_c,heater_on,setpoint_c`. One chosen photo per day goes into that day's log entry. Hourly time-lapse frames stay on the website only.

## Versioning
`/v1` stays stable. A breaking change creates `/v2` and both run side by side until the Pi is updated.
