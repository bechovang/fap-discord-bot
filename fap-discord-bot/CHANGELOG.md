# Changelog

All notable changes to the FAP Discord Bot project.

## [2026-05-20] - Fix Attendance Scheduler Timezone & Date Matching

### Fixed

#### Critical: Timezone Mismatch in Attendance Scheduler
- **`bot/scheduler.py`** - All `datetime.now()` calls returned UTC time on the Docker container (system TZ = UTC), but were compared against FAP class times in Vietnam timezone (UTC+7)
  - **Root cause:** `datetime.now()` returns system time (UTC in Docker), not Vietnam time. The APScheduler timezone was set to `Asia/Ho_Chi_Minh` but only affected job scheduling, not the code inside jobs.
  - **Impact:** Attendance window check (`_is_in_attendance_window`) compared UTC clock against Vietnam class times, causing a 7-hour offset:
    - Class 9:30-11:45 VN → bot thought it was active at UTC 09:30 (= VN 16:30, already over)
    - Bot missed the actual window (VN 09:30-12:15) entirely and checked 7 hours late
  - **Fix:** Added `from zoneinfo import ZoneInfo` and `VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")`. All 7 `datetime.now()` calls replaced with `datetime.now(VN_TZ)`:
    - `_get_today_schedule()`: schedule fetch date caching
    - `_check_attendance()`: attendance window time comparison
    - `_daily_check()`: schedule parsing, snapshot timestamps
    - `schedule_session_recovery()`: recovery job scheduling

#### Critical: Day-of-Week Label Mismatch in Schedule Parser
- **`scraper/parser.py`** - `get_today_schedule()` now accepts optional `now` parameter for timezone-correct weekday matching
  - **Context:** FAP's date numbers in schedule table headers are often off by 1 day from the real calendar (e.g. FAP says "Wed 21/05" when the actual Wednesday is 20/05). However, the weekday labels (`Mon`, `Wed`, etc.) are correct and correspond to the actual day of week.
  - **Fix:** Added optional `now` parameter so callers can pass timezone-aware datetime. The method still matches by FAP weekday label (which is correct), not by date string (which would fail because FAP dates are wrong).
  - **Method signature:** `get_today_schedule(items: List[ScheduleItem], now: datetime = None)`

#### Timezone Fixes in Command Files
- **`bot/commands/pending_checks.py`** - Fixed 4 `datetime.now()` calls:
  - Added `from zoneinfo import ZoneInfo` and `VN_TZ` constant
  - `get_today_schedule()` call now passes `now=datetime.now(VN_TZ)`
  - Exam date comparisons (`now = datetime.now(VN_TZ)`) in `/pending grades`, `/pending exams`, `/pending attendance`

### Technical Details

#### The Two-Bug Interaction

The timezone bug was the only real issue. The day matching was correct all along:

```
Bug (timezone only):    Bot used UTC 09:45 vs VN class time 9:30-11:45
                        → thought class was in session at 4:45 PM VN (wrong time)
                        → missed actual window 9:30-12:15 VN

NOT a bug (day matching): FAP weekday labels (Mon, Wed, Thu) correctly match
                           real weekdays. Only the date NUMBERS are off by 1.
                           The old weekday matching was correct.
```

#### Timeline: What Happened vs What Should Happen

```
ACTUAL (broken):                          EXPECTED (fixed):
─────────────────────────────────────────────────────────────────
May 20 (Wed) - No class today             May 20 (Wed) - No class today
  07:25 VN: Fetch schedule                  → No attendance checks all day
           → "1 classes" (wrong!)         
  09:45 VN: Check IOT102 attendance       May 21 (Thu) - IOT102 9:30-11:45
           → session expired, login       09:30 VN: Window opens
  10:02 VN: Login OK, fetch abort                  → Attendance check runs
  16:16 VN: Attendance fetch OK           11:45 VN: Class ends
           → class ended 5h ago           12:15 VN: Window closes (+30 min)
  ...checks every 15min until 19:15 VN              → Final check, window closes
```

#### Files Changed

| File | Changes |
|------|---------|
| `bot/scheduler.py` | +`ZoneInfo` import, +`VN_TZ` constant, 7× `datetime.now()` → `datetime.now(VN_TZ)`, 2× `get_today_schedule()` calls pass `now=` |
| `scraper/parser.py` | `get_today_schedule()` added optional `now` parameter for timezone-correct weekday matching |
| `bot/commands/pending_checks.py` | +`ZoneInfo` import, +`VN_TZ` constant, 1× `get_today_schedule()` call passes `now=`, 3× `datetime.now()` → `datetime.now(VN_TZ)` |

---

