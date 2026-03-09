# Exam Schedule Feature - Implementation Summary

## Overview

Exam schedule viewing feature for FAP Discord Bot, allowing users to check their exam schedules through Discord slash commands.

## Features

### Commands

| Command | Description |
|---------|-------------|
| `/exam schedule` | View full exam schedule |
| `/exam upcoming` | View upcoming exams (next 7 days) |

### Data Model

```python
@dataclass
class ExamItem:
    no: int                 # Số thứ tự
    subject_code: str       # Mã môn học (DBI202)
    subject_name: str       # Tên môn học
    date: str              # Ngày thi (22/03/2026)
    room: str              # Phòng thi (115)
    time: str              # Giờ thi (07h00-09h00)
    exam_form: str         # Hình thức (PRACTICAL_EXAM, ONLINE_EXAM)
    exam_type: str         # Loại (PE - Practical Exam, FE - Final Exam)
    publication_date: str  # Ngày đăng lịch
```

## Architecture

```
User (Discord)
    │
    ▼
/exam schedule command
    │
    ▼
ExamCommands (bot/commands/exam.py)
    │
    ├─► FAPAuth.get_auth() [shared instance]
    │       │
    │       ▼
    │   fetch_exam_schedule() [with lock]
    │       │
    │       ├─► Try fetch with current session
    │       ├─► Failed? → Refresh session
    │       └─► Retry fetch
    │
    ▼
ExamParser.parse_exam_schedule(html)
    │
    ├─► Parse HTML table
    ├─► Extract ExamItem[]
    └─► Filter by date if needed
    │
    ▼
Format for Discord
    │
    ▼
Send response
```

## Files Created/Modified

### New Files

1. **`scraper/exam_parser.py`**
   - `ExamItem` dataclass
   - `ExamParser` class
   - `parse_exam_schedule()` - Parse HTML table to ExamItem[]
   - `get_upcoming_exams()` - Filter exams by date range

### Modified Files

1. **`scraper/auth.py`**
   - Added `fetch_exam_schedule()` method
   - Added `get_session()` method for startup validation
   - Added global lock `_auth_lock` for concurrency control
   - Added `_refreshing` flag to prevent duplicate refresh

2. **`scraper/auto_login_feid.py`**
   - Added `fetch_exam_schedule()` method

3. **`bot/commands/exam.py`**
   - Complete rewrite to use shared `FAPAuth`
   - Added `exam_schedule` command
   - Added `exam_upcoming` command
   - Uses `cog_unload` for cleanup

4. **`.env.example`**
   - Added `FAP_EXAM_URL`

5. **`README.md`**
   - Updated with exam features
   - Updated commands list
   - Added ExamItem data model
   - Updated architecture diagram

6. **`CHANGELOG.md`** (new)
   - Documented all changes made

## Concurrency Handling

### Problem

Multiple commands accessing Chrome simultaneously caused "Target closed" errors:
- `/schedule` launches Chrome
- `/exam` tries to launch Chrome → kills `/schedule`'s Chrome
- Both commands fail

### Solution

Global `asyncio.Lock` in `FAPAuth`:

```python
_auth_lock = asyncio.Lock()

async def fetch_exam_schedule(self):
    async with _auth_lock:  # Only one Chrome operation at a time
        await self._ensure_auth()
        html = await self._auth.fetch_exam_schedule()
        # Auto-refresh if needed...
        return html
```

### Refresh Coordination

```python
self._refreshing = False  # Flag to prevent duplicate refresh

async def _refresh_session_once(self):
    if self._refreshing:
        # Another command is already refreshing, wait for it
        while self._refreshing:
            await asyncio.sleep(0.5)
        return True  # Assume refresh succeeded

    self._refreshing = True
    try:
        # Do refresh...
    finally:
        self._refreshing = False
```

## URL Endpoints

| Purpose | URL |
|---------|-----|
| Login | `https://fap.fpt.edu.vn/Default.aspx` |
| Schedule | `https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx` |
| Exam | `https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx` |

## HTML Parsing

### Exam Table Structure

