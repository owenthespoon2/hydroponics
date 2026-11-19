# Entry format and sync contract

This repo is a **mirror of posts made on my website (Spoon Archive → Projects → Hydroponic System 1)**. I never edit `log/` or `runs/` by hand. The website is the source of truth and writes here automatically.

This file is the contract between the website's sync code and this repo. If the two ever disagree, change this file and the code together.

## Who writes what

| Path | Written by | Notes |
| :--- | :--- | :--- |
| `log/**` | website sync | One folder per post. Never edit by hand. |
| `runs/**` | website sync | One file per run (a crop grown start to finish). |
| `README.md`, between `<!-- status:start -->` and `<!-- status:end -->` | website sync | Current run, day count, latest photo. Everything else in the README is hand-written. |
| `docs/`, `hardware/`, `firmware/`, `data/` | git / hand / AI-assisted | The sync must never touch these. |

Keeping these paths separate means the sync and hand edits can never conflict.

## Layout of a post

```
log/
  2026/
    2026-11-19-1558/        # YYYY-MM-DD-HHMM in Asia/Tokyo (JST)
      entry.md              # the post
      01.jpg                # photos, numbered in the order shown
      02.jpg
      files/                # optional: other attachments (CSV, PDF, STL…), small only
```

- The folder name is the post's local timestamp in JST. Two posts in the same minute get a `-2` suffix.
- Several posts on one day are fine and expected.
- The post's stable identity is `id` in the front matter, **not** the folder name. The sync looks posts up by `id`, so editing a post's date does not create a duplicate (it moves the folder).

## `entry.md`

YAML front matter, then the body in Markdown. The body is exactly what I wrote on the website.

```yaml
---
id: day0-setup                      # required. Stable ID from the website. Never changes.
date: 2026-11-19T15:58:00+09:00     # required. ISO 8601 with offset. JST.
run: 2026-11-tomato-01              # optional. ID of the run this belongs to.
type: update                        # update | build | note | harvest | problem
title: Day 0, setting up            # optional
day: 0                              # optional. Days since the run's start_date. Computed by the sync.
tags: [setup, tomato, kratky]       # optional
measurements:                       # optional. Include only what I actually entered.
  water_temp_c: 21.5
  air_temp_c: 18.0
  water_level: "sponge base just touching"
  nutrient_added: "2 ml A + 2 ml B per L"
photos:                             # optional. In display order.
  - file: 01.jpg
    caption: What the photo shows
source: spoon-archive
---

Body text in Markdown. Images are referenced with relative paths: ![alt](01.jpg)
```

Rules:
- Only write fields that have a value. No empty placeholders.
- Never invent a measurement. If I didn't enter water temperature, the field is absent.
- `day` is computed from the run's `start_date`, with the start date as day 0.

## `runs/<run-id>.md`

One file per run, named after the run's `id`. Front matter holds the facts, the body holds free-form notes.

```yaml
---
id: 2026-11-tomato-01
title: Run 1, Premium Ruby tomato
crop: tomato
variety: Premium Ruby (プレミアムルビー), F1 cherry tomato, Kaneko Seeds
start_date: 2026-11-19
end_date:                  # empty while active
status: active             # active | finished | failed | paused
system: kratky-jar-1.3L
container_litres: 1.3
---
```

The starter file already in `runs/` follows this format. When the sync takes over, it matches on `id` and updates in place.

## Photos

Applied by the sync before committing:
- Convert HEIC/PNG to JPEG.
- Auto-rotate from EXIF orientation, then **strip all EXIF** (this removes GPS location and device data).
- Resize so the long edge is at most 1600 px. JPEG quality about 82.
- Target under 500 KB per photo. Hard limit 5 MB.

`.gitignore` deliberately does not ignore images.

## Commits

- One commit per post (text and photos together).
- Message: `log: 2026-11-19 Day 0, setting up`. Edits: `log (edit): …`. Deletes: `log (delete): …`.
- Delete removes the post's folder. Git history keeps the old version.

## Time

All dates are Asia/Tokyo. Store the offset (`+09:00`) so entries stay correct if I'm in England.

## Not built yet (reserved)

- `data/`: sensor readings from the Raspberry Pi (water temperature, heater on/off), likely one CSV per month. Not part of the website sync for now.
- `firmware/`: code for the Pi thermostat, camera, and later ESP32 nodes.
