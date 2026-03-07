---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success']
inputDocuments: ['docs/brainstorming-documentation.md']
workflowType: 'prd'
briefCount: 0
researchCount: 0
brainstormingCount: 1
projectDocsCount: 0
classification:
  projectType: Bot Service (Discord + Backend Scraper)
  domain: EdTech (University/Student focused)
  complexity: Medium
  projectContext: Greenfield MVP → Brownfield Future (Multi-user SaaS)
  userScope: 1 (MVP) → N (Future FPT students)
  valueProps: Save time, Never miss deadlines, Get notified faster
  botPersonality: Utility + Helper + Notification Service
---

# Product Requirements Document - cao resource lam tool

**Author:** Admin
**Date:** 2026-03-07

---

## Document Info

**Project:** FAP Discord Bot
**Status:** Planning Phase
**Workflow Step:** 1 of 11 - Initialization Complete

---

## Input Documents Loaded

✅ **1 brainstorming document loaded:**
- `docs/brainstorming-documentation.md` - Contains FAP analysis, proposed architecture, implementation plan

---

## Executive Summary

**Product Vision:**

FAP Discord Bot is a self-hosted Discord bot that automatically scrapes academic data from FPT University's Academic Portal (FAP) and delivers it to students via Discord—eliminating the need for manual portal checks. The bot operates as a seamless pipeline that bridges the gap between where students live (Discord) and where their data resides (FAP), transforming reactive information retrieval into proactive, push-based notifications.

**Target Users:**
- **MVP:** Single user (Admin) - personal utility tool
- **Future:** All FPT University students seeking efficient access to academic information

**Problem Being Solved:**

FPT students must manually log into FAP multiple times daily to check schedules, grades, exam dates, and application status. This process involves navigating Cloudflare protection, Google OAuth authentication, and ASP.NET WebForms—consuming 30-60 seconds per check and requiring active attention. Students risk missing time-sensitive updates (schedule changes, new grades, exam announcements) due to the friction of manual checking.

**Core Value Proposition:**

*"Get FPT schedule and grades in 2 seconds on Discord, no Cloudflare, no waiting."*

---

### What Makes This Special

**The 7:00 AM "Ping" Moment:**

The user delight moment occurs when, instead of groggily opening a browser and navigating through Cloudflare and OAuth at 7:00 AM to check today's class schedule, the student receives a proactive Discord notification: *"15 minutes from now: OSG subject at Room 202."* The shift from reactive manual checking to proactive, zero-effort information delivery creates the "this is exactly what I needed" response.

**Zero-Second Wait Time:**

The differentiation is clear: manual FAP access requires 30-60 seconds across multiple authentication barriers. The bot delivers instant results via simple Discord commands (`/schedule`, `/grades`, `/exams`) or pushes notifications automatically. Data appears where the user already is (Discord) rather than requiring context switching to a separate portal.

**Core Technical Insight:**

Students conduct their daily digital lives on Discord, but their critical academic data remains trapped in the FAP "island"—protected by Cloudflare Turnstile, ASP.NET session timeouts, and Google OAuth. The product's existence is justified by building and maintaining a persistent authentication pipeline (PatchRight stealth browser + Turnstile-Solver + BeautifulSoup) that bypasses these barriers and creates a reliable data bridge. This technical approach makes possible what was previously impractical: continuous, automated access to FAP data without user intervention.

**Personality Triad:**

The bot embodies three complementary personas: (1) **Utility Tool**—functional, minimal, command-driven; (2) **Helper**—friendly, conversational when needed; (3) **Notification Service**—silent unless delivering important updates. This flexibility ensures the bot serves practical needs while remaining unobtrusive.

---

### Project Classification

| Aspect | Classification |
|--------|----------------|
| **Project Type** | Bot Service (Discord + Backend Scraper) |
| **Domain** | EdTech (University/Student focused) |
| **Complexity** | Medium—authentication challenges, session management, DOM scraping, real-time notifications |
| **Project Context** | Greenfield MVP (single user) → Brownfield expansion (multi-user SaaS) |
| **User Scope** | Phase 1: 1 user (Admin) → Phase 2: N users (all FPT students) |
| **Key Dependencies** | PatchRight, Turnstile-Solver, BeautifulSoup4, discord.py, asyncio |

---

## Success Criteria

### User Success

**The "Aha!" Moment:**
User realizes the bot works when their first Discord command (`/schedule`) returns their FAP schedule instantly—correctly formatted and readable—without ever opening a browser or navigating Cloudflare.

**Daily Success Indicators:**
- User completed zero manual FAP checks that day
- Critical information (schedule changes, new grades, class reminders) received proactively before deadlines
- User felt informed without expending effort to retrieve information

**Emotional Success States:**
- **Relieved** — Reduced stress about missing important academic updates
- **Empowered** — Academic information accessible at fingertips, not chased after
- **In Control** — Proactive notifications replace reactive checking anxiety

