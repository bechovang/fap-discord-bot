# FAP Discord Bot - Logic & Operations Document

## Tài liệu kỹ thuật chi tiết

Cơ sở để phát triển thêm functions mới.

---

## 1. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Discord Gateway                              │
│  Bot: FAP_FPT_BOT#3123                                              │
│  Token: from .env DISCORD_TOKEN                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          main.py                                     │
│  - Load environment variables (.env)                                │
│  - Create FAPBot instance                                           │
│  - Setup cogs (commands)                                            │
│  - Run bot until interrupted                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌──────────┐   ┌──────────┐   ┌──────────┐
         │ Schedule │   │   Exam   │   │  Status  │
         │   Cog    │   │   Cog    │   │   Cog    │
         └────┬─────┘   └────┬─────┘   └────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌─────────────────┐
                    │    FAPAuth      │
                    │   (Shared)      │
                    └────────┬─────────┘
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
         ┌──────────┐  ┌──────────┐  ┌──────────┐
         │ AutoLogin│  │Validator │  │  Parser  │
         │   FeID   │  │ Session  │  │  HTML    │
         └────┬─────┘  └────┬─────┘  └────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │   FAP Portal    │
                    │ fap.fpt.edu.vn  │
                    └─────────────────┘
```

---

## 2. Flow khởi động Bot (Startup)

### File: `main.py`

```python
def main():
    # 1. Load environment variables
    load_dotenv()

    # 2. Get Discord token
    token = os.getenv('DISCORD_TOKEN')

    # 3. Create bot instance
    bot = FAPBot()

    # 4. Run bot (blocking)
    bot.run(token)
```

### File: `bot/bot.py` - FAPBot Class

```python
class FAPBot(commands.Bot):
    async def setup_hook(self):
        """Called when bot is starting"""

        # 1. Initialize FAPAuth if credentials provided
        if os.getenv('FAP_USERNAME') and os.getenv('FAP_PASSWORD'):
            self.auth = FAPAuth(
                username=os.getenv('FAP_USERNAME'),
                password=os.getenv('FAP_PASSWORD'),
                headless=os.getenv('HEADLESS', 'true').lower() == 'true'
            )

        # 2. Load command cogs
        await self.add_cog(ScheduleCommands(self))
        await self.add_cog(ExamCommands(self))
        await self.add_cog(StatusCommands(self))

        # 3. Sync slash commands with Discord
        self.tree.copy_global_to(guild=Object(guild_id))
        await self.tree.sync(guild=Object(guild_id))

    async def on_ready(self):
        """Called when bot is connected to Discord"""

        # 1. Log connection info
        logger.info(f"Logged in as {self.user}")

        # 2. Test FAP authentication
        if self.auth:
            result = await self.auth.get_session()
            if result:
                logger.info("✅ FAP authentication successful")
            else:
                logger.error("❌ FAP authentication failed")
```

**Startup Flow:**
```
main.py
  │
  ├─► load_dotenv() → Read .env file
  │
  ├─► FAPBot() → Create bot instance
  │       │
  │       └─► setup_hook()
  │               │
  │               ├─► Create FAPAuth instance
  │               ├─► Add ScheduleCommands cog
  │               ├─► Add ExamCommands cog
  │               ├─► Add StatusCommands cog
  │               └─► Sync slash commands
  │
  ├─► bot.run(token) → Connect to Discord
  │
  └─► on_ready()
          │
          └─► auth.get_session() → Validate FAP session
                  │
                  ├─► Check cookies exist
                  ├─► Check session health
                  └─► Refresh if needed
```

---

## 3. Session Management Logic

### File: `scraper/auth.py` - FAPAuth Class

#### Khởi tạo

```python
class FAPAuth:
    def __init__(self, username, password, headless=True, auto_refresh=True):
        self.username = username
        self.password = password
        self.headless = headless
        self.auto_refresh = auto_refresh
        self._auth = None          # FAPAutoLogin instance (lazy)
        self._validator = None     # SessionValidator instance (lazy)
        self._refreshing = False   # Flag to prevent duplicate refresh
```

#### Method: `get_session()` - Startup Validation

```python
async def get_session(self, force_refresh=False):
    """
    Called during bot startup to validate session.
    Returns: self if valid, None if failed
    """
    # 1. Check cookies file exists
    cookies_file = Path("data/fap_cookies.json")
    if not cookies_file.exists():
        # No cookies - need to login
        if self.auto_refresh:
            await self._refresh_session_once()
        return self if success else None

    # 2. Check session health
    if force_refresh or self.auto_refresh:
        await self._ensure_validator()
        if not await self._validator.check_session_health():
            # Session expired - refresh
            await self._refresh_session_once()

    return self
