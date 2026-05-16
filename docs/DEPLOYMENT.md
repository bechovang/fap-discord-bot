# Deployment Guide
## FAP Discord Bot - DigitalOcean Deployment

**Version:** 2.0
**Date:** 2026-05-14
**Target Platform:** DigitalOcean VPS (GitHub Education)
**Document Status:** Updated

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Docker Configuration](#docker-configuration)
6. [Environment Variables](#environment-variables)
7. [Proxy Setup](#proxy-setup)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Lessons Learned](#lessons-learned)
11. [Cost Analysis](#cost-analysis)

---

## Deployment Overview

### What We're Deploying

```
+-------------------------------------------------------------+
|                    DIGITAL OCEAN DROPLET                     |
|                  (Ubuntu 22.04, Singapore)                   |
+-------------------------------------------------------------+
|                                                              |
|  +-------------------------------------------------------+  |
|  |              DOCKER ENGINE                             |  |
|  |  +--------------------------------------------------+ |  |
|  |  |  fap-discord-bot container                        | |  |
|  |  |  - Python 3.11                                    | |  |
|  |  |  - Camoufox (Firefox anti-detect browser)         | |  |
|  |  |  - Xvfb virtual display                           | |  |
|  |  |  - Discord Bot                                    | |  |
|  |  |  - SQLite Database                                | |  |
|  |  |  - Background Scheduler                           | |  |
|  |  |  - HTML Parsers (BeautifulSoup)                   | |  |
|  |  +--------------------------------------------------+ |  |
|  |                                                         |  |
|  |  Volumes:                                               |  |
|  |  - ./data -> /app/data (cookies, database, profile)    |  |
|  |  - ./logs -> /app/logs                                 |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

### Key Differences from v1

| Aspect | v1 (Old) | v2 (Current) |
|--------|----------|-------------|
| **Browser** | FlareSolverr (Chrome) | Camoufox (Firefox anti-detect) |
| **Architecture** | 2 containers | 1 container |
| **Cloudflare Bypass** | External service | Built-in browser |
| **Data Fetching** | aiohttp with cookies | Browser page.goto() |
| **Project Path** | /root/fap-discord-bot | /opt/fap-bot |
| **Session Management** | Cookie file only | Browser kept open + cookie backup |

---

## Architecture

### Why Camoufox Instead of FlareSolverr?

The project went through 3 iterations of browser automation:

1. **FlareSolverr** (Chrome-based proxy service) — Failed because it couldn't handle the multi-step FeID OAuth redirect chain (PKCE mismatch between FlareSolverr's browser and our HTTP client).

2. **patchright** (Patched Chromium) — Login worked but Cloudflare Turnstile never resolved on datacenter IPs. `navigator.webdriver=False` wasn't enough.

3. **Camoufox** (Firefox-based anti-detect) — Final solution. Works because:
   - Firefox TLS fingerprint is harder to detect than Chromium's
   - Built-in humanize mode for mouse movement simulation
   - Explicit Turnstile checkbox clicking
   - Can be paired with residential proxies

### Single Container Design

```
+-------------------------------------------------------------+
|              fap-discord-bot container                        |
+-------------------------------------------------------------+
|                                                              |
|  Xvfb :99 (virtual display)                                 |
|    |                                                         |
|    v                                                         |
|  Camoufox (Firefox anti-detect)                              |
|    |- Persistent profile (cleaned on each login)             |
|    |- Residential proxy                                      |
|    |- Cloudflare Turnstile auto-click                        |
|    |- FeID form fill + submit                                |
|    |                                                         |
|    v                                                         |
|  FAPAutoLogin (auto_login_feid.py)                           |
|    |- Login flow automation                                  |
|    |- Page fetching via browser (page.goto + page.content)   |
|    |- Cookie export to JSON backup                           |
|    |                                                         |
|    v                                                         |
|  FAPAuth (auth.py)                                           |
|    |- Auto-refresh on session expiry                         |
|    |- Retry with SessionValidator                            |
|    |                                                         |
|    v                                                         |
|  Discord Bot                                                 |
|    |- Slash commands (schedule, grade, exam, attendance)     |
|    |- Background scheduler (attendance, weekly, keepalive)   |
|    |- SQLite database                                        |
+-------------------------------------------------------------+
```

### Why Browser Stays Open After Login

Cloudflare's `cf_clearance` cookie is tied to:
1. **IP address** — must match the IP used when solving the challenge
2. **TLS fingerprint (JA3/JA4)** — must match the browser's fingerprint
3. **User-Agent** — must match exactly

No Python HTTP client (aiohttp, requests, curl_cffi) can reproduce Firefox's exact TLS fingerprint. The only way to fetch pages from a Cloudflare-protected site is using the same browser that solved the challenge. So after login, the browser stays open and uses `page.goto()` + `page.content()` for data fetching.

---

## Prerequisites

### Before You Start

- [ ] DigitalOcean account with credits (GitHub Student Developer Pack: $200)
- [ ] Discord Bot Token from [Discord Developer Portal](https://discord.com/developers/applications)
- [ ] FAP credentials (FeID email and password)
- [ ] SSH key pair (ed25519 recommended)
- [ ] Residential proxy (required for datacenter IP)

### Droplet Requirements

| Usage | RAM | CPU | Disk | Price |
|-------|-----|-----|------|-------|
| **Minimum** | 1GB | 1 vCPU | 25GB | $6/mo |
| **Recommended** | 2GB | 1 vCPU | 50GB | $12/mo |

Camoufox + Firefox needs ~300-400MB RAM during active scraping. 1GB droplet works but is tight.

---

## Step-by-Step Deployment

### Phase 1: Create Droplet (5 minutes)

1. Go to DigitalOcean → Create → Droplets
2. **Image:** Ubuntu 22.04 LTS x64
3. **Plan:** Basic $6/month (1GB RAM, 1 vCPU)
4. **Region:** Singapore (sgp1) — closest to Vietnam
5. **Authentication:** SSH Key (upload your public key)
6. **Hostname:** fap-bot

### Phase 2: Server Setup (10 minutes)

```bash
# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl enable docker

# Install useful tools
apt install -y git curl vim htop

# Set timezone
timedatectl set-timezone Asia/Ho_Chi_Minh
```

### Phase 3: Deploy Bot Code (10 minutes)

```bash
# Create project directory
mkdir -p /opt/fap-bot
cd /opt/fap-bot

# Clone repository
git clone https://github.com/bechovang/fap-discord-bot.git .

# Create .env file
cp .env.example .env
nano .env
```

### Phase 4: Configure Environment (5 minutes)

Edit `/opt/fap-bot/.env`:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
FAP_USERNAME=your_feid_email
FAP_PASSWORD=your_password
ENCRYPTION_KEY=generate_with_python

# Important
HEADLESS=true
FAP_CAMPUS=4
PROXY_URL=http://user:pass@host:port

# Optional
FAP_STUDENT_ID=SE123456
SCHEDULER_TIMEZONE=Asia/Ho_Chi_Minh
DEFAULT_CHANNEL_ID=123456789
LOG_LEVEL=INFO
```

Generate encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Phase 5: Build and Start (5 minutes)

```bash
cd /opt/fap-bot

# Build and start
docker compose up -d --build

# Check logs
docker logs fap-discord-bot -f

# Should see:
# - "Starting Camoufox (Firefox anti-detect) with persistent profile..."
# - "Login successful! Schedule page accessible!"
# - "Bot is ready!"
```

### Phase 6: Verify (2 minutes)

1. Go to your Discord server
2. Type `/ping` — bot should respond
3. Type `/schedule today` — should show schedule or "No classes"
4. Type `/status` — should show bot and session status

---

## Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Firefox/Camoufox dependencies + Xvfb for virtual display
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth \
    libgtk-3-0 libx11-xcb1 libasound2 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the Camoufox browser binary (Firefox-based anti-detect)
RUN python3 -m camoufox fetch

COPY . .
RUN mkdir -p data logs

ENV DISPLAY=:99
ENV PYTHONPATH=/app

CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & until [ -e /tmp/.X99-lock ]; do sleep 0.1; done; python fap-discord-bot/main.py"]
```

**Key points:**
- `xvfb xauth` — Virtual display server (Camoufox needs a display even in headless mode)
- `libgtk-3-0 libx11-xcb1 libasound2` — Firefox runtime dependencies
- `python3 -m camoufox fetch` — Downloads Firefox binary during build (saves runtime startup time)
- `DISPLAY=:99` — Tells Firefox which X display to use
- CMD starts Xvfb first, waits for lock file, then starts bot

### Docker Compose

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
      - FAP_STUDENT_ID=${FAP_STUDENT_ID}
      - FAP_CAMPUS=${FAP_CAMPUS:-4}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DATABASE_PATH=data/fap.db
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - SCHEDULER_TIMEZONE=${SCHEDULER_TIMEZONE:-Asia/Ho_Chi_Minh}
      - DEFAULT_CHANNEL_ID=${DEFAULT_CHANNEL_ID}
      - HEADLESS=false
      - PROXY_URL=${PROXY_URL:-}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

**Note:** `HEADLESS=false` in docker-compose.yml is the default. The actual headless mode is controlled by the `HEADLESS` env var in `.env` file. When `HEADLESS=true`, Camoufox uses its built-in virtual display (`headless="virtual"` mode).

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token from Developer Portal | `MTIzNDU2Nzg5...` |
| `FAP_USERNAME` | FeID email | `student@fe.edu.vn` |
| `FAP_PASSWORD` | FeID password | `Eg8$Fw1$` |
| `ENCRYPTION_KEY` | Fernet key for encrypting stored passwords | Auto-generated |

### Important

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLESS` | `false` | `true` = Camoufox virtual display mode, `false` = Xvfb display |
| `PROXY_URL` | (empty) | Residential proxy URL. **Required** on datacenter IPs |
| `FAP_CAMPUS` | `4` | Campus ID for FAP |
| `FAP_STUDENT_ID` | (empty) | Student ID for grade/attendance commands |

### .env File Rules

**CRITICAL:** `.env` file values are read literally by Docker Compose. `$` does NOT need escaping:

```env
# CORRECT (.env file):
FAP_PASSWORD=Eg8$Fw1$

# WRONG (.env file — do NOT do this):
FAP_PASSWORD=Eg8$$Fw1$$
```

However, if you put values directly in `docker-compose.yml` under `environment:`, THEN you must escape `$` as `$$`:

```yaml
# In docker-compose.yml, escape is needed:
environment:
  - FAP_PASSWORD=Eg8$$Fw1$$
```

### Applying .env Changes

```bash
# WRONG — does NOT reload .env:
docker restart fap-discord-bot

# CORRECT — recreates container with new env:
cd /opt/fap-bot && docker compose up -d --force-recreate
```

---

## Proxy Setup

### Why Residential Proxy is Required

Cloudflare Turnstile checks IP reputation. Datacenter IPs (DigitalOcean, AWS, etc.) have low reputation scores, causing Turnstile to fail silently — the challenge never resolves, no error is shown.

### Proxy Configuration

```env
PROXY_URL=http://username:password@proxy-host:port
```

**Important:** Always use `http://` scheme, even for "HTTPS" proxies. The scheme refers to the connection TO the proxy, not the traffic through it. Using `https://` causes `SSL: UNEXPECTED_EOF_WHILE_READING`.

### Runtime Proxy Change from Discord

The bot now supports proxy rotation directly from Discord without editing `.env`.

Available commands:

- `/config proxy` - Set a runtime proxy override and immediately test session refresh/login
- `/config proxy-clear` - Remove the runtime override and fall back to `PROXY_URL` from `.env`
- `/config status` - Show the currently active proxy summary

How it works:

- The runtime override is stored in `data/runtime_config.json`
- This override takes precedence over `PROXY_URL` from `.env`
- Provider labels like `HTTPS` should still be entered as `http://user:pass@host:port` internally
- The command response shows whether an immediate refresh/login attempt succeeded
- Attendance checks only run inside real class windows derived from the weekly schedule, and each class remains eligible through 30 minutes after class end
- The bot runs an initial daily check shortly after startup so schedule and snapshot caches are warm before the first normal cycle

### Changing Proxy on Production

```bash
# Update proxy in .env
ssh root@YOUR_IP
cd /opt/fap-bot
nano .env  # Update PROXY_URL

# Rebuild and recreate container
docker compose up -d --build --force-recreate bot

# Check logs for proxy usage
docker logs fap-discord-bot --tail 30 | grep -i proxy
```

Prefer `/config proxy` when you need a fast proxy switch during the day. Edit `.env` when you want the new proxy to survive container rebuilds and remain the baseline configuration.

### Proxy Providers

Recommended residential proxy providers:
- **Webshare** — Good pricing, rotating residential IPs
- **Bright Data** — Enterprise grade, high reliability
- **Oxylabs** — Large pool, good for automation

---

## Monitoring & Maintenance

### Essential Commands

```bash
# SSH into server
ssh -i ~/.ssh/id_ed25519_fapbot root@68.183.233.253

# Check container status
docker ps
docker stats --no-stream

# View logs
docker logs fap-discord-bot -f                    # Follow logs
docker logs fap-discord-bot --tail 100            # Last 100 lines
docker logs fap-discord-bot --since 1h            # Last hour
docker logs fap-discord-bot 2>&1 | grep -i error  # Errors only

# Restart / Redeploy
docker compose up -d --force-recreate              # Recreate with new env
docker compose up -d --build --force-recreate      # Rebuild + recreate

# Important:
# This project copies source code into the image at build time.
# If you changed Python code, use `--build --force-recreate`, not only `--force-recreate`.

# Cleanup
docker system prune -af --volumes                  # Free disk space

# Check resources
df -h                          # Disk space
free -h                        # Memory
du -sh /opt/fap-bot/data/      # Data directory size
```

### Health Check Script

```bash
#!/bin/bash
# /opt/fap-bot/health-check.sh

if ! docker ps | grep -q "fap-discord-bot.*Up"; then
    echo "$(date): Bot is down! Restarting..." >> /opt/fap-bot/health.log
    cd /opt/fap-bot && docker compose up -d --force-recreate
else
    echo "$(date): Bot is healthy" >> /opt/fap-bot/health.log
fi
```

```bash
chmod +x /opt/fap-bot/health-check.sh

# Add to crontab (every 5 minutes):
crontab -e
# */5 * * * * /opt/fap-bot/health-check.sh
```

### Backup

```bash
#!/bin/bash
# /opt/fap-bot/backup.sh

BACKUP_DIR="/opt/fap-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

cp /opt/fap-bot/data/fap.db "$BACKUP_DIR/fap_$DATE.db"
cp /opt/fap-bot/.env "$BACKUP_DIR/env_$DATE.bak"

# Keep last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.bak" -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR"
```

### Update Bot Code

```bash
cd /opt/fap-bot
git pull origin master
docker compose up -d --build --force-recreate
docker logs fap-discord-bot -f
```

---

## Troubleshooting

### Common Issues & Solutions

#### Issue 1: "No classes scheduled!" / "No terms found" but bot is running

**Symptom:** Slash commands return empty results even though bot logged in successfully.

**Root Cause:** FAP session expired mid-flight. `_fetch_page()` was returning login page HTML instead of data, and parsers couldn't find expected elements.

**Diagnosis:**
```bash
docker logs fap-discord-bot --tail 50 | grep -i "redirect\|expired\|login button"
```

**Solution:** The code now detects expired sessions automatically (4 checks in `_fetch_page()`) and triggers re-login. If it persists:
1. Check if proxy is still active: `docker logs fap-discord-bot | grep -i proxy`
2. Force re-login: `docker compose up -d --build --force-recreate bot`

#### Issue 2: FeID Login Error "incorrect username or password"

**Symptom:** Logs show "FeID login error: Ten tai khoan hoac mat khau khong dung"

**Root Cause:** Password with `$` character is being truncated or double-escaped in `.env`.

**Diagnosis:**
```bash
# Check what the container sees:
docker exec fap-discord-bot env | grep FAP_PASSWORD
```

**Solution:**
- In `.env` file: use literal `$` — `FAP_PASSWORD=Eg8$Fw1$`
- In `docker-compose.yml` environment section: escape `$$` — `FAP_PASSWORD=Eg8$$Fw1$$`
- After any change: `docker compose up -d --force-recreate`

#### Issue 3: Cloudflare Challenge Never Resolves

**Symptom:** Logs show "Waiting for Cloudflare challenge..." repeatedly for 60+ seconds.

**Root Cause:** Datacenter IP has low reputation, or proxy is expired/misconfigured.

**Diagnosis:**
```bash
docker logs fap-discord-bot | grep -i "cloudflare\|turnstile\|challenge"
```

**Solutions:**
1. Verify proxy is working: `docker logs fap-discord-bot | grep "Using proxy"`
2. Test proxy manually from server:
   ```bash
   curl -x http://user:pass@proxy:port https://fap.fpt.edu.vn -I
   ```
3. Replace expired proxy in `.env` and rebuild the container, or switch immediately with `/config proxy`
4. Ensure using `http://` scheme (not `https://`) for proxy URL

#### Issue 4: "cannot open display: :99"

**Symptom:** Browser crash with display error.

**Root Cause:** Xvfb not ready when Camoufox starts, or DISPLAY conflict with Camoufox virtual mode.

**Solution:**
1. Ensure `HEADLESS=true` in `.env` (Camoufox uses built-in virtual display)
2. Code automatically clears DISPLAY env var when in virtual mode
3. If still failing, check Xvfb is in Dockerfile CMD

#### Issue 5: Browser Timeout on Startup

**Symptom:** Browser hangs during launch, eventually times out.

**Root Cause:** Stale Firefox profile lock files from previous crash.

**Solution:** Code automatically removes lock files and cleans profile before login. If persistent:
```bash
rm -rf /opt/fap-bot/data/firefox_profile/
docker compose restart
```

#### Issue 6: `docker restart` Doesn't Apply Changes

**Symptom:** Changed `.env` but bot still uses old values.

**Root Cause:** `docker restart` restarts the existing container process with its original environment. New `.env` values are only loaded when creating a new container.

**Solution:**
```bash
# Always use this instead of docker restart:
cd /opt/fap-bot && docker compose up -d --force-recreate
```

#### Issue 7: `No space left on device` During Build

**Symptom:** Docker build fails with disk space error.

**Solution:**
```bash
docker system prune -af --volumes
docker builder prune -af
```

#### Issue 8: Grade/Attendance Returns Empty

**Symptom:** Commands show no data.

**Root Cause:** Missing `FAP_STUDENT_ID` or `FAP_CAMPUS` in `.env`.

**Solution:**
```env
FAP_STUDENT_ID=SE123456
FAP_CAMPUS=4
```

---

## Lessons Learned

### 1. Session Expiry Detection is Critical

When FAP session expires, the server redirects to `Default.aspx` (login page). If the fetch code doesn't detect this, login page HTML gets passed to parsers which return empty results. Users see "No classes" or "No terms found" without any error indication.

**What we learned:** Always validate that fetched content is actually the expected data, not just "HTTP 200 OK". Check for:
- Unexpected URL redirects (Default.aspx when requesting ScheduleOfWeek.aspx)
- Login form elements in page content (`btnloginFeId`)
- Cloudflare challenge titles

### 2. Fresh Browser Profile Beats Persistent

Cloudflare fingerprints accumulate over time in Firefox profiles. Persistent profiles that work initially start getting flagged after days/weeks. Similar to how incognito mode works for manual browsing.

**What we learned:** Clear the entire profile directory before each login. The slight overhead of re-solving Cloudflare is worth the reliability gain.

### 3. Docker Environment Variable Gotchas

Three separate traps:
1. `.env` file reads `$` literally — no escaping needed
2. `docker-compose.yml` environment section substitutes `$` — must escape to `$$`
3. `docker restart` does NOT reload `.env` — must `docker compose up -d --force-recreate`

### 4. DISPLAY Conflicts with Virtual Display

Running both external Xvfb (in CMD) and Camoufox's built-in virtual display (`headless="virtual"`) creates a conflict. The DISPLAY env var set by CMD overrides Camoufox's virtual display setup.

**What we learned:** When `HEADLESS=true`, unset DISPLAY so Camoufox manages its own display server.

### 5. Proxy is Non-Negotiable for Datacenter IPs

Cloudflare Turnstile's IP reputation check is the hardest gate to pass. No amount of browser fingerprinting can overcome a datacenter IP. Residential proxy is the single most important factor for reliability.

### 6. The Browser IS the HTTP Client

We tried multiple approaches to extract cookies from the browser and reuse them with Python HTTP clients. All failed because Cloudflare ties `cf_clearance` to the exact TLS fingerprint of the browser that solved the challenge. The browser must stay open and handle all subsequent requests.

---

## Cost Analysis

### Monthly Costs

| Service | Price | Notes |
|---------|-------|-------|
| **DigitalOcean Droplet** | $6/mo (1GB) | Sufficient for single user |
| **Residential Proxy** | $5-15/mo | Rotating residential IPs |
| **Total** | $11-21/mo | |

### With GitHub Student Pack ($200 Credit)

| Item | Calculation | Result |
|------|------------|--------|
| DO Credit | $200 | $200 |
| DO Cost | $6/mo | ~33 months |
| Proxy | $5-15/mo | Not covered by credit |

---

## Quick Reference

### Server Info

```
Droplet: fap-bot (ID: 570186178)
IP: 68.183.233.253
SSH: ssh -i ~/.ssh/id_ed25519_fapbot root@68.183.233.253
Project: /opt/fap-bot/
Container: fap-discord-bot
```

### Essential Commands

| Command | Purpose |
|---------|---------|
| `ssh -i ~/.ssh/id_ed25519_fapbot root@68.183.233.253` | SSH into server |
| `docker logs fap-discord-bot -f` | Follow bot logs |
| `docker compose up -d --force-recreate` | Restart with new env |
| `docker compose up -d --build --force-recreate` | Rebuild + restart |
| `docker stats --no-stream` | Resource usage |
| `df -h` | Disk space |
| `free -h` | Memory |

### Deploy Checklist

- [ ] SSH into server
- [ ] `cd /opt/fap-bot`
- [ ] `git pull origin master`
- [ ] Check `.env` is correct (especially `PROXY_URL` and `FAP_PASSWORD`)
- [ ] `docker compose up -d --build --force-recreate`
- [ ] `docker logs fap-discord-bot -f` — verify "Login successful!"
- [ ] Test `/ping` and `/schedule today` in Discord
