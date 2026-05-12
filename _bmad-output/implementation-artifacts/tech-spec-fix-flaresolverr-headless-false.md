---
title: 'Fix FlareSolverr Cloudflare Bypass with HEADLESS=false'
slug: 'fix-flaresolverr-headless-false'
created: '2026-05-12'
status: 'Verified'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Docker', 'Docker Compose', 'FlareSolverr', 'Python', 'supervisord']
files_to_modify: ['docker-compose.yml', '.env.example']
files_to_delete: ['flaresolverr.Dockerfile', 'flaresolverr-entrypoint.sh']
code_patterns: ['Docker Compose service config', 'FlareSolverr HTTP API client']
test_patterns: ['Manual integration test']
---

# Tech-Spec: Fix FlareSolverr Cloudflare Bypass with HEADLESS=false

**Created:** 2026-05-12

## Overview

### Problem Statement

FlareSolverr runs with `HEADLESS=true` in Docker, causing Cloudflare to detect the headless browser and block all requests to the FAP portal. The university portal requires a non-headless browser to pass Cloudflare protection. A custom Dockerfile (`flaresolverr.Dockerfile`) and entrypoint script (`flaresolverr-entrypoint.sh`) were created to add Xvfb, but the stock FlareSolverr image already includes Xvfb and manages it via supervisord — making the custom files redundant.

### Solution

Remove the custom `flaresolverr.Dockerfile` and `flaresolverr-entrypoint.sh`. Revert `docker-compose.yml` to use the stock `flaresolverr/flaresolverr:latest` image with `HEADLESS=false` environment variable. The stock image's built-in supervisord + Xvfb will handle the virtual display automatically.

### Scope

**In Scope:**
- Remove `flaresolverr.Dockerfile` and `flaresolverr-entrypoint.sh`
- Update `docker-compose.yml` to use stock image with `HEADLESS=false`
- Update `.env.example` to reflect correct configuration
- Verify `flaresolverr_auth.py` config is consistent with the change

**Out of Scope:**
- Test files (`test_feid_*.py`, `cdp_login.py`)
- Refactoring the auth flow or login logic
- Changes to `auto_login_feid.py` or `auth.py`
- Adding new features

## Context for Development

### Codebase Patterns

- Docker Compose orchestrates three services: `bot`, `flaresolverr`, and optional `chrome`
- FlareSolverr is used as a proxy to bypass Cloudflare and obtain clearance cookies
- The auth flow: `flaresolverr_auth.py` gets Cloudflare cookies → `auto_login_feid.py` performs the actual FEID OAuth login using Playwright with those cookies
- Environment variables in `.env` control all runtime behavior
- Stock FlareSolverr image uses `dumb-init` as PID 1, supervisord manages Xvfb + Chrome
- `HEADLESS=false` in FlareSolverr context means Chrome runs with a visible window on Xvfb virtual display
- `HEADLESS=false` in bot context (line 24 of docker-compose.yml) controls Playwright headless mode for `auto_login_feid.py` — these are independent settings

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `docker-compose.yml` | Service orchestration config |
| `.env.example` | Environment variable template |
| `fap-discord-bot/scraper/flaresolverr_auth.py` | FlareSolverr API client for Cloudflare bypass |
| `flaresolverr.Dockerfile` | Custom FlareSolverr image (TO BE DELETED) |
| `flaresolverr-entrypoint.sh` | Custom Xvfb entrypoint (TO BE DELETED) |

### Technical Decisions

- **Stock image with Xvfb entrypoint wrapper:** The official `flaresolverr/flaresolverr:latest` (v3.4.6) does NOT include supervisord. It uses `dumb-init` as PID 1. Xvfb binary is available at `/usr/bin/Xvfb` but must be started manually via an entrypoint override: `Xvfb :99 -screen 0 1280x720x24 &` before launching FlareSolverr.
- **DISPLAY env var required:** Set `DISPLAY=:99` in the flaresolverr environment so Chrome connects to the Xvfb virtual display.
- **Memory overhead:** Non-headless browser + Xvfb consumes ~200-400MB RAM. Acceptable for single-server Discord bot deployment.

## Implementation Plan

### Tasks

