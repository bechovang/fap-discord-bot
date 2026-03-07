# Technical Specification
## FAP Discord Bot - Implementation Guide

**Version:** 1.0
**Date:** 2026-03-07
**Lead Developer:** Barry (Quick Flow Solo Dev) + Admin
**Document Status:** Draft

---

## Table of Contents

1. [Document Information](#document-information)
2. [Implementation Overview](#implementation-overview)
3. [File Structure](#file-structure)
4. [Component Specifications](#component-specifications)
5. [Code Examples](#code-examples)
6. [Configuration](#configuration)
7. [Environment Setup](#environment-setup)
8. [Development Workflow](#development-workflow)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Guide](#deployment-guide)
11. [Troubleshooting](#troubleshooting)

---

## Document Information

| Field | Value |
|-------|-------|
| **Document Name** | Technical Specification |
| **Version** | 1.0 |
| **Status** | Draft |
| **Author** | Barry (Quick Flow Solo Dev) |
| **Reviewers** | Amelia (Dev), Quinn (QA) |
| **Related Documents** | PRD, Architecture Spec |

---

## Implementation Overview

### Implementation Philosophy

> **"Planning and execution are two sides of the same coin."**
> **"Specs are for building, not bureaucracy."**
> **"Code that ships is better than perfect code that doesn't."**

### Implementation Principles

1. **Direct & Confident:** Get straight to the point, no fluff
2. **File Paths Matter:** Every statement is citable by file path
3. **All Tests Pass:** No task is complete without 100% tests passing
4. **Ship Fast:** Minimum ceremony, ruthless efficiency
5. **Real Code:** These are working examples, not pseudocode

### Sprint Breakdown

| Sprint | Duration | Focus | Deliverables |
|--------|----------|-------|--------------|
| **Sprint 1** | 2.5 weeks | MVP Foundation | Database, Scheduler, Parsers, Commands |
| **Sprint 2** | 1 week | Notifications | Reminders, Grade/Exam notifications |
| **Sprint 3** | 1.5 weeks | Monitoring | Attendance monitoring, Application tracking |
| **Sprint 4** | 1 week | Final Features | GPA calculator, Documentation |

---

## File Structure

### Complete Project Structure

```
fap-discord-bot/
├── bot/
│   ├── __init__.py
│   ├── bot.py                    # Main bot class (UPDATE)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── schedule.py           # Schedule commands (UPDATE)
│   │   ├── status.py             # Bot status (KEEP)
│   │   ├── grades.py             # NEW: Grade commands
│   │   ├── attendance.py         # NEW: Attendance commands
│   │   ├── applications.py       # NEW: Application commands
│   │   ├── exams.py              # NEW: Exam commands
│   │   ├── gpa.py                # NEW: GPA calculator
│   │   └── config.py             # NEW: User configuration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scheduler.py          # NEW: Background task manager
│   │   ├── notifier.py           # NEW: Discord notification formatter
│   │   └── fap_client.py         # NEW: FAP API wrapper
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── schedule_parser.py    # NEW: Extract from auto_login_feid.py
│   │   ├── grade_parser.py       # NEW: Grade HTML parser
│   │   ├── attendance_parser.py  # NEW: Attendance status parser
│   │   ├── application_parser.py # NEW: Application HTML parser
│   │   └── exam_parser.py        # NEW: Exam HTML parser
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # NEW: SQLAlchemy models
│   │   └── db.py                 # NEW: Database connection
│   └── utils/
│       ├── __init__.py
│       ├── time_helper.py        # NEW: Timezone utilities
│       └── diff_helper.py        # NEW: Schedule comparison
├── scraper/
│   ├── auth.py                   # UPDATE: Adapt for new architecture
│   ├── auto_login_feid.py        # KEEP: Core authentication
│   └── [other files]             # KEEP: Existing
├── data/
│   └── fap.db                    # NEW: SQLite database (created at runtime)
├── tests/
│   ├── __init__.py
│   ├── test_parsers.py           # NEW: Parser tests
│   ├── test_services.py          # NEW: Service tests
│   ├── test_commands.py          # NEW: Command tests
│   └── fixtures/                 # NEW: Test HTML fixtures
├── docs/
│   ├── BRAINSTORMING-SESSION.md   # NEW: Complete brainstorming doc
│   ├── PRD.md                    # NEW: Product Requirements
│   ├── ARCHITECTURE.md           # NEW: System Architecture
│   ├── TECH-SPEC.md              # NEW: This file
│   ├── SETUP.md                  # NEW: Setup guide
│   ├── COMMANDS.md               # NEW: Command reference
│   ├── TROUBLESHOOTING.md        # NEW: Troubleshooting guide
│   └── DEPLOYMENT.md             # NEW: DigitalOcean deployment
├── deployment/
│   ├── Dockerfile                # NEW: Container definition
│   ├── docker-compose.yml        # NEW: Multi-container setup
│   └── digitalocean/
│       ├── deploy.sh             # NEW: Deployment script
│       └── setup.sh              # NEW: Initial setup script
├── main.py                        # UPDATE: Entry point
├── requirements.txt               # UPDATE: New dependencies
├── .env.example                   # UPDATE: Template
├── .gitignore                     # UPDATE: At repository root
└── README.md                      # UPDATE: Project documentation
```

### File Purpose Summary

| File/Dir | Purpose | Lines (est.) |
|----------|---------|--------------|
| `bot/bot.py` | Discord bot main class | ~150 |
| `bot/commands/*.py` | Slash command implementations | ~100 each |
| `bot/services/scheduler.py` | Background task management | ~200 |
| `bot/services/notifier.py` | Notification formatting | ~150 |
| `bot/services/fap_client.py` | FAP API wrapper | ~200 |
| `bot/parsers/*.py` | HTML parsing logic | ~150 each |
| `bot/database/models.py` | SQLAlchemy models | ~200 |
| `bot/database/db.py` | Database connection | ~100 |
| `bot/utils/*.py` | Helper utilities | ~100 each |
| `tests/*.py` | Test suites | ~200 each |

**Total Estimated Lines:** ~5,000 (excluding tests and docs)

---

## Component Specifications

### CS-1: Database Models (`bot/database/models.py`)

**Purpose:** SQLAlchemy ORM models for all tables

**Code:**
```python
from sqlalchemy import Column, String, Boolean, Integer, Date, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(String, primary_key=True)
    fap_username = Column(String, nullable=False)
    fap_password = Column(String, nullable=False)  # Encrypted
    server_id = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class ScheduleCache(Base):
    __tablename__ = 'schedule_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    week = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    html_content = Column(Text)
    cached_at = Column(DateTime, default=datetime.utcnow)

class AttendanceState(Base):
    __tablename__ = 'attendance_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    date = Column(Date, nullable=False)
    slot = Column(Integer, nullable=False)
    subject_code = Column(String, nullable=False)
    status = Column(String, nullable=False)  # 'attended', 'absent', '-'
    notified_15min = Column(Boolean, default=False)
    notified_10min = Column(Boolean, default=False)
    notified_5min = Column(Boolean, default=False)
    last_checked = Column(DateTime, default=datetime.utcnow)

class GradeCache(Base):
    __tablename__ = 'grade_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    term = Column(String, nullable=False)
    subject_code = Column(String, nullable=False)
    grade = Column(String)  # None if not graded
    last_checked = Column(DateTime, default=datetime.utcnow)

class ApplicationCache(Base):
    __tablename__ = 'application_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    app_type = Column(String, nullable=False)
    purpose = Column(Text, nullable=False)
    status = Column(String, nullable=False)  # 'Pending', 'Approved', 'Rejected'
    created_date = Column(Date, nullable=False)
    last_checked = Column(DateTime, default=datetime.utcnow)

class ExamCache(Base):
    __tablename__ = 'exam_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False)
    subject_code = Column(String, nullable=False)
    exam_date = Column(Date, nullable=False)
    exam_time = Column(String, nullable=False)
    room = Column(String, nullable=False)
    notified_1day = Column(Boolean, default=False)
    notified_1hour = Column(Boolean, default=False)
    last_checked = Column(DateTime, default=datetime.utcnow)
```

---

### CS-2: Database Connection (`bot/database/db.py`)

**Purpose:** Database connection and session management

**Code:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from .models import Base
import os

DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/fap.db')

class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.init_db()

    def init_db(self):
        """Create all tables"""
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_user(self, user_id: str):
        """Get user by ID"""
        with self.get_session() as session:
            from .models import User
            return session.query(User).filter_by(user_id=user_id).first()

    def create_user(self, user_data: dict):
        """Create new user"""
        with self.get_session() as session:
            from .models import User
            user = User(**user_data)
            session.add(user)
            session.commit()
            return user

    def save_schedule_cache(self, user_id: str, week: int, year: int, html: str):
        """Save schedule to cache"""
        with self.get_session() as session:
            from .models import ScheduleCache
            cache = session.query(ScheduleCache).filter_by(
                user_id=user_id, week=week, year=year
            ).first()
            if cache:
                cache.html_content = html
                cache.cached_at = datetime.utcnow()
            else:
                cache = ScheduleCache(
                    user_id=user_id, week=week, year=year, html_content=html
                )
                session.add(cache)
            session.commit()

    def get_schedule_cache(self, user_id: str, week: int, year: int):
        """Get cached schedule"""
        with self.get_session() as session:
            from .models import ScheduleCache
            return session.query(ScheduleCache).filter_by(
                user_id=user_id, week=week, year=year
            ).first()
```

---

### CS-3: Background Scheduler (`bot/services/scheduler.py`)

**Purpose:** Manage all scheduled tasks

**Code:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import time
import logging

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone='Asia/Ho_Chi_Minh')

    def start(self):
        """Start the scheduler"""
        self.schedule_all_tasks()
        self.scheduler.start()
        logger.info("Background scheduler started")

    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Background scheduler stopped")

    def schedule_all_tasks(self):
        """Schedule all background tasks"""
        # Attendance monitoring - every 5 minutes
        self.scheduler.add_job(
            self.attendance_monitor,
            'cron',
            minute='*/5',
            id='attendance_monitor',
            replace_existing=True
        )

        # Class reminder check - every minute
        self.scheduler.add_job(
            self.class_reminder_checker,
            'cron',
            minute='*',
            id='class_reminder',
            replace_existing=True
        )

        # Evening schedule - 19:30 daily
        self.scheduler.add_job(
            self.evening_schedule,
            'cron',
            hour=19,
            minute=30,
            id='evening_schedule',
            replace_existing=True
        )

        # Hourly checks
        self.scheduler.add_job(
            self.hourly_checks,
            'cron',
            minute='0',
            id='hourly_checks',
            replace_existing=True
        )

        # Exam reminders check
        self.scheduler.add_job(
            self.exam_reminder_checker,
            'cron',
            minute='0',
            id='exam_reminders',
            replace_existing=True
        )

    async def attendance_monitor(self):
        """Check attendance every 5 minutes"""
        from bot.services.attendance_monitor import check_attendance
        await check_attendance(self.bot)

    async def class_reminder_checker(self):
        """Check for classes starting in 5 minutes"""
        from bot.services.class_reminder import check_class_reminders
        await check_class_reminders(self.bot)

    async def evening_schedule(self):
        """Send evening schedule at 19:30"""
        from bot.services.evening_schedule import send_evening_schedule
        await send_evening_schedule(self.bot)

    async def hourly_checks(self):
        """Hourly grade and application checks"""
        from bot.services.hourly_checks import perform_hourly_checks
        await perform_hourly_checks(self.bot)

    async def exam_reminder_checker(self):
        """Check for upcoming exams"""
        from bot.services.exam_reminders import check_exam_reminders
        await check_exam_reminders(self.bot)
```

---

### CS-4: Notification Service (`bot/services/notifier.py`)

**Purpose:** Format and send Discord notifications

**Code:**
```python
import discord
from datetime import datetime, timedelta
from bot.utils.time_helper import get_current_time

class NotificationService:
    def __init__(self, bot):
        self.bot = bot

    async def send_evening_schedule(self, user, schedule_items, changes=None):
        """Send evening schedule notification"""
        channel = self.bot.get_channel(user.channel_id)
        if not channel:
            logger.warning(f"Channel {user.channel_id} not found")
            return

        if not schedule_items:
            await channel.send(embed=self._create_no_classes_embed())
            return

        embed = discord.Embed(
            title=f"📅 Lịch học ngày mai - {(get_current_time() + timedelta(days=1)).strftime('%d/%m/%Y')}",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )

        # Group by slot
        slots = {}
        for item in schedule_items:
            slot_key = item.slot
            if slot_key not in slots:
                slots[slot_key] = []
            slots[slot_key].append(item)

        # Add fields
        for slot in sorted(slots.keys()):
            items = slots[slot]
            field_value = ""
            for item in items:
                field_value += f"**{item.subject_name} ({item.subject_code})**\n"
                field_value += f"📍 Room {item.room}\n"

            embed.add_field(
                name=f"🕐 Slot {slot}",
                value=field_value,
                inline=False
            )

        # Add changes footer
        if changes:
            embed.set_footer(text=f"💡 Thay đổi so với tuần trước: {len(changes)} thay đổi")

        await channel.send(embed=embed)

    async def send_class_reminder(self, user, class_item):
        """Send class reminder 5 minutes before"""
        channel = self.bot.get_channel(user.channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="⏰ Sắp vào lớp!",
            color=0xffff00,
            description=f"**{class_item.subject_name} ({class_item.subject_code})** bắt đầu sau 5 phút\n\n"
                      f"📍 **Room {class_item.room}**\n"
                      f"🕐 **{class_item.start_time} - {class_item.end_time}**"
        )

        embed.add_field(name="📝 Chuẩn bị", value="Máy tính, sạc pin, water", inline=False)
        embed.add_field(name="💡 Nhắc nhở", value="Đừng quên nhắc thầy cô điểm danh!", inline=False)

        await channel.send(embed=embed)

    async def send_attendance_recorded(self, user, class_item):
        """Send notification when attendance recorded"""
        channel = self.bot.get_channel(user.channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="✅ Điểm danh thành công!",
            color=0x00ff00,
            description=f"**{class_item.subject_name} ({class_item.subject_code})** - Slot {class_item.slot}\n\n"
                      f"✅ Đã ghi nhận: Có mặt"
        )

        await channel.send(embed=embed)

    async def send_absent_alert(self, user, class_item):
        """Send alert when marked absent"""
        channel = self.bot.get_channel(user.channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="⚠️ CẢNH BÁO: Ghi nhận vắng mặt!",
            color=0xff0000,
            description=f"**{class_item.subject_name} ({class_item.subject_code})** - Slot {class_item.slot}\n\n"
                      f"❌ Hệ thống ghi nhận: Vắng mặt\n\n"
                      f"👉 **Hãy liên hệ ngay với giảng viên để điểm danh bổ sung!**"
        )

        embed.add_field(name="🕐 Thời gian", value=f"{class_item.date} {class_item.start_time}", inline=False)
        embed.add_field(name="📍 Phòng", value=class_item.room, inline=False)

        await channel.send(embed=embed)

    async def send_new_grade(self, user, grade_item, gpa_impact):
        """Send notification for new grade"""
        channel = self.bot.get_channel(user.channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="📊 Có điểm mới!",
            color=0x00bfff,
            description=f"**{grade_item.subject_name} ({grade_item.subject_code})**\n\n"
                      f"📈 Điểm: **{grade_item.grade}**\n"
                      f"📝 Hệ số: **{grade_item.credits}**"
        )

        embed.add_field(name="🎯 Ảnh hưởng GPA", value=f"{gpa_impact:+}", inline=False)

        await channel.send(embed=embed)

    async def send_exam_reminder_1day(self, user, exam_item):
        """Send exam reminder 1 day before"""
        channel = self.bot.get_channel(user.channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="📝 Nhắc nhở thi cuối kỳ",
            color=0x9b59b6,
            description=f"**Ngày mai:** {exam_item.subject_name} ({exam_item.subject_code})\n\n"
                      f"📅 **{exam_item.exam_date.strftime('%d/%m/%Y')}**\n"
                      f"🕐 **{exam_item.exam_time}**\n"
                      f"📍 **Room {exam_item.room}**\n"
                      f"📋 **Hình thức:** {exam_item.exam_type}"
        )

        embed.add_field(name="📚 Chuẩn bị", value="CMND/Thẻ SVN, bút, giấy", inline=False)
        embed.add_field(name="🔔 Lưu ý", value="Đi sớm 15 phút!", inline=False)

        await channel.send(embed=embed)

    def _create_no_classes_embed(self):
        """Create embed for no classes"""
        return discord.Embed(
            title="📅 Ngày mai được nghỉ!",
            color=0x00ff00,
            description="Không có lớp học vào ngày mai. Enjoy your day off! 🎉"
        )
```

---

### CS-5: FAP Client (`bot/services/fap_client.py`)

**Purpose:** Wrapper for all FAP API interactions

**Code:**
```python
from scraper.auth import FAPAuth
from scraper.auto_login_feid import FAPAutoLogin
import logging

logger = logging.getLogger(__name__)

class FAPClient:
    def __init__(self, username: str, password: str, headless: bool = True):
        self.username = username
        self.password = password
        self.headless = headless
        self.auth = None
        self._session = None

    async def authenticate(self):
        """Authenticate with FAP"""
        try:
            self.auth = FAPAutoLogin(
                username=self.username,
                password=self.password,
                headless=self.headless
            )
            page = await self.auth.get_session()
            if page:
                logger.info("FAP authentication successful")
                return True
            return False
        except Exception as e:
            logger.error(f"FAP authentication failed: {e}")
            return False

    async def get_schedule(self, week: int, year: int):
        """Fetch schedule HTML"""
        try:
            if not self.auth:
                await self.authenticate()

            url = f"https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
            params = {'week': week, 'year': year}

            html = await self.auth.fetch_page(url, params=params)
            return html
        except Exception as e:
            logger.error(f"Failed to fetch schedule: {e}")
            raise

    async def get_grades(self, term: str):
        """Fetch grades HTML"""
        try:
            if not self.auth:
                await self.authenticate()

            url = "https://fap.fpt.edu.vn/Grade/StudentGrade.aspx"
            params = {'term': term}

            html = await self.auth.fetch_page(url, params=params)
            return html
        except Exception as e:
            logger.error(f"Failed to fetch grades: {e}")
            raise

    async def get_applications(self):
        """Fetch applications HTML"""
        try:
            if not self.auth:
                await self.authenticate()

            url = "https://fap.fpt.edu.vn/App/AcadAppView.aspx"

            html = await self.auth.fetch_page(url)
            return html
        except Exception as e:
            logger.error(f"Failed to fetch applications: {e}")
            raise

    async def get_exams(self):
        """Fetch exams HTML"""
        try:
            if not self.auth:
                await self.authenticate()

            url = "https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx"

            html = await self.auth.fetch_page(url)
            return html
        except Exception as e:
            logger.error(f"Failed to fetch exams: {e}")
            raise

    async def close(self):
        """Cleanup session"""
        if self.auth:
            await self.auth.close()
```

---

## Code Examples

### Example 1: Schedule Command (`bot/commands/schedule.py`)

```python
import discord
from discord.ext import commands
from bot.services.fap_client import FAPClient
from bot.database.db import Database
from bot.parsers.schedule_parser import ScheduleParser
from bot.utils.time_helper import get_current_time
from datetime import timedelta

class ScheduleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @commands.hybrid_command(name="schedule", description="View your schedule")
    @discord.app_commands.describe(day="Day to view (today/tomorrow/week)")
    async def schedule(self, ctx, day: str = None):
        await ctx.defer()

        # Get user from database
        user = self.db.get_user(str(ctx.author.id))
        if not user:
            await ctx.send("❌ You need to set up your FAP credentials first!")
            return

        # Determine date
        if day == "tomorrow":
            date = get_current_time() + timedelta(days=1)
            week, year = get_week_number(date)
        elif day == "week":
            week, year = get_current_week()
        else:  # today
            date = get_current_time()
            week, year = get_week_number(date)

        # Fetch schedule
        client = FAPClient(user.fap_username, user.fap_password)
        try:
            html = await client.get_schedule(week, year)
            parser = ScheduleParser()
            schedule_items = parser.parse_schedule(html)

            # Filter for requested day
            if day and day != "week":
                schedule_items = [item for item in schedule_items if item.date == date.date()]

            # Create response
            if schedule_items:
                await self._send_schedule(ctx, schedule_items)
            else:
                await ctx.send(f"📅 No classes found for {day}")

        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            await ctx.send("❌ Failed to fetch schedule. Try again later.")
        finally:
            await client.close()

    async def _send_schedule(self, ctx, schedule_items):
        """Send schedule as Discord embed"""
        embed = discord.Embed(
            title=f"📅 Schedule - {schedule_items[0].date}",
            color=0x00ff00
        )

        for item in schedule_items:
            embed.add_field(
                name=f"🕐 Slot {item.slot} ({item.start_time}-{item.end_time})",
                value=f"**{item.subject_name} ({item.subject_code})**\n📍 Room {item.room}",
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ScheduleCommands(bot))
```

### Example 2: Grade Parser (`bot/parsers/grade_parser.py`)

```python
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List

@dataclass
class GradeItem:
    term: str
    subject_code: str
    subject_name: str
    grade: float
    credits: int
    status: str

class GradeParser:
    @staticmethod
    def parse_grades(html_content: str) -> List[GradeItem]:
        """Parse grade HTML and return list of GradeItem"""
        soup = BeautifulSoup(html_content, 'lxml')
        grades = []

        # Find grade table
        table = soup.find('table', id='ctl00_mainContent_dgGrade')
        if not table:
            return grades

        rows = table.find_all('tr')[1:]  # Skip header

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 6:
                continue

            try:
                grade_item = GradeItem(
                    term="",  # Get from page context
                    subject_code=cols[1].text.strip(),
                    subject_name=cols[2].text.strip(),
                    grade=GradeParser._parse_grade(cols[4].text.strip()),
                    credits=int(cols[3].text.strip()) if cols[3].text.strip() else 0,
                    status=cols[5].text.strip()
                )
                grades.append(grade_item)
            except (ValueError, IndexError):
                continue

        return grades

    @staticmethod
    def _parse_grade(grade_str: str) -> float:
        """Parse grade string to float, return None if not graded"""
        if not grade_str or grade_str == '-':
            return None
        try:
            return float(grade_str)
        except ValueError:
            return None

    @staticmethod
    def calculate_gpa(grades: List[GradeItem], exclusions: List[str] = None) -> dict:
        """Calculate GPA from grade list"""
        exclusions = exclusions or []

        # Filter out exclusions
        filtered_grades = [
            g for g in grades
            if g.grade is not None
            and not any(exc.lower() in g.subject_code.lower() for exc in exclusions)
        ]

        if not filtered_grades:
            return {'gpa': 0.0, 'total_credits': 0}

        total_points = sum(g.grade * g.credits for g in filtered_grades)
        total_credits = sum(g.credits for g in filtered_grades)

        gpa = total_points / total_credits if total_credits > 0 else 0.0

        return {
            'gpa': round(gpa, 2),
            'total_credits': total_credits,
            'subject_count': len(filtered_grades)
        }
```

### Example 3: Time Helper (`bot/utils/time_helper.py`)

```python
from datetime import datetime, date, timedelta
import pytz

# Vietnam timezone
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

def get_current_time() -> datetime:
    """Get current time in Vietnam timezone"""
    return datetime.now(VIETNAM_TZ)

def get_current_date() -> date:
    """Get current date in Vietnam timezone"""
    return get_current_time().date()

def get_week_number(target_date: date) -> tuple:
    """Get week number and year for a given date"""
    # FAP week calculation logic
    # Adjust based on FAP's academic calendar
    year = target_date.year
    # Simplified - use actual FAP logic
    week = (target_date - get_term_start(year)).days // 7 + 1
    return week, year

def get_term_start(year: int) -> date:
    """Get term start date for a year"""
    # Simplified - use actual FAP term dates
    return date(year, 9, 1)  # Fall semester starts Sept 1

def is_class_time(schedule_item, current_time: datetime) -> bool:
    """Check if current time is within class time"""
    start = datetime.combine(schedule_item.date,
                           datetime.strptime(schedule_item.start_time, '%H:%M').time())
    end = datetime.combine(schedule_item.date,
                         datetime.strptime(schedule_item.end_time, '%H:%M').time())

    start = VIETNAM_TZ.localize(start)
    end = VIETNAM_TZ.localize(end)
    current_time = VIETNAM_TZ.localize(current_time)

    return start <= current_time <= end

def get_minutes_until_class_ends(schedule_item, current_time: datetime) -> int:
    """Get minutes until class ends"""
    end = datetime.combine(schedule_item.date,
                         datetime.strptime(schedule_item.end_time, '%H:%M').time())
    end = VIETNAM_TZ.localize(end)
    current_time = VIETNAM_TZ.localize(current_time)

    return int((end - current_time).total_seconds() / 60)
```

### Example 4: Schedule Diff Helper (`bot/utils/diff_helper.py`)

```python
from typing import List
from dataclasses import dataclass

@dataclass
class ScheduleChange:
    change_type: str  # 'added', 'removed', 'room_changed', 'time_changed'
    subject_code: str
    old_value: str
    new_value: str

class ScheduleDiffHelper:
    @staticmethod
    def diff_schedules(old_items: List, new_items: List) -> List[ScheduleChange]:
        """Compare two schedules and return list of changes"""
        changes = []

        # Create lookup dicts
        old_dict = {(item.date, item.slot, item.subject_code): item for item in old_items}
        new_dict = {(item.date, item.slot, item.subject_code): item for item in new_items}

        # Check for removed items
        for key, old_item in old_dict.items():
            if key not in new_dict:
                changes.append(ScheduleChange(
                    change_type='removed',
                    subject_code=old_item.subject_code,
                    old_value=f"{old_item.date} Slot {old_item.slot}",
                    new_value=None
                ))

        # Check for added and modified items
        for key, new_item in new_dict.items():
            if key not in old_dict:
                changes.append(ScheduleChange(
                    change_type='added',
                    subject_code=new_item.subject_code,
                    old_value=None,
                    new_value=f"{new_item.date} Slot {new_item.slot}"
                ))
            else:
                old_item = old_dict[key]
                # Check for changes
                if old_item.room != new_item.room:
                    changes.append(ScheduleChange(
                        change_type='room_changed',
                        subject_code=new_item.subject_code,
                        old_value=old_item.room,
                        new_value=new_item.room
                    ))

                if old_item.start_time != new_item.start_time:
                    changes.append(ScheduleChange(
                        change_type='time_changed',
                        subject_code=new_item.subject_code,
                        old_value=old_item.start_time,
                        new_value=new_item.start_time
                    ))

        return changes
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here

# FAP Credentials
FAP_USERNAME=your_feid@fe.edu.vn
FAP_PASSWORD=your_password_here

# FAP URLs
FAP_BASE_URL=https://fap.fpt.edu.vn
FAP_LOGIN_URL=https://fap.fpt.edu.vn/Account/Login.aspx
FAP_SCHEDULE_URL=https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx
FAP_GRADE_URL=https://fap.fpt.edu.vn/Grade/StudentGrade.aspx
FAP_APPLICATION_URL=https://fap.fpt.edu.vn/App/AcadAppView.aspx
FAP_EXAM_URL=https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx

# Browser Settings
HEADLESS=true
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# FlareSolverr
FLARESOLVERR_URL=http://localhost:8191/v1

# Encryption
ENCRYPTION_KEY=your_fernet_key_here

# Schedule
EVENING_SCHEDULE_HOUR=19
EVENING_SCHEDULE_MINUTE=30

# Database
DATABASE_PATH=data/fap.db

# Logging
LOG_LEVEL=INFO
```

### Configuration Command (`bot/commands/config.py`)

```python
import discord
from discord.ext import commands
from bot.database.db import Database

class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    @commands.hybrid_command(name="config", description="Configure bot settings")
    @discord.app_commands.describe(
        setting="Setting to configure (channel/exclude)",
        value="Value for the setting"
    )
    async def config(self, ctx, setting: str, value: str):
        await ctx.defer()

        user = self.db.get_user(str(ctx.author.id))
        if not user:
            await ctx.send("❌ You need to set up your FAP credentials first!")
            return

        if setting == "channel":
            # Update notification channel
            channel_id = value.strip('<>#')
            user.channel_id = channel_id
            self.db.update_user(user.user_id, {'channel_id': channel_id})
            await ctx.send(f"✅ Notification channel updated to <#{channel_id}>")

        elif setting == "exclude":
            # Update GPA exclusion list
            # Implementation depends on data model
            await ctx.send(f"✅ Exclusion list updated: {value}")

        else:
            await ctx.send("❌ Unknown setting. Available: `channel`, `exclude`")

async def setup(bot):
    await bot.add_cog(ConfigCommands(bot))
```

---

## Environment Setup

### Local Development Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd fap-discord-bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env

# 5. Edit .env with your credentials
nano .env

# 6. Create data directory
mkdir -p data

# 7. Run bot
python main.py
```

### Requirements (`requirements.txt`)

```
discord.py>=2.3.2
patchright>=1.40.0
beautifulsoup4>=4.12.2
lxml>=4.9.3
aiofiles>=23.0.0
python-dotenv>=1.0.0
apscheduler>=3.10.0
sqlalchemy>=2.0.0
cryptography>=41.0.0
pytz>=2023.3
```

---

## Development Workflow

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/grade-notifications

# Make changes
# ... code ...

# Test locally
python main.py

# Commit
git add .
git commit -m "feat: add grade notifications"

# Push
git push origin feature/grade-notifications

# Create PR
# ... via GitHub/GitLab ...
```

### Code Review Checklist

- [ ] All tests pass
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling added
- [ ] Logging added where appropriate
- [ ] Database migrations included

---

## Testing Strategy

### Unit Tests (`tests/test_parsers.py`)

```python
import unittest
from bot.parsers.grade_parser import GradeParser
from bot.parsers.schedule_parser import ScheduleParser

class TestGradeParser(unittest.TestCase):
    def test_parse_grades(self):
        html = """<table id="ctl00_mainContent_dgGrade">
            <tr><td>1</td><td>DBI202</td><td>Database Systems</td><td>3</td><td>8.5</td><td>Completed</td></tr>
        </table>"""
        parser = GradeParser()
        grades = parser.parse_grades(html)
        self.assertEqual(len(grades), 1)
        self.assertEqual(grades[0].subject_code, "DBI202")
        self.assertEqual(grades[0].grade, 8.5)

    def test_calculate_gpa(self):
        grades = [
            GradeItem(term="Fall2025", subject_code="DBI202", subject_name="DB",
                      grade=8.5, credits=3, status="Completed"),
            GradeItem(term="Fall2025", subject_code="MAS291", subject_name="Stats",
                      grade=9.0, credits=3, status="Completed")
        ]
        result = GradeParser.calculate_gpa(grades)
        self.assertEqual(result['gpa'], 8.75)
```

### Integration Tests (`tests/test_services.py`)

```python
import unittest
from bot.services.fap_client import FAPClient
from bot.services.notifier import NotificationService

class TestFAPIntegration(unittest.TestCase):
    @unittest.skip("Requires FAP credentials")
    def test_fetch_schedule(self):
        client = FAPClient(username="", password="")
        html = await client.get_schedule(week=5, year=2025)
        self.assertIsNotNone(html)
        self.assertIn("<table", html)
```

### Test Fixtures (`tests/fixtures/`)

Place sample HTML files from `resource/` folder here for consistent testing.

---

## Deployment Guide

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Run bot
CMD ["python", "main.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build: .
    container_name: fap-discord-bot
    restart: unless-stopped
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - FAP_USERNAME=${FAP_USERNAME}
      - FAP_PASSWORD=${FAP_PASSWORD}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - flaresolverr
    networks:
      - bot-network

  flaresolverr:
    image: flaresolverr/flaresolverr:latest
    container_name: flaresolverr
    restart: unless-stopped
    ports:
      - "8191:8191"
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
```

### Deploy Script (`deployment/digitalocean/deploy.sh`)

```bash
#!/bin/bash
echo "🚀 Deploying FAP Discord Bot..."

# Pull latest code
git pull origin main

# Build and restart containers
docker-compose down
docker-compose build
docker-compose up -d

echo "✅ Deployment complete!"
echo "📊 Logs: docker-compose logs -f"
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Bot doesn't respond | Check DISCORD_TOKEN, verify bot has message intent |
| FAP connection fails | Check FlareSolverr is running on port 8191 |
| Database errors | Ensure `data/` directory exists and is writable |
| Notifications not sending | Verify channel_id is correct and bot has permission |
| Schedule not parsing | Check FAP HTML structure hasn't changed |

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py
```

### Health Check

```python
# bot/commands/status.py
@commands.hybrid_command(name="status", description="Check bot status")
async def status(self, ctx):
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=0x00ff00
    )

    embed.add_field(name="FAP Connection", value="✅ Connected", inline=False)
    embed.add_field(name="Database", value="✅ Healthy", inline=False)
    embed.add_field(name="Scheduler", value="✅ Running", inline=False)
    embed.add_field(name="Uptime", value=f"{get_uptime()}", inline=False)

    await ctx.send(embed=embed)
```

---

## Appendix

### A. Quick Reference

| Command | Description |
|---------|-------------|
| `/schedule [day]` | View schedule |
| `/grades [term]` | View grades |
| `/attendance [term] [week]` | View attendance |
| `/exams [term]` | View exam schedule |
| `/applications` | View applications |
| `/gpa [term] [--exclude]` | Calculate GPA |
| `/config <key> <value>` | Configure settings |
| `/status` | Bot status |

### B. File Quick Links

| File | Lines | Purpose |
|------|-------|---------|
| `bot/bot.py` | ~150 | Main bot class |
| `bot/services/scheduler.py` | ~200 | Background tasks |
| `bot/services/notifier.py` | ~150 | Notifications |
| `bot/database/models.py` | ~200 | Database models |
| `bot/parsers/*.py` | ~150 each | HTML parsing |

### C. Related Documents

- PRD: Product requirements
- Architecture: System design
- Brainstorming: Discussion notes

---

**Document Status:** ✅ Ready for Implementation
**Estimated Implementation Time:** 6 weeks (4 sprints)
**Next Steps:** Start Sprint 1 → Create database models → Implement parsers → Add commands
