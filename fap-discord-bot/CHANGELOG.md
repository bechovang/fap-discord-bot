# Changelog

All notable changes to the FAP Discord Bot project.

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