```html
<table>
  <tr>
    <th>No</th>
    <th>SubjectCode</th>
    <th>SubjectName</th>
    <th>Date</th>
    <th>Room</th>
    <th>Time</th>
    <th>ExamForm</th>
    <th>ExamType</th>
    <th>PublicationDate</th>
  </tr>
  <tr>
    <td>1</td>
    <td>DBI202</td>
    <td>Database Systems</td>
    <td>22/03/2026</td>
    <td>115</td>
    <td>07h00-09h00</td>
    <td>PRACTICAL_EXAM</td>
    <td>PE</td>
    <td>09/03/2026</td>
  </tr>
  <!-- More rows... -->
</table>
```

### Parser Logic

1. Find table with exam data
2. Iterate through rows (skip header)
3. Extract each cell's text
4. Clean and format data
5. Create `ExamItem` objects
6. Return list of exams

## Session Management

### Auto-Refresh Flow

```
1. Bot starts → auth.get_session()
   └─► Check session health
       ├─► Valid → Ready
       └─► Expired → Refresh (non-headless, ~30s)

2. User runs command → auth.fetch_exam_schedule()
   └─► Try fetch with current session
       ├─► Success → Return HTML
       └─► Failed → Refresh session
                   └─► Retry fetch
                       └─► Return HTML
```

### Lock Strategy

| Operation | Lock Required | Duration |
|-----------|--------------|----------|
| Fetch schedule | Yes | ~5-10s |
| Fetch exam | Yes | ~5-10s |
| Check health | Yes (within fetch) | ~5s |
| Refresh session | No (uses flag) | ~30s |

## Discord Response Format

### /exam schedule

```
📚 **Exam Schedule**

Found 3 exam(s)

**1. DBI202 - Database Systems**
📅 22/03/2026 | 🕐 07h00-09h00
📍 Room 115 | 📝 PRACTICAL_EXAM

**2. COM301 - Software Engineering**
📅 25/03/2026 | 🕐 13h30-15h30
📍 Room 203 | 📝 PRACTICAL_EXAM

**3. MAT202 - Linear Algebra**
📅 28/03/2026 | 🕐 09h00-11h00
📍 Room 105 | 📝 FINAL_EXAM
```

### /exam upcoming

```
📚 **Upcoming Exams (Next 7 Days)**

Found 2 exam(s)

**DBI202 - Database Systems**
📅 22/03/2026 | 🕐 07h00-09h00
📍 Room 115

**COM301 - Software Engineering**
📅 25/03/2026 | 🕐 13h30-15h30
📍 Room 203
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "No exams found" | Table empty or parse failed | Check HTML in `exam_schedule_final.html` |
| "Target closed" | Chrome conflict | Lock should prevent, restart bot if persists |
| "Session expired" | Cookies expired | Auto-refresh triggers |
| Interaction timeout | Refresh took too long | Defer immediate, background refresh |

## Testing

### Manual Testing

```bash
# 1. Test parser directly
python -c "
from scraper.exam_parser import ExamParser
parser = ExamParser()
with open('exam_schedule_final.html', 'r', encoding='utf-8') as f:
    html = f.read()
exams = parser.parse_exam_schedule(html)
for exam in exams:
    print(f'{exam.subject_code}: {exam.date}')
"

# 2. Test full flow
python scraper/auto_login_feid.py login your_email password
python -c "
import asyncio
from scraper.auth import FAPAuth
async def test():
    auth = FAPAuth(username='your_email', password='password')
    html = await auth.fetch_exam_schedule()
    print(html[:500] if html else 'Failed')
asyncio.run(test())
"

# 3. Test Discord bot
# Run bot and use /exam schedule command
```

## Future Enhancements

- [ ] Filter exams by subject code
- [ ] Export exam schedule to calendar (ICS)
- [ ] Exam reminders (notifications before exam)
- [ ] Grade checking after exam
- [ ] Exam statistics (pass rate, average score)

---

**Implemented:** 2026-03-09
**Status:** ✅ Production Ready
**Maintainer:** Claude Code + User
