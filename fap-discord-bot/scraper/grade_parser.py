"""
FAP Grade Parser
Parses grade HTML from FAP portal
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

MAX_RECENT_TERMS = 10

# Non-GPA subjects to exclude from calculations
EXCLUDED_SUBJECTS = ['PE', 'MUSIC', 'ENG', 'EN', 'PHYSICAL_EDUCATION']

# Grade scale conversion (10-point to 4-point)
GRADE_SCALE = {
    10: 4.0,
    9: 4.0,
    8: 3.5,
    7: 3.0,
    6: 2.0,
    5: 1.0,
    4: 0.5,
    0: 0.0,
}


@dataclass
class GradeItem:
    """Single grade record"""
    no: int
    subject_code: str
    subject_name: str
    credits: int
    mid_term: float
    final: float
    total: float
    status: str  # "Passed", "Is Suspended", "In Progress"
    grade_4scale: float  # Converted to 4.0 scale


@dataclass
class GradeDetail:
    """Detailed grade breakdown by component"""
    component: str  # e.g., "Labs", "Progress Tests", "Assignment", "Exams"
    weight: float
    score: float


@dataclass
class TermGPA:
    """GPA information for a single term"""
    term: str
    term_gpa: float
    credits_earned: int
    credits_total: int
    subjects_passed: int
    subjects_failed: int


@dataclass
class GPASummary:
    """GPA calculation summary"""
    term: Optional[str]
    term_gpa: Optional[float]
    cumulative_gpa: float
    total_credits: int
    earned_credits: int
    subjects_passed: int
    subjects_failed: int
    grade_breakdown: Dict[str, int]
    by_term: Dict[str, TermGPA]
    excluded_subjects: List[str]

    def __str__(self) -> str:
        lines = [
            f"📊 **GPA Summary**",
            ""
        ]

        if self.term and self.term_gpa is not None:
            lines.append(f"📈 Term GPA ({self.term}): **{self.term_gpa:.2f}** / 4.0")
        else:
            lines.append(f"📈 Term GPA: N/A")

        lines.append(f"🎯 Cumulative GPA: **{self.cumulative_gpa:.2f}** / 4.0")
        lines.append(f"📚 Credits: {self.earned_credits}/{self.total_credits}")
        lines.append(f"✅ Passed: {self.subjects_passed} | ❌ Failed: {self.subjects_failed}")

        if self.excluded_subjects:
            lines.append(f"⚠️ Excluded from GPA: {', '.join(self.excluded_subjects)}")

        return "\n".join(lines)


@dataclass
class GradeSummary:
    """Complete grade summary"""
    term: str
    grades: List[GradeItem]
    gpa_summary: GPASummary


class GradeParser:
    """Parser for FAP grade pages"""

    def __init__(self, exclude_subjects: List[str] = None):
        self.exclude_subjects = exclude_subjects or EXCLUDED_SUBJECTS.copy()
        self.student_id: Optional[str] = None

    def extract_terms(self, html: str) -> List[dict]:
        """
        Extract term list from grade page

        Args:
            html: Page HTML content

        Returns:
            List of term dicts with keys: name, is_current
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
                terms.append({
                    'name': term_name,
                    'is_current': False
                })
            else:
                # Current term - no link, just text
                term_name = td.get_text(strip=True)
                if term_name:
                    terms.append({
                        'name': term_name,
                        'is_current': True
                    })

        # Terms are already in order (oldest → newest) in HTML
        # Take only the 10 most recent (last 10 items)
        terms = terms[-MAX_RECENT_TERMS:] if len(terms) > MAX_RECENT_TERMS else terms

        return terms

    def extract_courses(self, html: str) -> List[dict]:
        """
        Extract course list for a term from grade page

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

            # Check for current course (bold tag, no link) - only in pro view
            b_tag = td.find('b')
            if b_tag:
                text = b_tag.get_text(strip=True)
                # Parse course name (e.g., "Discrete mathematics (MAD101) (IS2002, from 08/09/2025 - 13/11/2025)")
                # Extract code from pattern like (MAD101)
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

                # Extract course ID from href (e.g., course=55340)
                course_id_match = re.search(r'course=(\d+)', href)
                course_id = course_id_match.group(1) if course_id_match else None

                # Parse subject code from text (e.g., "Discrete mathematics (MAD101)")
                code_match = re.search(r'\(([A-Z]{3}\d{3})\)', text)
                code = code_match.group(1) if code_match else ''

                # All courses in base page have course_id (no bold "current" course in base view)
                if course_id:
                    courses.append({
                        'course_id': int(course_id),
                        'code': code,
                        'name': text,
                        'is_current': False
                    })
                elif code:  # Fallback - if we have code but no ID
                    courses.append({
                        'course_id': None,
                        'code': code,
                        'name': text,
                        'is_current': False
                    })

        logger.info(f"Extracted {len(courses)} courses")
        return courses

    def parse_grades(self, html: str) -> List[GradeItem]:
        """
        Parse grade records from page

        Args:
            html: Page HTML content

        Returns:
            List of GradeItem objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        # Try to find the grade div first (ctl00_mainContent_divGrade)
        grade_div = soup.find('div', {'id': 'ctl00_mainContent_divGrade'})

        if grade_div:
            # This is a detailed grade page for a specific course
            table = grade_div.find('table')
            if table:
                return self._parse_detailed_grade_table(table, soup)

        # Fall back to looking for summary table (list of all subjects)
        # Method 1: By ID
        table = soup.find('table', {'id': 'ctl00_mainContent_grvStudent'})

        # Method 2: By class patterns
        if not table:
            table = soup.find('table', class_=re.compile(r'table-bordered|table1|gridview'))

        # Method 3: Any table with Subject Code in header
        if not table:
            for t in soup.find_all('table'):
                headers = t.find_all('th')
                header_text = ' '.join([h.get_text() for h in headers])
                if 'Subject' in header_text or 'Code' in header_text or 'Mã MH' in header_text:
                    table = t
                    logger.info(f"Found grade table by header match: {header_text[:50]}")
                    break

        if not table:
            logger.warning("Grade table not found")
            # Save debug HTML
            with open('debug_grade_parse_error.html', 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info("Saved HTML to debug_grade_parse_error.html")
            return []

        return self._parse_summary_grade_table(table)

    def _parse_detailed_grade_table(self, table, soup) -> List[GradeItem]:
        """Parse detailed grade table for a single course

        Table structure:
        - Headers: Grade category | Grade item | Weight | Value | Comment
        - Footer: Average (total grade) | Status
        """
        items = []

        # Get course info from page title/h2
        h2 = soup.find('h2')
        student_info = h2.get_text() if h2 else ""

        # Get course name from divCourse - find the <b> tag (current course)
        course_div = soup.find('div', {'id': 'ctl00_mainContent_divCourse'})
        course_name = "Unknown Course"
        if course_div:
            b_tag = course_div.find('b')
            if b_tag:
                course_text = b_tag.get_text(strip=True)
                # Extract course code from parentheses
                code_match = re.search(r'\(([A-Z]{3}\d{3})\)', course_text)
                subject_code = code_match.group(1) if code_match else "UNKNOWN"
                course_name = course_text
            else:
                # Try from links
                first_link = course_div.find('a')
                if first_link:
                    course_text = first_link.get_text(strip=True)
                    code_match = re.search(r'\(([A-Z]{3}\d{3})\)', course_text)
                    subject_code = code_match.group(1) if code_match else "UNKNOWN"
                    course_name = course_text
                else:
                    subject_code = "UNKNOWN"

        # Find the footer with Average and Status
        tfoot = table.find('tfoot')
        total_grade = 0.0
        status = "Unknown"

        if tfoot:
            for row in tfoot.find_all('tr'):
                cells = row.find_all('td')
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if 'Average' in text:
                        # Find the value in adjacent cells
                        idx = cells.index(cell)
                        if idx + 1 < len(cells):
                            val_text = cells[idx + 1].get_text(strip=True)
                            try:
                                total_grade = float(val_text)
                            except ValueError:
                                pass
                    elif 'Status' in text:
                        idx = cells.index(cell)
                        if idx + 1 < len(cells):
                            status_text = cells[idx + 1].get_text(strip=True)
                            if 'Suspended' in status_text or 'Fail' in status_text:
                                status = "Is Suspended"
                            elif 'Passed' in status_text:
                                status = "Passed"
                            else:
                                status = status_text

        # Create a single GradeItem for this course
        grade_4scale = self._convert_to_4scale(total_grade)

        item = GradeItem(
            no=1,
            subject_code=subject_code,
            subject_name=course_name,
            credits=0,  # Not available in detailed view
            mid_term=0.0,  # Not available in detailed view
            final=total_grade,
            total=total_grade,
            status=status,
            grade_4scale=grade_4scale
        )
        items.append(item)

        logger.info(f"Parsed detailed grade: {subject_code} - Total: {total_grade} - Status: {status}")
        return items

    def _parse_summary_grade_table(self, table) -> List[GradeItem]:
        """Parse summary grade table with multiple subjects

        Table structure (varies):
        - No | Subject Code | Subject Name | Credits | Mid | Final | Total | Status
        """
        items = []

        rows = table.find_all('tr')
        logger.info(f"Found {len(rows)} rows in grade table")

        for row_idx, row in enumerate(rows[1:], start=1):  # Skip header row
            cells = row.find_all('td')
            if len(cells) < 3:  # Minimum 3 columns
                continue

            try:
                no = row_idx

                # Try to extract data from cells flexibly
                subject_code = ""
                subject_name = ""
                credits = 0
                mid_term = 0.0
                final = 0.0
                total = 0.0
                status = "Unknown"

                # Extract subject code (pattern: ABC123)
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    # Check for subject code pattern
                    if re.match(r'^[A-Z]{3}\d{3}$', text):
                        subject_code = text
                        # Try to get name from title attribute or next cell
                        subject_name = cell.get('title', '')
                        if not subject_name and i + 1 < len(cells):
                            subject_name = cells[i + 1].get_text(strip=True)
                        break
                    # Also check if subject code is in parentheses
                    elif '(' in text and ')' in text:
                        code_match = re.search(r'\(([A-Z]{3}\d{3})\)', text)
                        if code_match:
                            subject_code = code_match.group(1)
                            subject_name = text
                            break

                # If no subject code found, use first non-empty cell as identifier
                if not subject_code:
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text and not text.replace('.', '').replace('-', '').isdigit():
                            subject_code = text[:10]  # First 10 chars as code
                            subject_name = text
                            break

                # Extract credits (look for small numbers, usually 2-4)
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if text.isdigit() and 2 <= int(text) <= 5:
                        credits = int(text)
                        break

                # Extract numeric grades (look for values 0-10)
                grade_values = []
                for cell in cells:
                    text = cell.get_text(strip=True)
                    try:
                        val = float(text)
                        if 0 <= val <= 10:
                            grade_values.append(val)
                    except ValueError:
                        pass

                # Assign grades based on position
                # Typically: mid-term, final, total (from left to right)
                if len(grade_values) >= 3:
                    mid_term = grade_values[0]
                    final = grade_values[1]
                    total = grade_values[2]
                elif len(grade_values) == 2:
                    mid_term = grade_values[0]
                    total = grade_values[1]
                elif len(grade_values) == 1:
                    total = grade_values[0]

                # Extract status (look for text like "Passed", "Is Suspended", etc.)
                for cell in cells:
                    text = cell.get_text(strip=True).lower()
                    if any(s in text for s in ['passed', 'đạt', 'hoàn thành']):
                        status = "Passed"
                        break
                    elif any(s in text for s in ['suspended', 'rớt', 'fail']):
                        status = "Is Suspended"
                        break
                    elif any(s in text for s in ['progress', 'đang học']):
                        status = "In Progress"
                        break

                # If total is 0 but we have other grades, calculate total
                if total == 0 and (mid_term > 0 or final > 0):
                    # Simple average (can be adjusted based on actual weight)
                    total = (mid_term + final) / 2 if mid_term > 0 and final > 0 else max(mid_term, final)

                # Convert to 4.0 scale
                grade_4scale = self._convert_to_4scale(total)

                item = GradeItem(
                    no=no,
                    subject_code=subject_code,
                    subject_name=subject_name,
                    credits=credits,
                    mid_term=mid_term,
                    final=final,
                    total=total,
                    status=status,
                    grade_4scale=grade_4scale
                )

                # Only add if we have meaningful data
                if subject_code or total > 0:
                    items.append(item)
                    logger.info(f"Parsed grade {no}: {subject_code} - Total: {total}")

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse grade row {row_idx}: {e}")
                continue

        logger.info(f"Total parsed grades: {len(items)}")
        return items

        # Parse rows
        rows = table.find_all('tr')
        logger.info(f"Found {len(rows)} rows in grade table")

        for row_idx, row in enumerate(rows[1:], start=1):  # Skip header row
            cells = row.find_all('td')
            if len(cells) < 3:  # Minimum 3 columns
                continue

            try:
                no = row_idx

                # Try to extract data from cells flexibly
                # Common column patterns:
                # 1. No | Subject Code | Subject Name | Credits | Mid | Final | Total | Status
                # 2. No | Subject | Credits | Mid | Final | Total | Status
                # 3. Other variations...

                # Initialize values
                subject_code = ""
                subject_name = ""
                credits = 0
                mid_term = 0.0
                final = 0.0
                total = 0.0
                status = "Unknown"

                # Extract subject code (pattern: ABC123)
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    # Check for subject code pattern
                    if re.match(r'^[A-Z]{3}\d{3}$', text):
                        subject_code = text
                        # Try to get name from title attribute or next cell
                        subject_name = cell.get('title', '')
                        if not subject_name and i + 1 < len(cells):
                            subject_name = cells[i + 1].get_text(strip=True)
                        break
                    # Also check if subject code is in parentheses
                    elif '(' in text and ')' in text:
                        code_match = re.search(r'\(([A-Z]{3}\d{3})\)', text)
                        if code_match:
                            subject_code = code_match.group(1)
                            subject_name = text
                            break

                # If no subject code found, use first non-empty cell as identifier
                if not subject_code:
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text and not text.replace('.', '').replace('-', '').isdigit():
                            subject_code = text[:10]  # First 10 chars as code
                            subject_name = text
                            break

                # Extract credits (look for small numbers, usually 2-4)
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if text.isdigit() and 2 <= int(text) <= 5:
                        credits = int(text)
                        break

                # Extract numeric grades (look for values 0-10)
                grade_values = []
                for cell in cells:
                    text = cell.get_text(strip=True)
                    try:
                        val = float(text)
                        if 0 <= val <= 10:
                            grade_values.append(val)
                    except ValueError:
                        pass

                # Assign grades based on position
                # Typically: mid-term, final, total (from left to right)
                if len(grade_values) >= 3:
                    mid_term = grade_values[0]
                    final = grade_values[1]
                    total = grade_values[2]
                elif len(grade_values) == 2:
                    mid_term = grade_values[0]
                    total = grade_values[1]
                elif len(grade_values) == 1:
                    total = grade_values[0]

                # Extract status (look for text like "Passed", "Is Suspended", etc.)
                for cell in cells:
                    text = cell.get_text(strip=True).lower()
                    if any(s in text for s in ['passed', 'đạt', 'hoàn thành']):
                        status = "Passed"
                        break
                    elif any(s in text for s in ['suspended', 'rớt', 'fail']):
                        status = "Is Suspended"
                        break
                    elif any(s in text for s in ['progress', 'đang học']):
                        status = "In Progress"
                        break

                # If total is 0 but we have other grades, calculate total
                if total == 0 and (mid_term > 0 or final > 0):
                    # Simple average (can be adjusted based on actual weight)
                    total = (mid_term + final) / 2 if mid_term > 0 and final > 0 else max(mid_term, final)

                # Convert to 4.0 scale
                grade_4scale = self._convert_to_4scale(total)

                item = GradeItem(
                    no=no,
                    subject_code=subject_code,
                    subject_name=subject_name,
                    credits=credits,
                    mid_term=mid_term,
                    final=final,
                    total=total,
                    status=status,
                    grade_4scale=grade_4scale
                )

                # Only add if we have meaningful data
                if subject_code or total > 0:
                    items.append(item)
                    logger.info(f"Parsed grade {no}: {subject_code} - Total: {total}")

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse grade row {row_idx}: {e}")
                continue

        logger.info(f"Total parsed grades: {len(items)}")
        return items

    def calculate_gpa(
        self,
        grades: List[GradeItem],
        all_terms_grades: Dict[str, List[GradeItem]] = None
    ) -> GPASummary:
        """
        Calculate GPA from grades

        Args:
            grades: List of grade items for current term
            all_terms_grades: Dict mapping term names to grade lists (for cumulative)

        Returns:
            GPASummary with calculated GPA
        """
        if not grades:
            return GPASummary(
                term=None,
                term_gpa=None,
                cumulative_gpa=0.0,
                total_credits=0,
                earned_credits=0,
                subjects_passed=0,
                subjects_failed=0,
                grade_breakdown={},
                by_term={},
                excluded_subjects=[]
            )

        # Filter out excluded subjects
        filtered_grades = [
            g for g in grades
            if not any(g.subject_code.startswith(prefix) for prefix in self.exclude_subjects)
        ]

        excluded_codes = [
            g.subject_code for g in grades
            if any(g.subject_code.startswith(prefix) for prefix in self.exclude_subjects)
        ]

        # Calculate term GPA
        total_points = sum(g.grade_4scale * g.credits for g in filtered_grades if g.total > 0)
        total_credits = sum(g.credits for g in filtered_grades if g.total > 0)
        term_gpa = total_points / total_credits if total_credits > 0 else 0.0

        # Calculate cumulative GPA across all terms
        cumulative_gpa = term_gpa
        by_term = {}

        if all_terms_grades:
            all_filtered = {}
            for term, term_grades in all_terms_grades.items():
                filtered = [
                    g for g in term_grades
                    if not any(g.subject_code.startswith(prefix) for prefix in self.exclude_subjects)
                ]
                all_filtered[term] = filtered

                # Calculate term GPA
                points = sum(g.grade_4scale * g.credits for g in filtered if g.total > 0)
                creds = sum(g.credits for g in filtered if g.total > 0)
                t_gpa = points / creds if creds > 0 else 0.0
                earned = sum(g.credits for g in filtered if g.status == "Passed")
                passed = sum(1 for g in filtered if g.status == "Passed")
                failed = sum(1 for g in filtered if g.status == "Is Suspended")

                by_term[term] = TermGPA(
                    term=term,
                    term_gpa=round(t_gpa, 2),
                    credits_earned=earned,
                    credits_total=creds,
                    subjects_passed=passed,
                    subjects_failed=failed
                )

            # Calculate cumulative
            cum_points = sum(
                g.grade_4scale * g.credits
                for term_grades in all_filtered.values()
                for g in term_grades
                if g.total > 0
            )
            cum_credits = sum(
                g.credits
                for term_grades in all_filtered.values()
                for g in term_grades
                if g.total > 0
            )
            cumulative_gpa = cum_points / cum_credits if cum_credits > 0 else 0.0

        # Count passed/failed
        subjects_passed = sum(1 for g in filtered_grades if g.status == "Passed")
        subjects_failed = sum(1 for g in filtered_grades if g.status == "Is Suspended")
        earned_credits = sum(g.credits for g in filtered_grades if g.status == "Passed")

        # Grade breakdown
        grade_breakdown = {}
        for g in filtered_grades:
            if g.total >= 8:
                grade_breakdown['A (8-10)'] = grade_breakdown.get('A (8-10)', 0) + 1
            elif g.total >= 6.5:
                grade_breakdown['B (6.5-7.9)'] = grade_breakdown.get('B (6.5-7.9)', 0) + 1
            elif g.total >= 5:
                grade_breakdown['C (5-6.4)'] = grade_breakdown.get('C (5-6.4)', 0) + 1
            elif g.total > 0:
                grade_breakdown['D/F (<5)'] = grade_breakdown.get('D/F (<5)', 0) + 1

        return GPASummary(
            term=None,
            term_gpa=round(term_gpa, 2),
            cumulative_gpa=round(cumulative_gpa, 2),
            total_credits=total_credits,
            earned_credits=earned_credits,
            subjects_passed=subjects_passed,
            subjects_failed=subjects_failed,
            grade_breakdown=grade_breakdown,
            by_term=by_term,
            excluded_subjects=excluded_codes
        )

    def format_for_discord(self, grades: List[GradeItem], gpa_summary: GPASummary, title: str = "Grades") -> str:
        """
        Format grade data for Discord message

        Args:
            grades: List of grade items
            gpa_summary: GPA summary
            title: Message title

        Returns:
            Formatted Discord message string
        """
        lines = [
            f"📊 **{title}**",
            "",
            str(gpa_summary),
            "",
            "**Subject Grades:**",
        ]

        for grade in grades[:25]:  # Discord limit
            status_emoji = {
                'Passed': '✅',
                'Is Suspended': '❌',
                'In Progress': '⏳'
            }.get(grade.status, '❓')

            # Grade letter
            if grade.total >= 8.5:
                grade_letter = 'A'
            elif grade.total >= 7.0:
                grade_letter = 'B'
            elif grade.total >= 5.5:
                grade_letter = 'C'
            elif grade.total >= 4.0:
                grade_letter = 'D'
            elif grade.total > 0:
                grade_letter = 'F'
            else:
                grade_letter = '-'

            lines.append(
                f"{status_emoji} **{grade.subject_code}** - {grade.subject_name[:30]}...\n"
                f"   Total: {grade.total}/10 ({grade_letter}) | Mid: {grade.mid_term} | Final: {grade.final}\n"
                f"   Credits: {grade.credits} | 4.0 Scale: {grade.grade_4scale}"
            )

        if len(grades) > 25:
            lines.append(f"\n_... and {len(grades) - 25} more subjects_")

        return "\n".join(lines)

    def _convert_to_4scale(self, grade_10scale: float) -> float:
        """
        Convert 10-point scale to 4-point scale

        Args:
            grade_10scale: Grade on 10-point scale

        Returns:
            Grade on 4-point scale
        """
        if grade_10scale >= 9.0:
            return 4.0
        elif grade_10scale >= 8.0:
            return 3.5
        elif grade_10scale >= 7.0:
            return 3.0
        elif grade_10scale >= 6.0:
            return 2.0
        elif grade_10scale >= 5.0:
            return 1.0
        elif grade_10scale >= 4.0:
            return 0.5
        else:
            return 0.0

    def _is_excluded_subject(self, subject_code: str) -> bool:
        """Check if subject should be excluded from GPA"""
        return any(subject_code.startswith(prefix) for prefix in self.exclude_subjects)
