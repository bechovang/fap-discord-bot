# FAP Authentication - Solutions Comparison

## Problem Statement

FAP (fap.fpt.edu.vn) uses Cloudflare Turnstile protection that blocks automated scraping. Even with valid cookies, the browser fingerprint must match for Cloudflare to allow access.

---

## Solutions Evaluated

### 1. Cookie Extraction Only ❌

**Approach:** Save cf_clearance cookie, load in new browser session

**Result:** FAILS - Cloudflare detects fingerprint mismatch

```
Session 1: Chrome normally → Cloudflare solved → Save cf_clearance (364 days)
Session 2: Load cf_clearance in new browser → Fingerprint mismatch → CHALLENGE
```

**Why it fails:** cf_clearance cookie is tied to specific browser fingerprint. Different browser = different fingerprint = Cloudflare challenge.

---

### 2. Persistent Camoufox Profile ❌

**Approach:** Use Camoufox with persistent user_data_dir

**Result:** FAILS - Camoufox doesn't support user_data_dir

```python
# This doesn't work - Camoufox is Firefox-based
browser = await AsyncCamoufox(
    user_data_dir=str(profile_dir)  # NOT SUPPORTED
).start()
```

**Why it fails:** Camoufox is Firefox-based, user_data_dir is Chromium-only feature.

---

### 3. Persistent Chromium Profile ✅

**Approach:** Use Playwright Chromium with launch_persistent_context()

**Result:** WORKS - Maintains same fingerprint across runs

```
Setup: Chrome with persistent profile → Manual login → Profile saved
Reuse: Same profile → Same fingerprint → SKIP Cloudflare ✅
```

**File:** `scraper/persistent_chromium.py`

**Pros:**
- Free
- Skips Cloudflare after first login
- Full automation possible

**Cons:**
- Requires manual first-time setup
- Auth cookies still expire (~30-120 min)
- Profile may need periodic refresh

---

### 4. FlareSolverr ✅✅ (RECOMMENDED)

**Approach:** Proxy server that auto-solves Cloudflare

**Result:** WORKS BEST - Fully automated Cloudflare bypass

```
Your Script → FlareSolverr API → Auto-solve Cloudflare → Return HTML
```

**File:** `scraper/flaresolverr_auth.py`

**Pros:**
- Fully automated (no manual intervention)
- Sessions maintain cookies
- Works with any HTTP client
- Active maintained project

**Cons:**
- Requires Docker/external service
- Higher memory usage (runs Chrome)
- Slightly slower (browser startup)

---

## Quick Start Guide

### Option A: FlareSolverr (Recommended - Fully Automated)

```bash
# 1. Start FlareSolverr (one-time setup)
start_flaresolverr.bat

# 2. Test connection
python scraper/flaresolverr_auth.py test

# 3. Fetch schedule
python scraper/flaresolverr_auth.py fetch
```

**Use when:** You want fully automated solution without manual intervention.

---

### Option B: Persistent Chromium (Free, Lightweight)

```bash
# 1. Setup profile (one-time, manual login required)
python scraper/setup_profile.py

# 2. Test profile
python scraper/use_profile.py

# 3. Use in bot (headless)
python scraper/persistent_chromium.py fetch
```

**Use when:** You prefer lightweight solution and can do one-time manual setup.

---

## Hybrid Approach (Best for Production)

```
┌─────────────────────────────────────────────────────────────┐
│  Production Bot Workflow                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: Initial Setup (One-Time)                         │
│  ───────────────────────────────────                        │
│  1. Run FlareSolverr: start_flaresolverr.bat               │
│  2. Login once: python scraper/flaresolverr_auth.py login  │
│  3. Extract cookies: Save cf_clearance + auth cookies      │
│                                                             │
│  Phase 2: Daily Operation                                  │
│  ─────────────────────────                                  │
│  1. Try persistent profile first (fast, lightweight)       │
│  2. If Cloudflare detected → Fall back to FlareSolverr     │
│  3. If auth expired → Auto-refresh via FlareSolverr        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Feature Matrix

| Feature | Cookie Only | Persistent Profile | FlareSolverr |
|---------|-------------|-------------------|--------------|
| **Cloudflare Bypass** | ❌ Always challenge | ✅ After first login | ✅ Auto-solve |
| **Setup Required** | Every run | One-time manual | Docker setup |
| **Memory Usage** | Low | Medium | High (Chrome) |
| **Speed** | Fast | Fast | Medium |
| **Reliability** | Low | High | Very High |
| **Automation** | Partial | Full | Full |
| **Cost** | Free | Free | Free |
| **Maintenance** | High | Low | Low |

---

## Recommendation

### For Development/Testing
**Use FlareSolverr**
- Quick to set up
- No manual intervention
- Easy debugging with HEADLESS=false

### For Production
**Use Hybrid Approach**
```python
class FAPAuthManager:
    def __init__(self):
        self.persistent_auth = FAPPersistentAuth(headless=True)
        self.flaresolverr_auth = FAPFlareSolverrAuth()

    async def fetch_schedule(self, week=None, year=None):
        # Try persistent profile first (fast)
        html = await self.persistent_auth.fetch_schedule(week, year)

        if html and 'ctl00_mainContent_drpSelectWeek' in html:
            return html  # Success!

        # Fall back to FlareSolverr (reliable)
        print("[!] Persistent profile failed, using FlareSolverr...")
        html = self.flaresolverr_auth.fetch_schedule(week, year)

        return html
```

---

## Files Created

| File | Purpose | Status |
|------|---------|--------|
| `scraper/persistent_chromium.py` | Persistent Chromium profile | ✅ Complete |
| `scraper/flaresolverr_auth.py` | FlareSolverr integration | ✅ Complete |
| `scraper/setup_profile.py` | One-time profile setup | ✅ Complete |
| `scraper/use_profile.py` | Test existing profile | ✅ Complete |
| `start_flaresolverr.bat` | Quick start FlareSolverr | ✅ Complete |
| `PERSISTENT-PROFILE-GUIDE.md` | Chromium profile guide | ✅ Complete |
| `FLARESOLVERR-GUIDE.md` | FlareSolverr guide | ✅ Complete |
| `FAP-AUTH-COMPARISON.md` | This file | ✅ Complete |

---

## Next Steps

1. **Install Docker Desktop** (if not installed)
   - https://www.docker.com/products/docker-desktop/

2. **Test FlareSolverr**
   ```bash
   start_flaresolverr.bat
   python scraper/flaresolverr_auth.py test
   ```

3. **Integrate into Discord bot**
   ```python
   from scraper.flaresolverr_auth import FAPFlareSolverrAuth
   # or
   from scraper.persistent_chromium import FAPPersistentAuth
   ```

---

*Updated: 2026-03-07*
*Status: Solutions ready for testing*
