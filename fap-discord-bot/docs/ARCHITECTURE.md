# FAP Discord Bot - Solution Architecture & Implementation Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Current Implementation](#current-implementation)
3. [Detailed Flow](#detailed-flow)
4. [File Structure](#file-structure)
5. [Data Structures](#data-structures)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What This Does

The FAP Discord Bot automatically fetches class schedules from FPT University's Academic Portal (FAP) and displays them in Discord.

### Challenge Solved

**Problem:** FAP is protected by Cloudflare Turnstile - detects automated browsers and blocks them.

**Solution:** Automated FeID login with cookie persistence.

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Browser Automation | Playwright Chromium | Web navigation & interaction |
| HTML Parsing | BeautifulSoup4 | Extract schedule data |
| Authentication | FeID OAuth + Cookie Export | Session persistence |
| Language | Python 3.11+ | Core implementation |

---

## Current Implementation

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  DISCORD BOT                                                 │
│  (User types: /schedule)                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  FAPAutoLogin (auto_login_feid.py)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ PHASE 1: Authentication (One-time or when expired)        │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ 1. Launch Chromium with persistent profile               │ │
│  │ 2. Navigate to fap.fpt.edu.vn/Default.aspx             │ │
│  │ 3. Select campus (FU-Hòa Lạc)                           │ │
│  │ 4. Click "Login With FeID" button                        │ │
│  │ 5. Redirect to feid.fpt.edu.vn/Account/Login            │ │
│  │ 6. Fill username + password form                         │ │
│  │ 7. Submit login                                         │ │
│  │ 8. OAuth redirect back to FAP                           │ │
│  │ 9. Navigate to schedule page                           │ │
│  │ 10. Export cookies to data/fap_cookies.json             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ PHASE 2: Fetch Schedule (Every request)                 │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ 1. Load cookies from data/fap_cookies.json              │ │
│  │ 2. Launch Chromium (non-persistent)                     │ │
│  │ 3. Add cookies to browser context                        │ │
│  │ 4. Navigate to schedule page                           │ │
│  │ 5. Select week/year (ASP.NET postback)                 │ │
│  │ 6. Get HTML content                                     │ │
│  │ 7. Parse with FAPParser                                │ │
│  │ 8. Return ScheduleItem[]                               │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  FAPParser (parser.py)                                         │
├─────────────────────────────────────────────────────────────────┤
│  - Parse HTML table structure                                 │
│  - Extract class information                                 │
│  - Return ScheduleItem objects                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Flow

### Phase 1: Authentication (`auto_login()`)

#### Step 1: Launch Browser with Persistent Profile

```python
self._browser = await self._playwright.chromium.launch_persistent_context(
    user_data_dir=str(self.profile_dir),  # "data/chrome_profile"
    headless=self.headless,                   # False = visible browser
    args=[
        '--disable-blink-features=AutomationControlled',  # Avoid detection
        '--no-sandbox',
    ],
    viewport={'width': 1920, 'height': 1080},
)
```

**Why persistent profile?**
- First run: Cloudflare challenge appears, user solves it manually
- Subsequent runs: Same profile = same fingerprint = Cloudflare skips challenge
- Stores cookies, localStorage, cache, fingerprint data

#### Step 2: Navigate to FAP Login Page

```python
await self._page.goto("https://fap.fpt.edu.vn/Default.aspx", timeout=60000)
```

**What happens:**
- If Cloudflare challenge present → User must solve manually (first time only)
- After challenge → Page loads with login options

#### Step 3: Select Campus

```python
campus_select = self._page.locator('#ctl00_mainContent_ddlCampus')
await campus_select.select_option('3')  # 3 = FU-Hòa Lạc
```

**Campus codes:**
- `3` = FU-Hòa Lạc
- `4` = FU-Hồ Chí Minh
- `5` = FU-Đà Nẵng
- `6` = FU-Cần Thơ
- `7` = FU-Quy Nhơn

#### Step 4: Click "Login With FeID"

```python
feid_button = self._page.locator('#ctl00_mainContent_btnloginFeId')
await feid_button.click()
```

**What happens:**
- ASP.NET postback triggered
- Redirect to: `https://feid.fpt.edu.vn/Account/Login?ReturnUrl=...`

#### Step 5: FeID Login Form

**Redirect URL contains:**
```
https://feid.fpt.edu.vn/Account/Login?
  ReturnUrl=/connect/authorize/callback?
    client_id=fap-service
    redirect_uri=https://fap.fpt.edu.vn/Default.aspx
    response_type=code
    scope=openid profile email identity-service
    ...
```

**Find form elements:**

Username input selectors tried:
```python
username_selectors = [
    'input[name="Username"]',      # ✅ This one works!
    'input[name="username"]',
    'input[name="email"]',
    'input[type="email"]',
    'input[id*="username"]',
    'input[id*="Email"]',
    '#Input_Email',
    '#Email',
    '#username',
]
```

Password input selectors tried:
```python
password_selectors = [
    'input[name="Password"]',       # ✅ This one works!
    'input[name="password"]',
    'input[type="password"]',
    'input[id*="password"]',
    '#Input_Password',
    '#Password',
    '#password',
]
```

Submit button selectors tried:
```python
submit_selectors = [
    'button[type="submit"]',         # ✅ This one works!
    'input[type="submit"]',
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    'button:has-text("Đăng nhập")',
]
```

#### Step 6: Fill and Submit Form

```python
await username_input.fill(self.feid)      # e.g., "phuchcm2006@gmail.com"
await password_input.fill(self.password)  # e.g., "password123"
await submit_btn.click()
```

**What happens:**
1. POST request to feid.fpt.edu.vn with credentials
2. FeID validates username/password
3. Creates authentication session
4. OAuth authorization code generated
5. Redirect back to FAP with code
6. FAP exchanges code for tokens
7. Session established!

#### Step 7: Navigate to Schedule Page

```python
if 'Thongbao.aspx' in self._page.url:
    # On notification page after login
    await self._page.goto(self.SCHEDULE_URL, timeout=30000)
    await asyncio.sleep(5)
```

**Verification:**
```python
content = await self._page.content()
if 'ctl00_mainContent_drpSelectWeek' in content:
    # Success! Schedule dropdown exists = authenticated
```

#### Step 8: Export Cookies to JSON

```python
cookies = await self._page.context.cookies()
with open('data/fap_cookies.json', 'w') as f:
    json.dump(cookies, f, indent=2)
```

**Why export to JSON?**
- Persistent profile cookies are NOT reliably flushed to disk
- JSON export guarantees cookies are saved
- Can load into any browser context later
- Portable across different machines

---

### Phase 2: Fetch Schedule (`fetch_schedule()`)

#### Step 1: Load Cookies from JSON

```python
with open('data/fap_cookies.json', 'r') as f:
    cookies = json.load(f)
```

**Expected cookies:**
```json
[
  {
    "name": "cf_clearance",
    "value": "xUoF8dm_.Yhlhl_Me06IurFGPFxciwgz1JRc...",
    "domain": ".fpt.edu.vn",
    "expires": 1804422172.83188
  },
  {
    "name": "ASP.NET_SessionId",
    "value": "kym2si5igycc3bqllldjfs5g",
    "domain": "fap.fpt.edu.vn"
  },
  {
    "name": "__AntiXsrfToken",
    "value": "ee7c217602b24abf9958abeb84f39958",
    "domain": "fap.fpt.edu.vn"
  }
]
```

#### Step 2: Launch Browser and Add Cookies

```python
self._browser = await self._playwright.chromium.launch(
    headless=self.headless,
    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
)

self._page = await self._browser.new_page()
await self._page.context.add_cookies(cookies)
```

**Why non-persistent browser?**
- Cookies from JSON provide authentication
- No need for persistent profile overhead
- Faster startup time

#### Step 3: Navigate to Schedule Page

```python
await self._page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=60000)
await asyncio.sleep(5)
```

**Cloudflare Bypass:**
- `cf_clearance` cookie present → Cloudflare recognizes return visitor
- No challenge! ✅

#### Step 4: Handle Redirect to Login Page

```python
if 'Login' in current_url or 'Default.aspx' in current_url:
    # Cookies expired - not logged in
    await self._page.goto("https://fap.fpt.edu.vn/Default.aspx", timeout=30000)
    await self._page.goto(self.SCHEDULE_URL, timeout=30000)
```

#### Step 5: Select Week/Year with ASP.NET Postback

```python
if week is not None:
    await self._page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))
    # IMPORTANT: Wait for postback navigation
    await self._page.wait_for_load_state('networkidle', timeout=10000)
    await asyncio.sleep(3)
```

**ASP.NET Postback:**
- `select_option()` triggers `__doPostBack()` JavaScript function
- Page navigates to itself with new parameters
- Server renders new HTML with selected week's data
- MUST wait for navigation to complete!

#### Step 6: Get HTML Content

```python
content = await self._page.content()
with open('schedule_fetched.html', 'w', encoding='utf-8') as f:
    f.write(content)
```

#### Step 7: Parse Schedule

```python
from scraper.parser import FAPParser
parser = FAPParser()
items = parser.parse_schedule(content)
```

---

### Phase 3: Parse HTML (`FAPParser.parse_schedule()`)

#### HTML Structure

```
<table>
  <thead>
    <tr>
      <th>Slot</th>
      <th>Mon</th>
      <th>Tue</th>
      <th>Wed</th>
      <th>Thu</th>
      <th>Fri</th>
      <th>Sat</th>
      <th>Sun</th>
    </tr>
    <tr>
      <th></th>
      <th>02/03/2026</th>
      <th>03/03/2026</th>
      ...
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Slot 1</td>
      <td>
        <a href="/ActivityDetail?id=...">COM101</a>
        at Room-A301
        (7:00-9:15)
        [attended]
      </td>
      <td>-</td>
      ...
    </tr>
    <tr>
      <td>Slot 2</td>
      ...
    </tr>
  </tbody>
</table>
```

#### Parsing Logic

```python
# 1. Find schedule table
for t in soup.find_all('table'):
    if 'Slot' in t.get_text():
        table = t
        break

# 2. Extract header dates
headers = table.find('thead').find_all('tr')[1].find_all('th')
# headers[1] = Mon date, headers[2] = Tue date, etc.

# 3. Parse each slot row
for row in table.find('tbody').find_all('tr'):
    slot_text = row.find_all('td')[0].get_text()  # "Slot 1"
    slot_num = int(re.search(r'Slot\s*(\d+)', slot_text).group(1))

    # Parse each day column (cells 1-7)
    for i in range(1, 8):
        cell = row.find_all('td')[i]
        if '-' not in cell.get_text():
            # Extract class info
            subject_code = cell.find('a').get_text()
            room = re.search(r'at\s+([A-Z0-9.]+)', cell.get_text()).group(1)
            time = re.search(r'\((\d{1,2}:\d{2})-(\d{1,2}:\d{2})\)', cell.get_text())
```

#### Data Class

```python
@dataclass
class ScheduleItem:
    subject_code: str      # e.g., "COM101"
    subject_name: str = "" # e.g., "Introduction to Computing"
    room: str = ""         # e.g., "A301"
    day: str = ""          # e.g., "Mon"
    date: str = ""         # e.g., "02/03/2026"
    slot: int = 0         # 1-8
    start_time: str = ""  # e.g., "7:00"
    end_time: str = ""    # e.g., "9:15"
    status: str = ""       # "attended", "absent", "-"
```

---

## File Structure

```
fap-discord-bot/
├── scraper/
│   ├── auto_login_feid.py      # Main auth module (457 lines)
│   ├── parser.py                # HTML parser (316 lines)
│   └── [other files...]
├── data/
│   ├── chrome_profile/          # Persistent Chromium profile
│   │   ├── Default/
│   │   │   ├── Network/
│   │   │   │   └── Cookies      # Cookie database (not reliable)
│   │   │   ├── Local Storage/
│   │   │   └── Session Storage/
│   │   └── [other profile data...]
│   └── fap_cookies.json         # Exported cookies (RELIABLE!)
├── schedule_fetched.html        # Debug: Latest fetched HTML
└── [other files...]
```

---

## Data Structures

### Cookie Structure

```json
{
  "name": "cf_clearance",
  "value": "xUoF8dm_.Yhlhl_Me06IurFGPFxciwgz1JRc_...",
  "domain": ".fpt.edu.vn",
  "path": "/",
  "expires": 1804422172.83188,
  "httpOnly": true,
  "secure": true,
  "sameSite": "None"
}
```

### Cookie Breakdown

| Cookie | Domain | Expires | Purpose |
|--------|--------|---------|---------|
| `cf_clearance` | .fpt.edu.vn | ~6 months | Cloudflare verification (CRITICAL) |
| `ASP.NET_SessionId` | fap.fpt.edu.vn | -1 (session) | ASP.NET session (CRITICAL) |
| `__AntiXsrfToken` | fap.fpt.edu.vn | -1 (session) | CSRF protection (CRITICAL) |
| `.AspNet.cookies` | fap.fpt.edu.vn | -1 (session) | Additional auth data |
| `idsrv.session` | feid.fpt.edu.vn | -1 (session) | FeID session |
| `.AspNetCore.Session` | feid.fpt.edu.vn | -1 (session) | ASP.NET Core session |
| `.FeIdIdentityServer.Auth` | feid.fpt.edu.vn | -1 (session) | FeID authentication |

### ScheduleItem Data Structure

```python
ScheduleItem(
    subject_code="COM101",
    subject_name="",
    room="A301",
    day="Mon",
    date="02/03/2026",
    slot=1,
    start_time="7:00",
    end_time="9:15",
    status="attended"  # or "absent", "-"
)
```

---

## Configuration

### Environment Variables (Optional)

```bash
# Windows Command Prompt
set FAP_FEID=your_feid@fe.edu.vn
set FAP_PASSWORD=your_password

# PowerShell
$env:FAP_FEID="your_feid@fe.edu.vn"
$env:FAP_PASSWORD="your_password"

# Linux/Mac
export FAP_FEID="your_feid@fe.edu.vn"
export FAP_PASSWORD="your_password"
```

### Constants

```python
# URLs
SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
LOGIN_URL = "https://fap.fpt.edu.vn/Default.aspx"

# Paths
PROFILE_DIR = "data/chrome_profile"
COOKIES_FILE = "data/fap_cookies.json"

# Campus Codes
CAMPUS_HOALAC = 3
CAMPUS_HCM = 4
CAMPUS_DANANG = 5
CAMPUS_CANTHO = 6
CAMPUS_QUYNHON = 7
```

---

## Usage

### Installation

```bash
# Install dependencies
pip install playwright beautifulsoup4 lxml

# Install Chromium browser
playwright install chromium
```

### Initial Setup (One-Time)

```bash
# Login and export cookies
python scraper/auto_login_feid.py login your_feid@fe.edu.vn your_password

# Expected output:
# ✅ FEID login successful
# ✅ Schedule page accessible
# ✅ 13 cookies saved to data/fap_cookies.json
```

### Fetch Schedule

```bash
# Current week
python scraper/auto_login_feid.py fetch

# Specific week
python scraper/auto_login_feid.py fetch 5 2026

# Expected output:
# ✅ Loaded 13 cookies
# ✅ Found 10 classes
```

### Programmatic Usage

```python
import asyncio
from scraper.auto_login_feid import FAPAutoLogin

async def main():
    # Fetch schedule
    auth = FAPAutoLogin(headless=False)
    html = await auth.fetch_schedule(week=5, year=2026)

    if html:
        from scraper.parser import FAPParser
        parser = FAPParser()
        items = parser.parse_schedule(html)

        # Use the data
        for item in items:
            print(f"{item.subject_code} - {item.room} - {item.day} {item.date}")

asyncio.run(main())
```

---

## Troubleshooting

### Issue: "No cookies found"

**Cause:** `data/fap_cookies.json` doesn't exist

**Solution:**
```bash
# Re-login to export cookies
python scraper/auto_login_feid.py login your_feid your_password
```

### Issue: "Schedule page not loaded"

**Cause:** Cookies expired or invalid

**Solution:**
```bash
# Check debug page
cat debug_fetch_page.html

# If "Login" in URL or HTML - cookies expired, re-login
python scraper/auto_login_feid.py login your_feid your_password
```

### Issue: "Found 0 classes"

**Cause 1:** Selected week has no classes (e.g., break week)

**Solution:**
```bash
# Try current week (no parameters)
python scraper/auto_login_feid.py fetch

# Or try different week
python scraper/auto_login_feid.py fetch 10 2026
```

**Cause 2:** Page didn't load properly

**Solution:**
```bash
# Check saved HTML
cat schedule_fetched.html

# Look for "ctl00_mainContent_drpSelectWeek"
# If missing - page load failed
```

### Issue: Browser process already running

**Error:** `Target page, context or browser has been closed`

**Solution:**
```bash
# Kill existing Chrome processes
taskkill /F /IM chrome.exe

# Then retry
python scraper/auto_login_feid.py fetch
```

### Issue: Week selection not working

**Symptom:** `Week selection failed: Execution context was destroyed`

**Cause:** Page navigation occurred after selection (expected!)

**Solution:** This is normal! The code already handles it:
```python
await self._page.wait_for_load_state('networkidle', timeout=10000)
await asyncio.sleep(3)
```

---

## Summary

### What We Built

1. **Automated Authentication**
   - FeID login form automation
   - Cookie export for persistence
   - No manual intervention after initial setup

2. **Schedule Fetching**
   - Cloudflare bypass via saved cookies
   - Week/year selection with ASP.NET postback
   - HTML parsing with BeautifulSoup4

3. **Data Structures**
   - `ScheduleItem` dataclass for class information
   - JSON cookie storage for portability

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `auto_login_feid.py` | 457 | Auth + fetch |
| `parser.py` | 316 | HTML parsing |
| `fap_cookies.json` | - | Cookie storage |

### Success Criteria

✅ Automated FeID login
✅ Cloudflare bypass
✅ Schedule fetching
✅ Week selection
✅ HTML parsing
✅ Export 13 cookies
✅ Parse 10+ classes

---

*Last Updated: 2025-01-07*
*Status: Production Ready*