```

#### Method: `fetch_schedule(week, year)` - Lấy lịch học

```python
async def fetch_schedule(self, week=None, year=None):
    """
    Fetch schedule HTML with auto-refresh on failure.
    Called by: /schedule today, /schedule week commands
    """
    # 1. Acquire lock (prevent concurrent Chrome access)
    async with _auth_lock:
        # 2. Ensure FAPAutoLogin instance exists
        await self._ensure_auth()

        # 3. First attempt - try with current session
        html = await self._auth.fetch_schedule(week=week, year=year)

        # 4. If failed and auto-refresh enabled
        if not html and self.auto_refresh:
            # 4a. Release lock before refresh (allow other commands to queue)
            # 4b. Refresh session
            if await self._refresh_session_once():
                # 4c. Re-fetch with new session
                html = await self._auth.fetch_schedule(week=week, year=year)

        # 5. Return HTML or None
        return html
```

#### Method: `fetch_exam_schedule()` - Lấy lịch thi

```python
async def fetch_exam_schedule(self):
    """
    Fetch exam schedule HTML with auto-refresh on failure.
    Called by: /exam schedule, /exam upcoming commands
    """
    # Same logic as fetch_schedule(), but calls:
    # await self._auth.fetch_exam_schedule()
    async with _auth_lock:
        await self._ensure_auth()
        html = await self._auth.fetch_exam_schedule()

        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                html = await self._auth.fetch_exam_schedule()

        return html
```

#### Method: `_refresh_session_once()` - Refresh Session

```python
async def _refresh_session_once(self):
    """
    Refresh session once with duplicate prevention.
    Uses flag instead of lock to avoid blocking other commands.
    """
    # 1. Check if already refreshing
    if self._refreshing:
        # Wait for other refresh to complete
        while self._refreshing:
            await asyncio.sleep(0.5)
        # Return True (assume refresh succeeded)
        return True

    # 2. Start refresh
    self._refreshing = True
    try:
        # 3. Do actual refresh (non-headless for Cloudflare)
        await self._ensure_validator()
        success = await self._validator.refresh_session(headless=False)
        return success
    finally:
        # 4. Clear flag
        self._refreshing = False
```

---

## 4. Command Handling Logic

### Pattern cho tất cả commands

```
User types slash command
        │
        ▼
Discord receives command
        │
        ▼
Discord routes to appropriate cog
        │
        ▼
Cog method executes:
        │
        ├─► 1. interaction.response.defer(thinking=True)
        │       (Tell Discord "I'm working on it")
        │
        ├─► 2. Get auth instance
        │       auth = await self._get_auth()
        │
        ├─► 3. Fetch data
        │       html = await auth.fetch_xxx()
        │
        ├─► 4. Parse data
        │       items = parser.parse_xxx(html)
        │
        ├─► 5. Format for Discord
        │       message = format_for_discord(items)
        │
        ├─► 6. Send response
        │       await interaction.followup.send(message)
        │
        └─► 7. Handle errors
                try/except with logging
```

### Example: ScheduleCommand - `/schedule today`

**File:** `bot/commands/schedule.py`

```python
class ScheduleCommands(commands.GroupCog, name="schedule"):
    def __init__(self, bot):
        self.bot = bot
        self.auth = None      # Shared auth instance
        self.parser = FAPParser()

    async def _get_auth(self):
        """Get or create shared auth instance"""
        if self.auth is None:
            from dotenv import load_dotenv
            load_dotenv()

            self.auth = FAPAuth(
                username=os.getenv('FAP_USERNAME'),
                password=os.getenv('FAP_PASSWORD'),
                headless=os.getenv('HEADLESS', 'true').lower() == 'true'
            )
        return self.auth

    @app_commands.command(name="today", description="View today's schedule")
    async def schedule_today(self, interaction: discord.Interaction):
        # 1. Defer response (Discord requires this within 3 seconds)
        await interaction.response.defer(thinking=True)

        try:
            # 2. Get auth instance
            auth = await self._get_auth()

            # 3. Fetch schedule HTML
            html = await auth.fetch_schedule()

            # 4. Check if fetch succeeded
            if not html:
                await interaction.followup.send("❌ Failed to fetch schedule")
                return

            # 5. Parse HTML to ScheduleItem[]
            items = self.parser.parse_schedule(html)

            # 6. Filter for today
            today_items = self.parser.get_today_schedule(items)

            # 7. Format for Discord
            message = self.parser.format_for_discord(today_items, "Today's Schedule")

            # 8. Send response
            await interaction.followup.send(message)

        except Exception as e:
            logger.error(f"Error: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")