## [2026-05-17] - HTML Dashboard, Parser Fixes, Login Reliability

### Added

#### HTML Dashboard
- **`bot/web_server.py`** - Lightweight aiohttp web server
  - Serves `data/daily_report.html` at `/` endpoint on port 8080
  - Runs on same asyncio event loop as discord.py (no extra process)
  - Port configurable via `WEB_PORT` env var (default 8080)
  - Returns "Report not ready yet" message if file doesn't exist

- **`bot/html_report.py`** - Full HTML dashboard renderer
  - `render_daily_report(data: dict) -> str` returns complete HTML page
  - Dark theme, responsive, CSS inline (no external dependencies except Chart.js CDN)
  - Chart.js bar chart for grade distribution, doughnut chart for attendance
  - Sections: summary cards, today's schedule, weekly grid, grades table + GPA chart, attendance summary + detail, exams table
  - Auto-updated every time daily check runs

- **`docker-compose.yml`** - Exposed port 8080 and added `DASHBOARD_URL` env var
  ```yaml
  ports:
    - "8080:8080"
  environment:
    - DASHBOARD_URL=${DASHBOARD_URL:-}
  ```

- Dashboard URL included in Discord daily check notification messages

#### New Slash Command
- **`/daily`** - Manually trigger daily check and update dashboard
  - Shows ephemeral "Running daily check..." message, then edits with result + dashboard URL
  - Added to `bot/commands/status.py`

### Fixed

#### Grade & Attendance Parser in Scheduler
- **`bot/scheduler.py`** - Fixed grade and attendance parsing in daily check
  - **Root cause:** Scheduler fetched only the term overview page which has no grade/attendance table. The FAP grade page shows course links but the actual grade data requires navigating to each individual course page.
  - **Fix:** Changed `_daily_check()` to follow the same course-iteration pattern as `/grade this-term` and `/attendance this-term` commands:
    1. Fetch base page → extract course list
    2. For each course, fetch individual course page with `course=course_id`
    3. Parse grade/attendance data from each course page
  - Grade parser now successfully extracts: CSD201 (8.0), DBI202 (6.6), JPD113 (7.8), LAB211 (0.0), MAS291 (8.4), SWE202 (6.7)
  - Attendance parser now iterates courses individually (4 fetches for 6 courses)

#### FeID Login Reliability
- **`scraper/auto_login_feid.py`** - Multiple login flow improvements
  - Refactored `_trigger_feid_login()` into 3 methods with retry loop:
    - `_click_feid_button()` - Click FeID button with `wait_for(state="visible", timeout=10000)` before checking button count
    - `_wait_for_feid_redirect(timeout=15.0)` - Poll-based redirect detection (replaces blind 3s sleep)
    - `_trigger_feid_login()` - 3-retry loop wrapping click + redirect
  - FeID redirect timeout increased from 3s blind sleep to 15s poll loop
  - FeID button now waits for visibility before interaction (fixes startup timing issue)

#### Cloudflare Title Detection (Multilingual)
- **`scraper/auto_login_feid.py`** - Expanded Cloudflare challenge detection
  - Added multilingual CF keywords: Vietnamese (chờ, vui lòng chờ), Japanese (稍候), Korean (잠시), French (un instant), German (einen moment), Italian (attendi), Portuguese (aguarde)
  - Increased non-CF title acceptance thresholds:
    - `i > 15` with `fap`/`fpt` title check (was `i > 5`)
    - `i > 30` hard fallback (was implicit at `i > 5`)
  - Added FAP content detection: checks for `btnloginFeId`, `drpSelectWeek`, `ddlCampus` in page body

### Changed

- `bot/bot.py` - Start web server in `setup_hook()` after auth setup
- `bot/scheduler.py` - Daily check now renders HTML dashboard after snapshot save
- `bot/commands/status.py` - Added `/daily` command
- `docker-compose.yml` - Added port 8080 exposure and `DASHBOARD_URL` env var

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_PORT` | `8080` | Dashboard web server port |
| `DASHBOARD_URL` | (empty) | Public URL shown in Discord notifications (e.g., `http://68.183.233.253:8080/`) |

---

## [2026-03-11] - Grade Feature Improvements

### Fixed

#### Grade Parsing & Discord Interaction
- **`bot/commands/grade.py`** - Fixed Discord interaction timeout issue
  - Changed from `defer(thinking=True)` to `defer(ephemeral=True)` for faster response
  - Added proper exception handling for `NotFound` (404) and `HTTPException` (40060)
  - Removed fallback `send_message` after failed defer (causes double-acknowledge error)
  - Added detailed logging for debugging:
    - Base page HTML length
    - Number of courses extracted
    - Per-course HTML fetch results
    - Grades parsed per course
    - Total grades collected

