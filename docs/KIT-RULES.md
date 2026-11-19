# Standing rules for AI work (supervisor kit)

The project's version of the kit's `protocol/RULES.md`. These rules win over the kit.

## Owner
- The owner works from the Claude desktop app and SSH. Often busy with the hardware: act on judgement inside these rules, report briefly.

## Money
- Claude subscription only. Never add an API key, never enable extra usage. Free tiers only for other AIs, with billing off.
- Never buy parts, pay for anything or start a subscription. Suggest; the owner buys.

## Privacy
- Private: the device token, Wi-Fi details, home IP addresses, the website URL and admin details, `.env` / `secrets/` / `config.yaml`.
- Never in: git, the board, commits, tests, task receipts, any cloud AI. Tests use fictional values.
- Cloud AI allowed for: code and fictional data only.
- Grow-log photos and notes in `log/` and `runs/` are public by design but owned by the website sync: read only.

## Hardware safety
- The owner does all wiring and all commands on the Pi. Task sessions never SSH in.
- Heater default is OFF: at boot, on a crash, on a missing or out-of-range probe reading. Software limits plus the heater's own cutoff, never software alone.
- 5 V DC only. Nothing touches mains.
- Before code drives a GPIO pin, the wiring doc must say what is on that pin.

## Protected files
- `log/`, `runs/`, `data/`, `docs/device-api.md`, this file, `kit.config.json` (also in `kit.config.json` → `protectedPaths`).

## Git
- Commit with a `Co-Authored-By` line. Feature branches, PR into `main`. **Push: never without asking.**

## Accounts
- Never sign in, approve OAuth, accept terms, or handle passwords or keys for the owner. Ask.
