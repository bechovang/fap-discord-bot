# FAP Discord Bot

A Discord bot that fetches and displays FPT University academic data — schedule, exams, grades, and attendance — directly in Discord using slash commands.

The bot authenticates with FAP (FPT Academic Portal) via FeID OAuth, bypasses Cloudflare Turnstile using Camoufox (Firefox-based anti-detect browser), and keeps the browser session alive for on-demand data fetching.

---

## Features

- **Schedule** — View today's classes or the full weekly schedule
- **Exams** — Check exam schedule and upcoming exams
- **Grades** — Browse grades by term, view cumulative GPA
- **Attendance** — Track attendance by course and term
- **Auto-refresh** — Session automatically refreshes when expired
- **Background jobs** — Attendance monitoring (15 min), weekly change reports (Sun 22:00), session keepalive (4h)
- **Cloudflare bypass** — Camoufox with Turnstile checkbox click + persistent Firefox profile

---

## Commands

| Command | Description |
|---|---|
| `/schedule today` | Today's class schedule |
| `/schedule week [week] [year]` | Weekly schedule |
| `/exam schedule` | Full exam schedule |
| `/exam upcoming` | Upcoming exams |
| `/grade view` | Interactive grade browser |
| `/grade this-term` | Current term grades |
| `/grade gpa` | Cumulative GPA calculation |
| `/attendance view` | Interactive attendance browser |
| `/attendance this-term` | Current term attendance |
| `/status` | Bot health and session info |
| `/ping` | Connectivity check |
| `/config channel` | Set notification channel |
| `/config status` | Show current config |

---

## Architecture

```
Discord Slash Command
  -> bot/commands/*.py          (Discord UI layer)
  -> scraper/auth.py            (FAPAuth adapter with auto-refresh)
  -> scraper/auto_login_feid.py (Camoufox browser: login + fetch)
  -> FAP portal HTML
  -> scraper/*_parser.py        (HTML parsers)
  -> Discord response
```

### Key Components

| File | Role |
|---|---|
| `bot/bot.py` | Discord client setup, command loading, scheduler startup |
| `bot/commands/` | Slash command implementations |
| `bot/scheduler.py` | Background jobs (attendance, weekly report, keepalive) |
| `scraper/auth.py` | `FAPAuth` adapter — wraps fetch + auto-refresh with retry |
| `scraper/auto_login_feid.py` | `FAPAutoLogin` — Camoufox browser automation for login and page fetching |
| `scraper/session_validator.py` | `SessionValidator` — session health check and refresh |
| `scraper/parser.py` | Schedule HTML parser |
| `scraper/exam_parser.py` | Exam schedule parser |
| `scraper/grade_parser.py` | Grade parser with GPA calculation |
| `scraper/attendance_parser.py` | Attendance parser |
| `scraper/cloudflare.py` | Turnstile helper utilities |

### Authentication Flow

```
1. Launch Camoufox (Firefox anti-detect) with persistent profile + proxy
2. Navigate to FAP -> Cloudflare Turnstile challenge
3. Find and click Turnstile checkbox inside challenges.cloudflare.com iframe
4. Select campus -> Click "Login With FeID" button
5. Fill FeID login form (username + password) -> Submit
6. Wait for OAuth redirect back to FAP
7. Keep browser open for subsequent page fetches
8. Cookies exported to data/fap_cookies.json as backup
```

### Why Keep the Browser Open?

Cloudflare `cf_clearance` cookies are validated against:
- **IP address** — must match the proxy IP used during challenge
- **TLS fingerprint (JA3/JA4)** — must match the browser that solved the challenge
- **User-Agent** — must match exactly

No Python HTTP client (aiohttp, requests, curl_cffi) can replicate the exact TLS fingerprint of a real Firefox browser. The only reliable way to fetch pages from a Cloudflare-protected site is to use the browser itself. So after login, the browser stays open and `page.goto()` + `page.content()` are used for all data fetching.

---

## Deployment

### Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/bechovang/fap-discord-bot.git
cd fap-discord-bot

# Create .env from template
cp .env.example .env
# Edit .env with your credentials

