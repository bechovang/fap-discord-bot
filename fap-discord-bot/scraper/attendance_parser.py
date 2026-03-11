"""
FAP Attendance Parser
Parses attendance HTML from FAP portal
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

MAX_RECENT_TERMS = 10


@dataclass
class AttendanceItem:
    """Single attendance record"""
    no: int
    subject_code: str
    subject_name: str
    room: str
    day: str
    date: str
    slot: int
    start_time: str
    end_time: str
    attendance_status: str  # "present", "absent", "future"
    lecturer: str = ""
    group_name: str = ""
    credits: int = 0


@dataclass
class AttendanceSummary:
    """Summary statistics for attendance"""
    total: int
    present: int
    absent: int
    future: int
    percentage: float


class AttendanceParser:
    """Parser for FAP attendance pages"""

    def __init__(self):
        self.student_id: Optional[str] = None
        self.campus_id: Optional[int] = None

    def extract_terms(self, html: str) -> List[dict]:
        """
        Extract term list from attendance page

        Args:
            html: Page HTML content

        Returns:
            List of term dicts with keys: id, name, is_current
        """
        soup = BeautifulSoup(html, 'html.parser')
        terms = []

        # Find term container
        term_container = soup.find('div', {'id': 'ctl00_mainContent_divTerm'})
        if not term_container:
            logger.warning("Term container not found")
            return []

        # Parse terms from table cells
        for td in term_container.find_all('td'):
            a_tag = td.find('a')
            if a_tag:
                # Non-current term - has link
                href = a_tag.get('href', '')
                term_name = a_tag.get_text(strip=True)
                term_id = self._extract_url_param(href, 'term')
                terms.append({
                    'id': term_id,
                    'name': term_name,
                    'is_current': False
                })
            else:
                # Current term - no link, just text
                term_name = td.get_text(strip=True)
                if term_name:
                    terms.append({
                        'id': 'current',
                        'name': term_name,
                        'is_current': True
                    })

        # Terms are already in order (oldest → newest) in HTML
        # Take only the 10 most recent (last 10 items)
        terms = terms[-MAX_RECENT_TERMS:] if len(terms) > MAX_RECENT_TERMS else terms

        return terms

    def extract_courses(self, html: str) -> List[dict]:
        """
        Extract course list for a term from attendance page

        Args:
            html: Page HTML content (already filtered for term)

        Returns:
            List of course dicts with keys: course_id, code, name
        """
        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Find course div - courses are listed as links in a table
        course_div = soup.find('div', {'id': 'ctl00_mainContent_divCourse'})
        if not course_div:
            logger.warning("Course div not found")
            return []

        # Find all table rows in the course div
        table = course_div.find('table')
        if not table:
            logger.warning("Course table not found")
            return []

        # Extract courses from rows
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue

            td = tds[0]  # First (and usually only) td

            # Check for current course (bold tag, no link)
            b_tag = td.find('b')
            if b_tag:
                text = b_tag.get_text(strip=True)
                # Parse course name (e.g., "Elementary Japanese 1- A1.1(JPD113)(SE2042,start 05/01/2026)")
                # Extract code from pattern like (JPD113) or (LAB211)
                code_match = re.search(r'\(([A-Z]{3}\d{3})\)', text)
                code = code_match.group(1) if code_match else ''

                courses.append({
                    'course_id': None,  # Current course has no ID
                    'code': code,
                    'name': text,
                    'is_current': True
                })
                continue

            # Check for other courses (links)
            a_tag = td.find('a')
            if a_tag:
                href = a_tag.get('href', '')
                text = a_tag.get_text(strip=True)

                # Extract course ID from href (e.g., course=57599)
                course_id_match = re.search(r'course=(\d+)', href)
                course_id = course_id_match.group(1) if course_id_match else None

                # Parse subject code from text (e.g., "Statistics & Probability(MAS291)")
                code_match = re.search(r'\(([A-Z]{3}\d{3})\)', text)
                code = code_match.group(1) if code_match else ''

                if course_id:
                    courses.append({
                        'course_id': int(course_id),
                        'code': code,
                        'name': text,
                        'is_current': False
                    })

        return courses

    def parse_attendance(self, html: str) -> List[AttendanceItem]:
        """
        Parse attendance records from page

        Args:
            html: Page HTML content

        Returns:
            List of AttendanceItem objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        # Find attendance table - try multiple selectors
        table = soup.find('table', {'id': 'ctl00_mainContent_grvStudent'})
        if not table:
            # Try class selector (table1, table-bordered)
            table = soup.find('table', class_='table1')
        if not table:
            # Try table-bordered class
            table = soup.find('table', class_='table-bordered')

        if not table:
            logger.warning("Attendance table not found")
            return []

        # Parse rows
        rows = table.find_all('tr')
        for row_idx, row in enumerate(rows[1:], start=1):  # Skip header row
            cells = row.find_all('td')
            if len(cells) < 7:
                continue

            try:
                # Extract cells based on actual HTML structure
                # No. | Date | Slot | Room | Lecturer | Group Name | Attendance Status | Comment
                no = row_idx

                # Date cell (may contain span)
                date_cell = cells[1]
                date_span = date_cell.find('span')
                if date_span:
                    date = date_span.get_text(strip=True)
                else:
                    date = date_cell.get_text(strip=True)

                # Extract day from date (e.g., "Monday 05/01/2026")
                day_parts = date.split()
                day = day_parts[0] if day_parts else date

                # Slot cell (may contain span with label-danger)
                slot_cell = cells[2]
                slot_span = slot_cell.find('span')
                if slot_span:
                    slot_text = slot_span.get_text(strip=True)
                else:
                    slot_text = slot_cell.get_text(strip=True)
                # Extract slot number from "1_(7:00-9:15)" or just "1"
                slot_match = re.search(r'(\d+)', slot_text)
                slot = int(slot_match.group(1)) if slot_match else 0

                # Room
                room = cells[3].get_text(strip=True)

                # Lecturer
                lecturer = cells[4].get_text(strip=True) if len(cells) > 4 else ""

                # Group name
                group_name = cells[5].get_text(strip=True) if len(cells) > 5 else ""

                # Attendance status from font color
                status_cell = cells[6]
                font_tag = status_cell.find('font')
                if font_tag:
                    color = font_tag.get('color', '').lower()
                    status_text = font_tag.get_text(strip=True).lower()

                    if 'green' in color or 'present' in status_text:
                        attendance_status = 'present'
                    elif 'red' in color or 'absent' in status_text:
                        attendance_status = 'absent'
                    elif 'black' in color or 'future' in status_text:
                        attendance_status = 'future'
                    else:
                        attendance_status = 'future'
                else:
                    # Check cell text directly
                    status_text = status_cell.get_text(strip=True).lower()
                    if 'present' in status_text:
                        attendance_status = 'present'
                    elif 'absent' in status_text:
                        attendance_status = 'absent'
                    else:
                        attendance_status = 'future'

                # Extract time from slot text (e.g., "1_(7:00-9:15)")
                time_match = re.search(r'\((\d{1,2}:\d{2})-(\d{1,2}:\d{2})\)', slot_text)
                if time_match:
                    start_time = time_match.group(1)
                    end_time = time_match.group(2)
                else:
                    start_time = ""
                    end_time = ""

                # Subject info - not in this table, would need to get from context
                # Use placeholder values
                subject_code = ""
                subject_name = ""

                item = AttendanceItem(
                    no=no,
                    subject_code=subject_code,
                    subject_name=subject_name,
                    room=room,
                    day=day,
                    date=date,
                    slot=slot,
                    start_time=start_time,
                    end_time=end_time,
                    attendance_status=attendance_status,
                    lecturer=lecturer
                )
                items.append(item)

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse row {row_idx}: {e}")
                continue

        return items

    def calculate_summary(self, items: List[AttendanceItem]) -> AttendanceSummary:
        """
        Calculate attendance summary statistics

        Args:
            items: List of attendance items

        Returns:
            AttendanceSummary with calculated stats
        """
        total = len(items)
        present = sum(1 for i in items if i.attendance_status == 'present')
        absent = sum(1 for i in items if i.attendance_status == 'absent')
        future = sum(1 for i in items if i.attendance_status == 'future')

        # Attendance percentage (excluding future classes)
        eligible = present + absent
        percentage = (present / eligible * 100) if eligible > 0 else 0.0

        return AttendanceSummary(
            total=total,
            present=present,
            absent=absent,
            future=future,
            percentage=round(percentage, 1)
        )

    def format_for_discord(self, items: List[AttendanceItem], summary: AttendanceSummary, title: str = "Attendance") -> str:
        """
        Format attendance data for Discord message

        Args:
            items: List of attendance items
            summary: Attendance summary
            title: Message title

        Returns:
            Formatted Discord message string
        """
        lines = [
            f"📊 **{title}**",
            "",
            f"📈 **Summary:** {summary.present}/{summary.present + summary.absent} present ({summary.percentage}%)",
            f"❌ Absent: {summary.absent} | ⏳ Future: {summary.future}",
            "",
            "**Classes:**",
        ]

        for item in items[:25]:  # Discord limit
            status_emoji = {
                'present': '✅',
                'absent': '❌',
                'future': '⏳'
            }.get(item.attendance_status, '❓')

            lines.append(
                f"{status_emoji} **{item.subject_code}** - {item.day} {item.date}\n"
                f"   Slot {item.slot} ({item.start_time}-{item.end_time}) | Room: {item.room}"
            )

        if len(items) > 25:
            lines.append(f"\n_... and {len(items) - 25} more classes_")

        return "\n".join(lines)

    def _extract_url_param(self, url: str, param: str) -> str:
        """Extract parameter value from URL query string"""
        pattern = rf'{param}=([^&]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else ''