```

### Example: ExamCommand - `/exam schedule`

**File:** `bot/commands/exam.py`

```python
class ExamCommands(commands.GroupCog, name="exam"):
    def __init__(self, bot):
        self.bot = bot
        self.auth = None
        self.parser = ExamParser()

    async def _get_auth(self):
        """Get or create shared auth instance"""
        if self.auth is None:
            from dotenv import load_dotenv
            load_dotenv()

            self.auth = FAPAuth(
                username=os.getenv('FAP_USERNAME'),
                password=os.getenv('FAP_PASSWORD'),
                headless=os.getenv('HEADLESS', 'true').lower() == 'true'
            )
        return self.auth

    @app_commands.command(name="schedule", description="View exam schedule")
    async def exam_schedule(self, interaction: discord.Interaction):
        # 1. Defer response
        await interaction.response.defer(thinking=True)

        try:
            # 2. Get auth instance
            auth = await self._get_auth()

            # 3. Fetch exam HTML
            html = await auth.fetch_exam_schedule()

            # 4. Check if fetch succeeded
            if not html:
                await interaction.followup.send("❌ Failed to fetch exam schedule")
                return

            # 5. Parse HTML to ExamItem[]
            exams = self.parser.parse_exam_schedule(html)

            # 6. Check if exams found
            if not exams:
                await interaction.followup.send("No exams found")
                return

            # 7. Format for Discord
            lines = [f"📚 **Exam Schedule**\n"]
            lines.append(f"Found {len(exams)} exam(s)\n")
            for exam in exams:
                lines.append(f"**{exam.no}. {exam.subject_code} - {exam.subject_name}**")
                lines.append(f"📅 {exam.date} | 🕐 {exam.time}")
                lines.append(f"📍 Room {exam.room} | 📝 {exam.exam_type}")
                lines.append("")
            message = "\n".join(lines)

            # 8. Handle long messages (Discord limit: 2000 chars)
            if len(message) > 1900:
                chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(message)

        except Exception as e:
            logger.error(f"Error: {e}")
            await interaction.followup.send(f"Error: {str(e)}")
```

---

## 5. Parser Logic

### File: `scraper/parser.py` - FAPParser (Schedule)

```python
class FAPParser:
    def parse_schedule(self, html: str) -> List[ScheduleItem]:
        """
        Parse HTML schedule table to ScheduleItem list

        HTML Structure:
        <table>
          <tr><td>COM101</td><td>Intro to Computing</td>...</tr>
          <tr><td>DBI202</td><td>Database</td>...</tr>
        </table>
        """
        # 1. Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # 2. Find the schedule table
        table = soup.find('table', {'id': 'ctl00_mainContent_grvSchedule'})

        # 3. Iterate through rows
        items = []
        for row in table.find_all('tr')[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) >= 8:
                # 4. Extract data from columns
                item = ScheduleItem(
                    subject_code=cols[0].text.strip(),
                    subject_name=cols[1].text.strip(),
                    room=cols[2].text.strip(),
                    day=cols[3].text.strip(),
                    date=cols[4].text.strip(),
                    slot=int(cols[5].text.strip()),
                    start_time=cols[6].text.strip(),
                    end_time=cols[7].text.strip(),
                    status=cols[8].text.strip() if len(cols) > 8 else ""
                )
                items.append(item)

        # 5. Return list
        return items

    def get_today_schedule(self, items: List[ScheduleItem]) -> List[ScheduleItem]:
        """Filter items for today's date"""
        today = datetime.now().strftime('%d/%m/%Y')
        return [item for item in items if item.date == today]

    def format_for_discord(self, items: List[ScheduleItem], title: str) -> str:
        """Format items for Discord message"""
        lines = [f"📅 **{title}**\n"]
        for item in items:
            lines.append(f"**{item.subject_code}** - {item.subject_name}")
            lines.append(f"📍 {item.room} | 🕐 {item.start_time}-{item.end_time}")
            lines.append(f"📆 {item.day} {item.date} | Slot {item.slot}")
            lines.append("")
        return "\n".join(lines)