# Build and run
docker compose up -d bot
```

The Dockerfile handles everything:
- Python 3.11-slim base
- Firefox dependencies + Xvfb virtual display
- Camoufox browser binary download
- Auto-start Xvfb + bot on container launch

### Manual Setup

```bash
pip install -r requirements.txt
python -m camoufox fetch          # Download Firefox binary
python fap-discord-bot/main.py
```

---

## Configuration

Create a `.env` file (see `.env.example`):

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
FAP_USERNAME=your_feid_email
FAP_PASSWORD=your_password

# Recommended
FAP_CAMPUS=4                              # Campus ID (default: 4)
HEADLESS=false                            # false = Xvfb virtual display
PROXY_URL=http://user:pass@host:port      # Residential proxy (required for datacenter IPs)

# Optional
FAP_STUDENT_ID=SE123456                   # Required for grade/attendance commands
SCHEDULER_TIMEZONE=Asia/Ho_Chi_Minh       # Scheduler timezone
DEFAULT_CHANNEL_ID=123456789              # Default notification channel
LOG_LEVEL=INFO
```

### Important: Password Escaping in Docker

If your password contains `$` (e.g., `Eg8$Fw1$`), Docker Compose interprets `$` as variable substitution. Escape it as `$$`:

```env
FAP_PASSWORD=Eg8$$Fw1$$
```

### Proxy Requirements

A **residential proxy** is required when running on datacenter IPs (DigitalOcean, AWS, etc.). Cloudflare Turnstile checks IP reputation and silently fails on datacenter IPs, regardless of browser fingerprinting.

Recommended: rotating residential proxies from providers like Webshare, Bright Data, or Oxylabs.

---

## Project Structure

```
fap-discord-bot/
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container build
├── docker-compose.yml          # Docker Compose config
├── .env.example                # Environment template
│
├── bot/
│   ├── bot.py                  # Discord client + startup
│   ├── scheduler.py            # Background jobs
│   ├── notifier.py             # Discord notification helper
│   ├── progress.py             # Progress tracking for long ops
│   └── commands/
│       ├── schedule.py         # /schedule today, /schedule week
│       ├── exam.py             # /exam schedule, /exam upcoming
│       ├── grade.py            # /grade view, /grade this-term, /grade gpa
│       ├── attendance.py       # /attendance view, /attendance this-term
│       ├── status.py           # /status, /ping
│       └── config.py           # /config channel, /config status
│
├── scraper/
│   ├── auth.py                 # FAPAuth adapter (auto-refresh + retry)
│   ├── auto_login_feid.py      # Camoufox browser automation
│   ├── session_validator.py    # Session health check + refresh
│   ├── cloudflare.py           # Turnstile utilities
│   ├── parser.py               # Schedule parser
│   ├── exam_parser.py          # Exam parser
│   ├── grade_parser.py         # Grade parser + GPA
│   ├── attendance_parser.py    # Attendance parser
│   └── fap_scraper.py          # Legacy scraper interface
│
└── data/                       # Runtime data (cookies, snapshots, DB)
```

---

## Background Jobs

The scheduler runs 3 jobs automatically:

| Job | Interval | Description |
|---|---|---|
| **Attendance Check** | Every 15 min | Monitors current slot for attendance status changes, sends Discord alerts |
| **Weekly Check** | Sunday 22:00 | Compares grades/schedule/exams with previous week, notifies changes |
| **Session Keepalive** | Every 4 hours | Validates session freshness, triggers re-login if expired |

---

## Lessons Learned

### 1. Cloudflare Turnstile is Not a Simple JS Challenge

Turnstile checks multiple signals beyond `navigator.webdriver`:
- **IP reputation** — datacenter IPs cause silent failure (no error, just never resolves)
- **TLS fingerprint (JA3/JA4)** — each TLS client has a unique fingerprint
- **Browser fingerprint** — WebGL, canvas, fonts, screen resolution
- **Mouse movement history** — human-like interaction patterns

**Lesson**: No headless browser trick alone can bypass Turnstile on a datacenter IP. You need residential proxies + anti-detect browser.

### 2. `cf_clearance` Cookies Are Browser-Bound

