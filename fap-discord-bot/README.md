# FAP Discord Bot

Discord bot for viewing FPT University FAP data from Discord. The current implementation supports schedule, exams, grades, attendance, session auto-refresh, and interactive grade/attendance views.

## What Works Now

- FeID login through Playwright
- Cookie reuse and session validation
- Auto-refresh when a fetch fails because the session expired
- Weekly schedule fetching
- Exam schedule fetching
- Grade parsing and cumulative GPA calculation
- Attendance parsing with per-term and per-course browsing
- Slash commands for status and health checks
- Global async lock in `scraper/auth.py` to avoid concurrent browser fetch conflicts

## Not Fully Live Yet

- Background schedulers and automatic notifications are still design/partial implementation work
- `bot/commands/pending_checks.py` exists, but it is not loaded by `bot/bot.py`
- Application scraping support is only partial

## Project Layout

```text
fap-discord-bot/
|-- main.py
|-- README.md
|-- CHANGELOG.md
|-- .env.example
|-- bot/
|   |-- bot.py
|   `-- commands/
|-- scraper/
|-- utils/
|-- docs/
|   |-- README.md
|   |-- DEVELOPMENT.md
|   |-- ARCHITECTURE.md
|   `-- features/
`-- data/
```

## Requirements

- Python 3.11+
- Chromium installed through Playwright
- Discord bot token
- FAP credentials

Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Create `.env` from `.env.example`.

Core values used by the loaded bot:

```env
DISCORD_TOKEN=your_discord_bot_token_here
FAP_USERNAME=your_feid@fe.edu.vn
FAP_PASSWORD=your_password
HEADLESS=true
USER_AGENT=Mozilla/5.0 ...
FAP_STUDENT_ID=SE123456
FAP_CAMPUS=4
```

Notes:

- `FAP_STUDENT_ID` is required by the attendance and grade commands.
- `FAP_CAMPUS` defaults to `4` in code if not set.
- The root-level `.env.example` includes extra scheduler-related variables for future notification work.

## First Run

1. Install dependencies.
2. Create `.env`.
3. Run the initial login flow:

```bash
python scraper/auto_login_feid.py login your_feid@fe.edu.vn your_password
```

4. Start the bot:

```bash
python main.py
```

Cookies are stored under `data/`, and session refresh is handled by `scraper/session_validator.py` plus the `FAPAuth` adapter in `scraper/auth.py`.

## Slash Commands

Currently loaded in `bot/bot.py`:

```text
/schedule today
/schedule week [week] [year]
/exam schedule
/exam upcoming
/grade view
/grade this-term
/grade gpa
/attendance view
/attendance this-term
/status
/ping
```

Command behavior:

- `schedule` fetches the current or requested week and formats classes from `scraper/parser.py`.
- `exam` uses `scraper/exam_parser.py`.
- `grade` provides an interactive term/course browser and GPA summary.
- `attendance` provides an interactive term/course browser plus a dashboard-style current-term view.
- `status` and `ping` expose runtime health information.

## Runtime Architecture

The main request path is:

```text
Discord slash command
  -> bot command cog
  -> scraper.auth.FAPAuth
  -> scraper.auto_login_feid.FAPAutoLogin
  -> FAP portal HTML
  -> parser module
  -> Discord response
```

Important runtime details:

- `FAPAuth` wraps fetch operations and retries once after a session refresh.
- A shared `asyncio.Lock` in `scraper/auth.py` serializes browser-backed fetches.
- `StatusCommands` receives the shared auth instance from `bot/bot.py`.

## Troubleshooting

- `Missing DISCORD_TOKEN`: check `.env`.
- `No cookies found`: run the login flow again.
- `Failed to fetch ...`: session may be expired or FAP may be unavailable.
- Attendance or grades returning empty data: verify `FAP_STUDENT_ID` and `FAP_CAMPUS`.
- Browser/login issues: rerun `playwright install chromium` and retry the login flow in non-headless mode if needed.

## Documentation

- Docs index: `docs/README.md`
- Developer notes: `docs/DEVELOPMENT.md`
- System architecture: `docs/ARCHITECTURE.md`
- Exam feature notes: `docs/features/EXAM.md`
- Grade feature notes: `docs/features/GRADE.md`
- Historical FlareSolverr guide: `docs/archive/FLARESOLVERR.md`

## Status

The bot is usable for manual slash-command queries. Proactive scheduling and notification documents exist in the repository, but they should be treated as planning/design references unless the corresponding runtime code is wired into `bot/bot.py`.