```

### File: `scraper/exam_parser.py` - ExamParser (Exam)

```python
class ExamParser:
    def parse_exam_schedule(self, html: str) -> List[ExamItem]:
        """
        Parse HTML exam table to ExamItem list

        HTML Structure:
        <table>
          <tr><th>No</th><th>SubjectCode</th>...</tr>
          <tr><td>1</td><td>DBI202</td>...</tr>
        </table>
        """
        # 1. Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # 2. Find table (may have different structure)
        table = soup.find('table')

        # 3. Iterate rows
        exams = []
        for row in table.find_all('tr')[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) >= 8:
                # 4. Extract data
                exam = ExamItem(
                    no=int(cols[0].text.strip()),
                    subject_code=cols[1].text.strip(),
                    subject_name=cols[2].text.strip(),
                    date=cols[3].text.strip(),
                    room=cols[4].text.strip(),
                    time=cols[5].text.strip(),
                    exam_form=cols[6].text.strip(),
                    exam_type=cols[7].text.strip()
                )
                exams.append(exam)

        return exams

    def get_upcoming_exams(self, exams: List[ExamItem], days: int = 7) -> List[ExamItem]:
        """Filter exams within next N days"""
        today = datetime.now().strftime('%d/%m/%Y')
        cutoff_date = datetime.now() + timedelta(days=days)

        upcoming = []
        for exam in exams:
            exam_date = datetime.strptime(exam.date, '%d/%m/%Y')
            if today <= exam_date <= cutoff_date:
                upcoming.append(exam)

        return upcoming
```

---

## 6. Concurrency & Locking

### Problem Solved

```
Timeline without lock:
├─ User A: /schedule today → launches Chrome
├─ User B: /exam schedule → launches Chrome → KILLS A's Chrome!
├─ User A: "Target closed" error
└─ User B: "Target closed" error