We tried extracting cookies from the browser and using them with `aiohttp` and `curl_cffi`. Both failed with 403 because:
- Cloudflare validates cookies against the TLS fingerprint of the client
- aiohttp's TLS fingerprint looks nothing like Firefox
- Even `curl_cffi` with `impersonate="firefox"` doesn't perfectly match Camoufox's TLS

**Lesson**: For Cloudflare-protected sites, the browser that solves the challenge must also be the one making subsequent requests. Keep the browser open and use `page.goto()` for fetching.

### 3. Password Escaping in Docker Compose

Password `Eg8$Fw1$` was silently mangled by Docker Compose's variable substitution (`$F` and trailing `$` eaten). This caused FeID to reject login with "incorrect username or password".

**Lesson**: In `.env` files used by Docker Compose, always escape `$` as `$$` for passwords containing dollar signs.

### 4. Vietnamese Cloudflare Titles

The Cloudflare challenge page title was `"Chờ một chút..."` (Vietnamese for "Just a moment..."). Our code only checked for English keywords `"moment"` and `"challenge"`, so it thought the page was loaded and tried to interact too early.

**Lesson**: Always check for localized Cloudflare titles, or better yet, wait for actual page content (login button, schedule dropdown) instead of checking what the title is NOT.

### 5. Profile Lock Conflicts

Running two Camoufox instances with the same persistent profile causes lock conflicts — the second instance hangs waiting for the profile, then times out after 180 seconds.

This happened because `FAPAuth` and `SessionValidator` each created their own `FAPAutoLogin` instance. The first browser (from login) stayed open, but the second browser (from session refresh) couldn't acquire the profile lock.

**Lesson**: Share a single browser instance across login and fetch operations. Close the old browser before launching a new one.

### 6. The FlareSolverr -> patchright -> Camoufox Journey

- **FlareSolverr**: First attempt. Used a separate service to solve Cloudflare, then `requests` for login. Failed because FlareSolverr couldn't handle the OAuth redirect chain (PKCE mismatch).
- **patchright** (Chromium): Second attempt. Successfully automated the full login flow but Cloudflare Turnstile never resolved on datacenter IPs, even with `navigator.webdriver=False`.
- **Camoufox** (Firefox): Final solution. Anti-detect Firefox with residential proxy + explicit Turnstile checkbox click. Works reliably.

**Lesson**: For Cloudflare-protected sites on servers, use Firefox-based anti-detect browsers with residential proxies. Chromium-based solutions (even with anti-detection patches) are more easily fingerprinted.

### 7. Xvfb Readiness Race

Starting Xvfb and immediately launching the browser can cause a race condition — the browser tries to connect to the display before Xvfb is ready.

**Fix**: Wait for the X11 lock file before starting the application:
```bash
Xvfb :99 -screen 0 1280x720x24 & until [ -e /tmp/.X99-lock ]; do sleep 0.1; done; python main.py
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `Failed to fetch schedule: refresh retry still could not access FAP` | Session expired and re-login failed. Check logs for Turnstile or FeID errors. |
| Cloudflare challenge never resolves | Need residential proxy. Datacenter IPs are blocked by Turnstile. |
| FeID login "incorrect password" | Check password escaping in `.env` — escape `$` as `$$`. |
| `TargetClosedError` on browser launch | Firefox dependencies missing. Check Dockerfile has `libgtk-3-0 libx11-xcb1 libasound2`. |
| Browser timeout on launch | Stale profile locks. Delete `data/firefox_profile/SingletonLock` files. |
| `No space left on device` during build | Old Docker images. Run `docker system prune -af --volumes`. |
| Attendance/grades return empty | Set `FAP_STUDENT_ID` and `FAP_CAMPUS` in `.env`. |

---

## Tech Stack

| Component | Technology |
|---|---|
| Bot framework | Discord.py 2.7+ |
| Browser automation | Camoufox 0.4+ (Firefox-based anti-detect) |
| HTML parsing | BeautifulSoup4 + lxml |
| Scheduler | APScheduler 3.x |
| Data validation | Pydantic 2.x |
| Container | Docker + Docker Compose |
| Virtual display | Xvfb |

---

## License

MIT
