# Deployment Guide
## FAP Discord Bot - DigitalOcean Deployment

**Version:** 1.0
**Date:** 2026-03-07
**Target Platform:** DigitalOcean VPS (GitHub Education)
**Document Status:** Ready

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [DigitalOcean GitHub Education Benefits](#digitalocean-github-education-benefits)
3. [Droplet Selection Guide](#droplet-selection-guide)
4. [Deployment Architecture](#deployment-architecture)
5. [Prerequisites](#prerequisites)
6. [Step-by-Step Deployment](#step-by-step-deployment)
7. [Docker Configuration](#docker-configuration)
8. [FlareSolverr Setup](#flaresolverr-setup)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Cost Analysis](#cost-analysis)
11. [Troubleshooting](#troubleshooting)

---

## Deployment Overview

### Deployment Target
- **Platform:** DigitalOcean VPS
- **Offer:** GitHub Student Developer Pack
- **Credit:** $200 USD (1 year validity)
- **Region:** Singapore (sgp1) - Closest to Vietnam

### What We're Deploying

```
┌─────────────────────────────────────────────────────────────┐
│                    DIGITAL OCEAN DROPLET                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DOCKER ENGINE                             │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │  fap-discord-bot container                      │   │    │
│  │  │  - Python 3.11                                  │   │    │
│  │  │  - Discord Bot                                   │   │    │
│  │  │  - SQLite Database                               │   │    │
│  │  │  - Background Scheduler                          │   │    │
│  │  │  - HTML Parsers                                  │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  │                                                        │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │  flaresolverr container                         │   │    │
│  │  │  - Cloudflare bypass                            │   │    │
│  │  │  - Chrome headless                              │   │    │
│  │  │  - WebSocket API                                │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  Volumes:                                                     │
│  - ./data → /app/data (bot data, database)                   │
│                                                               │
│  Network:                                                     │
│  - Bridge network for container communication                 │
│  - Port 8191 exposed for FlareSolverr (internal only)        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## DigitalOcean GitHub Education Benefits

### GitHub Student Developer Pack - DigitalOcean Offer

#### What You Get

| Benefit | Details | Value |
|---------|---------|-------|
| **Platform Credit** | $200 USD credit | **Free** |
| **Validity** | 12 months from activation | **1 year** |
| **Eligibility** | GitHub Student Developer Pack members | **Verified students** |
| **Credit Card Required** | ❌ No - only GitHub account needed | **No CC needed** |
| **Auto-renewal** | ❌ No - one-time benefit | **Not recurring** |

#### How to Claim

1. **Join GitHub Student Developer Pack**
   - Go to: https://education.github.com/pack
   - Sign up with your school email (`.edu` preferred)
   - Upload proof of enrollment (student ID, transcript, etc.)
   - Wait for approval (usually 1-7 days)

2. **Link GitHub to DigitalOcean**
   - After approval, go to GitHub Student Pack benefits page
   - Find "DigitalOcean" offer
   - Click "Claim" or "Activate"
   - You'll be redirected to DigitalOcean
   - Authorize GitHub to link your account
   - $200 credit will be automatically added!

3. **Verify Credit**
   - Login to DigitalOcean: https://cloud.digitalocean.com/
   - Go to Billing → Credits
   - You should see $200 in available credits

### Important Notes

⚠️ **Critical Information:**
- Credits expire after 12 months
- Only for **new** DigitalOcean users (existing accounts don't qualify)
- Credits are applied to hourly usage automatically
- If you exceed $200, you'll be charged for the overage
- You can upgrade/downgrade droplets anytime

---

## Droplet Selection Guide

### Resource Requirements Analysis

#### FAP Discord Bot Resource Needs

| Component | RAM | CPU | Disk | Notes |
|-----------|-----|-----|------|-------|
| **Python Runtime** | ~50-100MB | Low | ~100MB | Base Python + libraries |
| **Discord.py** | ~20-50MB | Low | - | Async I/O, efficient |
| **Playwright/Browser** | ~200-400MB | Medium | ~100MB | When actively scraping |
| **SQLite Database** | ~5-10MB | Low | ~10MB (grows slowly) | Small for MVP |
| **Background Scheduler** | ~10-20MB | Low | - | APScheduler overhead |
| **HTML Parsing** | ~20-50MB | Low | - | BeautifulSoup/lxml |
| **Buffer/Caches** | ~50-100MB | Low | - | Schedule/grade caches |
| **OS Overhead** | ~100-200MB | Low | ~1GB | Ubuntu base system |

#### Total Estimated Requirements

| Usage Scenario | RAM Needed | CPU Needed | Recommended Droplet |
|----------------|------------|------------|---------------------|
| **Idle** (no active scraping) | ~300-400MB | Minimal | Basic 512MB ($4/mo) |
| **Light Load** (1 user, occasional scraping) | ~400-600MB | 1 vCPU | Basic 1GB ($6/mo) **⭐ RECOMMENDED** |
| **Medium Load** (5-10 users, regular scraping) | ~600MB-1GB | 1 vCPU | Basic 2GB ($12/mo) |
| **Heavy Load** (10+ users, constant scraping) | 1-2GB | 2 vCPU | General Purpose 4GB ($24/mo) |

### DigitalOcean Droplet Comparison (2025)

| Droplet Type | RAM | CPU | Disk | Transfer | Price/mo | $200 Credit Duration |
|--------------|-----|-----|------|-----------|----------|---------------------|
| **Basic 512MB** | 512 MB | 1 vCPU | 25 GB SSD | 1 TB | **$4** | ~50 months ✅ |
| **Basic 1GB** | 1 GB | 1 vCPU | 25 GB SSD | 2 TB | **$6** | ~33 months ✅ |
| **Basic 2GB** | 2 GB | 1 vCPU | 50 GB SSD | 3 TB | **$12** | ~16 months ✅ |
| **Basic 4GB** | 4 GB | 2 vCPU | 80 GB SSD | 4 TB | **$24** | ~8 months |
| **Basic 8GB** | 8 GB | 4 vCPU | 160 GB SSD | 5 TB | **$48** | ~4 months |
| **General 4GB** | 4 GB | 2 vCPU (better) | 25 GB SSD | 4 TB | **$24** | ~8 months |
| **General 8GB** | 8 GB | 4 vCPU (better) | 25 GB SSD | 5 TB | **$48** | ~4 months |

**Legend:** ✅ = Covered by $200 credit for full academic year

---

## 🎯 RECOMMENDATION

### For FAP Discord Bot (MVP - Single User)

**BEST VALUE: Basic 1GB RAM ($6/month)**

**Why:**
- ✅ Sufficient RAM for single-user bot
- ✅ Enough CPU for background tasks
- ✅ $200 credit covers ~33 months (2+ years!)
- ✅ Room to grow to 5-10 users
- ✅ Lowest cost with good headroom

**Second Choice: Basic 512MB RAM ($4/month)**
- ✅ Even cheaper ($200 lasts 50 months!)
- ⚠️ Tight on memory if multiple scraping operations run
- ✅ Fine if you monitor and restart containers weekly
- ✅ Can upgrade anytime if needed

---

## Deployment Architecture

### Container Architecture Explained

#### Why Docker?

```
┌─────────────────────────────────────────────────────────────┐
│                      WHY DOCKER?                              │
├─────────────────────────────────────────────────────────────┤
│  ✅ Consistent Environment                                  │
│     → Dev, Test, Production all identical                   │
│     → "Works on my machine" problem solved                   │
├─────────────────────────────────────────────────────────────┤
│  ✅ Easy Deployment                                         │
│     → Single command to deploy                              │
│     → No manual Python setup needed                         │
├─────────────────────────────────────────────────────────────┤
│  ✅ Isolation                                               │
│     → Bot and FlareSolverr in separate containers           │
│     → One crash doesn't affect the other                    │
├─────────────────────────────────────────────────────────────┤
│  ✅ Auto-Restart                                            │
│     → Containers restart automatically on failure             │
│     → No manual intervention needed                          │
├─────────────────────────────────────────────────────────────┤
│  ✅ Easy Updates                                            │
│     → Update code: git pull + docker-compose up -d          │
│     → No SSH needed for updates                             │
├─────────────────────────────────────────────────────────────┤
│  ✅ Resource Management                                     │
│     → Limit container memory/CPU usage                      │
│     → Prevent one service from hogging resources            │
└─────────────────────────────────────────────────────────────┘
```

#### Docker Compose Architecture

```yaml
# docker-compose.yml explained:

services:
  # ============================================
  # FAP DISCORD BOT CONTAINER
  # ============================================
  bot:
    build: .                    # Build from Dockerfile in current dir
    container_name: fap-discord-bot
    restart: unless-stopped    # Auto-restart on crash/error
    environment:
      - All .env variables loaded here
    volumes:
      - ./data:/app/data       # Persistent data storage
    depends_on:
      - flaresolverr          # Start after FlareSolverr
    networks:
      - bot-network            # Internal network
    deploy:
      resources:
        limits:
          memory: 512M          # Limit to 512MB RAM
          cpus: '0.5'           # Limit to 50% of 1 CPU
    # No exposed ports needed (bot doesn't accept incoming connections)

  # ============================================
  # FLARESOLVERR CONTAINER (Cloudflare Bypass)
  # ============================================
  flaresolverr:
    image: flaresolverr/flaresolverr:latest
    container_name: flaresolverr
    restart: unless-stopped
    ports:
      - "8191:8191"            # Expose to localhost only
    environment:
      - LOG_LEVEL=info
      - HEADLESS=true           # Run Chrome in headless mode
      - BROWSER_TIMEOUT=60000   # 60 second timeout
    networks:
      - bot-network            # Internal network
    deploy:
      resources:
        limits:
          memory: 512M          # Limit to 512MB RAM
          cpus: '0.5'           # Limit to 50% of 1 CPU

# ============================================
# INTERNAL NETWORK (Containers communicate here)
# ============================================
networks:
  bot-network:
    driver: bridge              # Isolated network (not accessible from internet)
    # Bot accesses FlareSolverr via http://flaresolverr:8191
```

### How Containers Communicate

```
┌─────────────────────────────────────────────────────────────┐
│              CONTAINER COMMUNICATION FLOW                     │
└─────────────────────────────────────────────────────────────┘

1. Bot needs to fetch FAP page:

   fap-discord-bot container
   ┌──────────────────────────────────────┐
   │ Python code makes HTTP request:     │
   │ http://flaresolverr:8191/v1         │
   │                                     │
   │ Internal network (bot-network):     │
   │ → Resolves to flaresolverr container│
   └──────────────────────────────────────┘
                  ↓
   flaresolverr container
   ┌──────────────────────────────────────┐
   │ Receives request on port 8191        │
   │ → Spawns Chrome browser             │
   │ → Connects to FAP portal            │
   │ → Bypasses Cloudflare               │
   │ → Returns HTML response             │
   └──────────────────────────────────────┘
                  ↓
   fap-discord-bot container
   ┌──────────────────────────────────────┐
   │ Receives HTML                       │
   │ → Parses with BeautifulSoup          │
   │ → Extracts data                     │
   │ → Stores in SQLite                  │
   │ → Sends Discord notification        │
   └──────────────────────────────────────┘

2. External connection (Discord API):

   fap-discord-bot container
   ┌──────────────────────────────────────┐
   │ Python code connects to Discord API: │
   │ https://discord.com/api/v10/...     │
   │                                     │
   │ Direct internet connection          │
   │ → No proxy needed                   │
   └──────────────────────────────────────┘
```

---

## Prerequisites

### Before You Start

#### 1. GitHub Student Developer Pack

- [ ] Sign up for GitHub Student Developer Pack
- [ ] Wait for approval (1-7 days)
- [ ] Claim DigitalOcean $200 credit

#### 2. Local Development Environment

- [ ] Git installed
- [ ] Docker installed (for local testing)
- [ ] Basic understanding of SSH commands
- [ ] Code editor (VS Code recommended)

#### 3. Required Accounts & Tokens

- [ ] GitHub account (linked to Student Pack)
- [ ] Discord Bot Token from [Discord Developer Portal](https://discord.com/developers/applications)
- [ ] FAP credentials (FeID username and password)
- [ ] SSH key (optional but recommended)

#### 4. Code Ready

- [ ] Bot code pushed to GitHub repository
- [ ] `.env.example` file created (don't commit `.env`!)
- [ ] Dockerfile created
- [ ] docker-compose.yml created

---

## Step-by-Step Deployment

### Phase 1: DigitalOcean Setup (15 minutes)

#### Step 1.1: Create DigitalOcean Account

```bash
# If you haven't already:
1. Go to: https://cloud.digitalocean.com/register
2. Sign up with GitHub (use your GitHub Student Pack account)
3. $200 credit should be automatically added
4. Verify in Billing → Credits
```

#### Step 1.2: Create SSH Key (Recommended)

```bash
# On your local machine:
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/do_key

# Display public key
cat ~/.ssh/do_key.pub
```

Copy the public key and save it for DigitalOcean.

#### Step 1.3: Create Droplet

```bash
# Via DigitalOcean Control Panel:

1. Go to: https://cloud.digitalocean.com/
2. Click: Create → Droplets
3. Choose an image: Ubuntu 22.04 LTS x64
4. Choose plan: Basic → $6/month (1GB RAM, 1 vCPU) ⭐ RECOMMENDED
5. Choose region: Singapore (sgp1) ⭐ CLOSEST TO VIETNAM
6. Authentication:
   [ ] SSH Key (paste your public key)
   [ ] Password (alternative, less secure)
7. Hostname: fap-discord-bot
8. Add backups: Enable (optional, $2/month extra)
9. Click: Create Droplet
10. Wait ~1 minute for droplet to be ready
11. Copy droplet IP address: 157.245.123.45 (example)
```

#### Step 1.4: Test SSH Connection

```bash
# Test SSH connection:
ssh root@157.245.123.45

# First time - accept fingerprint
# You should be logged in as root

# Exit when done:
exit
```

---

### Phase 2: Initial Server Setup (10 minutes)

#### Step 2.1: Update System

```bash
# SSH into your droplet:
ssh root@157.245.123.45

# Update package list:
apt update

# Upgrade installed packages:
apt upgrade -y

# Install useful tools:
apt install -y git curl wget vim htop

# (Optional) Set timezone to Vietnam:
timedatectl set-timezone Asia/Ho_Chi_Minh

# Verify date:
date
```

#### Step 2.2: Install Docker

```bash
# Install Docker using convenience script:
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add your user to docker group (if non-root):
usermod -aG docker $USER

# Enable Docker to start on boot:
systemctl enable docker

# Start Docker:
systemctl start docker

# Verify installation:
docker --version
# Should output: Docker version 27.x.x or similar
```

#### Step 2.3: Install Docker Compose

```bash
# Download Docker Compose:
curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose

# Make executable:
chmod +x /usr/local/bin/docker-compose

# Verify installation:
docker-compose --version
# Should output: Docker Compose version v2.27.x
```

#### Step 2.4: Create Project Directory

```bash
# Create directory for bot:
mkdir -p /root/fap-discord-bot
cd /root/fap-discord-bot

# Create data directory:
mkdir -p data

# Verify:
ls -la
# Should see: data/ directory
```

---

### Phase 3: Deploy Bot Code (10 minutes)

#### Step 3.1: Clone Repository

```bash
# Method A: Clone from GitHub (recommended)
git clone https://github.com/your-username/fap-discord-bot.git .
# Note the "." at the end - clones into current directory

# Method B: Upload via SCP (from your local machine)
# In a new terminal on your local machine:
scp -r /path/to/fap-discord-bot/* root@157.245.123.45:/root/fap-discord-bot/

# Verify files are on server:
ls -la
```

#### Step 3.2: Create Environment File

```bash
# Copy example file:
cp .env.example .env

# Edit with your credentials:
nano .env

# Add your values:
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
FAP_USERNAME=your_feid@fe.edu.vn
FAP_PASSWORD=your_password_here
ENCRYPTION_KEY=generate_new_key_here

# Generate encryption key (Python):
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to ENCRYPTION_KEY

# Save and exit (Ctrl+X, then Y, then Enter)
```

#### Step 3.3: Build Docker Images

```bash
# Build bot image:
docker-compose build

# This will:
# 1. Pull flaresolverr/flaresolverr:latest image
# 2. Build fap-discord-bot image from Dockerfile
# 3. Install Python dependencies
# 4. Set up the container environment

# Expected output:
# [+] Building 23.4s (12/12) FINISHED
# => => naming to fap-discord-bot
```

#### Step 3.4: Start Containers

```bash
# Start all containers:
docker-compose up -d

# Expected output:
# [+] Running 2/2
# ✔ Network fap-discord-bot_bot-network     Created
# ✔ Container flaresolverr                   Started
# ✔ Container fap-discord-bot                Started

# Verify containers are running:
docker-compose ps

# Should see:
# NAME                 COMMAND                  SERVICE       STATUS
# fap-discord-bot      "python main.py"         bot           Up
# flaresolverr         "/opt/flaresolverr/..."   flaresolverr   Up
```

#### Step 3.5: View Logs

```bash
# View all logs:
docker-compose logs -f

# View bot logs only:
docker-compose logs -f bot

# View FlareSolverr logs only:
docker-compose logs -f flaresolverr

# Check for errors:
docker-compose logs bot | grep -i error
```

---

### Phase 4: Verify Deployment (5 minutes)

#### Step 4.1: Check Bot Status

```bash
# Check bot is running:
docker-compose ps

# Should show both containers as "Up"

# Check bot logs for successful startup:
docker-compose logs bot | grep -i "ready\|started\|logged in"
```

#### Step 4.2: Test Discord Bot

1. Go to your Discord server
2. Type: `/status` or `/schedule`
3. Bot should respond with schedule/status
4. Check that 19:30 schedule notification works

---

### Phase 5: Set Up Auto-Restart (5 minutes)

#### Step 5.1: Create Restart Script

```bash
# Create restart script:
nano /root/fap-discord-bot/restart.sh
```

Add this content:
```bash
#!/bin/bash
cd /root/fap-discord-bot

echo "🔄 Pulling latest code..."
git pull origin main

echo "🔄 Rebuilding containers..."
docker-compose down
docker-compose build
docker-compose up -d

echo "✅ Restart complete!"
echo "📊 Logs:"
docker-compose logs -f --tail=50
```

```bash
# Make executable:
chmod +x /root/fap-discord-bot/restart.sh

# Test it:
./restart.sh
```

#### Step 5.2: Schedule Health Check (Optional)

```bash
# Create health check script:
nano /root/fap-discord-bot/health-check.sh
```

Add this content:
```bash
#!/bin/bash
cd /root/fap-discord-bot

# Check if bot container is running
if ! docker-compose ps | grep -q "fap-discord-bot.*Up"; then
    echo "⚠️ Bot is down! Restarting..."
    docker-compose up -d
    echo "✅ Bot restarted"
else
    echo "✅ Bot is healthy"
fi
```

```bash
# Make executable:
chmod +x /root/fap-discord-bot/health-check.sh

# Add to crontab (runs every 5 minutes):
crontab -e

# Add this line:
*/5 * * * * /root/fap-discord-bot/health-check.sh >> /root/fap-discord-bot/health.log 2>&1
```

---

## Docker Configuration

### Dockerfile Explained

```dockerfile
# ============================================
# BASE IMAGE
# ============================================
FROM python:3.11-slim
# Why: Python 3.11 is latest stable
# Why slim: Smaller image (no extra packages), faster download

# ============================================
# WORKING DIRECTORY
# ============================================
WORKDIR /app
# All subsequent commands run from /app directory

# ============================================
# SYSTEM DEPENDENCIES
# ============================================
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*
# Why: Required for Playwright browser download
# Why rm -rf /var/lib/apt/lists: Clean up to reduce image size

# ============================================
# PYTHON DEPENDENCIES
# ============================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Why: Install all Python packages
# Why --no-cache-dir: Smaller image (no cache metadata)

# ============================================
# PLAYWRIGHT BROWSERS
# ============================================
RUN playwright install chromium
# Why: Download Chromium browser for FAP scraping
# Why chromium: Fatest, most compatible
# Note: This takes time during build, but saves time at runtime

# ============================================
# COPY APPLICATION CODE
# ============================================
COPY . .
# Copy all files from current directory to /app in container

# ============================================
# CREATE DATA DIRECTORY
# ============================================
RUN mkdir -p data
# Create directory for persistent data (database, cookies)

# ============================================
# ENTRYPOINT
# ============================================
CMD ["python", "main.py"]
# Command to run when container starts
```

### Docker Compose Explained

```yaml
# Docker Compose version
version: '3.8'

# ============================================
# SERVICES
# ============================================
services:

  # ============================================
  # BOT SERVICE
  # ============================================
  bot:
    # Build configuration
    build: .
    # Build from Dockerfile in current directory

    # Container name
    container_name: fap-discord-bot
    # Use this name for docker commands (docker logs fap-discord-bot)

    # Restart policy
    restart: unless-stopped
    # Options: no, always, on-failure, unless-stopped
    # Why unless-stopped: Auto-restart on crash/error, but not if stopped manually

    # Environment variables from .env file
    env_file:
      - .env
    # Load all variables from .env file
    # Alternative: Use environment section (below)

    # OR explicit environment variables
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - FAP_USERNAME=${FAP_USERNAME}
      - FAP_PASSWORD=${FAP_PASSWORD}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      # These override .env values if both exist

    # Volume mounts
    volumes:
      - ./data:/app/data
      # Format: host_path:container_path
      # ./data on host → /app/data in container
      # Why: Persist database and cookies even if container is deleted

    # Dependencies
    depends_on:
      - flaresolverr
      # Start flaresolverr before bot
      # Bot can fail if flaresolverr is not ready

    # Networks
    networks:
      - bot-network
      # Connect to this internal network
      # Allows communication with flaresolverr

    # Resource limits (optional but recommended)
    deploy:
      resources:
        limits:
          memory: 512M      # Maximum 512MB RAM
          cpus: '0.5'       # Maximum 50% of 1 CPU core

  # ============================================
  # FLARESOLVERR SERVICE
  # ============================================
  flaresolverr:
    # Use pre-built image
    image: flaresolverr/flaresolverr:latest
    # No build needed - use official image

    container_name: flaresolverr

    restart: unless-stopped

    # Port mapping
    ports:
      - "8191:8191"
      # Format: "host_port:container_port"
      # Host port 8191 → Container port 8191
      # Bot accesses via http://flaresolverr:8191 (internal network)

    # Environment variables
    environment:
      - LOG_LEVEL=info
      # Options: debug, info, warn, error
      # Why info: Good balance of detail

      - HEADLESS=true
      # Run Chrome in headless mode (no GUI)
      # Why: Server has no display

      - BROWSER_TIMEOUT=60000
      # 60 second timeout per request
      # FAP pages can be slow to load

    # Networks
    networks:
      - bot-network

    # Resource limits
    deploy:
      resources:
        limits:
          memory: 512M      # Chrome needs memory!
          cpus: '0.5'       # Limit CPU usage

# ============================================
# NETWORKS
# ============================================
networks:
  bot-network:
    driver: bridge
    # Bridge driver: Internal network for containers
    # Containers can communicate by service name
    # Example: http://flaresolverr:8191 (not localhost:8191)

# ============================================
# VOLUMES
# ============================================
volumes:
  data:
    # Named volume (optional)
    # Not used here since we use bind mount (./data:/app/data)
    # Named volumes are managed by Docker
    # Bind mounts map host directory directly
```

---

## FlareSolverr Setup

### What is FlareSolverr?

```
┌─────────────────────────────────────────────────────────────┐
│                   WHAT IS FLARESOLVERR?                        │
└─────────────────────────────────────────────────────────────┘

FlareSolverr is a web server that:
- Acts as a proxy between your bot and Cloudflare-protected sites
- Spawns a Chrome browser for each request
- Bypasses Cloudflare challenges automatically
- Returns the HTML response to your bot

┌─────────────────────┐         ┌──────────────────┐
│   FAP Discord Bot   │         │   FlareSolverr    │
│                     │         │                   │
│  Needs FAP data     │────────>│  Receives request │
│                     │         │                   │
│                     │         │  Spawns Chrome    │
│                     │         │                   │
│                     │         │  Connects to FAP   │
│                     │         │                   │
│                     │         │  Bypasses CF      │
│                     │         │                   │
│                     │<────────│  Returns HTML    │
│                     │         │                   │
│  Parses HTML        │         │                   │
└─────────────────────┘         └──────────────────┘
```

### Why Do We Need FlareSolverr?

```
FAP Portal uses Cloudflare protection:

Without FlareSolverr:
┌────────────────────────────────────────────────────────────┐
│ Bot Request → FAP                                         │
│             → Cloudflare: "Are you a robot?"              │
│             → Bot: "I can't solve this!" ❌               │
│             → Result: BLOCKED                             │
└────────────────────────────────────────────────────────────┘

With FlareSolverr:
┌────────────────────────────────────────────────────────────┐
│ Bot Request → FlareSolverr                                │
│             → FlareSolverr: "Let me handle this"           │
│             → Chrome browser spawns                        │
│             → FAP: "OK, you're human"                       │
│             → HTML Response ✅                               │
└────────────────────────────────────────────────────────────┘
```

### FlareSolverr Configuration

#### Environment Variables

| Variable | Default | Description | Recommended |
|----------|---------|-------------|--------------|
| `LOG_LEVEL` | info | Logging verbosity | `info` (use `debug` for troubleshooting) |
| `HEADLESS` | true | Run Chrome with/without GUI | `true` (server has no display) |
| `BROWSER_TIMEOUT` | 60000 | Request timeout (ms) | `60000` (60s for slow FAP pages) |
| `CHROME_PATH` | auto | Path to Chrome binary | `auto` (use bundled) |

#### Resource Management

```
Chrome (via FlareSolverr) Resource Usage:

┌─────────────────────────────────────────────────────────────┐
│  ACTIVITY              │ RAM     │ CPU    │ Duration      │
├─────────────────────────────────────────────────────────────┤
│  Idle                  │ ~100MB  │ <1%    │ Continuous    │
│  Loading FAP page      │ ~300MB  │ 50%    │ 10-30 seconds │
│  Bypassing Cloudflare   │ ~350MB  │ 80%    │ 5-10 seconds  │
│  Waiting for page load  │ ~400MB  │ 30%    │ 5-20 seconds  │
│  Returning HTML         │ ~300MB  │ 5%     | <1 second     │
└─────────────────────────────────────────────────────────────┘

Peak: ~400MB RAM during Cloudflare bypass

RECOMMENDATION: Set memory limit to 512MB for safety
```

#### Troubleshooting FlareSolverr

```bash
# Check if FlareSolverr is responding:
curl -X POST http://localhost:8191/v1 \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "cmd": "request.get"}'

# Expected response: JSON with solution object

# View FlareSolverr logs:
docker logs flaresolverr -f

# Check FlareSolverr metrics:
docker exec flaresolverr curl http://localhost:8191/metrics

# Restart if needed:
docker-compose restart flaresolverr
```

---

## Monitoring & Maintenance

### Health Monitoring Commands

#### Check Container Status

```bash
# Check all containers:
docker-compose ps

# Detailed stats:
docker stats

# Resource usage:
docker stats --no-stream

# Check disk usage:
du -sh data/

# Check memory usage:
free -h
```

#### View Logs

```bash
# All logs (real-time):
docker-compose logs -f

# Last 100 lines:
docker-compose logs --tail=100

# Logs since last restart:
docker-compose logs --since 1h

# Only errors:
docker-compose logs | grep -i error

# Specific service:
docker-compose logs -f bot
docker-compose logs -f flaresolverr
```

### Maintenance Tasks

#### Daily (Automated)

```bash
# Health check script runs automatically (crontab)
# Checks if bot is running, restarts if needed
```

#### Weekly (Manual)

```bash
# 1. Check disk space:
df -h

# 2. Check database size:
ls -lh data/fap.db

# 3. Review logs for errors:
docker-compose logs bot | grep -i error | tail -20

# 4. Restart containers (optional):
docker-compose restart

# 5. Pull latest code (if updates available):
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

#### Monthly (Manual)

```bash
# 1. Backup database:
cp data/fap.db backups/fap-$(date +%Y%m%d).db

# 2. Clean old logs (older than 30 days):
find . -name "*.log" -mtime +30 -delete

# 3. Update system packages:
apt update && apt upgrade -y

# 4. Review DigitalOcean billing:
# Check credits remaining at https://cloud.digitalocean.com/billing
```

### Backup Strategy

#### Automated Backup Script

```bash
# Create backup script:
nano /root/fap-discord-bot/backup.sh
```

```bash
#!/bin/bash

# Backup FAP Discord Bot
# Run this weekly or monthly

BACKUP_DIR="/root/fap-discord-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
echo "📦 Backing up database..."
cp data/fap.db $BACKUP_DIR/fap_$DATE.db

# Backup .env file (important!)
echo "📦 Backing up configuration..."
cp .env $BACKUP_DIR/env_$DATE.bak

# Compress old backups (older than 7 days)
echo "🗜️  Compressing old backups..."
find $BACKUP_DIR -name "fap_*.db" -mtime +7 -exec gzip {} \;

# Keep only last 90 days of backups
echo "🧹 Cleaning up old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +90 -delete

# Show backup summary
echo ""
echo "✅ Backup complete!"
echo "📊 Backup directory: $BACKUP_DIR"
du -sh $BACKUP_DIR
```

```bash
# Make executable:
chmod +x /root/fap-discord-bot/backup.sh

# Create backups directory:
mkdir -p backups

# Test backup:
./backup.sh
```

---

## Cost Analysis

### Detailed Cost Breakdown

#### Monthly Costs (Without GitHub Education)

| Service | Plan | Price/mo | Price/yr |
|---------|------|---------|---------|
| **Droplet** | Basic 1GB | $6.00 | $72.00 |
| **Backup** | Optional | $2.00 | $24.00 |
| **Bandwidth Overage** | Unlikely | $0.00 | $0.00 |
| **Total** | | **$8.00** | **$96.00** |

#### With GitHub Student Developer Pack ($200 Credit)

| Item | Calculation | Result |
|------|------------|--------|
| **Credit** | $200 | **$200** |
| **Monthly Cost** | $6-8/mo (depending on backup) | **~$8** |
| **Months Covered** | $200 ÷ $8 | **~25 months** |
| **Years Covered** | 25 months ÷ 12 | **~2 years** |

### Cost Optimization Tips

```
┌─────────────────────────────────────────────────────────────┐
│                  HOW TO STAY WITHIN $200                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Use Basic 1GB droplet ($6/mo) ✅                     │
│     → Sufficient for single-user bot                       │
│     → $200 lasts ~33 months                                  │
│                                                               │
│  2. Skip backup add-on ($2/mo)                             │
│     → Use script backup instead (included)                   │
│     → Saves $24/year                                        │
│                                                               │
│  3. Monitor bandwidth usage                                  │
│     → Bot uses minimal bandwidth                             │
│     → 1TB transfer included with droplet                    │
│     → Unlikely to exceed                                    │
│                                                               │
│  4. Power off during breaks                                  │
│     → DigitalOcean charges by the hour                       │
│     → Power off droplet during summer break                  │
│     → Saves $6/month                                        │
│                                                               │
│  5. Clean up resources                                       │
│     → Delete unused snapshots                                │
│     → Delete old backups                                     │
│     → Monitor disk usage                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### When to Upgrade Droplet

```
Current: Basic 1GB ($6/mo)

Consider upgrading when:
→ RAM usage consistently > 80%
→ CPU usage consistently > 80%
→ Adding more users (5+)
→ Running additional services

Upgrade path:
Basic 1GB ($6) → Basic 2GB ($12) → General 4GB ($24)

Note: Can upgrade anytime without losing data
```

---

## Troubleshooting

### Common Issues & Solutions

#### Issue 1: Bot Won't Start

```
ERROR: Container exits immediately

DIAGNOSTIC:
docker-compose logs bot

SOLUTIONS:
1. Check .env file exists and has correct values
2. Check DISCORD_TOKEN is valid
3. Check FAP credentials are correct
4. Check dependencies installed: docker-compose build
```

#### Issue 2: FlareSolverr Not Responding

```
ERROR: Could not connect to FlareSolverr

DIAGNOSTIC:
docker logs flaresolverr
curl http://localhost:8191/metrics

SOLUTIONS:
1. Restart FlareSolverr: docker-compose restart flaresolverr
2. Check if port 8191 is blocked
3. Check FlareSolverr memory limit (increase if needed)
4. Check FAP is accessible from server
```

#### Issue 3: Out of Memory

```
ERROR: Container killed due to OOM

DIAGNOSTIC:
docker stats
free -h

SOLUTIONS:
1. Check memory limits in docker-compose.yml
2. Increase memory limit:
   deploy:
     resources:
       limits:
         memory: 1G  # Increase from 512M
3. Upgrade droplet to next size (1GB → 2GB)
4. Add swap space to droplet
```

#### Issue 4: Database Locked

```
ERROR: database is locked

DIAGNOSTIC:
docker exec fap-discord-bot ls -la /app/data/

SOLUTIONS:
1. Stop bot: docker-compose stop bot
2. Check for other processes using database
3. Delete lock file: rm data/fap.db-journal
4. Restart bot: docker-compose start bot
```

#### Issue 5: Git Pull Fails

```
ERROR: cannot pull into dirty repository

DIAGNOSTIC:
git status

SOLUTIONS:
1. Commit local changes: git add . && git commit -m "local"
2. Stash changes: git stash
3. Force pull: git fetch && git reset --hard origin/main
4. Apply stash: git stash pop
```

#### Issue 6: Discord Bot Commands Not Working

```
ERROR: Application did not respond

DIAGNOSTIC:
docker-compose logs bot | grep -i "sync\|command"

SOLUTIONS:
1. Commands may not be synced: Wait 1 hour for global sync
2. Check bot has applications.commands scope
3. Manually sync: Add code to on_ready()
4. Check bot has permissions in server
```

### Emergency Recovery Procedures

#### Bot Completely Down

```bash
# 1. Check if containers exist:
docker-compose ps

# 2. Check if droplet is running:
# Go to DigitalOcean control panel
# Check droplet status

# 3. If droplet is off: Turn it on

# 4. SSH into droplet:
ssh root@your-droplet-ip

# 5. Navigate to project:
cd /root/fap-discord-bot

# 6. Pull latest code:
git pull origin main

# 7. Rebuild and restart:
docker-compose down
docker-compose build
docker-compose up -d

# 8. Check logs:
docker-compose logs -f
```

#### Data Loss Recovery

```bash
# If database is corrupted:

# 1. Stop bot:
docker-compose stop bot

# 2. Check backups:
ls -lh backups/

# 3. Restore from backup:
cp backups/fap_YYYYMMDD.db data/fap.db

# 4. Restart bot:
docker-compose start bot

# 5. Verify:
docker-compose logs bot
```

---

## Quick Reference

### Essential Commands

| Command | Purpose |
|---------|---------|
| `ssh root@ip` | SSH into droplet |
| `docker-compose ps` | Check container status |
| `docker-compose logs -f` | View all logs |
| `docker-compose restart` | Restart all services |
| `docker-compose down && docker-compose up -d` | Rebuild & restart |
| `docker stats` | View resource usage |
| `du -sh data/` | Check data directory size |
| `free -h` | Check system memory |
| `df -h` | Check disk space |

### Useful Links

- **DigitalOcean Control Panel:** https://cloud.digitalocean.com/
- **GitHub Student Pack:** https://education.github.com/pack
- **Docker Documentation:** https://docs.docker.com/
- **Docker Compose Documentation:** https://docs.docker.com/compose/
- **FlareSolverr GitHub:** https://github.com/FlareSolverr/FlareSolverr
- **Discord.py Documentation:** https://discordpy.readthedocs.io/

---

## Appendix

### A. Server Hardening (Optional but Recommended)

```bash
# 1. Configure firewall (UFW)
ufw enable
ufw allow ssh
ufw allow 80
ufw allow 443
ufw deny 8191  # Don't expose FlareSolverr to internet

# 2. Disable root login
# Create new user:
adduser deploy
usermod -aG sudo deploy
ssh-copy-id deploy@localhost

# Edit SSH config:
nano /etc/ssh/sshd_config
# Change: PermitRootLogin no

# 3. Install fail2ban
apt install fail2ban -y
```

### B. Performance Tuning

```yaml
# docker-compose.yml additions:

deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### C. Monitoring Setup

```bash
# Install monitoring tools:
apt install htop sysstat -y

# Enable system stats:
nano /etc/default/sysstat
# Set ENABLED=true
systemctl restart sysstat
```

---

**Document Status:** ✅ Complete
**Deployment Time Estimate:** 30-45 minutes (first time)
**Ongoing Maintenance:** ~5 minutes/week

**Ready to deploy? Follow the steps in Phase 1-5! 🚀**
