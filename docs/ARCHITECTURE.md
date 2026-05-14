# Architecture Specification
## FAP Discord Bot - System Design Document

**Version:** 2.0
**Date:** 2026-05-14
**Document Status:** Updated

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [System Architecture](#system-architecture)
4. [Component Design](#component-design)
5. [Data Architecture](#data-architecture)
6. [Security Architecture](#security-architecture)
7. [Integration Architecture](#integration-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Technology Stack](#technology-stack)
10. [Design Decisions](#design-decisions)
11. [Lessons Learned](#lessons-learned)

---

## System Overview

### Purpose

FAP Discord Bot is a **proactive monitoring and notification system** that tracks FPT University students' academic information through the FAP portal and delivers timely updates via Discord.

### System Context

```
Student (Discord)
    |
    | Slash Commands (/schedule, /grade, /exam, /attendance)
    v
+-------------------------------------------------------------+
|                    FAP Discord Bot                            |
|                                                               |
|  Discord Bot (discord.py)                                    |
|    |                                                          |
|  Command Handler (bot/commands/)                             |
|    |                                                          |
|  FAPAuth Adapter (scraper/auth.py)                           |
|    |                                                          |
|  FAPAutoLogin (scraper/auto_login_feid.py)                   |
|    |                                                          |
|  Camoufox Browser (Firefox anti-detect)                      |
|    |                                                          |
+-------------------------------------------------------------+
    |                              |
    v                              v
FAP Portal                    Discord API
(fap.fpt.edu.vn)             (discord.com)
    |
    +-- Cloudflare Turnstile
    +-- FeID SSO (identity.fpt.edu.vn)
```

### Key Design Decision: Browser as HTTP Client

Cloudflare's `cf_clearance` cookie is cryptographically tied to the browser's TLS fingerprint (JA3/JA4). No Python HTTP client can reproduce this fingerprint. Therefore, the browser that solves the Cloudflare challenge must also make all subsequent requests. The browser stays open after login and all data fetching uses `page.goto()` + `page.content()`.

---

## Architecture Principles

### AP-1: Simplicity First
- SQLite over PostgreSQL, single container over microservices
- One browser instance handles login AND data fetching

### AP-2: Fail Gracefully
- Auto-refresh expired sessions via Camoufox re-login
- Return cached data when FAP is unavailable
- Diagnostic system for user-facing error messages

### AP-3: Defense in Depth for Session Management
- 4-layer session expiry detection in `_fetch_page()`
- Auto-refresh with lock to prevent concurrent re-logins
- Cookie backup file for diagnostic purposes

---

## System Architecture

### High-Level Architecture

```
+-------------------------------------------------------------+
|                    PRESENTATION LAYER                         |
|  bot/bot.py — Discord client, event handlers                |
|  bot/commands/ — Slash command implementations               |
|  bot/notifier.py — Discord notification formatting           |
+-------------------------------------------------------------+
                          |
                          v
+-------------------------------------------------------------+
|                    APPLICATION LAYER                          |
|  bot/scheduler.py — Background jobs (APScheduler)            |
|  scraper/auth.py — FAPAuth adapter (auto-refresh + retry)    |
+-------------------------------------------------------------+
                          |
                          v
+-------------------------------------------------------------+
|                    INFRASTRUCTURE LAYER                       |
|  scraper/auto_login_feid.py — Camoufox browser automation    |
|  scraper/session_validator.py — Session health check          |
|  scraper/cloudflare.py — Turnstile utilities                 |
|  scraper/*_parser.py — HTML parsers (BeautifulSoup)          |
+-------------------------------------------------------------+
                          |
                          v
+-------------------------------------------------------------+
|                    EXTERNAL SYSTEMS                           |
|  Camoufox (Firefox anti-detect browser)                      |
|  FAP Portal (fap.fpt.edu.vn)                                |
|  FeID SSO (identity.fpt.edu.vn / feid.fpt.edu.vn)           |
|  Discord API (discord.com)                                   |
+-------------------------------------------------------------+
```

### Request Flow

```
1. User types /schedule today in Discord
2. Discord Bot receives interaction
3. Command handler calls auth.fetch_schedule()
4. FAPAuth calls _auth.fetch_schedule() on FAPAutoLogin
5. FAPAutoLogin calls _fetch_page(url) using open browser
6. Browser navigates to FAP schedule page
7. _fetch_page() validates response (4 checks for session expiry)
8. If valid: returns HTML to parser -> formatted Discord response
9. If expired (returns None): FAPAuth triggers _refresh_session_once()
10. SessionValidator refreshes via new Camoufox login
11. Retry fetch with new session
```

### Session Expiry Detection (4 Layers)

```python
# In _fetch_page():
# Check 1: Redirected to Default.aspx (FAP landing/login page)
if 'Default.aspx' in final_url and 'Default.aspx' not in url:
    return None

# Check 2: URL contains "Login" (but not ScheduleOfWeek)
if "Login" in final_url and "ScheduleOfWeek" not in final_url:
    return None

# Check 3: Page content has FeID login button
if 'btnloginFeId' in content:
    return None

# Check 4: Still on Cloudflare challenge page
cf_keywords = ("just a moment", "checking your browser", ...)
if any(kw in title.lower() for kw in cf_keywords):
    return None
```

When `_fetch_page()` returns `None`, the FAPAuth adapter:
1. Records diagnostic (operation, status, code, detail)
2. Calls `_refresh_session_once()` with asyncio lock
3. SessionValidator closes old browser, launches new Camoufox
4. Runs full login flow (Cloudflare -> FeID -> cookies)
5. Retries the original fetch

---

## Component Design

### C1: FAPAutoLogin (auto_login_feid.py)

**Purpose:** Camoufox-based browser automation for FAP login and page fetching.

**Responsibilities:**
- Launch Camoufox with persistent profile and proxy
- Navigate to FAP, wait for Cloudflare challenge to resolve
- Click Turnstile checkbox if needed
- Handle FeID SSO login form
- Fetch pages via browser (page.goto + page.content)
- Export cookies to JSON backup

**Key Methods:**
| Method | Description |
|--------|-------------|
| `auto_login()` | Full login flow: launch browser -> navigate -> FeID -> save cookies |
| `_launch_browser()` | Start Camoufox with profile cleanup, proxy, headless config |
| `_open_login_page()` | Navigate to FAP, wait for Cloudflare to resolve (up to 60s) |
| `_click_turnstile()` | Find and click Turnstile checkbox in challenges.cloudflare.com iframe |
| `_trigger_feid_login()` | Click "Login With FeID" button or use __doPostBack fallback |
| `_handle_feid_login()` | Fill FeID username/password form and submit |
| `_fetch_page(url)` | Fetch any FAP page with 4-layer session validation |
| `fetch_schedule()` | Fetch schedule HTML via browser |
| `fetch_exam_schedule()` | Fetch exam schedule HTML via browser |
| `fetch_attendance()` | Fetch attendance HTML via browser |
| `fetch_grades()` | Fetch grades HTML via browser |

**Browser Lifecycle:**
```
_launch_browser()
  |- Clear stale profile locks (SingletonLock, SingletonCookie, etc.)
  |- Delete entire profile directory (fresh start for each login)
  |- Set headless mode: "virtual" if HEADLESS=true, False otherwise
  |- Unset DISPLAY env var for virtual mode (avoid Xvfb conflict)
  |- Configure proxy from PROXY_URL env var
  |- Create Camoufox instance with persistent context

auto_login()
  |- _launch_browser()
  |- _open_login_page() (Cloudflare wait)
  |- Check if already logged in (_is_schedule_page)
  |- _select_campus_if_needed()
  |- _trigger_feid_login()
  |- _handle_feid_login()
  |- _persist_cookies() (JSON backup)
  |- Browser stays OPEN for subsequent fetches

_fetch_page(url) — called for each data request
  |- page.goto(url)
  |- 4 validation checks
  |- Return HTML or None
```

### C2: FAPAuth (auth.py)

**Purpose:** Authentication adapter providing auto-refresh with retry logic.

**Responsibilities:**
- Wrap FAPAutoLogin for data fetching
- Detect fetch failures and trigger session refresh
- Prevent concurrent refresh with asyncio lock
- Track diagnostics for each operation
- Format user-facing error messages

**Key Methods:**
| Method | Description |
|--------|-------------|
| `get_session()` | Ensure session is valid, refresh if needed |
| `fetch_schedule()` | Fetch schedule with auto-refresh on failure |
| `fetch_exam_schedule()` | Fetch exams with auto-refresh on failure |
| `fetch_grades()` | Fetch grades with auto-refresh on failure |
| `fetch_attendance()` | Fetch attendance with auto-refresh on failure |
| `format_last_failure()` | Convert diagnostic to user-facing error message |

**Diagnostic System:**
```python
_diagnostic = {
    "timestamp": "2026-05-14T10:30:00",
    "operation": "schedule",        # What was being fetched
    "status": "warning",            # ok, warning, error
    "code": "page_unavailable",     # Machine-readable code
    "detail": "Initial schedule fetch returned no usable HTML."
}
```

Error codes:
| Code | Meaning |
|------|---------|
| `cookies_missing` | No cookie file found |
| `session_invalid` | Cookies exist but health check failed |
| `refresh_failed` | Camoufox re-login failed |
| `refresh_retry_failed` | Re-login succeeded but fetch still fails |
| `missing_credentials` | FAP_USERNAME or FAP_PASSWORD not set |
| `page_unavailable` | FAP returned login/unexpected page |
| `session_ready` | Session is valid and ready |
| `fetch_ok` | Fetch succeeded without refresh |

### C3: SessionValidator (session_validator.py)

**Purpose:** Check session health and trigger refresh when needed.

**Methods:**
| Method | Description |
|--------|-------------|
| `is_session_valid()` | Check if cookie file exists |
| `is_session_fresh()` | Check if cookies are less than N hours old |
| `check_session_health()` | Full health check: file age or aiohttp probe |
| `refresh_session()` | Run full Camoufox auto-login to refresh session |

**Health Check Modes:**
- `fast_check=True`: Only checks file age (< 2 hours = fresh)
- `fast_check=False`: Makes actual HTTP request to FAP and checks for schedule page elements

### C4: HTML Parsers (scraper/*_parser.py)

| Parser | File | Output |
|--------|------|--------|
| Schedule Parser | `parser.py` | List of class sessions with date, slot, room, attendance |
| Grade Parser | `grade_parser.py` | Terms, subjects, grades, GPA calculation |
| Exam Parser | `exam_parser.py` | Exam schedule with date, time, room, type |
| Attendance Parser | `attendance_parser.py` | Attendance status per date/slot |

All parsers use BeautifulSoup4 with lxml backend. They return structured data (dicts/lists) that command handlers format into Discord embeds.

### C5: Discord Bot (bot/)

| Component | File | Purpose |
|-----------|------|---------|
| Bot Core | `bot.py` | Discord client, startup, command sync, scheduler init |
| Scheduler | `scheduler.py` | Background jobs via APScheduler |
| Notifier | `notifier.py` | Discord embed formatting and sending |
| Schedule Commands | `commands/schedule.py` | `/schedule today`, `/schedule week` |
| Exam Commands | `commands/exam.py` | `/exam schedule`, `/exam upcoming` |
| Grade Commands | `commands/grade.py` | `/grade view`, `/grade this-term`, `/grade gpa` |
| Attendance Commands | `commands/attendance.py` | `/attendance view`, `/attendance this-term` |
| Status Commands | `commands/status.py` | `/status`, `/ping` |
| Config Commands | `commands/config.py` | `/config channel`, `/config status` |

### C6: Background Scheduler (scheduler.py)

| Job | Interval | Description |
|-----|----------|-------------|
| Attendance Check | Every 15 min | Monitor current slot for attendance changes, alert Discord |
| Weekly Check | Sunday 22:00 | Compare grades/schedule/exams with last week, notify changes |
| Session Keepalive | Every 4 hours | Check session health, trigger re-login if expired |

---

## Data Architecture

### Storage

| Data | Location | Format | Persistence |
|------|----------|--------|-------------|
| Bot Database | `data/fap.db` | SQLite | Persistent (volume mount) |
| FAP Cookies | `data/fap_cookies.json` | JSON | Backup; browser is primary |
| Firefox Profile | `data/firefox_profile/` | Firefox profile dir | Cleared on each login |
| Logs | `logs/` | Text files | Persistent (volume mount) |

### Database Schema (SQLite)

Key tables:
- **users** — Discord user ID, FAP credentials (encrypted), notification preferences
- **schedule_cache** — Cached schedule HTML by week/year
- **attendance_state** — Attendance tracking per date/slot
- **grade_cache** — Cached grade data by term
- **exam_cache** — Cached exam schedule

---

## Security Architecture

### Password Encryption
- **Algorithm:** Fernet (AES-128-CBC with HMAC)
- **Key:** Stored in `ENCRYPTION_KEY` env var
- **Scope:** FAP passwords stored in database are encrypted

### Credential Handling
- FAP credentials read from env vars (`FAP_USERNAME`, `FAP_PASSWORD`)
- Never logged or exposed in error messages
- Cookies exported to JSON file for backup purposes only

### Environment Variables
- `.env` file is never committed to git (in `.gitignore`)
- All secrets injected via Docker Compose environment section
- Different keys for development and production

---

## Integration Architecture

### I1: FAP Portal via Camoufox

```
Bot -> Camoufox Browser -> FAP Portal

Flow:
1. Launch Camoufox (Firefox anti-detect) with:
   - Clean profile (cleared before each login)
   - Residential proxy
   - Virtual display (Xvfb or built-in)
2. Navigate to https://fap.fpt.edu.vn/Default.aspx
3. Wait for Cloudflare Turnstile challenge (up to 60 seconds)
4. Click Turnstile checkbox in challenges.cloudflare.com iframe
5. Select campus from dropdown
6. Click "Login With FeID" button
7. FeID SSO redirect -> identity.fpt.edu.vn
8. Fill username + password form
9. Submit -> OAuth redirect back to FAP
10. Browser stays open for data fetching
```

### I2: Discord API

```
Bot -> discord.py -> Discord Gateway (WebSocket)

- Slash commands registered via bot.tree.sync()
- Responses via interaction.response.send_message()
- Notifications via channel.send(embed=...)
- Rate limiting handled by discord.py internally
```

### I3: Session Management Flow

```
1. get_session() called
2. Check if cookie file exists
   |- No: trigger auto-login via Camoufox
   |- Yes: check session health
      |- Healthy: return session
      |- Expired: trigger refresh

Refresh flow:
1. Acquire asyncio lock (prevent concurrent refresh)
2. Close existing browser
3. Clear Firefox profile
4. Launch new Camoufox instance
5. Run full login flow
6. Return success/failure
7. Release lock
```

---

## Deployment Architecture

### Single Container Design

```yaml
services:
  bot:
    build: .
    container_name: fap-discord-bot
    restart: unless-stopped
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - FAP_USERNAME=${FAP_USERNAME}
      - FAP_PASSWORD=${FAP_PASSWORD}
      - HEADLESS=false
      - PROXY_URL=${PROXY_URL:-}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

### Runtime Architecture in Container

```
Container: fap-discord-bot
|
+-- Xvfb :99 (virtual display, started by CMD)
|     |
+-- Python (main.py)
      |
      +-- Discord Bot (discord.py async loop)
      |     |
      |     +-- Command Handlers
      |     +-- Background Scheduler
      |
      +-- FAPAutoLogin
            |
            +-- Camoufox (Firefox)
                  |- Profile: /app/data/firefox_profile/
                  |- Proxy: from PROXY_URL env
                  |- Display: :99 or virtual
```

### Server Details

| Item | Value |
|------|-------|
| **Provider** | DigitalOcean |
| **Region** | Singapore (sgp1) |
| **Droplet** | Basic 1GB ($6/mo) |
| **OS** | Ubuntu 22.04 LTS |
| **Project Path** | /opt/fap-bot/ |
| **Container** | fap-discord-bot |

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Bot Framework | discord.py | 2.7+ |
| Browser Automation | Camoufox | 0.4+ (Firefox-based anti-detect) |
| HTML Parsing | BeautifulSoup4 | 4.12+ |
| HTML Parser Backend | lxml | 4.9+ |
| Scheduler | APScheduler | 3.10+ |
| Data Validation | Pydantic | 2.x |
| Database | SQLite | Built-in |
| Encryption | cryptography (Fernet) | 41.0+ |
| Container | Docker + Docker Compose | Latest |
| Virtual Display | Xvfb | System package |
| Server | DigitalOcean Droplet | Basic 1GB |

---

## Design Decisions

### DD-1: Camoufox (Firefox) over Playwright (Chromium)

| Factor | Camoufox (Firefox) | Playwright/patchright (Chromium) |
|--------|-------------------|----------------------------------|
| TLS Fingerprint | Harder to detect | Well-documented, easier to detect |
| Cloudflare Bypass | Works with residential proxy | Fails on datacenter IPs |
| Anti-detection | Built-in (humanize, fingerprint randomization) | Requires manual patches |
| Cloudflare on datacenter | Fails without proxy | Fails regardless of proxy |

### DD-2: Browser Stays Open vs Cookie Reuse

| Factor | Browser Open | Cookie Reuse |
|--------|-------------|--------------|
| Reliability | 100% (same TLS context) | 0% (TLS mismatch) |
| Resource Usage | ~300-400MB RAM constant | ~50MB, spikes during login |
| Complexity | Low (page.goto) | High (cookie management) |

**Decision:** Keep browser open. Tried cookie reuse with aiohttp and curl_cffi — both failed with 403.

### DD-3: Profile Cleanup Before Login

| Factor | Fresh Profile | Persistent Profile |
|--------|--------------|-------------------|
| Cloudflare detection | Less likely | Accumulates fingerprints |
| Login speed | Slower (re-solve CF) | Faster (CF already solved) |
| Reliability | High | Degrades over time |

**Decision:** Clean profile before each login. Stability > speed.

---

## Lessons Learned

### 1. Cloudflare Turnstile is IP-Reputation First

No browser trick can overcome a datacenter IP. Turnstile checks IP reputation before browser fingerprinting. Residential proxy is the #1 requirement.

### 2. TLS Fingerprint Ties Cookies to Browser

`cf_clearance` is bound to the JA3/JA4 fingerprint. Extracting cookies and using them with a different HTTP client always fails. The browser that solves the challenge must make all subsequent requests.

### 3. FAP Session Expiry is Silent

FAP doesn't return 401 or error JSON when session expires. It redirects to `Default.aspx` with HTTP 200. The login page HTML looks like a valid response unless you check content specifically. Four validation checks are needed: URL redirect, Login URL, login button presence, and Cloudflare challenge title.

### 4. Firefox Anti-Detect Beats Chromium Anti-Detect

Three browser iterations (FlareSolverr/Chrome -> patchright/Chromium -> Camoufox/Firefox) showed that Firefox's TLS fingerprint is inherently harder for Cloudflare to classify as bot-like.

### 5. Docker Environment Quirks

- `.env` file values are literal (no `$` escaping)
- `docker-compose.yml` environment section does variable substitution (escape `$` to `$$`)
- `docker restart` does NOT reload `.env`
- Always use `docker compose up -d --force-recreate` after env changes

### 6. Shared Browser Instance Prevents Profile Lock

Running two Camoufox instances with the same profile directory causes lock contention. Share one `FAPAutoLogin` instance between `FAPAuth` and `SessionValidator`, and close the old browser before launching a new one.

### 7. Vietnamese Cloudflare Titles

Cloudflare challenge page title is "Cho mot chut..." in Vietnamese. Code must check both English and Vietnamese keywords, or better yet, wait for actual page content (login button, schedule dropdown) rather than relying on title checks.

### 8. Xvfb Readiness Race Condition

Starting Xvfb and immediately launching the browser can race — browser tries to connect before Xvfb is ready. The CMD waits for the X11 lock file: `until [ -e /tmp/.X99-lock ]; do sleep 0.1; done`

---

**Document Status:** Updated
**Last Updated:** 2026-05-14
