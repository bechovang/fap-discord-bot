"""
Exam Schedule Parser for FAP
"""
from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup


@dataclass
class ExamItem:
    """Exam schedule item"""
    no: int
    subject_code: str
    subject_name: str
    date: str
    room: str
    time: str
    exam_form: str
    exam_type: str  # PE = Practical Exam, FE = Final Exam
    publication_date: str = ""

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


class ExamParser:
    """Parser for FAP exam schedule HTML"""

    def parse_exam_schedule(self, html: str) -> List[ExamItem]:
        """
        Parse exam schedule from HTML

        Args:
            html: HTML content from exam schedule page

        Returns:
            List of ExamItem objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        exams = []

        # Find the exam table
        # The table is inside ctl00_mainContent_divContent
        content_div = soup.find('div', id='ctl00_mainContent_divContent')

        if not content_div:
            return exams

        # Find the table
        table = content_div.find('table')
        if not table:
            return exams

        # Parse table rows
        tbody = table.find('tbody')
        if not tbody:
            tbody = table  # Some tables don't have tbody

        rows = tbody.find_all('tr')

        # Skip header row
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 8:
                try:
                    exam = ExamItem(
                        no=int(cols[0].get_text(strip=True)),
                        subject_code=cols[1].get_text(strip=True),
                        subject_name=cols[2].get_text(strip=True),
                        date=cols[3].get_text(strip=True),
                        room=cols[4].get_text(strip=True),
                        time=cols[5].get_text(strip=True),
                        exam_form=cols[6].get_text(strip=True),
                        exam_type=cols[7].get_text(strip=True),
                        publication_date=cols[8].get_text(strip=True) if len(cols) > 8 else ""
                    )
                    exams.append(exam)
                except (ValueError, IndexError) as e:
                    continue

        return exams

    def get_upcoming_exams(self, exams: List[ExamItem], days: int = 7) -> List[ExamItem]:
        """
        Get exams within next N days

        Args:
            exams: List of all exams
            days: Number of days to look ahead

        Returns:
            List of upcoming exams
        """
        from datetime import datetime, timedelta

        today = datetime.now()
        upcoming = []

        for exam in exams:
            try:
                # Parse date (format: DD/MM/YYYY)
                day, month, year = map(int, exam.date.split('/'))
                exam_date = datetime(year, month, day)

                # Check if within range
                delta = exam_date - today
                if timedelta(0) <= delta <= timedelta(days=days):
                    upcoming.append(exam)
            except (ValueError, AttributeError):
                continue

        return sorted(upcoming, key=lambda x: x.date)

    def format_for_discord(self, exams: List[ExamItem], title: str = "Exam Schedule") -> str:
        """
        Format exam list for Discord message

        Args:
            exams: List of exam items
            title: Title for the message

        Returns:
            Formatted string for Discord
        """
        if not exams:
            return f"📚 **{title}**\n\nNo exams found."

        lines = [f"📚 **{title}**\n"]
        lines.append(f"Found {len(exams)} exam(s)\n")

        for exam in exams:
            lines.append(f"**{exam.no}. {exam.subject_code} - {exam.subject_name}**")
            lines.append(f"📅 Date: {exam.date}")
            lines.append(f"🕐 Time: {exam.time}")
            lines.append(f"📍 Room: {exam.room}")
            lines.append(f"📝 Type: {exam.exam_type} ({exam.exam_form})")
            lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test parser
    import sys

    html_file = sys.argv[1] if len(sys.argv) > 1 else "exam_final2.html"

    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    parser = ExamParser()
    exams = parser.parse_exam_schedule(html)

    print(f"Found {len(exams)} exams:")
    for exam in exams:
        print(f"  {exam}")

    print("\nFormatted for Discord:")
    print(parser.format_for_discord(exams))
