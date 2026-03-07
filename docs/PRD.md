# Product Requirements Document (PRD)
## FAP Discord Bot - Personal Assistant for FPT University Students

**Version:** 1.0
**Date:** 2026-03-07
**Product Owner:** Admin
**Document Status:** Draft

---

## Table of Contents

1. [Document Information](#document-information)
2. [Executive Summary](#executive-summary)
3. [Product Vision](#product-vision)
4. [Problem Statement](#problem-statement)
5. [User Personas](#user-personas)
6. [User Stories](#user-stories)
7. [Functional Requirements](#functional-requirements)
8. [Non-Functional Requirements](#non-functional-requirements)
9. [User Interface Requirements](#user-interface-requirements)
10. [Data Requirements](#data-requirements)
11. [Integration Requirements](#integration-requirements)
12. [Success Metrics](#success-metrics)
13. [Release Phases](#release-phases)
14. [Risks & Mitigations](#risks--mitigations)

---

## Document Information

| Field | Value |
|-------|-------|
| **Product Name** | FAP Discord Bot |
| **Version** | 1.0 |
| **Status** | Draft |
| **Author** | Admin + BMAD Team |
| **Stakeholders** | FPT University Students |
| **Target Platform** | Discord |
| **Target Users** | FPT University students (initially single-user) |

---

## Executive Summary

### Product Overview
FAP Discord Bot is a **proactive personal assistant** for FPT University students that monitors their FAP (FPT Academic Portal) account and provides timely notifications through Discord. Unlike the myFAP app which requires manual checking, this bot pushes important updates to students.

### Key Differentiators
| Feature | myFAP App | FAP Discord Bot |
|---------|-----------|----------------|
| **Attendance** | Manual check | Automatic monitoring + alerts |
| **Schedule Changes** | Must check | Proactive notifications |
| **Grades** | Manual check | Immediate notifications |
| **Exam Reminders** | None | Multi-level reminders |
| **Application Status** | Manual check | Automatic status updates |
| **Platform** | Mobile app | Discord (always accessible) |

### Business Value
- **Time Savings:** Students save 30+ minutes/day checking FAP
- **Reduced Anxiety:** Proactive attendance monitoring prevents "Did I get marked absent?" stress
- **Academic Performance:** Timely reminders prevent missed classes/exams
- **Transparency:** Immediate notification of grade/application changes

---

## Product Vision

### Vision Statement
> "Every FPT student deserves a personal assistant that keeps them informed about their academic life without constant manual checking."

### Mission
> "To provide timely, actionable academic information to FPT University students through their preferred communication platform (Discord)."

### Success Criteria
- **User Adoption:** 90% daily active rate
- **Notification Accuracy:** 99%+ accuracy in attendance/grade detection
- **Response Time:** Notifications sent within 5 minutes of FAP updates
- **User Satisfaction:** 4.5/5 star rating

---

## Problem Statement

### Current Pain Points

#### Problem 1: Attendance Anxiety
**User Quote:** *"I constantly worry whether I was marked present or absent. I have to keep checking FAP throughout the day."*

**Impact:**
- Students spend 15-30 minutes/day checking FAP
- Anxiety about attendance status affects focus in class
- Late discovery of incorrect attendance = harder to fix

**Frequency:** Every class day, multiple times per day

#### Problem 2: Schedule Changes
**User Quote:** *"The schedule changed but I didn't know until I showed up at the wrong room."*

**Impact:**
- Missed classes or late arrivals
- Wasted time commuting to wrong locations
- Embarrassment and academic consequences

**Frequency:** Weekly occurrences during add/drop periods

#### Problem 3: Grade Waiting Game
**User Quote:** *"I keep refreshing FAP to see if grades are posted yet. It's exhausting."*

**Impact:**
- Productivity loss from constant checking
- Anxiety about academic performance
- No centralized grade tracking

**Frequency:** Daily during and after exam periods

#### Problem 4: Exam Amnesia
**User Quote:** *"I completely forgot about an exam until the night before. No time to prepare."*

**Impact:**
- Poor exam performance
- Last-minute cramming stress
- Potential grade impact

**Frequency:** Each exam period (monthly)

#### Problem 5: Application Black Hole
**User Quote:** *"I submitted a request but have no idea if it's approved. It's been weeks."*

**Impact:**
- Uncertainty about application status
- Delayed follow-up actions
- Missed deadlines for appeals

**Frequency:** Per application submission

### Root Causes
| Problem | Root Cause | Solution |
|---------|------------|----------|
| Attendance anxiety | No real-time monitoring | Automated 5-min checks |
| Schedule changes | Manual checking required | Change detection + alerts |
| Grade waiting | No push notifications | Immediate grade alerts |
| Exam amnesia | No reminders | Multi-level exam reminders |
| Application black hole | No status updates | Real-time status tracking |

---

## User Personas

### Primary Persona: Alex - The Proactive Student

**Demographics:**
- Age: 20
- Year: Sophomore
- Major: Software Engineering
- Campus: FPT University Ho Chi Minh
- Discord User: 8+ hours/day

**Goals:**
- Maintain high GPA (target: 3.7+)
- Never miss a class or exam
- Stay on top of administrative tasks
- Focus on studies, not paperwork

**Frustrations:**
- "I waste too much time checking FAP"
- "I'm always anxious about my attendance"
- "I hate discovering things too late"

**Tech Savviness:** High - comfortable with bots, automation, Discord

### Secondary Persona: Minh - The Busy Student

**Demographics:**
- Age: 21
- Year: Junior
- Major: Business Administration
- Works part-time: 20 hours/week
- Discord User: 2-3 hours/day

**Goals:**
- Balance work and studies
- Never miss deadlines
- Stay organized without effort

**Frustrations:**
- "I forget things because I'm so busy"
- "Checking FAP is not my priority"
- "I need reminders, not more apps"

**Tech Savviness:** Medium - uses basic apps, prefers simplicity

---

## User Stories

### Epic 1: Attendance Monitoring

#### US-1.1: Real-time Attendance Tracking
**As a** student
**I want** to be notified immediately when my attendance is recorded
**So that** I can verify it's correct and fix errors promptly

**Acceptance Criteria:**
- [ ] System checks attendance status every 5 minutes during class hours
- [ ] Notification sent when status changes from "not marked" to "attended"
- [ ] Notification sent when status changes from "not marked" to "absent"
- [ ] Absent notification includes call-to-action to contact teacher
- [ ] No duplicate notifications for same status

**Priority:** P0 (Must Have)

---

#### US-1.2: Class Ending Warnings
**As a** student
**I want** to be warned before class ends
**So that** I can ensure I was marked present before leaving

**Acceptance Criteria:**
- [ ] First warning sent 15 minutes before class ends
- [ ] Second warning sent 10 minutes before class ends
- [ ] Final warning sent 5 minutes before class ends
- [ ] Warnings only sent if attendance not yet marked
- [ ] Warnings stop once attendance is confirmed

**Priority:** P0 (Must Have)

---

#### US-1.3: Attendance History
**As a** student
**I want** to view my attendance history
**So that** I can track my attendance record over time

**Acceptance Criteria:**
- [ ] Command: `/attendance [term?] [week?]`
- [ ] Shows attendance status for each class
- [ ] Displays attendance statistics (present/absent/total)
- [ ] Defaults to current term and week

**Priority:** P1 (Should Have)

---

### Epic 2: Schedule Management

#### US-2.1: Evening Schedule Summary
**As a** student
**I want** to receive tomorrow's schedule every evening
**So that** I can plan my day in advance

**Acceptance Criteria:**
- [ ] Schedule sent at 7:30 PM daily
- [ ] Includes all classes for tomorrow
- [ ] Shows subject, room, and time for each class
- [ ] Displays "No classes tomorrow" if applicable
- [ ] Shows cached data if FAP is unavailable

**Priority:** P0 (Must Have)

---

#### US-2.2: Schedule Change Detection
**As a** student
**I want** to be notified of schedule changes
**So that** I'm not surprised by room/time changes

**Acceptance Criteria:**
- [ ] System detects changes between cached and current schedule
- [ ] Notifications sent for:
  - [ ] New classes added
  - [ ] Classes removed
  - [ ] Room changes
  - [ ] Time changes
- [ ] Changes highlighted in evening schedule

**Priority:** P0 (Must Have)

---

#### US-2.3: Class Reminders
**As a** student
**I want** to be reminded 5 minutes before each class
**So that** I can prepare and remind the teacher to mark attendance

**Acceptance Criteria:**
- [ ] Reminder sent 5 minutes before class starts
- [ ] Includes subject name, room number, and time
- [ ] Reminds to tell teacher about attendance
- [ ] No reminders if class already started/ended

**Priority:** P1 (Should Have)

---

### Epic 3: Grade Management

#### US-3.1: Grade Notifications
**As a** student
**I want** to be notified when new grades are posted
**So that** I don't have to keep checking FAP

**Acceptance Criteria:**
- [ ] System checks for new grades every hour
- [ ] Notification sent when new grade appears
- [ ] Notification sent when grade value changes
- [ ] Notification includes subject, grade, and GPA impact

**Priority:** P0 (Must Have)

---

#### US-3.2: Grade Summary
**As a** student
**I want** to view all my grades in one place
**So that** I can track my academic performance

**Acceptance Criteria:**
- [ ] Command: `/grades [term?]`
- [ ] Shows all subjects with grades
- [ ] Displays term GPA and cumulative GPA
- [ ] Defaults to latest term with grades
- [ ] Supports term selection

**Priority:** P1 (Should Have)

---

#### US-3.3: Pending Grade Alerts
**As a** student
**I want** to know which subjects don't have grades yet
**So that** I can follow up if needed

**Acceptance Criteria:**
- [ ] Identifies subjects without grades
- [ ] Checks if exam is completed
- [ ] Notifies if exam passed but no grade after 7 days
- [ ] Includes exam date for upcoming exams

**Priority:** P2 (Nice to Have)

---

### Epic 4: Exam Management

#### US-4.1: Exam Schedule
**As a** student
**I want** to view my exam schedule
**So that** I can plan my preparation

**Acceptance Criteria:**
- [ ] Command: `/exams [term?]`
- [ ] Shows all exams with date, time, room, and format
- [ ] Defaults to current/upcoming term

**Priority:** P1 (Should Have)

---

#### US-4.2: Exam Reminders
**As a** student
**I want** to be reminded before exams
**So that** I don't miss them or under-prepare

**Acceptance Criteria:**
- [ ] Reminder sent 1 day before exam
- [ ] Reminder sent 1 hour before exam
- [ ] Includes exam date, time, room, and format
- [ ] Reminds to bring required items (ID, etc.)

**Priority:** P0 (Must Have)

---

#### US-4.3: New Exam Detection
**As a** student
**I want** to be notified when new exams appear
**So that** I'm not surprised by last-minute additions

**Acceptance Criteria:**
- [ ] System checks for new exams every hour
- [ ] Notification sent when new exam detected
- [ ] Notification sent when exam details change
- [ ] Includes all exam details

**Priority:** P1 (Should Have)

---

### Epic 5: Application Tracking

#### US-5.1: Application Status Updates
**As a** student
**I want** to be notified when my application status changes
**So that** I know if it was approved or rejected

**Acceptance Criteria:**
- [ ] System checks application status hourly (if pending) or daily (if none pending)
- [ ] Notification sent when status changes from Pending → Approved
- [ ] Notification sent when status changes from Pending → Rejected
- [ ] Includes application details and reason for rejection

**Priority:** P1 (Should Have)

---

#### US-5.2: Application History
**As a** student
**I want** to view my submitted applications
**So that** I can track their status

**Acceptance Criteria:**
- [ ] Command: `/applications`
- [ ] Shows all applications with status
- [ ] Sorted by most recent first
- [ ] Includes application type, purpose, and status

**Priority:** P2 (Nice to Have)

---

### Epic 6: GPA Calculator

#### US-6.1: GPA Calculation
**As a** student
**I want** to calculate my GPA
**So that** I can track my academic progress

**Acceptance Criteria:**
- [ ] Command: `/gpa [term?] [--exclude="subjects"]`
- [ ] Calculates term GPA
- [ ] Calculates cumulative GPA
- [ ] Shows term-by-term breakdown
- [ ] Allows excluding certain subjects (PE, music, etc.)

**Priority:** P1 (Should Have)

---

## Functional Requirements

### FR-1: Authentication
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | User must authenticate with Discord | P0 |
| FR-1.2 | User must provide FAP credentials (FeID) | P0 |
| FR-1.3 | FAP credentials must be encrypted in storage | P0 |
| FR-1.4 | User must specify notification channel | P0 |
| FR-1.5 | System must maintain FAP session via cookies | P0 |

### FR-2: Schedule Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | System must fetch schedule from FAP | P0 |
| FR-2.2 | System must cache schedule for offline access | P0 |
| FR-2.3 | System must detect schedule changes | P0 |
| FR-2.4 | System must send evening schedule at 19:30 | P0 |
| FR-2.5 | System must send class reminders 5 min before | P1 |
| FR-2.6 | User must be able to query schedule via command | P0 |

### FR-3: Attendance Monitoring
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | System must check attendance every 5 minutes during class hours | P0 |
| FR-3.2 | System must detect attendance status changes | P0 |
| FR-3.3 | System must send escalating warnings (15/10/5 min) | P0 |
| FR-3.4 | System must notify when attendance recorded | P0 |
| FR-3.5 | System must alert when marked absent | P0 |
| FR-3.6 | User must be able to query attendance history | P1 |

### FR-4: Grade Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | System must check for new grades hourly | P0 |
| FR-4.2 | System must detect grade changes | P0 |
| FR-4.3 | System must notify of new grades | P0 |
| FR-4.4 | System must notify of grade changes | P0 |
| FR-4.5 | User must be able to query grades by term | P1 |
| FR-4.6 | System must calculate GPA | P1 |
| FR-4.7 | System must support subject exclusions for GPA | P2 |

### FR-5: Exam Management
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | System must fetch exam schedule from FAP | P1 |
| FR-5.2 | System must detect new exams | P1 |
| FR-5.3 | System must detect exam changes | P1 |
| FR-5.4 | System must send 1-day-before exam reminder | P0 |
| FR-5.5 | System must send 1-hour-before exam reminder | P0 |
| FR-5.6 | User must be able to query exam schedule | P1 |

### FR-6: Application Tracking
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | System must fetch applications from FAP | P1 |
| FR-6.2 | System must check pending applications hourly | P1 |
| FR-6.3 | System must check non-pending applications daily | P1 |
| FR-6.4 | System must detect application status changes | P1 |
| FR-6.5 | System must notify of status changes | P1 |
| FR-6.6 | User must be able to query application history | P2 |

### FR-7: Notifications
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | System must send notifications to specified channel | P0 |
| FR-7.2 | System must format notifications as Discord embeds | P0 |
| FR-7.3 | System must handle FAP downtime gracefully | P0 |
| FR-7.4 | System must show cached data when FAP is down | P0 |
| FR-7.5 | System must avoid duplicate notifications | P0 |

### FR-8: Error Handling
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-8.1 | System must log all errors | P0 |
| FR-8.2 | System must notify user of FAP connection failures | P0 |
| FR-8.3 | System must retry failed requests with exponential backoff | P1 |
| FR-8.4 | System must handle Cloudflare challenges | P0 |
| FR-8.5 | System must handle session expiration | P0 |

---

## Non-Functional Requirements

### NFR-1: Performance
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1.1 | Notification latency | < 5 minutes from FAP update |
| NFR-1.2 | Command response time | < 10 seconds |
| NFR-1.3 | FAP page fetch time | < 30 seconds |
| NFR-1.4 | Database query time | < 1 second |
| NFR-1.5 | Background task overhead | < 5% CPU |

### NFR-2: Reliability
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-2.1 | System uptime | > 99% |
| NFR-2.2 | Notification accuracy | > 99% |
| NFR-2.3 | Data persistence | No data loss |
| NFR-2.4 | Recovery time | < 5 minutes |

### NFR-3: Scalability
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-3.1 | Concurrent users | Support 10+ users in MVP |
| NFR-3.2 | Notifications per hour | Support 100+ notifications/hour |
| NFR-3.3 | Database size | Support 1GB+ data |
| NFR-3.4 | Memory usage | < 512MB RAM |

### NFR-4: Security
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-4.1 | Password encryption | Fernet/AES-256 |
| NFR-4.2 | Discord token security | Environment variables only |
| NFR-4.3 | FAP credentials protection | Never logged or exposed |
| NFR-4.4 | SQL injection prevention | Parameterized queries |
| NFR-4.5 | XSS prevention | Input sanitization |

### NFR-5: Maintainability
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-5.1 | Code documentation | All functions documented |
| NFR-5.2 | Test coverage | > 80% |
| NFR-5.3 | Logging | Comprehensive logging |
| NFR-5.4 | Configuration | Externalized (.env) |
| NFR-5.5 | Deployment | Automated deployment |

---

## User Interface Requirements

### UI-1: Discord Commands
| Command | Description | Parameters |
|---------|-------------|------------|
| `/schedule [day?]` | View schedule | day: today/tomorrow/week |
| `/grades [term?]` | View grades | term: term identifier |
| `/attendance [term?] [week?]` | View attendance | term: term, week: week number |
| `/exams [term?]` | View exam schedule | term: term identifier |
| `/applications` | View applications | none |
| `/gpa [term?] [--exclude]` | Calculate GPA | term: term, exclude: subject list |
| `/config` | Configure bot | key: setting name, value: setting value |
| `/status` | View bot status | none |

### UI-2: Notification Formats

#### N2.1: Evening Schedule
```
📅 Lịch học ngày mai - [Date]

┌─────────────────────────────────────┐
│ 🕐 Slot 1-2 (7:00-9:15)             │
│ **Subject (Code)**                  │
│ 📍 Room XXX                         │
└─────────────────────────────────────┘

💡 Thay đổi: [Changes detected]
```

#### N2.2: Class Reminder
```
⏰ Sắp vào lớp!

**Subject (Code)** bắt đầu sau 5 phút

📍 Room XXX
🕐 Time - Time

💡 Đừng quên nhắc thầy cô điểm danh!
```

#### N2.3: Attendance Recorded
```
✅ Điểm danh thành công!

**Subject (Code)** - Slot X

✅ Đã ghi nhận: Có mặt
```

#### N2.4: Absent Alert
```
⚠️ CẢNH BÁO: Ghi nhận vắng mặt!

**Subject (Code)** - Slot X

❌ Hệ thống ghi nhận: Vắng mặt

👉 Hãy liên hệ ngay với giảng viên!
```

#### N2.5: New Grade
```
📊 Có điểm mới!

**Subject Name (Code)**

📈 Điểm: X.X
📝 Hệ số: X

🎯 Ảnh hưởng GPA: ±X.XXX
```

#### N2.6: Exam Reminder
```
📝 Nhắc nhở thi cuối kỳ

**Ngày mai:** Subject (Code)

📅 Date
🕐 Time
📍 Room
📋 Format

📚 Chuẩn bị: CMND, bút, giấy
```

### UI-3: Color Scheme
| Notification Type | Color (Hex) |
|------------------|-------------|
| Success | 0x00ff00 (Green) |
| Warning | 0xffff00 (Yellow) |
| Error | 0xff0000 (Red) |
| Info | 0x00bfff (Blue) |
| Exam | 0x9b59b6 (Purple) |
| Grade | 0x00ff00 (Green) |
| Application | 0x00ff00 / 0xff0000 |

---

## Data Requirements

### DR-1: Data Storage
| Entity | Storage | Retention |
|--------|---------|-----------|
| User credentials | Encrypted | Until deleted |
| Schedule cache | SQLite | 7 days |
| Attendance state | SQLite | Current term |
| Grade cache | SQLite | Current term |
| Application cache | SQLite | 30 days |
| Exam cache | SQLite | Until exam passed |

### DR-2: Data Elements

#### User Data
| Field | Type | Required | Encrypted |
|-------|------|----------|----------|
| user_id | String | Yes | No |
| fap_username | String | Yes | No |
| fap_password | String | Yes | Yes |
| server_id | String | Yes | No |
| channel_id | String | Yes | No |

#### Schedule Data
| Field | Type | Source |
|-------|------|--------|
| date | Date | FAP |
| slot | Integer | FAP |
| subject_code | String | FAP |
| subject_name | String | FAP |
| room | String | FAP |
| start_time | Time | FAP |
| end_time | Time | FAP |
| attendance_status | String | FAP |

#### Grade Data
| Field | Type | Source |
|-------|------|--------|
| term | String | FAP |
| subject_code | String | FAP |
| subject_name | String | FAP |
| grade | Float | FAP |
| credits | Integer | FAP |

---

## Integration Requirements

### IR-1: FAP Portal Integration
| Aspect | Requirement |
|--------|-------------|
| **Protocol** | HTTPS |
| **Authentication** | FeID + FlareSolverr |
| **Session Management** | Cookie persistence |
| **Rate Limiting** | Respect FAP limits (1 req/sec) |
| **Error Handling** | Retry on failure |
| **Pages** | Schedule, Grades, Applications, Exams |

### IR-2: Discord Integration
| Aspect | Requirement |
|--------|-------------|
| **API** | discord.py 2.3.2+ |
| **Bot Token** | Environment variable |
| **Intents** | Message content, Guilds, Members |
| **Commands** | Slash commands |
| **Notifications** | Channel messages (embeds) |

### IR-3: FlareSolverr Integration
| Aspect | Requirement |
|--------|-------------|
| **Protocol** | HTTP (WebSocket) |
| **Endpoint** | http://localhost:8191/v1 |
| **Fallback** | Error notification |
| **Deployment** | Docker container |

---

## Success Metrics

### SM-1: User Engagement
| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily Active Users | > 90% | User activity logs |
| Command Usage | > 10 commands/day/user | Command logs |
| Notification Read Rate | > 80% | Discord analytics |

### SM-2: Technical Performance
| Metric | Target | Measurement |
|--------|--------|-------------|
| Notification Latency | < 5 min | Timestamp comparison |
| System Uptime | > 99% | Monitoring logs |
| Error Rate | < 1% | Error logs |

### SM-3: User Satisfaction
| Metric | Target | Measurement |
|--------|--------|-------------|
| User Satisfaction | > 4.5/5 | User survey |
| Feature Completion | > 90% stories completed | Sprint tracking |
| Bug Reports | < 5 per release | Issue tracker |

---

## Release Phases

### Phase 1: MVP Foundation (Sprint 1-2, ~3 weeks)
**Goal:** Core schedule and grade functionality

**Features:**
- Evening schedule (19:30)
- Schedule change detection
- Grade check command
- Attendance check command
- Exam schedule command
- SQLite database
- Background scheduler

**Success Criteria:**
- All Phase 1 stories completed
- Tests passing
- Deployed to DigitalOcean
- User can receive evening schedule
- User can query grades/attendance/exams

---

### Phase 2: Notifications (Sprint 3, ~1 week)
**Goal:** Proactive notifications

**Features:**
- Class reminders (5 min before)
- Grade update notifications
- Exam reminders (1 day, 1 hour)
- New exam detection

**Success Criteria:**
- All Phase 2 stories completed
- User receives class reminders
- User receives grade notifications
- User receives exam reminders

---

### Phase 3: Real-time Monitoring (Sprint 4, ~1.5 weeks)
**Goal:** Continuous monitoring

**Features:**
- Attendance monitoring (5 min checks)
- Class ending warnings (15/10/5 min)
- Application status monitoring
- Dynamic check frequency

**Success Criteria:**
- All Phase 3 stories completed
- Attendance status changes detected within 5 min
- Application status changes detected within 1 hour

---

### Phase 4: Final Features (Sprint 5, ~1 week)
**Goal:** Complete feature set

**Features:**
- GPA calculator
- Application history command
- Complete documentation
- Deployment guide
- Troubleshooting guide

**Success Criteria:**
- All stories completed
- Documentation complete
- User can calculate GPA
- Deployment guide tested

---

### Phase 5: Future Enhancements (Post-MVP)
**Potential Features:**
- Multi-user support with separate FAP accounts
- AI chat notes for exam/homework reminders
- Analytics dashboard
- Mobile app companion
- Integration with other university systems

---

## Risks & Mitigations

### Risk 1: FAP Portal Changes
**Impact:** High
**Probability:** Medium

**Description:** FAP portal structure changes could break parsers.

**Mitigation:**
- Create flexible parsers using CSS selectors
- Implement error detection and alerts
- Maintain parser versioning
- Create automated parser tests

**Contingency:**
- Fallback to cached data with warnings
- Quick parser update turnaround (< 24 hours)

---

### Risk 2: Cloudflare Detection
**Impact:** High
**Probability:** Medium

**Description:** FlareSolverr may be detected and blocked by Cloudflare.

**Mitigation:**
- Monitor FlareSolverr updates
- Implement multiple bypass methods
- Use rotating user agents
- Implement exponential backoff

**Contingency:**
- Manual login via provided instructions
- Queue requests during outages

---

### Risk 3: Rate Limiting
**Impact:** Medium
**Probability:** High

**Description:** FAP may implement rate limiting, blocking frequent requests.

**Mitigation:**
- Implement request queuing
- Use exponential backoff
- Cache data aggressively
- Distribute requests across time

**Contingency:**
- Reduce check frequency
- Prioritize critical checks (attendance)

---

### Risk 4: Data Privacy
**Impact:** High
**Probability:** Low

**Description:** FAP credentials could be exposed, compromising user accounts.

**Mitigation:**
- Encrypt all credentials (Fernet/AES-256)
- Never log credentials
- Use environment variables
- Regular security audits

**Contingency:**
- Immediate credential rotation
- User notification of breach
- Security incident response plan

---

### Risk 5: Discord API Limitations
**Impact:** Medium
**Probability:** Low

**Description:** Discord API changes or rate limits could affect bot functionality.

**Mitigation:**
- Monitor Discord API changelog
- Implement rate limit handling
- Use official discord.py library
- Graceful degradation

**Contingency:**
- Queue notifications during rate limits
- User notification of delays

---

### Risk 6: VPS Downtime
**Impact:** Medium
**Probability:** Low

**Description:** DigitalOcean VPS downtime affects all users.

**Mitigation:**
- Use DigitalOcean monitoring
- Implement health checks
- Automated restart scripts
- Backup strategy

**Contingency:**
- Switch to backup VPS
- Data restoration from backup
- User notification of outage

---

## Appendix

### A. Terminology

| Term | Definition |
|------|------------|
| **FAP** | FPT Academic Portal - student information system |
| **FeID** | FPT University single sign-on |
| **FlareSolverr** | Cloudflare bypass proxy |
| **Discord Embed** | Rich Discord message format |
| **Slash Command** | Discord command starting with `/` |
| **Slot** | Time block (1-8) for classes |
| **Term** | Academic semester (Fall, Spring, Summer) |

### B. References
- FAP Portal: https://fap.fpt.edu.vn
- Discord.py Documentation: https://discordpy.readthedocs.io/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- APScheduler Documentation: https://apscheduler.readthedocs.io/

### C. Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-07 | Admin + BMAD Team | Initial PRD creation |

---

**Document Status:** ✅ Ready for Review
**Next Steps:** Architecture Specification → Technical Specification → Implementation