- **`scraper/grade_parser.py`** - Improved grade table parsing
  - Split parsing into two methods: `_parse_detailed_grade_table()` and `_parse_summary_grade_table()`
  - Detailed grade table: Parses footer for Average (total grade) and Status
  - Falls back to summary table if grade div not found
  - Saves debug HTML to `debug_grade_parse_error.html` when parsing fails

### Changed

- All followup messages in grade commands now use `ephemeral=True` consistently
- Grade fetching now logs each step for better debugging

### Known Issues

- Credits showing as 0: Detailed grade view doesn't display credit count
- Some courses show "UNKNOWN" as subject code when HTML doesn't contain course code pattern
- Grade fetching is slow (~30-60s for 6 courses) because each course creates a new browser instance

---

## [2026-03-11] - Attendance & Grade Features

### Added

#### Attendance Tracking
- **`scraper/attendance_parser.py`** - New parser for attendance data
  - `AttendanceItem` dataclass with fields: no, subject_code, subject_name, room, day, date, slot, start_time, end_time, attendance_status, lecturer, group_name, credits
  - `AttendanceSummary` dataclass for statistics (total, present, absent, future, percentage)
  - `AttendanceParser` class with methods: `extract_terms()`, `extract_courses()`, `parse_attendance()`, `calculate_summary()`, `format_for_discord()`
  - Support for parsing term list (limited to 10 most recent terms)
  - Support for parsing course list and attendance records
  - Attendance status detection via font color attributes (green=present, red=absent)

- **`bot/commands/attendance.py`** - New Discord slash commands
  - `/attendance view [term] [course]` - Interactive attendance viewer with dropdown menus
  - `/attendance this-term` - Quick view attendance for most recent term
  - Interactive `AttendanceView` with term/course selectors and refresh button
  - Aggregates attendance across all courses in a term

#### Grade/Score Viewing
- **`scraper/grade_parser.py`** - New parser for grade data
  - `GradeItem` dataclass with fields: no, subject_code, subject_name, credits, mid_term, final, total, status, grade_4scale
  - `TermGPA` dataclass for per-term GPA breakdown
  - `GPASummary` dataclass with fields: term, term_gpa, cumulative_gpa, total_credits, earned_credits, subjects_passed, subjects_failed, grade_breakdown, by_term, excluded_subjects
  - `GradeParser` class with methods: `extract_terms()`, `extract_courses()`, `parse_grades()`, `calculate_gpa()`, `format_for_discord()`
  - 10-point to 4-point GPA scale conversion
  - Automatic exclusion of non-GPA subjects (PE, MUSIC, ENG, EN)
  - Cumulative GPA calculation across all recent terms

- **`bot/commands/grade.py`** - New Discord slash commands
  - `/grade view [term] [course]` - Interactive grade viewer with dropdown menus
  - `/grade this-term` - Quick view grades for most recent term
  - `/grade gpa` - Calculate cumulative GPA across all terms
  - Interactive `GradeView` with term/course selectors and GPA calculation button
  - Detailed grade breakdown with letter grades and 4.0 scale conversion

#### Authentication Updates
- **`scraper/auto_login_feid.py`** - Added new fetch methods
  - `fetch_attendance(student_id, campus, term, course)` - Fetch attendance page from FAP
  - `fetch_grades(student_id, term, course)` - Fetch grade page from FAP

- **`scraper/auth.py`** - Added new wrapper methods with auto-refresh
  - `fetch_attendance()` - Wrapper with session auto-refresh on failure
  - `fetch_grades()` - Wrapper with session auto-refresh on failure

#### Bot Configuration
- **`bot/bot.py`** - Registered new command cogs
  - Added `AttendanceCommands` cog
  - Added `GradeCommands` cog

### Changed

- Environment Variables (add to `.env`):
  - `FAP_STUDENT_ID` - Student ID for attendance/grade queries (e.g., SE203055)
  - `FAP_CAMPUS` - Campus ID (default: 4 for FPTU-HCM)

### URLs

- **Attendance:** `https://fap.fpt.edu.vn/Report/ViewAttendstudent.aspx?id={student_id}&campus={campus}&term={term_id}&course={course_id}`
- **Grades:** `https://fap.fpt.edu.vn/Grade/StudentGrade.aspx?rollNumber={student_id}&term={term_name}&course={course_id}`

---

## [2026-03-09] - Docs Reorganization

### Changed

