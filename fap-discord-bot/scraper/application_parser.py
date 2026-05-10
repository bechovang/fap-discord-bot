"""
Application Parser for FAP
Parses application status from AcadAppView.aspx
"""
from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ApplicationItem:
    """Application item"""
    app_type: str
    purpose: str
    create_date: str
    process_note: str
    file: str
    status: str  # 'Pending', 'Approved', 'Rejected'
    processed_date: Optional[str] = None

    def __str__(self):
        return f"{self.app_type}: {self.status}"


class ApplicationParser:
    """Parser for FAP application HTML"""

    def parse_applications(self, html: str) -> List[ApplicationItem]:
        """
        Parse applications from HTML

        Args:
            html: HTML content from application page

        Returns:
            List of ApplicationItem objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        applications = []

        # Find the content div
        content_div = soup.find('div', id='ctl00_mainContent_content')

        if not content_div:
            logger.warning("Could not find application content div")
            return applications

        # Find the table
        table = content_div.find('table', class_='table')
        if not table:
            logger.warning("Could not find application table")
            return applications

        # Parse table rows
        tbody = table.find('tbody')
        if not tbody:
            tbody = table

        rows = tbody.find_all('tr')

        # Skip header row
        for row in rows[1:]:
            try:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    # Extract data from columns
                    app_type = cols[0].get_text(strip=True)
                    purpose = cols[1].get_text(strip=True)
                    create_date = cols[2].get_text(strip=True)
                    process_note = cols[3].get_text(strip=True)
                    file = cols[4].get_text(strip=True) if len(cols) > 4 else ""

                    # Extract status from the <p> tag with class
                    status_col = cols[5]
                    status_p = status_col.find('p')
                    if status_p:
                        # Check class for status
                        status_text = status_p.get_text(strip=True).lower()
                        if 'approved' in status_text:
                            status = 'Approved'
                        elif 'rejected' in status_text:
                            status = 'Rejected'
                        elif 'pending' in status_text:
                            status = 'Pending'
                        else:
                            # Check if there's a class indicating status
                            if 'text-success' in str(status_p):
                                status = 'Approved'
                            elif 'text-warning' in str(status_p):
                                status = 'Pending'
                            elif 'text-danger' in str(status_p):
                                status = 'Rejected'
                            else:
                                status = 'Unknown'
                    else:
                        status = 'Unknown'

                    # Get processed date if available (column 6 or 7)
                    processed_date = None
                    if len(cols) > 6:
                        processed_date = cols[6].get_text(strip=True)
                        if not processed_date:
                            processed_date = None

                    app = ApplicationItem(
                        app_type=app_type,
                        purpose=purpose,
                        create_date=create_date,
                        process_note=process_note,
                        file=file,
                        status=status,
                        processed_date=processed_date
                    )
                    applications.append(app)

            except Exception as e:
                logger.warning(f"Error parsing application row: {e}")
                continue

        logger.info(f"Parsed {len(applications)} applications")
        return applications

    def get_pending_applications(self, applications: List[ApplicationItem]) -> List[ApplicationItem]:
        """Filter only pending applications"""
        return [app for app in applications if app.status == 'Pending']

    def get_recent_applications(
        self,
        applications: List[ApplicationItem],
        days: int = 30
    ) -> List[ApplicationItem]:
        """Get applications from last N days"""
        recent = []
        now = datetime.now()

        for app in applications:
            try:
                # Parse date (format: DD/MM/YYYY)
                day, month, year = map(int, app.create_date.split('/'))
                app_date = datetime(year, month, day)

                # Check if within range
                delta = now - app_date
                if delta.days <= days:
                    recent.append(app)
            except (ValueError, AttributeError):
                continue

        return recent

    def format_for_discord(self, applications: List[ApplicationItem], title: str = "Applications") -> str:
        """Format applications for Discord message"""
        if not applications:
            return f"📋 **{title}**\n\nNo applications found."

        lines = [f"📋 **{title}**\n"]
        lines.append(f"Found {len(applications)} application(s)\n")

        # Count by status
        pending = sum(1 for a in applications if a.status == 'Pending')
        approved = sum(1 for a in applications if a.status == 'Approved')
        rejected = sum(1 for a in applications if a.status == 'Rejected')

        lines.append(f"📊 Summary: ⏳ {pending} Pending | ✅ {approved} Approved | ❌ {rejected} Rejected\n")

        for app in applications:
            status_emoji = {
                'Pending': '⏳',
                'Approved': '✅',
                'Rejected': '❌',
                'Unknown': '❓'
            }.get(app.status, '❓')

            # Truncate purpose if too long
            purpose = app.purpose[:100] + "..." if len(app.purpose) > 100 else app.purpose

            lines.append(f"{status_emoji} **{app.app_type}**")
            lines.append(f"   📝 {purpose}")
            lines.append(f"   📅 Created: {app.create_date}")
            if app.status != 'Pending':
                lines.append(f"   📌 Status: {app.status}")
            if app.process_note:
                note = app.process_note[:100] + "..." if len(app.process_note) > 100 else app.process_note
                lines.append(f"   💬 Note: {note}")
            lines.append("")

        return "\n".join(lines)
