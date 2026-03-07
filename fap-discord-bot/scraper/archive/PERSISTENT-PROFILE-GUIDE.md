# FAP Authentication - Persistent Chromium Profile Solution

## What This Does

**OLD APPROACH (Cookie extraction):**
```
Login → Save cookies → Load cookies → Cloudflare: "New browser!" → CHALLENGE
```

**NEW APPROACH (Persistent Chromium profile):**
```
Login → Save ENTIRE Chromium profile → Load SAME profile → Cloudflare: "Same browser!" → SKIP
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  SETUP (One-Time)                                           │
├─────────────────────────────────────────────────────────────┤
│  $ python scraper/setup_profile.py                          │
│                                                             │
│  1. Chromium starts with user_data_dir                      │
│  2. You complete login manually                             │
│  3. Cloudflare verifies browser fingerprint                 │
│  4. Entire profile saved to disk:                           │
│     - Cookies (cf_clearance + auth)                         │
│     - LocalStorage                                           │
│     - SessionStorage                                         │
│     - Cache                                                 │
│     - Browser fingerprint data                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  USE (Every time)                                           │
├─────────────────────────────────────────────────────────────┤
│  $ python scraper/use_profile.py                            │
│                                                             │
│  1. Chromium starts with SAME user_data_dir                 │
│  2. Load SAME profile = SAME fingerprint                    │
│  3. Navigate to FAP                                         │
│  4. Cloudflare recognizes browser → SKIP CHALLENGE ✅       │
│  5. Fetch schedule directly                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage

### Step 1: Setup Profile (One-Time)

```bash
python scraper/setup_profile.py
```

**What happens:**
1. Browser window opens
2. Navigate to FAP
3. You complete Google login
4. Wait for schedule page to load
5. Press Enter
6. Profile saved to `data/chrome_profile/`

### Step 2: Test Profile

```bash
python scraper/use_profile.py
```

**Expected result:**
- Browser opens
- Navigates to FAP
- **NO Cloudflare challenge** ✅
- Schedule page loads directly

### Step 3: Use in Bot

```python
from scraper.persistent_chromium import FAPPersistentAuth

async def get_schedule():
    auth = FAPPersistentAuth(headless=True)  # Headless for bot
    html = await auth.fetch_schedule(week=1, year=2026)

    if html:
        from scraper.parser import FAPParser
        parser = FAPParser()
        return parser.parse_schedule(html)
    return None
```

---

## Key Differences

| Aspect | Cookie Extraction | Persistent Profile |
|--------|------------------|-------------------|
| **What's saved** | Cookies only | Entire browser state |
| **Cloudflare** | Challenges every time | Skips after first login ✅ |
| **Fingerprint** | Different each run | Same every run ✅ |
| **Complexity** | Simple | Slightly more complex |
| **Reliability** | Medium | High ✅ |

---

## Profile Contents

```
data/chrome_profile/
├── Default/
│   ├── Cookies             # Browser cookies (cf_clearance, auth)
│   ├── Local Storage/      # localStorage data
│   ├── Session Storage/    # sessionStorage data
│   ├── Cache/              # HTTP cache
│   └── [browser fingerprint data]
└── [other Chromium profile data]
```

---

## Troubleshooting

### "Profile already exists"
```bash
# Profile exists from previous setup
# Either use it:
python scraper/use_profile.py

# Or delete and re-setup:
rm -rf data/chrome_profile
python scraper/setup_profile.py
```

### "Cloudflare detected during use"
```
This means profile is corrupted or expired.

Solution:
rm -rf data/chrome_profile
python scraper/setup_profile.py
```

### "Session expired (auth cookies)"
```
The profile is still valid for Cloudflare,
but auth cookies need refresh.

Solution:
1. Delete profile: rm -rf data/chrome_profile
2. Re-setup: python scraper/setup_profile.py
3. Or: Add auto-relogin mechanism to bot
```

---

## Comparison with Other Solutions

| Solution | Cloudflare | Setup | Automation |
|----------|------------|-------|------------|
| **Persistent Profile** | Skip ✅ | One-time | Full ✅ |
| Cookie Extraction | Challenge ❌ | Every run | Partial |
| CapSolve API | Solve ✅ | Complex | Full ✅ |
| Manual Login | Challenge ❌ | Every run | None |

---

## Why This Works

```
Cloudflare Turnstile checks:
1. Is cf_clearance cookie present?
2. Does browser fingerprint match?

If BOTH = YES → Skip challenge ✅

Persistent profile ensures:
- cf_clearance cookie is present (from first login)
- Browser fingerprint matches (same profile)
```

---

## Best Practices

1. **Keep profile private**
   - Don't share `data/camoufox_profile/` folder
   - Contains your authentication tokens

2. **Backup profile**
   ```bash
   cp -r data/camoufox_profile data/camoufox_profile.backup
   ```

3. **Monitor profile health**
   - Test regularly with `use_profile.py`
   - Re-setup if Cloudflare returns

4. **Use in production**
   ```python
   # Bot runs in headless mode
   auth = FAPPersistentAuth(headless=True)
   html = await auth.fetch_schedule()
   ```

---

## Next Steps

1. **Test the setup:**
   ```bash
   rm -rf data/chrome_profile  # Clean start
   python scraper/setup_profile.py
   python scraper/use_profile.py
   ```

2. **Integrate into bot:**
   ```python
   # bot/bot.py
   from scraper.persistent_chromium import FAPPersistentAuth

   async def schedule_command(ctx):
       auth = FAPPersistentAuth(headless=True)
       items = await auth.fetch_schedule()
       # ... send to Discord
   ```

3. **Monitor expiry:**
   - Test daily for 1 week
   - Note when profile needs refresh
   - Document expected lifetime

---

*Updated: 2026-03-07*
*Status: Ready for testing*