- **Documentation Structure** - Reorganized into `docs/` folder
  - `BOT_LOGIC.md` → `docs/DEVELOPMENT.md`
  - `EXAM_FEATURE.md` → `docs/features/EXAM.md`
  - `FAP-SOLUTION-ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
  - `FLARESOLVERR-GUIDE.md` → `docs/archive/FLARESOLVERR.md`
- Updated README.md with new documentation section

## [2026-03-09] - Exam Schedule & Session Management

### Added

#### Exam Schedule Feature
- **`scraper/exam_parser.py`** - New parser for exam schedule
  - `ExamItem` dataclass with fields: no, subject_code, subject_name, date, room, time, exam_form, exam_type, publication_date
  - `ExamParser` class with `parse_exam_schedule()` method
  - `get_upcoming_exams()` method to filter exams within N days
  - Support for parsing exam schedule table from FAP

- **`bot/commands/exam.py`** - New Discord slash commands
  - `/exam schedule` - View full exam schedule
  - `/exam upcoming` - View upcoming exams (next 7 days)
  - Uses shared `FAPAuth` instance for consistency
  - Formats exam data for Discord with emojis

#### Session Management
- **`scraper/session_validator.py`** - Session health check & auto-refresh
  - `check_session_health()` - Validate if session can access FAP
  - `refresh_session()` - Auto-login when session expired
  - `get_valid_session()` - Ensure valid session before use
  - `ensure_valid_session()` - Convenience function

#### Authentication Refactor
- **`scraper/auth.py`** - Major refactor with concurrency support
  - Global `asyncio.Lock` (`_auth_lock`) to prevent concurrent Chrome access
  - `_refreshing` flag to avoid duplicate refresh attempts
  - `get_session()` method for bot startup validation
  - `fetch_exam_schedule()` method for exam schedule fetching
  - Auto-refresh on fetch failure with retry logic
  - Removed nested locks to prevent deadlock

- **`scraper/auto_login_feid.py`** - Added exam support
  - `fetch_exam_schedule()` method to fetch exam schedule HTML
  - Uses same cookie-based authentication as schedule
  - Handles login redirect and session validation

### Fixed

- **Chrome Profile Lock Issue**
  - Problem: Multiple processes (Schedule, Exam, SessionValidator) trying to use `chrome_profile` simultaneously
  - Solution: Global lock in `FAPAuth` ensures only one Chrome operation at a time
  - Commands wait patiently if another is using Chrome

- **Nested Lock Deadlock**
  - Problem: `_validate_and_refresh_if_needed()` had its own lock, causing nested lock with fetch methods
  - Solution: Removed lock from validator, use `_refreshing` flag instead

- **Race Condition in Exam Command**
  - Problem: Exam command created new `FAPScraper` instance each time, causing Chrome conflicts
  - Solution: Exam now uses shared `FAPAuth` instance like Schedule command

- **Interaction Timeout**
  - Problem: Non-headless refresh took too long, causing Discord interaction timeout
  - Solution: Commands defer immediately, refresh happens in background

### Changed

- **`bot/commands/schedule.py`**
  - Now uses shared `FAPAuth` instance (unchanged)
  - Maintains consistency with exam commands

- **`bot/bot.py`**
  - Startup now calls `auth.get_session()` to validate connection
  - Logs authentication status

### Technical Details

#### Concurrency Flow

```
Command 1 (/schedule today)          Command 2 (/exam schedule)
        │                                    │
        ▼                                    ▼
   fetch_schedule()                    fetch_exam_schedule()
        │                                    │
        ▼                                    ▼
   await _auth_lock                    await _auth_lock
   [ACQUIRED]                          [WAITS...]
        │                                    │
        ▼                                    │
   Try fetch...                         │
        │                                    │
        ▼                                    │
   Failed? _refresh_session_once()      │
        │                                    │
        ▼                                    │
   [Release lock]                       │
        │                                    │
        ▼                                    ▼
   Refresh...                         [ACQUIRED]
   (non-headless, ~30s)                     │
        │                                    ▼
        ▼                               Try fetch...
   [Re-acquire lock]                        │
        │                                    ▼
        ▼                               Failed? Check
   Retry fetch...                       _refreshing flag
        │                               (true = wait)
        ▼                                    │
   [Release lock]                       │
        │                                    ▼
        ▼                               Use existing
   Return HTML                         valid session
                                              │
                                              ▼
                                         Return HTML
```

#### URLs

- **Schedule:** `https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx`
- **Exam:** `https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx`
- **Login:** `https://fap.fpt.edu.vn/Default.aspx`

---

## [2026-03-07]

### Initial Release

- FeID authentication with Playwright
- Schedule fetching and parsing
- Discord bot integration
- Cookie persistence
- FlareSolverr integration (archived later)
