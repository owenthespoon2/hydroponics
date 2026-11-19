# Hydroponics

Physical hydroponics project: a grow log (`log/`, `runs/`) plus a Raspberry Pi 4 (`hydro-pi`) rig with DS18B20 water probes, a Pi camera and a relay-switched 5 V heater. Hardware docs in `docs/` (start with `docs/pi-setup.md`, `docs/wiring-diagrams.md`, `docs/heating-project.md`). Pi code goes in `firmware/`.

Work is run with the AI supervisor kit (`C:\Projects\ai-supervisor-kit`): an Opus supervisor plans and checks; Sonnet task sessions do one board task each. Standing rules: [docs/KIT-RULES.md](docs/KIT-RULES.md).

## Lean routing (token budget first)

1. One `[ ]` task per session from `BOARD.md`: mark `[x]`, commit only task files + board, stop.
2. If the task names files, read them directly (whole functions, one call). Use the `scout` subagent only when files are unknown. Never grep the whole repo yourself.
3. Fewer, bigger turns: batch independent reads in one message, combine shell steps, never read the same file twice.
4. Edit only with Edit/Write (never sed/perl/heredoc).
5. Tests via the `tester` subagent. One test file: `python -m pytest <file> -q`. Never run bare `pytest` from the repo root.
6. Never background-and-wait on long jobs: leave them to the supervisor and say so in the receipt.
7. After 3 failed attempts: revert task files, mark `[!]` with one line why, stop.

## Guardrails

- Task sessions never SSH to the Pi or run anything on it. The owner deploys and tests on the Pi by hand.
- Safety: the heater must be OFF at boot, on a crash and when a probe reading is missing. Never write code that can leave it on without a reading. Nothing in this build touches mains voltage.
- Private data: never put device tokens, Wi-Fi details, IP addresses, the website URL or personal details in code, tests, commits or the board. Fictional values only.
- Protected files (never modify or stage): `log/`, `runs/`, `data/` (website sync owns them), `docs/device-api.md` (contract, owner changes it first), `docs/KIT-RULES.md`, `kit.config.json`.
- Money: Claude subscription only. Never add API keys or enable paid usage. Never buy parts.
- Docs: after each finished build step, add a dated entry with photos to `docs/build-journal.md` and replace the `<!-- build:start -->` block in `README.md` with that step (one photo, two sentences). Never edit the `status:` block (the website sync owns it).
- Git: commit with a `Co-Authored-By` line. Never push without the owner saying so.
