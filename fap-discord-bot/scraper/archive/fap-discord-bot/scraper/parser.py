"""
FAP Schedule Parser
Generic HTML parser for FAP schedule pages
"""
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime, time
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScheduleItem:
    """Represents a single schedule item"""
    subject_code: str
    subject_name: str = ""
    room: str = ""
    day: str = ""
    date: str = ""
    slot: int = 0
    start_time: str = ""
    end_time: str = ""
    instructor: str = ""
    status: str = ""  # attended, absent, -
    attendance_color: str = ""
    notes: List[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'subject_code': self.subject_code,
            'subject_name': self.subject_name,
            'room': self.room,
            'day': self.day,
            'date': self.date,
            'slot': self.slot,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'instructor': self.instructor,
            'status': self.status
        }

    def __str__(self) -> str:
        """String representation for Discord"""
        status_emoji = {
            'attended': '✅',
            'absent': '❌',
            '-': '➖'
        }.get(self.status, '❓')

        return (
            f"{status_emoji} **{self.subject_code}**\n"
            f"📍 Room: {self.room}\n"
            f"📅 {self.day} {self.date}\n"
            f"🕐 {self.start_time} - {self.end_time}\n"
            f"📚 Status: {self.status or 'N/A'}"
        )


class FAPParser:
    """
    Generic FAP HTML Parser
    Extracts schedule data from FAP HTML responses
    """

    # Slot time mappings
    SLOT_TIMES = {
        1: ("7:00", "9:15"),
        2: ("9:30", "11:45"),
        3: ("12:30", "14:45"),
        4: ("15:00", "17:15"),
        5: ("17:30", "19:45"),
        6: ("19:45", "22:00"),
        7: ("22:00", "00:00"),
        8: ("00:00", "7:00"),
    }

    # Day column indices (after slot column)
    DAY_COLUMNS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    def __init__(self):
        self.current_week: Optional[int] = None
        self.current_year: Optional[int] = None
        self.week_dates: Dict[str, str] = {}

    def parse_schedule(self, html_content: str) -> List[ScheduleItem]:
        """
        Parse schedule HTML content

        Args:
            html_content: Raw HTML from FAP schedule page

        Returns:
            List of ScheduleItem objects
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            schedule_items = []

            # Extract week info
            self._extract_week_info(soup)

            # Find the schedule table - it's the main table in the content
            table = None
            for t in soup.find_all('table'):
                # Check if table has a tbody with slot rows
                tbody = t.find('tbody')
                if tbody:
                    # Check for "Slot" text in first row
                    first_row = tbody.find('tr')
                    if first_row and 'Slot' in first_row.get_text():
                        table = t
                        break

            if not table:
                logger.error("Could not find schedule table")
                return []

            # Extract date headers from thead
            thead = table.find('thead')
            if thead:
                rows = thead.find_all('tr')
                if len(rows) >= 2:
                    self._extract_date_headers(rows[1])

            # Parse slot rows from tbody
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                logger.info(f"Found {len(rows)} rows in tbody")
                for row in rows:
                    items = self._parse_slot_row(row)
                    schedule_items.extend(items)

            logger.info(f"Parsed {len(schedule_items)} schedule items")
            return schedule_items

        except Exception as e:
            logger.error(f"Error parsing schedule: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_week_info(self, soup: BeautifulSoup) -> None:
        """Extract current week and year from dropdowns"""
        try:
            week_select = soup.find('select', {'id': 'ctl00_mainContent_drpSelectWeek'})
            if week_select:
                selected = week_select.find('option', selected=True)
                if selected:
                    self.current_week = int(selected.get('value', 0))

            year_select = soup.find('select', {'id': 'ctl00_mainContent_drpYear'})
            if year_select:
                selected = year_select.find('option', selected=True)
                if selected:
                    self.current_year = int(selected.get('value', datetime.now().year))

            logger.info(f"Week info: {self.current_week}/{self.current_year}")

        except Exception as e:
            logger.warning(f"Could not extract week info: {e}")

    def _extract_date_headers(self, row: Tag) -> None:
        """Extract dates from the header row"""
        try:
            headers = row.find_all('th')
            self.week_dates = {}

            # Start from index 1 (skip the Year/Week column)
            for i in range(1, min(len(headers), 8)):
                if i - 1 < len(self.DAY_COLUMNS):
                    day_name = self.DAY_COLUMNS[i - 1]
                    date_text = headers[i].get_text(strip=True)
                    self.week_dates[day_name] = date_text

            logger.debug(f"Week dates: {self.week_dates}")

        except Exception as e:
            logger.warning(f"Could not extract date headers: {e}")

    def _parse_slot_row(self, row: Tag) -> List[ScheduleItem]:
        """Parse a single slot row"""
        items = []
        try:
            cells = row.find_all('td')
            if len(cells) < 2:
                return items

            # Get slot number from first cell
            slot_text = cells[0].get_text(strip=True)
            slot_match = re.search(r'Slot\s*(\d+)', slot_text, re.IGNORECASE)
            if not slot_match:
                return items

            slot_num = int(slot_match.group(1))
            times = self.SLOT_TIMES.get(slot_num, ("", ""))

            # Parse each day column (cells 1-7 for Mon-Sun)
            for i in range(1, min(8, len(cells))):
                day = self.DAY_COLUMNS[i - 1]
                cell = cells[i]
                cell_content = cell.get_text(strip=True)

                # Skip empty cells
                if cell_content == '-' or not cell_content:
                    continue

                item = self._parse_schedule_cell(cell, slot_num, day, times)
                if item:
                    items.append(item)

        except Exception as e:
            logger.warning(f"Error parsing slot row: {e}")

        return items

    def _parse_schedule_cell(self, cell: Tag, slot_num: int, day: str, times: tuple) -> Optional[ScheduleItem]:
        """Parse a single schedule cell"""
        try:
            # Extract subject code from link
            links = cell.find_all('a', href=re.compile(r'ActivityDetail'))
            if not links:
                return None

            # First link contains subject code
            subject_code = links[0].get_text(strip=True).rstrip('-')
            if not subject_code:
                return None

            # Parse cell content
            cell_text = cell.get_text()

            # Extract room
            room_match = re.search(r'at\s+([A-Z0-9.]+)', cell_text)
            room = room_match.group(1) if room_match else ""

            # Extract time from label
            time_match = re.search(r'\((\d{1,2}:\d{2})-(\d{1,2}:\d{2})\)', cell_text)
            if time_match:
                start_time = time_match.group(1)
                end_time = time_match.group(2)
            else:
                start_time, end_time = times

            # Extract attendance status
            status = "-"
            if 'attended' in cell_text.lower():
                status = "attended"
            elif 'absent' in cell_text.lower():
                status = "absent"

            # Get date for this day
            date = self.week_dates.get(day, "")

            item = ScheduleItem(
                subject_code=subject_code,
                room=room,
                day=day,
                date=date,
                slot=slot_num,
                start_time=start_time,
                end_time=end_time,
                status=status
            )

            logger.debug(f"Parsed: {subject_code} on {day} at {room}")
            return item

        except Exception as e:
            logger.warning(f"Error parsing cell: {e}")
            return None

    def filter_by_day(self, items: List[ScheduleItem], day: str) -> List[ScheduleItem]:
        """Filter schedule items by day (Mon, Tue, etc.)"""
        day = day.capitalize()
        if day not in self.DAY_COLUMNS:
            return []
        return [item for item in items if item.day == day]

    def filter_by_date(self, items: List[ScheduleItem], date: str) -> List[ScheduleItem]:
        """Filter schedule items by date (DD/MM)"""
        return [item for item in items if date in item.date]

    def get_today_schedule(self, items: List[ScheduleItem]) -> List[ScheduleItem]:
        """Get schedule items for today"""
        today_map = {
            0: 'Mon',
            1: 'Tue',
            2: 'Wed',
            3: 'Thu',
            4: 'Fri',
            5: 'Sat',
            6: 'Sun'
        }
        today = today_map.get(datetime.now().weekday(), '')
        return self.filter_by_day(items, today)

    def format_for_discord(self, items: List[ScheduleItem], title: str = "Schedule") -> str:
        """
        Format schedule items for Discord message

        Args:
            items: List of schedule items
            title: Message title

        Returns:
            Formatted string for Discord
        """
        if not items:
            return f"📅 **{title}**\n\nNo classes scheduled!"

        lines = [f"📅 **{title}**\n"]
        lines.append("=" * 40)

        # Group by day
        by_day = {}
        for item in items:
            if item.day not in by_day:
                by_day[item.day] = []
            by_day[item.day].append(item)

        # Sort by day order
        day_order = {d: i for i, d in enumerate(self.DAY_COLUMNS)}

        for day in sorted(by_day.keys(), key=lambda d: day_order.get(d, 999)):
            lines.append(f"\n📆 **{day}** ({by_day[day][0].date})")
            lines.append("-" * 30)
            for item in by_day[day]:
                lines.append(str(item))
                lines.append("")

        return "\n".join(lines)
