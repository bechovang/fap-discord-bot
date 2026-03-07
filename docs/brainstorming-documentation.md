# FAP Discord Bot - Brainstorming Documentation

**Project:** Self-hosted Discord Bot to scrape FAP (FPT Academic Portal) data
**Date:** 2026-03-07
**Author:** Admin
**Status:** Planning Phase

---

## 📋 Table of Contents

1. [Problem Statement](#problem-statement)
2. [FAP Analysis](#fap-analysis)
3. [Proposed Solution](#proposed-solution)
4. [Architecture](#architecture)
5. [Implementation Plan](#implementation-plan)
6. [Challenges & Solutions](#challenges--solutions)

---

## Problem Statement

**Goal:** Create a Discord bot that automatically pulls data from FAP (fap.fpt.edu.vn) and pushes it to Discord, so users don't need to actively check FAP.

**Desired Features:**
- Schedule scraping (weekly: current, past, next)
- Grade scraping
- Exam schedule scraping
- Application status viewing
- Automatic notifications for changes
- Keep-alive session management

---

## FAP Analysis

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | ASP.NET WebForms (legacy) |
| Rendering | Server-side rendering (no JSON API) |
| Authentication | Google OAuth / FeID |
| Protection | Cloudflare Turnstile |
| Session Management | ASP.NET Session with timeout |

### Key Endpoints

```
/Student.aspx                 - Home/Dashboard
/Report/ScheduleOfWeek.aspx   - Weekly schedule
/Grade/StudentGrade.aspx      - Grade report
/Exam/ScheduleExams.aspx      - Exam schedule
/App/AcadAppView.aspx         - Application status
```

### Critical Discovery: No REST API

**FAP does NOT expose JSON APIs** for data retrieval. All data is rendered server-side as HTML tables.

**Implication:** We must use **DOM Scraping** (BeautifulSoup) instead of API calls.

### HTML Structure (from scraped files)

```
week_cur.html          - Current week schedule
week_next.html         - Next week schedule
week_past.html         - Past week schedule
Grade report.html      - Grade report
Exam Schedules.html    - Exam schedules
View Application.html  - Application status
```

**ASP.NET Form Structure:**
- `__VIEWSTATE` - Encrypted state tracking
- `__EVENTVALIDATION` - Event validation token
- `.AspNet.ApplicationCookie` - Authentication cookie
- `.AspNet.SessionId` - Session identifier

---

## Proposed Solution

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | **Python** | Excellent scraping ecosystem (BeautifulSoup), async support, Discord.py |
| Browser Automation | **PatchRight** | Stealth fork of Playwright from Turnstile-Solver project |
| Cloudflare Bypass | **Turnstile-Solver** | Proven solution for Cloudflare Turnstile |
| HTML Parsing | **BeautifulSoup4** | Mature, powerful HTML parsing |
| Discord Library | **discord.py** | Industry standard, async support |
| Task Scheduling | **asyncio** | Native Python async for keep-alive heartbeat |

### Why PatchRight over Playwright?

```diff
- playwright       # Standard, easily detected
+ patchright       # Stealth fork with anti-detection
+ camoufox         # Optional anti-detection browser
```

**PatchRight** is a fork of Playwright specifically designed to bypass bot detection, used successfully by the Turnstile-Solver project.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FAP Discord Bot System                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────┐    ┌─────────────────────────────────┐  │
│  │   Discord Bot     │◄────│         FAP Scraper Module     │  │
│  │   (discord.py)    │    │                                 │  │
│  │                   │    │  ┌─────────────────────────────┐ │  │
│  │  - Commands       │    │  │  Auth Manager               │ │  │
│  │  - Notifications  │    │  │  - PatchRight browser       │ │  │
│  │  - User configs   │    │  │  - Cookie persistence       │ │  │
│  └───────────────────┘    │  │  - Auto-login               │ │  │
│                           │  └─────────────────────────────┘ │  │
│                           │                                   │  │
│                           │  ┌─────────────────────────────┐ │  │
│                           │  │  Cloudflare Handler         │ │  │
│                           │  │  - Turnstile detection      │ │  │
│                           │  │  - Auto-solve               │ │  │
│                           │  │  - Stealth mode             │ │  │
│                           │  └─────────────────────────────┘ │  │
│                           │                                   │  │
│                           │  ┌─────────────────────────────┐ │  │
│                           │  │  HTML Parser                │ │  │
│                           │  │  - BeautifulSoup             │ │  │
│                           │  │  - Schedule extraction      │ │  │
│                           │  │  - Grade extraction         │ │  │
│                           │  │  - Exam extraction          │ │  │
│                           │  └─────────────────────────────┘ │  │
│                           └─────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Data Persistence Layer                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │ │
│  │  │ cookies.json│  │ user.db     │  │ cache/              │ │ │
│  │  └─────────────┘  │ (SQLite)    │  │ - parsed data       │ │ │
│  │                   └─────────────┘  └─────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Background Services                           │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  Keep-Alive Heartbeat (asyncio)                       │  │ │
│  │  │  - Runs every 10-15 minutes                           │  │ │
│  │  │  - Makes lightweight FAP request                      │  │ │
│  │  │  - Prevents ASP.NET session timeout                    │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Optional: Separate Process                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │    Turnstile-Solver API (port 5000)                        │ │
│  │    GET /turnstile?url=...&sitekey=...                      │ │
│  │    Returns: {"task_id": "..."}                             │ │
│  │    GET /result?id=...                                      │ │
│  │    Returns: {"value": "turnstile.token"}                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Authentication (Priority: CRITICAL)

**Task #1:** Setup project structure
```
fap-discord-bot/
├── bot/
│   ├── __init__.py
│   ├── bot.py              # Discord bot main
│   └── commands/
│       ├── __init__.py
│       ├── schedule.py
│       ├── grades.py
│       └── exams.py
├── scraper/
│   ├── __init__.py
│   ├── auth.py              # Authentication manager
│   ├── parser.py            # BeautifulSoup parser
│   └── cloudflare.py        # Turnstile handler
├── data/
│   ├── cookies.json
│   ├── fap_profile/         # Chrome profile dir
│   └── cache/
├── utils/
│   ├── __init__.py
│   └── heartbeat.py         # Keep-alive scheduler
├── tests/
├── requirements.txt
├── .env.template
└── main.py
```

**Task #2:** Implement PatchRight authentication
```python
# scraper/auth.py
class FAPAuth:
    async def get_session(self):
        """Main entry - returns valid browser session"""
        # Try existing cookies first
        if self._load_cookies():
            if await self._test_session():
                return self.browser

        # Cookies expired - full login
        return await self._full_login_flow()

    async def _full_login_flow(self):
        """Complete login with Cloudflare handling"""
        # 1. Launch patchright with stealth
        # 2. Load existing Chrome profile (has Google session)
        # 3. Navigate to FAP
        # 4. Handle Cloudflare Turnstile
        # 5. Save new cookies
        return self.browser
```

**Task #3:** Session management
```python
# Cookie validation logic
- Check file exists
- Check age < 24 hours
- Test with lightweight request to FAP
- Auto-relogin if validation fails
```

### Phase 2: HTML Parsing

**Task #4:** Parse FAP schedule with BeautifulSoup
```python
# scraper/parser.py
def parse_schedule_week(html_content: str) -> List[ScheduleItem]:
    """Extract schedule from week_cur.html structure"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find schedule table (ID needs to be extracted from HTML)
    table = soup.find('table', {'id': 'ctl00_mainContent_*'})

    items = []
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 5:
            items.append(ScheduleItem(
                subject=cells[0].text.strip(),
                room=cells[1].text.strip(),
                day=cells[2].text.strip(),
                time=cells[3].text.strip(),
                instructor=cells[4].text.strip()
            ))

    return items
```

**Priority:** First analyze `week_cur.html` to find exact table IDs and structure.

### Phase 3: Keep-Alive System

**Task #5:** Heartbeat scheduler
```python
# utils/heartbeat.py
async def heartbeat_scheduler(fap_auth: FAPAuth, interval_minutes: int = 10):
    """Run every 10-15 minutes to keep ASP.NET session alive"""
    while True:
        try:
            # Make lightweight request
            await fap_auth.ping()
            logger.info("Heartbeat: Session alive")
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")

        await asyncio.sleep(interval_minutes * 60)
```

### Phase 4: Discord Integration

**Task #6 (Future):** Discord bot implementation
- Command: `/schedule today`, `/schedule week`, `/schedule next`
- Command: `/grades`, `/grades <term>`
- Command: `/exams`, `/exams <month>`
- Auto-notification for new grades/exams

---

## Challenges & Solutions

### Challenge 1: Google "Unsafe Browser" 🔴 CRITICAL

**Problem:** Puppeteer/Playwright auto-login blocked by Google's "This browser or app may not be secure"

**Solution:**
```python
# Use Chrome profile with existing Google session
browser = await p.chromium.launch_persistent_context(
    user_data_dir='./data/fap_profile',
    headless=False,
    args=['--disable-blink-features=AutomationControlled']
)
```

**User Action Required:**
1. Manually login to Google once in browser
2. Save profile to `data/fap_profile/`
3. Bot loads this profile for auto-login

### Challenge 2: Cloudflare Turnstile 🟡 HIGH

**Problem:** Random Cloudflare challenges block automated access

**Solution Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | PatchRight with stealth | Built-in detection bypass | May still fail occasionally |
| B | Turnstile-Solver integration | Proven working method | Additional dependency |
| C | Separate API process | Isolated failure domain | More complex deployment |

**Recommended:** Option B - Use Turnstile-Solver pattern

```python
# scraper/cloudflare.py
async def solve_turnstile(page: Page) -> bool:
    """Detect and solve Cloudflare Turnstile"""
    # Check if Turnstile is present
    turnstile_iframe = await page.query_selector('iframe[src*="turnstile"]')

    if turnstile_iframe:
        # Use PatchRight's built-in solve
        # Or call Turnstile-Solver API
        token = await get_turnstile_token(
            url=page.url,
            sitekey=extract_sitekey(page)
        )

        # Inject token and submit
        await page.evaluate(f'document.querySelector("[name=\'cf-turnstile-response\']").value = "{token}"')
        await page.click('input[type="submit"]')

    return True
```

### Challenge 3: ASP.NET Session Timeout 🟠 MEDIUM

**Problem:** Session expires after 20-60 minutes of inactivity

**Solution:** Keep-alive heartbeat every 10-15 minutes
```python
# Make lightweight navigation to keep session active
await page.goto('https://fap.fpt.edu.vn/Student.aspx')
await asyncio.sleep(2)
await page.goto('https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx')
```

### Challenge 4: Cookie Persistence 🟡 MEDIUM

**Problem:** Cookies expire quickly (< 24 hours typically)

**Solution:**
```python
# Multi-layer validation
def is_session_valid():
    # 1. Check file exists
    if not os.path.exists('cookies.json'):
        return False

    # 2. Check age
    if time.time() - os.path.getmtime('cookies.json') > 24*3600:
        return False

    # 3. Test request
    response = requests.get(fap_url, cookies=load_cookies())
    return 'Logout' in response.text  # Still logged in
```

---

## Dependencies

### requirements.txt

```txt
# Discord
discord.py>=2.3.2

# Web Scraping & Browser Automation
patchright>=1.0.0      # Stealth Playwright fork
beautifulsoup4>=4.12.2
lxml>=4.9.3            # BeautifulSoup parser

# Async & Utilities
aiofiles>=23.0.0       # Async file operations
python-dotenv>=1.0.0   # Environment variables

# Optional - for Turnstile-Solver integration
quart>=0.19.4          # Async web framework
camoufox[geoip]>=0.4.0 # Anti-detection browser
```

---

## External Resources

### Turnstile-Solver Repository

**Location:** `Turnstile-Solver/`

**Key Files:**
- `api_solver.py` - API server mode
- `async_solver.py` - Async solver implementation
- `sync_solver.py` - Sync solver implementation

**API Usage:**
```bash
# Start solver API server
python api_solver.py --headless --useragent <UA>

# Solve Turnstile
curl "http://localhost:5000/turnstile?url=https://fap.fpt.edu.vn&sitekey=<SITEKEY>"

# Get result
curl "http://localhost:5000/result?id=<TASK_ID>"
```

### FAP HTML Data

**Available scraped files:**
- `week_cur.html` - Current week schedule
- `week_next.html` - Next week schedule
- `week_past.html` - Past week schedule
- `Grade report.html` - Grade report
- `Exam Schedules.html` - Exam schedules
- `View Application.html` - Application status

**Note:** HAR files contain only Cloudflare RUM data, NOT actual FAP data.

---

## Next Steps

### Immediate Actions

1. ✅ **Extract FAP Turnstile sitekey** from HTML files
   ```bash
   grep -r "turnstile" *.html
   grep -r "data-sitekey" *.html
   ```

2. ✅ **Test Turnstile-Solver with FAP**
   ```bash
   cd Turnstile-Solver
   pip install -r requirements.txt
   python -m patchright install chromium
   python api_solver.py
   ```

3. ⏳ **Create project structure** (Task #1)

4. ⏳ **Implement authentication** (Task #2)

5. ⏳ **Test full login flow** with real FAP account

### Development Order

```
1. Cloudflare bypass verification  ← START HERE
2. Project structure setup
3. Authentication implementation
4. Session management
5. HTML parsing (schedule first)
6. Discord bot integration
7. Keep-alive heartbeat
8. Notification system
```

---

## Notes

### FAP Session Cookie Behavior

| Cookie Type | Lifetime | Persistence |
|-------------|----------|-------------|
| `.AspNet.ApplicationCookie` | Sliding (30-60 min) | Not persistent |
| `.AspNet.SessionId` | Session only | Lost on browser close |
| Google OAuth tokens | 7-14 days | Refreshable |

**Conclusion:** Cookies CANNOT be relied upon for long-term storage. Auto-relogin is required.

### Deployment Considerations

| Factor | Recommendation |
|--------|----------------|
| Runtime | Python 3.8+ |
| OS | Linux (Ubuntu/Debian) or Windows |
| Browser storage | 100-500MB for Chrome profile |
| RAM | 512MB - 1GB per browser instance |
| Network | Stable connection required for keep-alive |

---

**Document Status:** Active - Subject to updates as development progresses

**Last Updated:** 2026-03-07
