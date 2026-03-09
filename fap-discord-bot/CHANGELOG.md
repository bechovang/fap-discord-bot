# Changelog

All notable changes to the FAP Discord Bot project.

## [2026-03-09]

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
