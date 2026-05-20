# FAP Discord Bot

Discord bot for viewing FPT University FAP data. Supports schedule, exams, grades, and attendance with automatic session management and Cloudflare Turnstile bypass via Camoufox.

## What Works

- Camoufox-based FeID login with Cloudflare Turnstile bypass
- Browser kept open for on-demand page fetching (cf_clearance is TLS-bound)
- Cookie persistence and automatic session refresh
- Auto-refresh with retry when a fetch fails because the session expired
- Schedule, exam, grade, and attendance fetching and parsing
- Interactive grade/attendance views with Discord UI components
- Background scheduler: attendance monitoring, daily reports, session keepalive
- Discord auth notifications for every login/refresh success or failure
- Runtime proxy override via Discord slash commands
- Global async lock in `scraper/auth.py` to avoid concurrent browser conflicts
- Shared `FAPAutoLogin` instance between `FAPAuth` and `SessionValidator`

## Not Fully Live

- `bot/commands/pending_checks.py` exists but is not loaded by `bot/bot.py`
- Application scraping is only partial

## Quick Start

```bash
# Docker (recommended)
docker compose up -d bot

# Manual
pip install -r requirements.txt
python -m camoufox fetch
python main.py
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
DISCORD_TOKEN=your_token
FAP_USERNAME=your_email
FAP_PASSWORD=your_password      # Escape $ as $$ in Docker .env
FAP_CAMPUS=4
FAP_STUDENT_ID=SE123456         # Required for grades/attendance
HEADLESS=false
PROXY_URL=http://user:pass@host:port  # Required for datacenter IPs
```

## Slash Commands

```
/schedule today                  Today's classes
/schedule week [week] [year]     Weekly schedule
/exam schedule                   Exam schedule
/exam upcoming                   Upcoming exams
/grade view                      Interactive grade browser
/grade this-term                 Current term grades
/grade gpa                       Cumulative GPA
/attendance view                 Interactive attendance browser
/attendance this-term            Current term attendance
/status                          Bot health and session info
/ping                            Connectivity check
/config channel                  Set notification channel
/config status                   Show config
/config proxy                    Set runtime proxy and test re-login
/config proxy-clear              Clear runtime proxy override
```

`/config proxy` stores a runtime override in `data/runtime_config.json`. This allows fast proxy rotation from Discord without editing `.env` or SSHing into the server.

## Architecture

```
Discord command -> bot/commands/ -> scraper/auth.py (FAPAuth)
  -> scraper/auto_login_feid.py (Camoufox browser)
  -> FAP HTML -> scraper/*_parser.py -> Discord response
```

The browser stays open after login because Cloudflare cookies are TLS-fingerprint-bound. No HTTP client can reuse them. All page fetches go through `page.goto()` + `page.content()`.

## Project Layout

```
main.py              Entry point
bot/
  bot.py             Discord client + startup
  scheduler.py       Background jobs (attendance, weekly, keepalive)
  notifier.py        Discord notification helper
  commands/          Slash command cogs
scraper/
  auth.py            FAPAuth adapter with auto-refresh + retry
  auto_login_feid.py Camoufox browser automation (login + fetch)
  session_validator.py  Session health check + refresh
  cloudflare.py      Turnstile utilities
  parser.py          Schedule parser
  exam_parser.py     Exam parser
  grade_parser.py    Grade parser + GPA
  attendance_parser.py Attendance parser
  fap_scraper.py     Legacy scraper interface
data/                Runtime data (cookies, snapshots, DB)
```

## Scheduler Behavior

- Attendance check runs every 15 minutes, but only inside real class windows from the weekly schedule.
- Each class is checked from class start until 30 minutes after class end.
- All time comparisons use `datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))` to ensure correct Vietnam time, even though the Docker container runs in UTC.
- Classes are matched by weekday label (`Mon`, `Wed`, etc.) from FAP's schedule table. FAP's date numbers can be off by 1 from the real calendar, but the weekday labels are always correct.
- Daily check runs every day at 22:07 VN time and sends either detected changes or a "no changes" summary.
- The bot runs one daily check shortly after startup to warm the schedule cache and snapshot files.
- Session recovery uses exponential backoff: on repeated login failures, retries are spaced increasingly far apart instead of hammering Cloudflare.
- Login/refresh attempts also produce Discord notifications.

## Troubleshooting

- **Schedule fetch fails**: Check logs — likely Turnstile not resolving (need proxy) or FeID password wrong (escape `$` in .env)
- **Browser timeout**: Stale profile locks — delete `data/firefox_profile/Singleton*` files
- **Empty grades/attendance**: Set `FAP_STUDENT_ID` and `FAP_CAMPUS` in `.env`
- **Disk full**: `docker system prune -af --volumes` to clean old images