**Completion Scenario:**
User ends their day having attended all classes on time, aware of any schedule changes, without once thinking "I need to check FAP."

---

### Business Success

**"This Is Working" Metric (Future Multi-User):**
- Positive qualitative feedback from users (testimonial quality, not just quantity)
- Daily Active Users (DAU) consistently engaging with bot commands or receiving notifications
- User behavior shift: Users voluntarily choose bot over manual FAP portal checks

**Timeline Milestones:**

| Horizon | Success Indicators |
|---------|-------------------|
| **3 Months** | Small user group (10-50 students) using daily, feedback loop established, authentication stability proven |
| **12 Months** | Recognized utility among FPT students, community adoption (100+ DAU), feature expansion based on user requests |
| **Vision** | Bot becomes standard tool for FPT students—checking FAP manually feels outdated |

**Key Business Metrics:**
- User retention: % of users who return after first week
- Engagement: Average commands per user per day
- Notification effectiveness: % of notifications acted upon (e.g., students attending classes they were reminded of)

---

### Technical Success

**Reliability Requirements:**
- ✅ Schedule retrieval success rate: >95% (accounting for FAP downtime)
- ✅ Notification delivery rate: >98% (critical alerts must not be missed)
- ✅ Authentication auto-recovery: Session restoration within 2 minutes
- ✅ Command response time: <5 seconds for schedule/grade queries
- ✅ Keep-alive heartbeat: Session maintained with 10-15 minute intervals

**Failure Modes (Must Not Occur):**
- ❌ Missed critical notifications (class cancellations, exam changes)
- ❌ Authentication failures requiring manual intervention >1x/week
- ❌ Data corruption or incorrect information delivery
- ❌ Response time >10 seconds for user commands
- ❌ Bot downtime >1 hour during active academic hours (7AM-10PM)

**Technical Quality Metrics:**
- Code coverage: >80% for critical authentication and scraping modules
- Error logging: All failures logged with sufficient detail for diagnosis
- Resource usage: <500MB RAM per browser instance, <1GB disk for profile/data

---

### Measurable Outcomes

**MVP Success (Single User):**
| Metric | Target |
|--------|--------|
| Schedule retrieval accuracy | 100% (matches FAP exactly) |
| Daily proactive notifications sent | ≥1 (class reminders) |
| Manual FAP checks eliminated | 100% (user never opens FAP manually) |
| Bot uptime | >95% during academic term |

**Growth Success (Multi-User):**
| Metric | 3-Month Target | 12-Month Target |
|--------|----------------|-----------------|
| Daily Active Users (DAU) | 10-50 | 100+ |
| User retention (week 1→4) | >70% | >80% |
| Avg. commands/user/day | 2-3 | 3-5 |
| Positive feedback sentiment | >80% | >90% |

---

## Product Scope

### MVP - Minimum Viable Product

**Must-Have Features (Proof of Concept):**
- ✅ Schedule scraping: Current week schedule retrieval via `/schedule` command
- ✅ Proactive notifications: Class reminders (15 min before), schedule changes
- ✅ Authentication: Auto-login with session persistence and auto-recovery
- ✅ Discord commands: `/schedule today`, `/schedule week`, `/status`
- ✅ Keep-alive heartbeat: Session maintenance to prevent timeout
- ✅ Error handling: Graceful failure notifications to user

**MVP Success Criteria:**
- Single user (Admin) can replace manual FAP schedule checks with bot
- Zero manual FAP logins required for schedule information
- Bot runs continuously for 1 week without manual intervention

---

### Growth Features (Post-MVP)

**Phase 2 - Enhanced Functionality:**
- Grade scraping: `/grades` command with term filtering
- Grade notifications: Immediate alert when new grades posted
- Exam schedule: `/exams` command with date filtering
- Exam notifications: Reminders 24 hours and 1 hour before exams
- Application status: View submitted academic applications
- Historical data: Access past weeks' schedules and grade history

**Phase 3 - Multi-User Support:**
- Individual credentials per user (encrypted storage)
- User preferences: Notification timing, delivery channel, content filters
- User management: Register, update credentials, delete account
- Usage analytics: Command usage, notification engagement tracking

---

### Vision (Future)

**Dream Scenario - Comprehensive Academic Assistant:**
- Full FAP integration: All accessible data types (attendance, assignments, announcements)
- AI-powered insights: Study schedule optimization, grade trend analysis
- Calendar integration: Export schedules to Google Calendar, Outlook
- Mobile support: Discord mobile commands optimized
- Community features: Share schedules with classmates, coordinate study groups
- Platform expansion: Beyond FAP—other university portals, LMS integration

**Technical Vision:**
- Self-healing architecture: Automatic recovery from any FAP changes
- Zero-downtime deployments: Updates without service interruption
- Multi-instance deployment: Scalable to hundreds of concurrent users
- Advanced anti-detection: Continuous evolution bypassing Cloudflare enhancements

