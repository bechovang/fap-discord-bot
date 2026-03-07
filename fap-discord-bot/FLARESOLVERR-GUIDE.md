# FAP Authentication - FlareSolverr Solution

## What is FlareSolverr?

**FlareSolverr** is a proxy server that bypasses Cloudflare and DDoS-GUARD protection automatically.

### How it works:

```
┌─────────────────────────────────────────────────────────────┐
│  Your Script                                                │
│  (requests / Python)                                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  FlareSolverr (localhost:8191)                              │
├─────────────────────────────────────────────────────────────┤
│  1. Receives request with target URL                        │
│  2. Launches Chrome with undetected-chromedriver            │
│  3. Navigates to URL                                        │
│  4. Waits for Cloudflare challenge to solve                 │
│  5. Returns: HTML + Cookies + User-Agent                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Option A: Docker (Recommended)

```bash
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest
```

### Option B: Windows Precompiled Binary

1. Download from [FlareSolverr Releases](https://github.com/FlareSolverr/FlareSolverr/releases)
2. Extract `flaresolverr.exe`
3. Run: `flaresolverr.exe`

### Verify Installation

```bash
curl http://localhost:8191
```

Should return: `FlareSolverr is ready!`

---

## Usage

### Step 1: Test Connection

```bash
python scraper/flaresolverr_auth.py test
```

Expected output:
```
============================================================
FAP Authentication via FlareSolverr
============================================================
[.] Creating FlareSolverr session: fap_session
[+] Session created: fap_session
[.] Fetching: https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx
[.] FlareSolverr solving Cloudflare challenge...
[.] Response status: 200
[+] SUCCESS! Schedule page loaded!
[+] Cookies received: X cookies
[+] cf_clearance: eyJhbGciOiJIUzI1Ni...
```

### Step 2: First-Time Login (If Needed)

If FAP requires Google login, run with visible browser:

```bash
# Stop FlareSolverr first
docker stop flaresolverr

# Restart with HEADLESS=false (visible browser)
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  -e HEADLESS=false \
  ghcr.io/flaresolverr/flaresolverr:latest

# Now run login
python scraper/flaresolverr_auth.py login
```

Complete the Google login in the browser window, then press Enter.

### Step 3: Fetch Schedule

```bash
python scraper/flaresolverr_auth.py fetch
```

---

## Use in Discord Bot

```python
from scraper.flaresolverr_auth import FAPFlareSolverrAuth
from scraper.parser import FAPParser

async def get_schedule(week: int = None, year: int = None):
    """Fetch FAP schedule using FlareSolverr"""
    auth = FAPFlareSolverrAuth()
    html = auth.fetch_schedule(week=week, year=year)

    if html:
        parser = FAPParser()
        return parser.parse_schedule(html)
    return None

# In your Discord bot command
@bot.command()
async def schedule(ctx):
    items = await get_schedule(week=1, year=2026)

    if items:
        await ctx.send(f"Found {len(items)} classes")
        # ... send schedule details
    else:
        await ctx.send("Failed to fetch schedule")
```

---

## FlareSolverr API Commands

### sessions.create
```python
payload = {
    "cmd": "sessions.create",
    "session": "fap_session"  # Optional, auto-generated if not provided
}
```
Creates a persistent browser session that maintains cookies.

### request.get
```python
payload = {
    "cmd": "request.get",
    "url": "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx",
    "session": "fap_session",  # Optional, uses existing session
    "maxTimeout": 60000,        # Max wait time (ms)
    "waitInSeconds": 3,         # Wait after challenge solved
}
```

### sessions.destroy
```python
payload = {
    "cmd": "sessions.destroy",
    "session": "fap_session"
}
```
Properly cleanup and free resources.

---

## Comparison: FlareSolverr vs Other Solutions

| Aspect | FlareSolverr | Persistent Profile | CapSolver API |
|--------|--------------|-------------------|---------------|
| **Setup** | Docker/Exe | One-time manual | API key |
| **Cloudflare** | Auto-solve ✅ | Skip after first | Auto-solve ✅ |
| **Auth** | Needs manual once | Needs manual once | Auto ✅ |
| **Reliability** | High ✅ | Medium | High |
| **Cost** | Free ✅ | Free | Paid |
| **Memory** | High (Chrome) | Medium | Low |
| **Best for** | First run | Daily automation | Production |

---

## Troubleshooting

### "Cannot connect to FlareSolverr"
```bash
# Check if running
docker ps | grep flaresolverr

# Check logs
docker logs flaresolverr

# Restart
docker restart flaresolverr
```

### "Cloudflare challenge detected"
This means FlareSolverr failed to solve the challenge. Options:

1. **Update FlareSolverr**: `docker pull ghcr.io/flaresolverr/flaresolverr:latest`
2. **Use visible browser**: Set `HEADLESS=false` to see what's happening
3. **Wait longer**: Increase `maxTimeout` to 120000 (2 minutes)

### "Session expired"
FlareSolverr sessions can time out. Solution:

```python
# Destroy and recreate
auth.destroy_session()
auth.create_session()
```

### Memory Issues
```bash
# Limit memory in Docker
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -m 512m \
  ghcr.io/flaresolverr/flaresolverr:latest

# Or destroy sessions when done
auth.destroy_session()
```

---

## Best Practices

1. **Use sessions for repeated requests**
   - Create session once
   - Reuse for multiple requests
   - Destroy when done

2. **Handle timeouts gracefully**
   ```python
   try:
       html = auth.fetch_schedule()
   except requests.exceptions.Timeout:
       print("[!] Request timed out, retrying...")
   ```

3. **Monitor FlareSolverr health**
   ```bash
   # Check active sessions
   curl -X POST http://localhost:8191/v1 \
     -H "Content-Type: application/json" \
     -d '{"cmd": "sessions.list"}'
   ```

4. **Use for initial setup, then persistent profile**
   ```
   First run: FlareSolverr → Get cf_clearance + cookies
   Subsequent: Use persistent profile with saved cookies
   ```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | info | debug, info, warning, error |
| `HEADLESS` | true | Run browser invisibly |
| `DISABLE_MEDIA` | false | Don't load images/CSS (faster) |
| `PROXY_URL` | none | Proxy for outgoing requests |
| `CAPTCHA_SOLVER` | none | Auto-solve CAPTCHAs (experimental) |

Example with variables:
```bash
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=debug \
  -e HEADLESS=false \
  -e DISABLE_MEDIA=true \
  ghcr.io/flaresolverr/flaresolverr:latest
```

---

## Architecture for FAP Bot

```
┌─────────────────────────────────────────────────────────────┐
│  Discord Bot                                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FAPFlareSolverrAuth                                 │  │
│  │  - create_session() (once at startup)                │  │
│  │  - fetch_schedule() (reused session)                 │  │
│  │  - destroy_session() (on shutdown)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FlareSolverr Docker Container                        │  │
│  │  - Handles Cloudflare automatically                   │  │
│  │  - Maintains browser session                          │  │
│  │  - Returns HTML + cookies                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FAP Parser                                          │  │
│  │  - Parse HTML from FlareSolverr                       │  │
│  │  - Extract schedule data                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Sources

- [FlareSolverr GitHub](https://github.com/FlareSolverr/FlareSolverr)
- [Docker Hub](https://hub.docker.com/r/flaresolverr/flaresolverr)

---

*Updated: 2026-03-07*
*Status: Ready for testing*