- [x] Task 1: Delete custom FlareSolverr files
  - Files: `flaresolverr.Dockerfile`, `flaresolverr-entrypoint.sh`
  - Action: Delete both files. They are redundant — the stock FlareSolverr image includes Xvfb binary but requires manual start via entrypoint.

- [x] Task 2: Revert docker-compose.yml FlareSolverr service to stock image
  - File: `docker-compose.yml`
  - Action: Replace the `build` block (lines 34-36) with `image: flaresolverr/flaresolverr:latest`. Add `HEADLESS=false` to the flaresolverr service's `environment` section. Remove the `LOG_LEVEL` env var (or keep it — it's harmless).
  - Target state for flaresolverr service:
    ```yaml
    flaresolverr:
      image: flaresolverr/flaresolverr:latest
      container_name: flaresolverr
      restart: unless-stopped
      ports:
        - "8191:8191"
      environment:
        - LOG_LEVEL=${LOG_LEVEL:-info}
        - HEADLESS=false
        - DISPLAY=:99
      entrypoint: ["/bin/sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & sleep 1 && /usr/bin/dumb-init -- /usr/local/bin/python -u /app/flaresolverr.py"]
      networks:
        - bot-network
    ```
    Note: Image v3.4.6 uses dumb-init (not supervisord). Xvfb must be started manually via entrypoint override.

- [x] Task 3: Clean up .env.example comments
  - File: `.env.example`
  - Action: Simplify the HEADLESS comment block. Remove references to Xvfb since it's now handled transparently by the stock image.
  - Target:
    ```
    # FAP Authentication
    # Set to false (recommended) — FlareSolverr needs non-headless to bypass Cloudflare
    # Also controls Playwright headless mode for bot login
    HEADLESS=false
    ```

- [x] Task 4: Verify flaresolverr_auth.py requires no changes
  - File: `fap-discord-bot/scraper/flaresolverr_auth.py`
  - Action: Read-only verification. Confirm the file only communicates with FlareSolverr via HTTP API (no Docker/config references). No code changes expected.

### Acceptance Criteria

- [x] AC 1: Given the custom files are deleted, when `docker compose config` is run, then it validates successfully without referencing `flaresolverr.Dockerfile` or `flaresolverr-entrypoint.sh`. **VERIFIED 2026-05-12**
- [x] AC 2: Given the updated docker-compose.yml, when `docker compose up -d` is run, then FlareSolverr container starts using `flaresolverr/flaresolverr:latest` image with `HEADLESS=false` environment variable. **VERIFIED 2026-05-12** (required Xvfb entrypoint fix — stock image v3.4.6 has no supervisord)
- [x] AC 3: Given FlareSolverr is running with HEADLESS=false, when the bot triggers a FlareSolverr request to `fap.fpt.edu.vn`, then Cloudflare challenge is solved and the response contains valid HTML (no Cloudflare block page). **VERIFIED 2026-05-12** — response: `"Challenge solved!"`, HTML: "FPT University Academic Portal"
- [x] AC 4: Given .env.example is updated, when a new user copies it to `.env`, then the HEADLESS setting and comments are clear and accurate. **VERIFIED 2026-05-12**

## Additional Context

### Dependencies

- FlareSolverr must be accessible from the bot container via Docker network (`http://flaresolverr:8191`)
- Stock FlareSolverr image must be pulled: `docker pull flaresolverr/flaresolverr:latest`
- No code dependencies — this is purely Docker config changes

### Testing Strategy

- **Validation:** Run `docker compose config` to verify YAML is valid and no references to deleted files remain
- **Integration:** Run `docker compose up -d` and check FlareSolverr logs for "HEADLESS=false" confirmation
- **Functional:** Trigger a bot command that calls FlareSolverr (e.g., `!schedule`) and verify Cloudflare is bypassed
- **No unit tests needed** — this is infrastructure config, not application code

### Notes

- The bot container's `HEADLESS` env var in `.env` controls Playwright's headless mode for `auto_login_feid.py` — this is separate from FlareSolverr's `HEADLESS` setting
- If FlareSolverr fails to start with HEADLESS=false, check Docker host memory (Xvfb + Chrome needs ~200-400MB)
- Future consideration: if Cloudflare updates their detection, may need to pin a specific FlareSolverr version instead of `:latest`