Timeline with lock:
├─ User A: /schedule today → acquires lock → launches Chrome
├─ User B: /exam schedule → waits for lock... (A's Chrome safe)
├─ User A: fetch done → releases lock
└─ User B: acquires lock → launches Chrome → fetch done → releases lock
```

### Implementation

```python
# Global lock in auth.py
_auth_lock = asyncio.Lock()

async def fetch_schedule(self):
    async with _auth_lock:  # Only one Chrome operation at a time
        html = await self._auth.fetch_schedule()
        return html

async def fetch_exam_schedule(self):
    async with _auth_lock:  # Waits if fetch_schedule() is running
        html = await self._auth.fetch_exam_schedule()
        return html
```

### Refresh Coordination

```python
# Flag instead of lock for refresh (to avoid blocking)
self._refreshing = False

async def _refresh_session_once(self):
    if self._refreshing:
        # Another command is refreshing, wait for it
        while self._refreshing:
            await asyncio.sleep(0.5)
        return True

    self._refreshing = True
    try:
        success = await self._validator.refresh_session()
        return success
    finally:
        self._refreshing = False
```

---

## 7. Hướng dẫn thêm Feature mới

### Bước 1: Xác định yêu cầu

```
Ví dụ: Thêm lệnh /grade để xem điểm
```

### Bước 2: Tạo Parser

**File:** `scraper/grade_parser.py`

```python
from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup

@dataclass
class GradeItem:
    subject_code: str
    subject_name: str
    mid_term: float
    final: float
    total: float
    status: str

class GradeParser:
    def parse_grades(self, html: str) -> List[GradeItem]:
        """Parse HTML grade table"""
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')

        grades = []
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            grade = GradeItem(
                subject_code=cols[0].text.strip(),
                subject_name=cols[1].text.strip(),
                mid_term=float(cols[2].text.strip()),
                final=float(cols[3].text.strip()),
                total=float(cols[4].text.strip()),
                status=cols[5].text.strip()
            )
            grades.append(grade)

        return grades

    def get_gpa(self, grades: List[GradeItem]) -> float:
        """Calculate GPA"""
        total = sum(g.total for g in grades)
        return total / len(grades) if grades else 0.0
```

### Bước 3: Thêm fetch method vào FAPAutoLogin

**File:** `scraper/auto_login_feid.py`

```python
async def fetch_grades(self) -> str:
    """Fetch grades HTML using saved cookies"""
    GRADE_URL = "https://fap.fpt.edu.vn/Grade/StudentGrade.aspx"

    # 1. Check cookies
    if not Path(self.COOKIES_FILE).exists():
        print("[!] No cookies found")
        return None

    # 2. Load cookies
    with open(self.COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    # 3. Launch browser
    self._playwright = await async_playwright().start()
    self._browser = await self._playwright.chromium.launch(
        headless=self.headless,
        args=['--disable-blink-features=AutomationControlled']
    )
    self._page = await self._browser.new_page()

    # 4. Add cookies
    await self._page.context.add_cookies(cookies)

    # 5. Navigate to grade page
    await self._page.goto(GRADE_URL, timeout=60000)
    await asyncio.sleep(5)

    # 6. Check if logged in
    current_url = self._page.url
    if 'Login' in current_url:
        await self._browser.close()
        await self._playwright.stop()
        return None

    # 7. Get content
    content = await self._page.content()

    # 8. Cleanup
    await self._browser.close()
    await self._playwright.stop()

    return content
```

### Bước 4: Thêm method vào FAPAuth

**File:** `scraper/auth.py`

```python
async def fetch_grades(self) -> Optional[str]:
    """Fetch grades with auto-refresh on failure"""
    async with _auth_lock:
        await self._ensure_auth()

        # Try fetch
        html = await self._auth.fetch_grades()

        # Refresh if needed
        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                html = await self._auth.fetch_grades()

        return html
```

### Bước 5: Tạo Command Cog

**File:** `bot/commands/grade.py`

```python
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scraper.auth import FAPAuth
from scraper.grade_parser import GradeParser

class GradeCommands(commands.GroupCog, name="grade"):
    """Grade viewing commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth: Optional[FAPAuth] = None
        self.parser = GradeParser()

    async def cog_unload(self):
        if self.auth:
            await self.auth.close()

    async def _get_auth(self) -> FAPAuth:
        if self.auth is None:
            from dotenv import load_dotenv
            import os
            load_dotenv()

            self.auth = FAPAuth(
                username=os.getenv('FAP_USERNAME'),
                password=os.getenv('FAP_PASSWORD'),
                headless=os.getenv('HEADLESS', 'true').lower() == 'true'
            )
        return self.auth

    @app_commands.command(name="view", description="View grades")
    async def grade_view(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        try:
            auth = await self._get_auth()
            html = await auth.fetch_grades()

            if not html:
                await interaction.followup.send("❌ Failed to fetch grades")
                return

            grades = self.parser.parse_grades(html)
            gpa = self.parser.get_gpa(grades)

            # Format
            lines = [f"📊 **Grades**\n"]
            lines.append(f"GPA: {gpa:.2f}\n")
            for grade in grades:
                lines.append(f"**{grade.subject_code}** - {grade.subject_name}")
                lines.append(f"Mid: {grade.mid_term} | Final: {grade.final} | Total: {grade.total}")
                lines.append("")

            message = "\n".join(lines)
            await interaction.followup.send(message)

        except Exception as e:
            logging.error(f"Error: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(GradeCommands(bot))
    logging.info("Grade commands loaded")
```

### Bước 6: Register cog trong main.py

**File:** `bot/bot.py`

```python
async def setup_hook(self):
    # ... existing cogs ...

    # Add grade cog
    from bot.commands.grade import GradeCommands
    await self.add_cog(GradeCommands(self))
```

---

## 8. URLs & Endpoints

| Purpose | URL | Method |
|---------|-----|--------|
| Login | `https://fap.fpt.edu.vn/Default.aspx` | POST (auto-login) |
| Schedule | `https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx` | GET |
| Exam | `https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx` | GET |
| Grade (future) | `https://fap.fpt.edu.vn/Grade/StudentGrade.aspx` | GET |
| Attendance (future) | `https://fap.fpt.edu.vn/Report/Attendance.aspx` | GET |

---

## 9. Environment Variables

```bash
# Required
DISCORD_TOKEN=your_bot_token
FAP_USERNAME=your_feid@fe.edu.vn
FAP_PASSWORD=your_password

# Optional
HEADLESS=true                    # Run browser headless (default: true)
USER_AGENT=Mozilla/5.0...        # Custom user agent
```

---

## 10. Common Patterns

### Pattern 1: Command with filter

```python
@app_commands.command(name="week", description="View weekly schedule")
@app_commands.describe(week="Week number (1-52)")
async def schedule_week(self, interaction, week: int = None):
    await interaction.response.defer()

    auth = await self._get_auth()
    html = await auth.fetch_schedule(week=week)  # Pass parameter

    items = self.parser.parse_schedule(html)
    message = format_items(items)
    await interaction.followup.send(message)
```

### Pattern 2: Error handling

```python
try:
    auth = await self._get_auth()
    html = await auth.fetch_xxx()

    if not html:
        await interaction.followup.send("❌ Failed to fetch")
        return

    data = self.parser.parse(html)
    # ... process data

except Exception as e:
    logger.error(f"Error: {e}")
    await interaction.followup.send(f"❌ Error: {str(e)}")
```

### Pattern 3: Long message handling

```python
message = format_data(data)

if len(message) > 1900:  # Discord limit is 2000
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)
else:
    await interaction.followup.send(message)
```

---

**Document Version:** 1.0
**Last Updated:** 2026-03-09
**Maintained by:** Development Team
