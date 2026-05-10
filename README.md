# FAP Discord Bot Repository

This repository currently has two documentation layers:

- `fap-discord-bot/` is the active Python application.
- `docs/`, `_bmad/`, and `_bmad-output/` contain BMAD planning, architecture, and implementation artifacts.

If you want to run or modify the bot, start here:

- App overview: `fap-discord-bot/README.md`
- App docs index: `fap-discord-bot/docs/README.md`

## Repository Layout

```text
.
|-- fap-discord-bot/         Active Discord bot code and runtime docs
|-- docs/                    Top-level planning and architecture documents
|-- _bmad/                   BMAD framework assets
|-- _bmad-output/            Generated BMAD artifacts
|-- Dockerfile               Container build for the project root workflow
|-- docker-compose.yml       Compose definition
|-- requirements.txt         Root Python dependencies
`-- .env.example             Root environment template
```

## Top-Level Docs

These files describe product intent and future design work rather than the exact current runtime behavior:

- `docs/PRD.md`
- `docs/TECH-SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEDULING-AND-NOTIFICATIONS.md`
- `docs/DEPLOYMENT.md`

Several of those planning documents discuss background scheduling and proactive notifications. As of May 10, 2026, those capabilities are still design or partial-implementation work, not the main loaded command surface in `fap-discord-bot/bot/bot.py`.

## Current Runtime Surface

The active bot currently loads these command groups:

- `/schedule today`
- `/schedule week`
- `/exam schedule`
- `/exam upcoming`
- `/grade view`
- `/grade this-term`
- `/grade gpa`
- `/attendance view`
- `/attendance this-term`
- `/status`
- `/ping`

There is also a `pending_checks.py` command module in the app, but it is not currently loaded because `fap-discord-bot/bot/bot.py` leaves it commented out due to command/refactor issues.
