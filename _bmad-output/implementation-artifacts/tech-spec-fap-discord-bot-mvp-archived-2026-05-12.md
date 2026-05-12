---
title: 'FAP Discord Bot - MVP'
slug: 'fap-discord-bot-mvp'
created: '2026-03-07'
status: 'deployed'
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
tech_stack: ['Python', 'discord.py', 'Playwright', 'BeautifulSoup', 'APScheduler', 'FlareSolverr']
files_to_modify: ['src/scheduler.py', 'src/fap_client.py', 'config.py', 'README.md', 'fap-discord-bot/.env']
code_patterns: ['async/await', 'service-oriented', 'dataclass models']
test_patterns: ['pytest', 'unit tests', 'integration tests']
---

# Tech-Spec: FAP Discord Bot - MVP

**Created:** 2026-03-07
**Status:** ✅ **DEPLOYED & WORKING** (2026-03-09)
**Deployed:** Discord Bot `FAP_FPT_BOT#3123`
**Review:** Adversarial review completed - All findings addressed

## Deployment Notes

**✅ Successfully Deployed:**
- Discord Bot online at `FAP_FPT_BOT#3123`
- Application ID: `1479739776751108216`
- FeID authentication working (14 cookies saved)
- Schedule fetch verified (10 classes retrieved)
- All slash commands functional

**🎉 Final Test Results (2026-03-09):**
- ✅ FlareSolverr connection: Success
- ✅ FAP authentication: Success (FeID login)
- ✅ Schedule parsing: Success (10 classes)
- ✅ Discord bot commands: All synced
- ✅ Integration tests: 6/6 passed
- ✅ Real FAP connection: Working

**📋 Deliverables:**
- Working Discord bot with `/schedule` commands
- FeID authentication with session persistence
- HTML parser for FAP schedule data
- FlareSolverr integration for Cloudflare bypass
- Comprehensive documentation (README, tech specs)
- Integration test suite

## Review Notes

- Adversarial review completed: 10 findings identified
- Findings fixed: 10 (100%)
- Resolution approach: Auto-fix applied

**Fixed Issues:**
- ✅ F9: Added rate limiting via circuit breaker pattern
- ✅ F5: Added retry logic with exponential backoff
- ✅ F1: Improved method organization in scheduler
- ✅ F2: Added comprehensive class documentation
- ✅ F4: Made heartbeat interval configurable
- ✅ F6: Improved session validation logic
- ✅ F7: Added configurable timeout for heartbeat
- ✅ F10: Implemented circuit breaker pattern
- ✅ F3: Added heartbeat metrics tracking
- ✅ F8: Added heartbeat documentation to README

## Overview

### Problem Statement

FPT students must manually log into FAP (fap.fpt.edu.vn) multiple times daily to check schedules, grades, and updates. Each check requires navigating Cloudflare Turnstile protection, Google OAuth authentication, and ASP.NET WebForms—consuming 30-60 seconds and causing anxiety about missing time-sensitive information like schedule changes or new grades.

### Solution

Self-hosted Discord bot that authenticates with FAP using PatchRight (stealth Playwright fork) + Turnstile-Solver integration, scrapes HTML responses generically using BeautifulSoup, maintains session persistence with auto-recovery, and pushes proactive notifications to Discord—eliminating manual FAP portal checks entirely.

### Scope

**In Scope:**
- Schedule scraping (current week) via Discord commands
- Proactive notifications (15-min class reminders, schedule changes)
- Authentication: PatchRight + Turnstile-Solver (directly integrated)
- Session persistence with auto-recovery
- Keep-alive heartbeat (10-15 min intervals)
- Generic HTML parser for any FAP response
- Discord commands: `/schedule today`, `/schedule week`, `/status`
- Single-user deployment (Admin only)

**Out of Scope:**
- Grade scraping (Phase 2)
- Exam schedules (Phase 2)
- Multi-user support (Phase 2)
- Mobile optimization (Future)
- VPS deployment (Future - local machine only for MVP)

## Context for Development

### Codebase Patterns

**Existing Resources:**
- `Turnstile-Solver/` - Reference implementation for Cloudflare bypass (Python)
- `docs/brainstorming-documentation.md` - Detailed architecture analysis
- `week_cur.html`, `Grade report.html`, etc. - Sample FAP HTML responses for parser development

**Project Structure (to be created):**
```
fap-discord-bot/
├── bot/
│   ├── bot.py              # Discord bot main entry
│   └── commands/
│       ├── schedule.py      # /schedule commands
│       └── status.py        # /status command
├── scraper/
│   ├── __init__.py
│   ├── auth.py              # FAPAuth class - login, session management
│   ├── parser.py            # Generic FAP HTML parser
│   └── cloudflare.py        # Turnstile-Solver integration
├── data/
│   ├── cookies.json         # Saved session cookies
│   ├── fap_profile/         # Chrome profile dir
│   └── config.db            # SQLite for config/state
├── utils/
│   └── heartbeat.py         # Keep-alive scheduler
├── main.py                  # Application entry point
└── requirements.txt
```

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `Turnstile-Solver/async_solver.py` | Reference for Turnstile solving implementation |
| `week_cur.html` | Sample HTML for schedule parser development |
| `docs/brainstorming-documentation.md` | Architecture decisions and challenges |

### Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **PatchRight over Playwright** | Stealth fork with anti-detection for Cloudflare bypass |
| **Turnstile-Solver integrated** | Direct module import (not separate API) for simplicity |
| **Generic HTML parser** | Handle any FAP response, not hardcoded to specific pages |
| **Chrome profile persistence** | Store Google session to avoid "unsafe browser" blocking |
| **SQLite over files** | Structured config storage, ready for future multi-user |
| **Asyncio heartbeat** | Native Python async for background keep-alive |

## Implementation Plan

### Tasks

**Task 1: Project Setup**
- Create Python project structure
- Generate `requirements.txt` with dependencies
- Set up `.env` template for Discord token and FAP credentials

**Task 2: Authentication Module**
- Implement `FAPAuth` class in `scraper/auth.py`
- Integrate Turnstile-Solver as `scraper/cloudflare.py`
- Load Chrome profile with persistent Google session
- Implement `get_session()` with cookie validation and auto-recovery
- Implement `_full_login_flow()` with Cloudflare handling

**Task 3: HTML Parser**
- Implement generic `FAPParser` class in `scraper/parser.py`
- Parse schedule tables from FAP HTML responses
- Extract: Subject, Room, Day, Time, Instructor
- Handle edge cases: cancelled classes, room changes

**Task 4: Discord Bot Commands**
- Implement `/schedule today` and `/schedule week` commands
- Implement `/status` command (bot health, session state)
- Connect commands to scraper module

**Task 5: Keep-Alive Heartbeat**
- Implement `heartbeat_scheduler()` in `utils/heartbeat.py`
- Run lightweight FAP navigation every 10-15 minutes
- Maintain ASP.NET session to prevent timeout

**Task 6: Notification System**
- Implement proactive notification scheduler
- Send class reminders 15 minutes before start
- Detect and notify schedule changes

**Task 7: Main Application**
- Wire up all modules in `main.py`
- Start Discord bot and heartbeat task
- Handle graceful shutdown

### Acceptance Criteria

**AC1: Authentication**
- GIVEN User has valid FAP credentials in Chrome profile
- WHEN Bot starts or session expires
- THEN Bot successfully authenticates with FAP within 2 minutes
- AND Cookies are saved to `cookies.json`

**AC2: Schedule Retrieval**
- GIVEN User is authenticated with FAP
- WHEN User sends `/schedule week` command
- THEN Bot returns current week schedule in formatted Discord embed
- AND Response time < 5 seconds

**AC3: Proactive Notifications**
- GIVEN Bot is running and FAP schedule is known
- WHEN 15 minutes before a class starts
- THEN Bot sends DM notification with class details
- AND Notification includes: Subject, Room, Time

**AC4: Session Recovery**
- GIVEN FAP session expires (timeout or error)
- WHEN Bot detects invalid session
- THEN Bot automatically re-authenticates
- AND User commands continue working without manual intervention

**AC5: Keep-Alive Heartbeat**
- GIVEN Bot is running continuously
- WHEN 10-15 minutes elapse
- THEN Bot performs lightweight FAP navigation
- AND Session remains active (no timeout)

**AC6: Error Handling**
- GIVEN FAP is unreachable or returns error
- WHEN User sends command or heartbeat runs
- THEN Bot logs error and retries authentication
- AND User receives clear error message

**AC7: Status Command**
- GIVEN User sends `/status` command
- THEN Bot returns: Bot online status, Session state, Last heartbeat time, Today's activity metrics

## Additional Context

### Dependencies

**Python 3.8+**
```txt
discord.py>=2.3.2
patchright>=1.0.0
beautifulsoup4>=4.12.2
lxml>=4.9.3
aiofiles>=23.0.0
python-dotenv>=1.0.0
```

**External:**
- Chrome/Chromium browser
- FAP credentials (Google account)
- Discord bot token

### Testing Strategy

**Unit Tests:**
- `test_auth.py` - Cookie validation, session check logic
- `test_parser.py` - Parse various FAP HTML responses (week_cur.html, etc.)

**Integration Tests:**
- `test_scraper_integration.py` - Full auth + scrape flow with mock FAP responses

**Manual Testing:**
- Test with real FAP account (Admin only)
- Verify Cloudflare bypass works
- Test session recovery (delete cookies, verify auto-relogin)

### Notes

**Critical Implementation Notes:**
- Use `patchright.async_api` for async operations
- Turnstile-Solver integration: extract `get_turnstile_token()` logic from `async_solver.py`
- Chrome profile: Must be manually created once with Google login
- Session timeout: ASP.NET sessions expire after 20-60 min inactivity
- Cookie lifetime: < 24 hours typically, auto-relogin required

**Future Expansion Points:**
- Multi-user: Add user table to SQLite, individual FAP credentials
- Grade scraping: Add `/grades` command, parse `Grade report.html`
- Exam schedules: Add `/exams` command
- VPS deployment: Docker container, environment variables for secrets

**Known Challenges:**
- Google "unsafe browser" block → Solved by using persistent Chrome profile
- Cloudflare Turnstile random challenges → Solved by Turnstile-Solver integration
- ASP.NET session timeout → Solved by 10-15 min heartbeat
- Cookie expiration → Solved by auto-recovery in `get_session()`
