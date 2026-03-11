# Architecture Specification
## Attendance Tracking & Grade/Score Viewing Features

**Version:** 1.0
**Date:** 2026-03-11
**Architect:** Winston (BMAD AI Agent) + Admin
**Document Status:** Draft
**Related Documents:** Main ARCHITECTURE.md, PRD.md

---

## Table of Contents

1. [Document Information](#document-information)
2. [Feature Overview](#feature-overview)
3. [Architecture Context](#architecture-context)
4. [FAP Portal Analysis](#fap-portal-analysis)
5. [Component Design](#component-design)
6. [Data Models](#data-models)
7. [Parser Implementation](#parser-implementation)
8. [Discord Commands](#discord-commands)
9. [Background Tasks](#background-tasks)
10. [Notification System](#notification-system)
11. [Database Schema](#database-schema)
12. [API Integration](#api-integration)
13. [Implementation Sequence](#implementation-sequence)

---

## Document Information

| Field | Value |
|-------|-------|
| **Document Name** | Attendance & Grades Architecture |
| **Version** | 1.0 |
| **Status** | Draft |
| **Author** | Winston (Architect Agent) |
| **Features** | Attendance Tracking, Grade/Score Viewing |

---

## Feature Overview

### FA1: Attendance Tracking

| Feature | Description | Priority |
|---------|-------------|----------|
| View History | Xem lịch sử điểm danh theo kỳ/tuần | P1 |
| Attendance % | Tính toán % đi học | P1 |
| Absence Warnings | Cảnh báo vắng học quá nhiều | P1 |
| Attendance Status | Xem trạng thái điểm danh hiện tại | P0 |

### FA2: Grade/Score Viewing

| Feature | Description | Priority |
|---------|-------------|----------|
| Exam Scores | Xem điểm thi các môn | P0 |
| GPA Calculation | Tính toán GPA (theo kỳ & tích lũy) | P1 |
| Grade Summary | Xem bảng điểm tổng hợp | P0 |
| Grade Notifications | Thông báo khi có điểm mới | P0 |

---

## Architecture Context

### Existing Pattern (Schedule & Exam)

```
┌─────────────────────────────────────────────────────────────┐
│                    EXISTING PATTERN                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Discord Command  →  FAPAuth  →  FAPAutoLogin  →  FAP      │
│       ↓                ↓              ↓             ↓        │
│  Parser          HTML Extract    Playwright    Response      │
│       ↓                ↓              ↓             ↓        │
│  Data Item      Parsed Data    Cookies Saved  HTML Table    │
│       ↓                ↓              ↓             ↓        │
│  Discord       Format for     Session      Schedule/Exam    │
│  Response       Discord        Managed         Page         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### New Features Pattern (Same Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                   NEW FEATURES PATTERN                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  /attendance  →  FAPAuth  →  FAPAutoLogin  →  FAP          │
│  /grades          ↓              ↓             ↓             │
│  /gpa         Parser      Playwright    Response             │
│                    ↓              ↓             ↓             │
│  Attendance/   Parsed     Cookies      Attendance/           │
│  Grade Data    Data        Saved        Grade Page           │
│                    ↓              ↓             ↓             │
│  Discord     Format for    Session      Calculated           │
│  Response     Discord      Managed       Data                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Insight

**Điểm khác biệt CHỈ nằm ở:**
1. **URL FAP khác nhau** (Schedule vs Grade vs Attendance page)
2. **Parser khác nhau** (HTML table structure khác)
3. **Data Models khác nhau** (ScheduleItem vs GradeItem vs AttendanceItem)
4. **Calculations khác nhau** (GPA calculation, % attendance)

**Kiến trúc GIỐNG HOÀN TOÀN:**
- Authentication flow
- Session management
- Discord command structure
- Background task pattern
- Notification system

---

## FAP Portal Analysis

### FAP Grade Page Structure

**URL:** `https://fap.fpt.edu.vn/Grade/StudentGrade.aspx?rollNumber={student_id}&term={term_name}&course={course_id}`

**URL Parameters:**
- `rollNumber`: Student ID (e.g., SE203055)
- `term`: Term name (e.g., Fall2025, Spring2025, Summer2025)
- `course`: Course ID (e.g., 55959 for PRO192)

**Login Requirements:**
- Must be authenticated via FeID
- Session cookie required

**Page Structure (from actual HTML):**

```html
<!-- Grade Page Structure -->
<h2>Grade report for <span id="ctl00_mainContent_lblRollNumber">Nguyễn Ngọc Phúc (SE203055)</span></h2>

<!-- Term Selector -->
<div id="ctl00_mainContent_divTerm">
    <a href="?rollNumber=SE203055&term=Fall2024">Fall2024</a>
    <a href="?rollNumber=SE203055&term=Spring2025">Spring2025</a>
    <b>Fall2025</b>  <!-- Current term -->
</div>

<!-- Course Selector -->
<div id="ctl00_mainContent_divCourse">
    <a href="?rollNumber=SE203055&term=Fall2025&course=55340">Discrete mathematics (MAD101)</a>
    <a href="?rollNumber=SE203055&term=Fall2025&course=55959">Operating Systems (OSG202)</a>
    <b>Object-Oriented Programming (PRO192)</b>  <!-- Selected course -->
</div>

<!-- Grade Table -->
<div id="ctl00_mainContent_divGrade">
    <table>
        <thead>
            <tr>
                <th>Grade category</th>
                <th>Grade item</th>
                <th>Weight</th>
                <th>Value</th>
                <th>Comment</th>
            </tr>
        </thead>
        <tbody>
            <!-- Labs -->
            <tr>
                <td rowspan="7">Labs</td>
                <td>Lab 1</td>
                <td>1.7 %</td>
                <td>10</td>
                <td></td>
            </tr>
            <tr>
                <td>Lab 2</td>
                <td>1.7 %</td>
                <td>10</td>
                <td></td>
            </tr>
            <!-- ... more labs ... -->
            <tr>
                <td>Total</td>
                <td>10.0 %</td>
                <td>9.7</td>
                <td></td>
            </tr>

            <!-- Progress Tests -->
            <tr>
                <td rowspan="3">Progress Tests</td>
                <td>Progress Test 1</td>
                <td>5.0 %</td>
                <td>7.9</td>
                <td></td>
            </tr>
            <!-- ... more tests ... -->

            <!-- Assignment -->
            <tr>
                <td rowspan="2">Assignment</td>
                <td>Assignment</td>
                <td>20.0 %</td>
                <td>8.5</td>
                <td></td>
            </tr>

            <!-- Practical Exam -->
            <tr>
                <td rowspan="2">Practical Exam</td>
                <td>Practical Exam</td>
                <td>30.0 %</td>
                <td>8.0</td>
                <td></td>
            </tr>

            <!-- Final Exam -->
            <tr>
                <td rowspan="2">Final Exam</td>
                <td>Final Exam</td>
                <td>30.0 %</td>
                <td>9.0</td>
                <td></td>
            </tr>
        </tbody>
        <tfoot>
            <tr>
                <td rowspan="2">Course total</td>
                <td>Average</td>
                <td colspan="3">8.5</td>
            </tr>
            <tr>
                <td>Status</td>
                <td colspan="3">Passed / Is Suspended</td>
            </tr>
        </tfoot>
    </table>
</div>
```

### FAP Attendance Page Structure

**URL:** `https://fap.fpt.edu.vn/Report/ViewAttendstudent.aspx?id={student_id}&campus={campus_id}&term={term_id}&course={course_id}`

**URL Parameters:**
- `id`: Student ID (e.g., SE203055)
- `campus`: Campus ID (e.g., 4 for FPTU-HCM)
- `term`: Term ID (e.g., 60 for Spring2026, 59 for Fall2025)
- `course`: Course ID (e.g., 57599 for MAS291)

**Page Structure (from actual HTML):**

```html
<!-- Attendance Page Structure -->
<h2>View attendance for <span id="ctl00_mainContent_lblStudent">Nguyễn Ngọc Phúc (SE203055)</span></h2>

<!-- Term Selector -->
<div id="ctl00_mainContent_divTerm">
    <a href="?id=SE203055&campus=4&term=34">Fall2017</a>
    <a href="?id=SE203055&campus=4&term=35">Spring2018</a>
    <!-- ... more terms ... -->
    <b>Spring2026</b>  <!-- Current term (term=60) -->
</div>

<!-- Course Selector -->
<div id="ctl00_mainContent_divCourse">
    <b>Elementary Japanese 1- A1.1(JPD113)(SE2042,start 05/01/2026)</b>
    <a href="?id=SE203055&campus=4&term=60&course=57582">OOP with Java Lab(LAB211)</a>
    <a href="?id=SE203055&campus=4&term=60&course=57599">Statistics & Probability(MAS291)</a>
    <a href="?id=SE203055&campus=4&term=60&course=57604">Database Systems(DBI202)</a>
</div>

<!-- Attendance Table -->
<table class="table table-bordered table1">
    <thead>
        <tr>
            <th>No.</th>
            <th>Date</th>
            <th>Slot</th>
            <th>Room</th>
            <th>Lecturer</th>
            <th>Group Name</th>
            <th>Attendance status</th>
            <th>Lecturer's comment</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>1</td>
            <td><span class="label label-primary">Monday 05/01/2026</span></td>
            <td><span class="label label-danger">1_(7:00-9:15)</span></td>
            <td>P.112</td>
            <td>TrinhVLB</td>
            <td>SE2042</td>
            <td><font color="green">Present</font></td>
            <td></td>
        </tr>
        <tr>
            <td>2</td>
            <td><span class="label label-primary">Thursday 08/01/2026</span></td>
            <td><span class="label label-danger">1_(7:00-9:15)</span></td>
            <td>P.112</td>
            <td>TrinhVLB</td>
            <td>SE2042</td>
            <td><font color="green">Present</font></td>
            <td></td>
        </tr>
        <tr>
            <td>3</td>
            <td><span class="label label-primary">Monday 12/01/2026</span></td>
            <td><span class="label label-danger">1_(7:00-9:15)</span></td>
            <td>P.112</td>
            <td>TrinhVLB</td>
            <td>SE2042</td>
            <td><font color="red">Absent</font></td>
            <td></td>
        </tr>
        <!-- ... more rows ... -->
        <tr>
            <td>16</td>
            <td><span class="label label-primary">Thursday 12/03/2026</span></td>
            <td><span class="label label-danger">1_(7:00-9:15)</span></td>
            <td>P.112</td>
            <td>TrinhVLB</td>
            <td>SE2042</td>
            <td><font color="black">Future</font></td>
            <td></td>
        </tr>
    </tbody>
    <tfoot>
        <tr>
            <td colspan="7">
                <b>Absent</b>: 15% absent so far (3 absent on 20 total).
            </td>
        </tr>
    </tfoot>
</table>
```

**Attendance Status Values:**
- `<font color="green">Present</font>` - Student attended
- `<font color="red">Absent</font>` - Student was absent
- `<font color="black">Future</font>` - Class hasn't happened yet

### FAP Grade Component Breakdown

| Component | Structure | Notes |
|-----------|-----------|-------|
| Grade Category | Column 1 (rowspan) | Labs, Progress Tests, Assignment, Practical Exam, Final Exam, etc. |
| Grade Item | Column 2 | Lab 1, Lab 2, Progress Test 1, Assignment, etc. |
| Weight | Column 3 | Percentage weight (e.g., "1.7 %", "30.0 %") |
| Value | Column 4 | Score (0-10 scale), empty if not graded |
| Comment | Column 5 | Lecturer comments (e.g., "Đình chỉ thi do vi phạm Nội quy thi") |
| Course Total | Footer | Average score and Status (Passed/Is Suspended) |

### FAP Attendance Component Breakdown

| Component | Structure | Notes |
|-----------|-----------|-------|
| No. | Column 1 | Row number (1, 2, 3, ...) |
| Date | Column 2 | Full date with day name (e.g., "Monday 05/01/2026") |
| Slot | Column 3 | Slot number with time (e.g., "1_(7:00-9:15)") |
| Room | Column 4 | Room number (e.g., "P.112") |
| Lecturer | Column 5 | Lecturer code (e.g., "TrinhVLB") |
| Group Name | Column 6 | Class group (e.g., "SE2042") |
| Attendance Status | Column 7 | Present/Absent/Future with color |
| Lecturer's Comment | Column 8 | Empty or comments |
| Summary | Footer | "15% absent so far (3 absent on 20 total)" |

---

## Component Design

### C8: Attendance Service

**Purpose:** Manages attendance data fetching, parsing, and calculation

**File:** `scraper/attendance_service.py`

```python
# Constants
MAX_RECENT_TERMS = 10  # Only show 10 most recent terms
# Term ID reference (higher ID = more recent)
# Spring2026 = 60, Fall2025 = 59, Summer2025 = 58, Spring2025 = 57, Fall2024 = 56
ESTIMATED_CURRENT_TERM_ID = 60

class AttendanceService:
    """
    Attendance Service for FAP Discord Bot
    Handles attendance tracking, % calculation, and absence warnings
    """

    def __init__(self, auth: FAPAuth):
        self.auth = auth
        self.parser = AttendanceParser()
        self.cache = {}  # Simple in-memory cache
        self.student_id = None  # Will be extracted from auth
        self.campus_id = 4     # Default: FPTU-HCM

    async def get_terms(self) -> List[dict]:
        """
        Get list of 10 most recent available terms

        Returns:
            List of term dicts with keys: id, name, is_current
            Ordered by newest first
        """
        # Fetch default page (no params) to get all terms
        html = await self.auth.fetch_attendance()
        all_terms = self.parser.extract_terms(html)

        # Filter to 10 most recent by ID
        recent_terms = sorted(
            all_terms,
            key=lambda t: int(t.get('id', 0)) if t.get('id', '').isdigit() else 0,
            reverse=True
        )[:MAX_RECENT_TERMS]

        return recent_terms

    async def get_courses(self, term_id: str) -> List[dict]:
        """
        Get list of courses for a specific term

        Args:
            term_id: Term ID (e.g., "60" for Spring2026)

        Returns:
            List of course dicts with keys: course_id, code, name, is_current
        """
        # Check cache first
        cache_key = f"courses_{term_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Fetch attendance page for specific term (no course selected)
        html = await self.auth.fetch_attendance(term=term_id)
        courses = self.parser.extract_courses(html)

        # Cache and return
        self.cache[cache_key] = courses
        return courses

    async def get_attendance(self, term: str = None, course: str = None) -> List[AttendanceItem]:
        """
        Fetch attendance data from FAP

        Args:
            term: Term ID (e.g., "60" for Spring2026)
            course: Course ID (e.g., "57599" for MAS291)

        Returns:
            List of AttendanceItem objects
        """
        html = await self.auth.fetch_attendance(
            student_id=self.student_id,
            campus=self.campus_id,
            term=term,
            course=course
        )

        return self.parser.parse_attendance(html)

    async def get_attendance_percentage(self, term: str = None) -> AttendancePercentage:
        """
        Calculate attendance percentage for a term

        Returns:
            AttendancePercentage with total, present, absent, %
        """

    async def get_absence_warnings(self) -> List[AbsenceWarning]:
        """
        Get subjects with excessive absences

        Returns:
            List of AbsenceWarning objects
        """

    async def get_attendance_history(self, user_id: str) -> List[AttendanceItem]:
        """
        Get historical attendance from database

        Returns:
            List of past attendance records
        """
```

### C9: Grade Service

**Purpose:** Manages grade data fetching, parsing, and GPA calculation

**File:** `scraper/grade_service.py`

```python
class GradeService:
    """
    Grade Service for FAP Discord Bot
    Handles grade fetching, GPA calculation, and grade tracking
    """

    def __init__(self, auth: FAPAuth):
        self.auth = auth
        self.parser = GradeParser()
        self.cache = {}
        self.roll_number = None  # Will be extracted from auth

    async def get_terms(self) -> List[dict]:
        """
        Get list of 10 most recent terms with available grades

        Returns:
            List of term dicts with keys: id, name, is_current
            Ordered by newest first
        """
        # Fetch default grade page (no params) to get all terms
        html = await self.auth.fetch_grades()

        # Parse terms from the page
        soup = BeautifulSoup(html, 'html.parser')
        terms = []

        term_container = soup.find('div', {'id': 'ctl00_mainContent_divTerm'})
        if not term_container:
            return terms

        # Extract terms from <a> tags and current term
        for td in term_container.find_all('td'):
            a_tag = td.find('a')
            if a_tag:
                href = a_tag.get('href', '')
                term_name = a_tag.get_text(strip=True)
                # Term name is directly in URL (e.g., "Fall2025", "Spring2026")
                if term_name:
                    terms.append({
                        'id': term_name,  # For grades, term_id = term_name
                        'name': term_name,
                        'is_current': False
                    })
            else:
                # Current term (no link)
                term_name = td.get_text(strip=True)
                if term_name:
                    terms.append({
                        'id': term_name,
                        'name': term_name,
                        'is_current': True
                    })

        # Sort and return 10 most recent
        # Terms are ordered Fall→Summer→Spring in FAP, need custom sort
        recent_terms = self._sort_terms_by_recency(terms)[:10]

        return recent_terms

    def _sort_terms_by_recency(self, terms: List[dict]) -> List[dict]:
        """
        Sort terms by recency (newest first)

        FAP term naming: Fall2025, Summer2025, Spring2025, Fall2024...
        We need to parse year and season to sort correctly.
        """
        def term_key(term):
            name = term['name']
            # Parse term name to extract year and season
            import re
            match = re.match(r'(Fall|Summer|Spring)(\d{4})', name)
            if match:
                season, year = match.groups()
                year = int(year)

                # Season order for sorting (later seasons = more recent)
                season_order = {'Spring': 3, 'Summer': 2, 'Fall': 1}
                # Adjust: If Fall2025, next is Spring2026 (newer)
                # We want: Spring2026 > Fall2025 > Summer2025 > Spring2025
                # Use inverse: Spring=3, Summer=2, Fall=1, but add year weighting
                return (year * 10) + season_order.get(season, 0)

            return 0  # Default for unrecognized terms

        return sorted(terms, key=term_key, reverse=True)

    async def get_grades(self, term: str = None) -> List[GradeItem]:
        """
        Fetch grades from FAP

        Args:
            term: Term identifier (e.g., "20261", "20262"), None for current

        Returns:
            List of GradeItem objects
        """

    async def get_gpa(self, term: str = None, exclude: List[str] = None) -> GPASummary:
        """
        Calculate GPA

        Args:
            term: Term for term GPA, None for cumulative
            exclude: List of subject codes to exclude (e.g., ["PE101", "MUS101"])

        Returns:
            GPASummary with term_gpa, cumulative_gpa, breakdown
        """

    async def get_grade_summary(self, term: str = None) -> GradeSummary:
        """
        Get complete grade summary with statistics

        Returns:
            GradeSummary with grades, GPA, statistics
        """

    async def detect_new_grades(self) -> List[GradeItem]:
        """
        Detect newly posted grades since last check

        Returns:
            List of new GradeItem objects
        """
```

---

## Data Models

### AttendanceItem

```python
@dataclass
class AttendanceItem:
    """Attendance record for a single class session"""
    no: int                          # Row number (1, 2, 3, ...)
    subject_code: str                # e.g., "JP113", "MAS291"
    subject_name: str                # e.g., "Elementary Japanese 1- A1.1", "Statistics & Probability"
    room: str                        # Room number (e.g., "P.112")
    day: str                         # "Monday", "Thursday", etc.
    date: str                        # "05/01/2026" (DD/MM/YYYY format)
    slot: int                        # Slot number (1-8)
    start_time: str                  # "7:00"
    end_time: str                    # "9:15"
    attendance_status: str           # "present", "absent", "future"
    lecturer: str = ""               # Lecturer code (e.g., "TrinhVLB")
    group_name: str = ""             # Class group (e.g., "SE2042")
    credits: int = 0                 # Subject credits (for calculation)

    @property
    def is_present(self) -> bool:
        return self.attendance_status.lower() == "present"

    @property
    def is_absent(self) -> bool:
        return self.attendance_status.lower() == "absent"

    @property
    def is_future(self) -> bool:
        return self.attendance_status.lower() == "future"

    @property
    def emoji(self) -> str:
        if self.is_present:
            return "✅"
        elif self.is_absent:
            return "❌"
        else:
            return "⏳"
```

### AttendancePercentage

```python
@dataclass
class AttendancePercentage:
    """Attendance percentage calculation"""
    term: str
    total_classes: int               # Total scheduled classes
    present_classes: int             # Classes attended
    absent_classes: int              # Classes missed
    pending_classes: int             # Classes not yet marked
    percentage: float                # % of classes attended
    by_subject: Dict[str, SubjectAttendance]  # Breakdown by subject

    @property
    def attendance_rate(self) -> str:
        return f"{self.percentage:.1f}%"

    @property
    def status(self) -> str:
        if self.percentage >= 80:
            return "✅ Good"
        elif self.percentage >= 60:
            return "⚠️ Warning"
        else:
            return "❌ Critical"
```

### AbsenceWarning

```python
@dataclass
class AbsenceWarning:
    """Warning for excessive absences"""
    subject_code: str
    subject_name: str
    absences: int                    # Number of absences
    total_classes: int               # Total classes for subject
    attendance_percentage: float
    severity: str                    # "warning", "critical"
    recommendation: str              # Action to take

    @property
    def emoji(self) -> str:
        return "🔴" if self.severity == "critical" else "🟡"
```

### GradeItem

```python
@dataclass
class GradeItem:
    """Grade record for a subject (course summary)"""
    no: int                          # Row number
    subject_code: str                # e.g., "PRO192", "MAD101"
    subject_name: str                # Full subject name
    credits: int                     # 1-4 credits
    total_grade: Optional[float]     # Course average (0-10)
    status: str                      # "Passed", "Is Suspended", "In Progress"
    term: str                        # Term name (e.g., "Fall2025")
    details: List[GradeDetailItem] = None  # Detailed grade breakdown

    @property
    def letter_grade(self) -> str:
        """Convert 10-point scale to letter grade"""
        if self.total_grade is None:
            return "N/A"
        if self.total_grade >= 9.0:
            return "A+"
        elif self.total_grade >= 8.5:
            return "A"
        elif self.total_grade >= 8.0:
            return "B+"
        elif self.total_grade >= 7.0:
            return "B"
        elif self.total_grade >= 6.0:
            return "C"
        elif self.total_grade >= 5.0:
            return "D"
        else:
            return "F"

    @property
    def is_passed(self) -> bool:
        return "Passed" in self.status or (self.total_grade is not None and self.total_grade >= 5.0)

    @property
    def grade_points(self) -> Optional[float]:
        """Convert to 4.0 scale for GPA calculation"""
        if self.total_grade is None or not self.is_passed:
            return None
        if self.total_grade >= 9.0:
            return 4.0
        elif self.total_grade >= 8.5:
            return 3.7
        elif self.total_grade >= 8.0:
            return 3.5
        elif self.total_grade >= 7.0:
            return 3.0
        elif self.total_grade >= 6.0:
            return 2.0
        elif self.total_grade >= 5.0:
            return 1.0
        else:
            return 0.0


@dataclass
class GradeDetailItem:
    """Detailed grade item for a single course"""
    category: str                   # e.g., "Labs", "Progress Tests", "Assignment"
    item_name: str                  # e.g., "Lab 1", "Progress Test 1"
    weight: float                   # Weight percentage (e.g., 1.7, 30.0)
    value: Optional[float]           # Score (0-10), None if not graded
    comment: str                    # Lecturer comment
```

### GPASummary

```python
@dataclass
class GPASummary:
    """GPA calculation summary"""
    term: Optional[str]              # None for cumulative
    term_gpa: Optional[float]        # GPA for specific term
    cumulative_gpa: float            # Cumulative GPA (all terms)
    total_credits: int               # Total credits earned
    earned_credits: int              # Credits with passing grades
    subjects_passed: int             # Number of passed subjects
    subjects_failed: int             # Number of failed subjects
    grade_breakdown: Dict[str, int]  # {"A+": 3, "A": 5, ...}
    by_term: Dict[str, TermGPA]      # Breakdown by term
    excluded_subjects: List[str]      # Subjects excluded from GPA

    def __str__(self) -> str:
        lines = [
            f"📊 **GPA Summary**",
            f"",
        ]

        if self.term:
            lines.append(f"📈 Term GPA ({self.term}): **{self.term_gpa:.2f}** / 4.0" if self.term_gpa else f"📈 Term GPA ({self.term}): N/A")
            lines.append(f"")

        lines.append(f"🎯 Cumulative GPA: **{self.cumulative_gpa:.2f}** / 4.0")
        lines.append(f"")
        lines.append(f"📚 Credits: {self.earned_credits}/{self.total_credits}")
        lines.append(f"✅ Passed: {self.subjects_passed}")
        lines.append(f"❌ Failed: {self.subjects_failed}")

        if self.excluded_subjects:
            lines.append(f"")
            lines.append(f"🔹 Excluded: {', '.join(self.excluded_subjects)}")

        return "\n".join(lines)


@dataclass
class TermGPA:
    """GPA information for a single term"""
    term_name: str                   # e.g., "Fall2025"
    term_gpa: float                   # GPA for this term
    credits_attempted: int           # Total credits in term
    credits_earned: int              # Credits with passing grades
    subjects_passed: int             # Number of passed subjects
    subjects_failed: int
```

### GradeSummary

```python
@dataclass
class GradeSummary:
    """Complete grade summary for a term"""
    term: str
    grades: List[GradeItem]
    gpa_summary: GPASummary
    average_grade: float
    highest_grade: GradeItem
    lowest_grade: GradeItem
    pending_subjects: List[str]     # Subjects without grades
```

---

## Parser Implementation

### AttendanceParser

**File:** `scraper/attendance_parser.py`

```python
class AttendanceParser:
    """Parse attendance data from FAP attendance page HTML"""

    def parse_attendance(self, html: str) -> List[AttendanceItem]:
        """
        Extract attendance from attendance table

        Args:
            html: HTML from ViewAttendstudent.aspx page

        Returns:
            List of AttendanceItem objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        attendance_items = []

        # Find the attendance table
        table = soup.find('table', class_='table table-bordered table1')
        if not table:
            return attendance_items

        rows = table.find_all('tr')[1:]  # Skip header

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:
                try:
                    # Parse attendance status from font color
                    status_elem = cols[6].find('font')
                    if status_elem:
                        color = status_elem.get('color', '').lower()
                        status_text = status_elem.get_text(strip=True).lower()

                        if color == 'green' or 'present' in status_text:
                            status = 'present'
                        elif color == 'red' or 'absent' in status_text:
                            status = 'absent'
                        elif color == 'black' or 'future' in status_text:
                            status = 'future'
                        else:
                            status = 'pending'
                    else:
                        status = 'pending'

                    # Parse date from label (e.g., "Monday 05/01/2026")
                    date_text = cols[1].get_text(strip=True)
                    day_name, date = self._parse_date(date_text)

                    # Parse slot (e.g., "1_(7:00-9:15)")
                    slot_text = cols[2].get_text(strip=True)
                    slot, start_time, end_time = self._parse_slot(slot_text)

                    # Parse course info from link text or use what we have
                    # Get course name from page title or elsewhere
                    course_name = self._extract_course_name(soup)

                    item = AttendanceItem(
                        no=int(cols[0].get_text(strip=True)),
                        subject_code=course_name.split('(')[1].split(')')[0] if '(' in course_name else '',
                        subject_name=course_name.split('(')[0].strip() if '(' in course_name else course_name,
                        room=cols[3].get_text(strip=True),
                        day=day_name,
                        date=date,
                        slot=slot,
                        start_time=start_time,
                        end_time=end_time,
                        attendance_status=status,
                        credits=3  # Default, can be extracted from course page
                    )
                    attendance_items.append(item)
                except (ValueError, IndexError) as e:
                    continue

        return attendance_items

    def extract_terms(self, html: str) -> List[dict]:
        """
        Extract all available terms from the attendance page

        Args:
            html: HTML from ViewAttendstudent.aspx

        Returns:
            List of term dicts with keys: id, name, is_current
        """
        soup = BeautifulSoup(html, 'html.parser')
        terms = []

        # Find term container
        term_container = soup.find('div', {'id': 'ctl00_mainContent_divTerm'})
        if not term_container:
            return terms

        # Find all <td> elements in term table
        for td in term_container.find_all('td'):
            # Check if it's a link (not current term)
            a_tag = td.find('a')
            if a_tag:
                href = a_tag.get('href', '')
                term_name = a_tag.get_text(strip=True)
                # Extract term_id from URL parameter
                term_id = self._extract_url_param(href, 'term')
                if term_id:
                    terms.append({
                        'id': term_id,
                        'name': term_name,
                        'is_current': False
                    })
            else:
                # No link = current term
                term_name = td.get_text(strip=True)
                # Try to find term_id from the page URL or adjacent elements
                # For current term, we might need to extract from page content
                # or use a special marker
                terms.append({
                    'id': 'current',
                    'name': term_name,
                    'is_current': True
                })

        return terms

    def extract_courses(self, html: str) -> List[dict]:
        """
        Extract all available courses for the current term

        Args:
            html: HTML from ViewAttendstudent.aspx

        Returns:
            List of course dicts with keys: course_id, code, name, is_current
        """
        import re
        soup = BeautifulSoup(html, 'html.parser')
        courses = []

        # Find course container
        course_container = soup.find('div', {'id': 'ctl00_mainContent_divCourse'})
        if not course_container:
            return courses

        # Parse course text: "Statistics & Probability(MAS291)(SE2043,start 05/01/2026)"
        def parse_course_text(text):
            match = re.match(r'(.+?)\s*\(([A-Z]{3}\d{3})\)', text)
            if match:
                return match.group(2), match.group(1).strip()  # code, name
            return None, text  # code not found

        # Find all <td> elements in course table
        for td in course_container.find_all('td'):
            # Check if it's a link (not current course)
            a_tag = td.find('a')
            if a_tag:
                href = a_tag.get('href', '')
                text = a_tag.get_text(strip=True)

                code, name = parse_course_text(text)
                if code:
                    course_id = self._extract_url_param(href, 'course')
                    if course_id:
                        courses.append({
                            'course_id': course_id,
                            'code': code,
                            'name': name,
                            'is_current': False
                        })
            else:
                # No link = current course
                text = td.get_text(strip=True)
                code, name = parse_course_text(text)
                if code:
                    courses.append({
                        'course_id': 'current',
                        'code': code,
                        'name': name,
                        'is_current': True
                    })

        return courses

    def _extract_url_param(self, url: str, param_name: str) -> str:
        """
        Extract parameter value from URL query string

        Args:
            url: URL string (e.g., "?id=SE203055&campus=4&term=60")
            param_name: Parameter name to extract

        Returns:
            Parameter value or empty string
        """
        from urllib.parse import urlparse, parse_qs

        try:
            parsed = urlparse(url)
            if parsed.query:
                params = parse_qs(parsed.query)
                return params.get(param_name, [''])[0]
        except Exception:
            pass

        return ''

    def _parse_date(self, date_text: str) -> Tuple[str, str]:
        """
        Parse date text to extract day name and date

        Args:
            date_text: e.g., "Monday 05/01/2026"

        Returns:
            Tuple of (day_name, date) - e.g., ("Monday", "05/01/2026")
        """
        parts = date_text.split()
        if len(parts) >= 2:
            return parts[0], parts[1]
        return '', date_text

    def _parse_slot(self, slot_text: str) -> Tuple[int, str, str]:
        """
        Parse slot text to extract slot number, start time, end time

        Args:
            slot_text: e.g., "1_(7:00-9:15)"

        Returns:
            Tuple of (slot, start_time, end_time)
        """
        # Parse slot number
        slot_match = re.match(r'(\d+)_', slot_text)
        slot = int(slot_match.group(1)) if slot_match else 0

        # Parse time range
        time_match = re.search(r'\((\d+:\d+)-(\d+:\d+)\)', slot_text)
        if time_match:
            return slot, time_match.group(1), time_match.group(2)

        return slot, '', ''

    def _extract_course_name(self, soup) -> str:
        """
        Extract current course name from page

        Args:
            soup: BeautifulSoup object

        Returns:
            Course name string
        """
        # Try to find course name from page title or breadcrumb
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            if 'View attendance for student' in title_text:
                # Try to get from the selected course (in bold)
                course_container = soup.find('div', {'id': 'ctl00_mainContent_divCourse'})
                if course_container:
                    bold_tag = course_container.find('b')
                    if bold_tag:
                        return bold_tag.get_text(strip=True)

        return ''

    def calculate_percentage(self, items: List[AttendanceItem]) -> AttendancePercentage:
        """Calculate attendance statistics"""
        total = len(items)
        present = sum(1 for item in items if item.is_present)
        absent = sum(1 for item in items if item.is_absent)
        pending = sum(1 for item in items if item.is_pending)
        percentage = (present / total * 100) if total > 0 else 0

        # Group by subject
        by_subject = {}
        for item in items:
            if item.subject_code not in by_subject:
                by_subject[item.subject_code] = SubjectAttendance(
                    subject_code=item.subject_code,
                    subject_name=item.subject_name,
                    total=0,
                    present=0,
                    absent=0
                )
            by_subject[item.subject_code].total += 1
            if item.is_present:
                by_subject[item.subject_code].present += 1
            elif item.is_absent:
                by_subject[item.subject_code].absent += 1

        return AttendancePercentage(
            term="current",
            total_classes=total,
            present_classes=present,
            absent_classes=absent,
            pending_classes=pending,
            percentage=percentage,
            by_subject=by_subject
        )

    def generate_warnings(self, percentage: AttendancePercentage) -> List[AbsenceWarning]:
        """Generate absence warnings for subjects with low attendance"""
        warnings = []

        for subject_code, data in percentage.by_subject.items():
            subject_pct = (data.present / data.total * 100) if data.total > 0 else 0

            if subject_pct < 60 and data.absent >= 2:
                warnings.append(AbsenceWarning(
                    subject_code=subject_code,
                    subject_name=data.subject_name,
                    absences=data.absent,
                    total_classes=data.total,
                    attendance_percentage=subject_pct,
                    severity="critical",
                    recommendation="Contact lecturer immediately!"
                ))
            elif subject_pct < 80 and data.absent >= 1:
                warnings.append(AbsenceWarning(
                    subject_code=subject_code,
                    subject_name=data.subject_name,
                    absences=data.absent,
                    total_classes=data.total,
                    attendance_percentage=subject_pct,
                    severity="warning",
                    recommendation="Be careful with future absences"
                ))

        return warnings

    def _parse_slot(self, slot_text: str) -> int:
        """Parse slot from text like '1-2' or 'S1'"""
        if '-' in slot_text:
            return int(slot_text.split('-')[0])
        elif slot_text.startswith('S'):
            return int(slot_text[1:])
        return 0

    def _extract_credits(self, subject_elem) -> int:
        """Extract credits from subject name or another source"""
        # This may need to be fetched from another page or parsed differently
        # For now, default to 3
        return 3
```

### GradeParser

**File:** `scraper/grade_parser.py`

```python
class GradeParser:
    """Parse grade data from FAP grade page HTML"""

    def parse_grades(self, html: str) -> List[GradeItem]:
        """
        Extract grades from grade table

        Args:
            html: HTML from grade page

        Returns:
            List of GradeItem objects (one per course)
        """
        soup = BeautifulSoup(html, 'html.parser')
        grades = []

        # First, get the list of courses from the course selector
        course_div = soup.find('div', {'id': 'ctl00_mainContent_divCourse'})
        if not course_div:
            return grades

        # Parse each course link
        course_links = course_div.find_all('a')
        for link in course_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Extract course info from link text: "Subject Name (CODE)(Class, start date)"
            # Example: "Discrete mathematics (MAD101)(IS2002, from 08/09/2025 - 13/11/2025)"
            match = re.match(r'(.+?)\s+\(([A-Z]{3}\d{3})\)', text)
            if match:
                subject_name = match.group(1).strip()
                subject_code = match.group(2)

                # Check if this course is selected (has <b> tag)
                is_selected = link.parent.name == 'b' or link.find('b') is not None

                if is_selected:
                    # This is the selected course, parse the grade table
                    grade_div = soup.find('div', {'id': 'ctl00_mainContent_divGrade'})
                    if grade_div:
                        grade_table = grade_div.find('table')
                        if grade_table:
                            # Parse the grade table to get course average
                            course_average, status = self._parse_course_summary(grade_table)

                            # Create GradeItem for this course
                            grade = GradeItem(
                                no=len(grades) + 1,
                                subject_code=subject_code,
                                subject_name=subject_name,
                                credits=self._extract_credits(text),
                                midterm_grade=None,  # Would need to parse from grade items
                                final_grade=None,
                                total_grade=course_average,
                                status=status,
                                term=self._extract_term(soup)
                            )
                            grades.append(grade)

        return grades

    def parse_grade_details(self, html: str) -> List[GradeDetailItem]:
        """
        Parse detailed grade breakdown for a single course

        Args:
            html: HTML from grade page with specific course selected

        Returns:
            List of grade detail items (labs, tests, assignments, exams)
        """
        soup = BeautifulSoup(html, 'html.parser')
        details = []

        grade_div = soup.find('div', {'id': 'ctl00_mainContent_divGrade'})
        if not grade_div:
            return details

        table = grade_div.find('table')
        if not table:
            return details

        tbody = table.find('tbody')
        if not tbody:
            return details

        rows = tbody.find_all('tr')
        current_category = None

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                # Check if this is a category row (has rowspan)
                first_col = cols[0]
                if first_col.get('rowspan'):
                    current_category = first_col.get_text(strip=True)
                elif first_col.get_text(strip=True) == 'Total':
                    # Skip total rows
                    continue

                # Parse grade item
                item_name = cols[1].get_text(strip=True)
                weight = cols[2].get_text(strip=True)  # e.g., "1.7 %"
                value = cols[3].get_text(strip=True)  # e.g., "10" or empty
                comment = cols[4].get_text(strip=True)

                detail = GradeDetailItem(
                    category=current_category,
                    item_name=item_name,
                    weight=self._parse_weight(weight),
                    value=self._parse_value(value),
                    comment=comment
                )
                details.append(detail)

        return details

    def _parse_course_summary(self, table) -> Tuple[Optional[float], str]:
        """Parse course total from table footer"""
        tfoot = table.find('tfoot')
        if not tfoot:
            return None, "Unknown"

        # Find the average row
        for row in tfoot.find_all('tr'):
            cols = row.find_all('td')
            for col in cols:
                text = col.get_text(strip=True)
                if 'Average' in text:
                    # Next column should have the value
                    idx = cols.index(col)
                    if idx + 1 < len(cols):
                        value_text = cols[idx + 1].get_text(strip=True)
                        try:
                            return float(value_text), ""
                        except ValueError:
                            pass
                elif 'Status' in text:
                    idx = cols.index(col)
                    if idx + 1 < len(cols):
                        return None, cols[idx + 1].get_text(strip=True)

        return None, "Unknown"

    def parse_gpa_summary(self, html: str) -> GPASummary:
        """
        Extract GPA summary from page

        Args:
            html: HTML from grade page

        Returns:
            GPASummary object
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Try to find GPA elements - these may be in specific divs or spans
        term_gpa = self._extract_gpa_value(soup, 'term-gpa') or self._extract_gpa_value(soup, 'ctl00_mainContent_lblTermGPA')
        cumulative_gpa = self._extract_gpa_value(soup, 'cumulative-gpa') or self._extract_gpa_value(soup, 'ctl00_mainContent_lblCumulativeGPA')

        # If not found in HTML, will be calculated from grades
        return GPASummary(
            term=None,
            term_gpa=term_gpa,
            cumulative_gpa=cumulative_gpa or 0.0,
            total_credits=0,
            earned_credits=0,
            subjects_passed=0,
            subjects_failed=0,
            grade_breakdown={},
            by_term={}
        )

    def calculate_gpa(self, grades: List[GradeItem], exclude: List[str] = None) -> GPASummary:
        """
        Calculate GPA from list of grades

        Args:
            grades: List of GradeItem objects
            exclude: Subject codes to exclude from calculation

        Returns:
            GPASummary with calculated values
        """
        exclude = exclude or []
        filtered_grades = [g for g in grades if g.subject_code not in exclude and g.total_grade is not None]

        if not filtered_grades:
            return GPASummary(
                term=None,
                term_gpa=None,
                cumulative_gpa=0.0,
                total_credits=0,
                earned_credits=0,
                subjects_passed=0,
                subjects_failed=0,
                grade_breakdown={},
                by_term={}
            )

        total_credits = sum(g.credits for g in filtered_grades)
        total_points = sum(g.grade_points * g.credits for g in filtered_grades if g.grade_points is not None)

        gpa = total_points / total_credits if total_credits > 0 else 0.0

        passed = sum(1 for g in filtered_grades if g.is_passed)
        failed = sum(1 for g in filtered_grades if not g.is_passed)

        # Grade breakdown
        breakdown = {}
        for grade in filtered_grades:
            letter = grade.letter_grade
            breakdown[letter] = breakdown.get(letter, 0) + 1

        return GPASummary(
            term=filtered_grades[0].term if filtered_grades else None,
            term_gpa=gpa,
            cumulative_gpa=gpa,  # For single term, same as term
            total_credits=total_credits,
            earned_credits=sum(g.credits for g in filtered_grades if g.is_passed),
            subjects_passed=passed,
            subjects_failed=failed,
            grade_breakdown=breakdown,
            by_term={}
        )

    def _parse_grade(self, grade_text: str) -> Optional[float]:
        """Parse grade string to float"""
        if not grade_text or grade_text in ['-', '', 'N/A']:
            return None
        try:
            return float(grade_text)
        except ValueError:
            return None

    def _extract_term(self, soup) -> str:
        """Extract term from page"""
        term_elem = soup.find('span', {'id': 'ctl00_mainContent_lblTerm'})
        if term_elem:
            return term_elem.get_text(strip=True)
        return "current"

    def _extract_gpa_value(self, soup, elem_id: str) -> Optional[float]:
        """Extract GPA value from element"""
        elem = soup.find('span', {'id': elem_id}) or soup.find('div', {'id': elem_id})
        if elem:
            text = elem.get_text(strip=True)
            try:
                return float(text)
            except ValueError:
                pass
        return None
```

---

## Discord Commands

### Attendance Commands

**File:** `bot/commands/attendance.py`

```python
class AttendanceView(discord.ui.View):
    """Interactive view with select menus for term and course selection"""

    def __init__(self, attendance_service, timeout=180):
        super().__init__(timeout=timeout)
        self.attendance_service = attendance_service
        self.selected_term = None
        self.selected_course = None

    async def refresh_menus(self, term_id=None):
        """Refresh select menus based on selection"""
        # Clear existing items
        self.clear_items()

        if term_id:
            # Show courses for selected term
            courses = await self.attendance_service.get_courses(term_id)

            course_select = discord.ui.Select(
                custom_id="attendance_course_select",
                placeholder="Select Course...",
                options=[
                    discord.SelectOption(
                        label=f"{course['code']} - {course['name']}",
                        value=course['course_id'],
                        description=course['name']
                    )
                    for course in courses[:25]  # Max 25
                ],
                row=0
            )
            self.add_item(course_select)

            # Add back button
            back_button = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="← Back to Terms",
                custom_id="attendance_back_to_terms"
            )
            self.add_item(back_button)
        else:
            # Show term selection
            terms = await self.attendance_service.get_terms()

            term_select = discord.ui.Select(
                custom_id="attendance_term_select",
                placeholder="Select Term...",
                options=[
                    discord.SelectOption(
                        label=term['name'],
                        value=term['id'],
                        description=f"Attendance for {term['name']}"
                    )
                    for term in terms  # Already limited to 10 recent terms
                ],
                row=0
            )
            self.add_item(term_select)


class AttendanceCommands(commands.Cog):
    """Attendance slash commands with interactive select menus"""

    def __init__(self, bot, auth: FAPAuth):
        self.bot = bot
        self.auth = auth
        self.attendance_service = AttendanceService(auth)

    @app_commands.command(name="attendance", description="View attendance history")
    async def attendance(self, interaction: discord.Interaction):
        """
        View attendance history with interactive term/course selection

        Shows 10 most recent terms, user can select term → course → view attendance
        """
        await interaction.response.defer()

        try:
            # Create initial view with term selection
            view = AttendanceView(self.attendance_service)
            await view.refresh_menus()

            # Get current attendance (what FAP shows by default)
            summary = await self.attendance_service.get_current_attendance()

            # Create embed
            embed = self.create_attendance_embed(summary)

            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in attendance command: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="attendance-this-term", description="Quick view attendance for current term")
    async def attendance_this_term(self, interaction: discord.Interaction):
        """
        Quick access: Show attendance summary for current/most recent term

        This is a shortcut that:
        1. Auto-detects the most recent term with attendance data
        2. Shows aggregated attendance across all courses in the term
        3. Displays warning if attendance is below 80%
        """
        await interaction.response.defer()

        try:
            # Get the most recent term with attendance data
            terms = await self.attendance_service.get_terms()
            if not terms:
                await interaction.followup.send("❌ No terms found. Please make sure you're logged in to FAP.")
                return

            # Use the most recent term (first in list = highest ID)
            recent_term = terms[0]
            term_id = recent_term['id']

            # Get all courses for this term
            courses = await self.attendance_service.get_courses(term_id)
            if not courses:
                await interaction.followup.send(f"❌ No courses found for {recent_term['name']}.")
                return

            # Fetch attendance for each course and aggregate
            all_items = []
            for course in courses:
                items = await self.attendance_service.get_attendance(
                    term=term_id,
                    course=course['course_id']
                )
                all_items.extend(items)

            if not all_items:
                await interaction.followup.send(f"❌ No attendance data found for {recent_term['name']}.")
                return

            # Calculate overall statistics
            total = len(all_items)
            present = sum(1 for item in all_items if item.is_present)
            absent = sum(1 for item in all_items if item.is_absent)
            future = sum(1 for item in all_items if item.is_future)
            percentage = ((present + future) / (total) * 100) if total > 0 else 0

            # Create embed with term summary
            embed = discord.Embed(
                title=f"📊 Attendance Summary - {recent_term['name']}",
                description=f"Aggregated across {len(courses)} courses",
                color=self._get_color_for_percentage(percentage)
            )

            # Overall statistics
            stats_text = (
                f"**Total:** {total} classes\n"
                f"**Present:** {present} ✅\n"
                f"**Absent:** {absent} ❌\n"
                f"**Future:** {future} ⏳\n"
                f"**Rate:** **{percentage:.1f}%**"
            )
            embed.add_field(name="📈 Overall Statistics", value=stats_text, inline=False)

            # Per-course breakdown
            by_course = {}
            for item in all_items:
                if item.subject_code not in by_course:
                    by_course[item.subject_code] = []
                by_course[item.subject_code].append(item)

            for subject_code, items in sorted(by_course.items()):
                course_present = sum(1 for i in items if i.is_present)
                course_total = len(items)
                course_pct = (course_present / course_total * 100) if course_total > 0 else 0

                status_emoji = "✅" if course_pct >= 80 else "⚠️" if course_pct >= 60 else "❌"

                embed.add_field(
                    name=f"{status_emoji} {subject_code}",
                    value=f"{course_present}/{course_total} ({course_pct:.0f}%)",
                    inline=True
                )

            # Warning if attendance is poor
            if percentage < 80:
                embed.add_field(
                    name="⚠️ Warning",
                    value="Your attendance is below 80%. Please improve to avoid issues!",
                    inline=False
                )

            embed.set_footer(text=f"Type /attendance to view details with course selection")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in attendance-this-term command: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @discord.ui.select(custom_id="attendance_term_select")
    async def term_selected(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle term selection"""
        await interaction.response.defer()

        term_id = select.values[0]
        self.selected_term = term_id

        # Refresh view with courses for selected term
        view = self.view  # Get the parent view
        await view.refresh_menus(term_id=term_id)

        # Update embed with loading message
        embed = discord.Embed(
            title="⏳ Loading...",
            description=f"Fetching courses for {select.options[select.indexes[0]].label}",
            color=discord.Color.yellow()
        )

        await interaction.edit_original(embed=embed, view=view)

        # Fetch courses and update
        try:
            courses = await self.attendance_service.get_courses(term_id)

            if courses:
                # Show first course by default
                first_course = courses[0]
                summary = await self.attendance_service.get_attendance_for(
                    term_id, first_course['course_id']
                )
                embed = self.create_attendance_embed(summary)
                await interaction.edit_original(embed=embed, view=view)
            else:
                embed = discord.Embed(
                    title="📋 No Courses Found",
                    description=f"No courses found for this term.",
                    color=discord.Color.orange()
                )
                await interaction.edit_original(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error fetching courses: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to load courses: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.edit_original(embed=embed, view=view)

    @discord.ui.select(custom_id="attendance_course_select")
    async def course_selected(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle course selection"""
        await interaction.response.defer()

        course_id = select.values[0]
        term_id = self.selected_term

        # Fetch attendance for selected course
        summary = await self.attendance_service.get_attendance_for(term_id, course_id)

        # Update embed
        embed = self.create_attendance_embed(summary)

        # Refresh view to keep term select
        view = self.view
        await view.refresh_menus(term_id=term_id)

        await interaction.edit_original(embed=embed, view=view)

    @discord.ui.button(custom_id="attendance_back_to_terms")
    async def back_to_terms(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to term selection"""
        await interaction.response.defer()

        # Reset selections
        self.selected_term = None
        self.selected_course = None

        # Refresh view with term selection
        view = self.view
        await view.refresh_menus()

        # Get current attendance
        summary = await self.attendance_service.get_current_attendance()
        embed = self.create_attendance_embed(summary)

        await interaction.edit_original(embed=embed, view=view)

    def create_attendance_embed(self, summary) -> discord.Embed:
        """Create Discord embed from attendance summary"""
        embed = discord.Embed(
            title=f"📊 Attendance - {summary.course['name']} ({summary.term['name']})",
            color=self._get_color_for_percentage(summary.summary.percentage)
        )

        # Add summary stats
        embed.add_field(
            name="📈 Summary",
            value=f"**{summary.summary.present_classes}/{summary.summary.total_classes}** ({summary.summary.attendance_rate})",
            inline=False
        )

        # Add attendance breakdown by date
        if summary.items:
            # Group recent items (last 10)
            recent = sorted(summary.items, key=lambda x: x.date, reverse=True)[:10]

            for item in recent:
                status_emoji = item.emoji
                date_display = f"{item.day} {item.date}"
                embed.add_field(
                    name=f"{status_emoji} {item.subject_code}",
                    value=f"{date_display} • Slot {item.slot}\n{item.start_time}-{item.end_time} • {item.room}",
                    inline=True
                )

        # Add warning if needed
        if summary.summary.percentage < 80:
            embed.add_field(
                name="⚠️ Warning",
                value=f"Attendance below 80%. Please improve!",
                inline=False
            )

        return embed

    def _get_color_for_percentage(self, percentage: float) -> discord.Color:
        if percentage >= 80:
            return discord.Color.green()
        elif percentage >= 60:
            return discord.Color.orange()
        else:
            return discord.Color.red()

    @app_commands.command(name="attendance-percentage", description="View attendance percentage")
    @app_commands.describe(term="Term identifier")
    async def attendance_percentage(
        self,
        interaction: discord.Interaction,
        term: str = None
    ):
        """View attendance percentage"""
        await interaction.response.defer()

        try:
            pct = await self.attendance_service.get_attendance_percentage(term)

            embed = discord.Embed(
                title=f"📊 Attendance Percentage - {pct.term}",
                color=self._get_color_for_percentage(pct.percentage)
            )

            embed.add_field(name="Total Classes", value=str(pct.total_classes), inline=True)
            embed.add_field(name="Present", value=str(pct.present_classes), inline=True)
            embed.add_field(name="Absent", value=str(pct.absent_classes), inline=True)
            embed.add_field(name="Percentage", value=pct.attendance_rate, inline=False)
            embed.add_field(name="Status", value=pct.status, inline=False)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")

    @app_commands.command(name="absence-warning", description="Check for absence warnings")
    async def absence_warning(self, interaction: discord.Interaction):
        """Check for absence warnings"""
        await interaction.response.defer()

        try:
            warnings = await self.attendance_service.get_absence_warnings()

            if not warnings:
                await interaction.followup.send("✅ No absence warnings! Keep up the good attendance.")
                return

            embed = discord.Embed(
                title="⚠️ Absence Warnings",
                color=discord.Color.orange()
            )

            for warning in warnings:
                embed.add_field(
                    name=f"{warning.emoji} {warning.subject_code}",
                    value=f"{warning.absent_classes}/{warning.total_classes} absent ({warning.attendance_percentage:.0f}%)\n{warning.recommendation}",
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")

    def _get_color_for_percentage(self, percentage: float) -> discord.Color:
        if percentage >= 80:
            return discord.Color.green()
        elif percentage >= 60:
            return discord.Color.orange()
        else:
            return discord.Color.red()


def setup(bot):
    """Setup function for cog"""
    # Will be called from main bot setup
    pass
```

### Grade Commands

**File:** `bot/commands/grade.py`

```python
class GradeCommands(commands.Cog):
    """Grade slash commands"""

    def __init__(self, bot, auth: FAPAuth):
        self.bot = bot
        self.auth = auth
        self.grade_service = GradeService(auth)

    @app_commands.command(name="grades", description="View grades")
    @app_commands.describe(term="Term identifier (e.g., 20261, 20262)")
    async def grades(
        self,
        interaction: discord.Interaction,
        term: str = None
    ):
        """View grades"""
        await interaction.response.defer()

        try:
            grades = await self.grade_service.get_grades(term)

            if not grades:
                await interaction.followup.send("No grades found.")
                return

            embed = discord.Embed(
                title=f"📊 Grades - {grades[0].term if grades else 'Current'}",
                color=discord.Color.green()
            )

            for grade in grades:
                status_emoji = "✅" if grade.is_passed else "❌" if grade.total_grade is not None else "⏳"

                value = f"Credits: {grade.credits}"
                if grade.total_grade is not None:
                    value += f" | Grade: **{grade.total_grade:.1f}** ({grade.letter_grade})"
                else:
                    value += " | Grade: *Pending*"

                embed.add_field(
                    name=f"{status_emoji} {grade.subject_code} - {grade.subject_name}",
                    value=value,
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")

    @app_commands.command(name="grades-this-term", description="Quick view grades for current term")
    async def grades_this_term(self, interaction: discord.Interaction):
        """
        Quick access: Show all grades for current/most recent term

        This is a shortcut that:
        1. Auto-detects the most recent term with grades
        2. Shows all courses with their grades
        3. Calculates and displays term GPA
        """
        await interaction.response.defer()

        try:
            # Get the most recent term with grades
            terms = await self.grade_service.get_terms()
            if not terms:
                await interaction.followup.send("❌ No terms found. Please make sure you're logged in to FAP.")
                return

            # Use the most recent term (first in list = highest ID)
            recent_term = terms[0]
            term_name = recent_term['name']

            # Fetch grades for this term
            grades = await self.grade_service.get_grades(term_name)

            if not grades:
                await interaction.followup.send(f"❌ No grades found for {term_name}.")
                return

            # Calculate term GPA
            gpa_summary = await self.grade_service.get_gpa(term_name)

            # Create embed
            embed = discord.Embed(
                title=f"📊 Grades - {term_name}",
                color=discord.Color.green()
            )

            # Add GPA summary at top
            if gpa_summary.term_gpa:
                embed.add_field(
                    name="📈 Term GPA",
                    value=f"**{gpa_summary.term_gpa:.2f}** / 4.0",
                    inline=False
                )

            embed.add_field(
                name="📊 Statistics",
                value=f"**Passed:** {gpa_summary.subjects_passed} | **Failed:** {gpa_summary.subjects_failed}",
                inline=False
            )

            # List all grades
            for grade in grades:
                status_emoji = "✅" if grade.is_passed else "❌" if grade.total_grade is not None else "⏳"

                value = f"Credits: {grade.credits}"
                if grade.total_grade is not None:
                    value += f" | **{grade.total_grade:.1f}** ({grade.letter_grade})"
                else:
                    value += " | *Pending*"

                embed.add_field(
                    name=f"{status_emoji} {grade.subject_code}",
                    value=value,
                    inline=False
                )

            embed.set_footer(text=f"Type /grades to view details with term selection")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in grades-this-term command: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name="gpa", description="Calculate GPA")
    @app_commands.describe(
        term="Term for term GPA (empty for cumulative)",
        exclude="Comma-separated subject codes to exclude (e.g., PE101,MUS101)"
    )
    async def gpa(
        self,
        interaction: discord.Interaction,
        term: str = None,
        exclude: str = None
    ):
        """Calculate GPA"""
        await interaction.response.defer()

        try:
            exclude_list = exclude.split(',') if exclude else None
            gpa_summary = await self.grade_service.get_gpa(term, exclude_list)

            embed = discord.Embed(
                title="📊 GPA Summary",
                color=discord.Color.gold()
            )

            if term:
                embed.add_field(
                    name=f"Term GPA ({term})",
                    value=f"**{gpa_summary.term_gpa:.2f}**" if gpa_summary.term_gpa else "N/A",
                    inline=False
                )

            embed.add_field(
                name="Cumulative GPA",
                value=f"**{gpa_summary.cumulative_gpa:.2f}**",
                inline=False
            )

            embed.add_field(
                name="Credits",
                value=f"{gpa_summary.earned_credits}/{gpa_summary.total_credits}",
                inline=True
            )

            embed.add_field(
                name="Passed",
                value=str(gpa_summary.subjects_passed),
                inline=True
            )

            embed.add_field(
                name="Failed",
                value=str(gpa_summary.subjects_failed),
                inline=True
            )

            # Grade breakdown
            if gpa_summary.grade_breakdown:
                breakdown_text = "\n".join([f"{grade}: {count}" for grade, count in sorted(gpa_summary.grade_breakdown.items())])
                embed.add_field(name="Grade Distribution", value=breakdown_text, inline=False)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")

    @app_commands.command(name="grade-summary", description="View complete grade summary")
    @app_commands.describe(term="Term identifier")
    async def grade_summary(
        self,
        interaction: discord.Interaction,
        term: str = None
    ):
        """View complete grade summary"""
        await interaction.response.defer()

        try:
            summary = await self.grade_service.get_grade_summary(term)

            embed = discord.Embed(
                title=f"📊 Grade Summary - {summary.term}",
                color=discord.Color.blue()
            )

            # GPA section
            embed.add_field(
                name="GPA",
                value=f"**{summary.gpa_summary.term_gpa:.2f}**" if summary.gpa_summary.term_gpa else "N/A",
                inline=True
            )

            embed.add_field(
                name="Average",
                value=f"**{summary.average_grade:.2f}**" if summary.average_grade else "N/A",
                inline=True
            )

            # Top and bottom performers
            if summary.highest_grade:
                embed.add_field(
                    name="🏆 Highest",
                    value=f"{summary.highest_grade.subject_code}: {summary.highest_grade.total_grade}",
                    inline=True
                )

            if summary.lowest_grade:
                embed.add_field(
                    name="📉 Lowest",
                    value=f"{summary.lowest_grade.subject_code}: {summary.lowest_grade.total_grade}",
                    inline=True
                )

            # Pending subjects
            if summary.pending_subjects:
                embed.add_field(
                    name="⏳ Pending Grades",
                    value=", ".join(summary.pending_subjects[:5]),
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")
```

---

## Background Tasks

### Grade Monitoring Task

**File:** `bot/tasks/grade_monitor.py`

```python
class GradeMonitor:
    """Background task to monitor for new grades"""

    def __init__(self, bot, grade_service: GradeService, notification_service):
        self.bot = bot
        self.grade_service = grade_service
        self.notification_service = notification_service
        self.last_check = None
        self.known_grades = set()

    async def start(self):
        """Start grade monitoring"""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        self.scheduler = AsyncIOScheduler()

        # Check every hour
        self.scheduler.add_job(
            self.check_grades,
            'interval',
            hours=1,
            id='grade_check'
        )

        self.scheduler.start()

    async def check_grades(self):
        """Check for new grades"""
        try:
            grades = await self.grade_service.get_grades()

            # Detect new grades
            new_grades = []
            for grade in grades:
                grade_key = f"{grade.term}_{grade.subject_code}"
                if grade_key not in self.known_grades and grade.total_grade is not None:
                    self.known_grades.add(grade_key)
                    new_grades.append(grade)

            # Send notifications for new grades
            for grade in new_grades:
                await self.notification_service.send_grade_notification(grade)

            self.last_check = datetime.now()

        except Exception as e:
            logger.error(f"Error checking grades: {e}")
```

### Attendance Warnings Task

**File:** `bot/tasks/attendance_monitor.py`

```python
class AttendanceWarningMonitor:
    """Background task to check for attendance warnings"""

    def __init__(self, bot, attendance_service: AttendanceService, notification_service):
        self.bot = bot
        self.attendance_service = attendance_service
        self.notification_service = notification_service
        self.last_check = None

    async def start(self):
        """Start attendance monitoring"""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        self.scheduler = AsyncIOScheduler()

        # Check daily at 20:00
        self.scheduler.add_job(
            self.check_attendance_warnings,
            'cron',
            hour=20,
            minute=0,
            id='attendance_warning_check'
        )

        self.scheduler.start()

    async def check_attendance_warnings(self):
        """Check for attendance warnings"""
        try:
            warnings = await self.attendance_service.get_absence_warnings()

            if warnings:
                await self.notification_service.send_attendance_warning(warnings)

            self.last_check = datetime.now()

        except Exception as e:
            logger.error(f"Error checking attendance warnings: {e}")
```

---

## Notification System

### Grade Notification

```python
async def send_grade_notification(self, grade: GradeItem):
    """Send notification for new grade"""
    embed = discord.Embed(
        title="📊 New Grade Posted!",
        color=discord.Color.green() if grade.is_passed else discord.Color.red()
    )

    embed.add_field(name="Subject", value=f"{grade.subject_code} - {grade.subject_name}", inline=False)
    embed.add_field(name="Grade", value=f"**{grade.total_grade:.1f}** ({grade.letter_grade})", inline=True)
    embed.add_field(name="Credits", value=str(grade.credits), inline=True)
    embed.add_field(name="Status", value="✅ Passed" if grade.is_passed else "❌ Failed", inline=True)

    await self.notification_channel.send(embed=embed)
```

### Attendance Warning Notification

```python
async def send_attendance_warning(self, warnings: List[AbsenceWarning]):
    """Send attendance warning notification"""
    embed = discord.Embed(
        title="⚠️ Attendance Warning",
        color=discord.Color.orange(),
        description="You have attendance issues that need attention:"
    )

    for warning in warnings[:5]:  # Limit to 5
        embed.add_field(
            name=f"{warning.emoji} {warning.subject_code}",
            value=f"{warning.absences}/{warning.total_classes} absent ({warning.attendance_percentage:.0f}%)\n{warning.recommendation}",
            inline=False
        )

    await self.notification_channel.send(embed=embed)
```

---

## Database Schema

### Attendance Table

```sql
CREATE TABLE IF NOT EXISTS attendance_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    subject_code TEXT NOT NULL,
    subject_name TEXT NOT NULL,
    date TEXT NOT NULL,
    slot INTEGER NOT NULL,
    attendance_status TEXT NOT NULL,
    term TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_code, date, slot)
);
```

### Grades Table

```sql
CREATE TABLE IF NOT EXISTS grades_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    subject_code TEXT NOT NULL,
    subject_name TEXT NOT NULL,
    credits INTEGER NOT NULL,
    midterm_grade REAL,
    final_grade REAL,
    total_grade REAL,
    status TEXT NOT NULL,
    term TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_code, term)
);
```

### Grade Notifications Table

```sql
CREATE TABLE IF NOT EXISTS grade_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    subject_code TEXT NOT NULL,
    grade REAL NOT NULL,
    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, subject_code)
);
```

---

## API Integration

### FAPAuth Extension

**Add to `scraper/auth.py`:**

```python
async def fetch_grades(self, roll_number: str = None, term: str = None, course: int = None) -> Optional[str]:
    """
    Fetch grades HTML with auto-refresh on failure

    Args:
        roll_number: Student ID (e.g., "SE203055")
        term: Term name (e.g., "Fall2025", "Spring2026")
        course: Course ID (e.g., 55959 for PRO192)

    Returns:
        HTML content or None if failed
    """
    GRADE_URL = "https://fap.fpt.edu.vn/Grade/StudentGrade.aspx"

    async with _auth_lock:
        await self._ensure_auth()

        # Build URL with parameters
        params = []
        if roll_number:
            params.append(f"rollNumber={roll_number}")
        if term:
            params.append(f"term={term}")
        if course:
            params.append(f"course={course}")

        url = GRADE_URL + ('?' + '&'.join(params) if params else '')

        # Navigate to grade page
        html = await self._auth.fetch_page(url)

        # If failed and auto-refresh enabled, refresh and retry
        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                logger.info("✅ Session refreshed - retrying grade fetch...")
                html = await self._auth.fetch_page(url)

        return html

async def fetch_attendance(self, student_id: str = None, campus: int = None, term: int = None, course: int = None) -> Optional[str]:
    """
    Fetch attendance HTML with auto-refresh

    Args:
        student_id: Student ID (e.g., "SE203055")
        campus: Campus ID (e.g., 4 for FPTU-HCM)
        term: Term ID (e.g., 60 for Spring2026, 59 for Fall2025)
        course: Course ID (e.g., 57599 for MAS291)

    Returns:
        HTML content or None if failed
    """
    ATTENDANCE_URL = "https://fap.fpt.edu.vn/Report/ViewAttendstudent.aspx"

    async with _auth_lock:
        await self._ensure_auth()

        # Build URL with parameters
        params = []
        if student_id:
            params.append(f"id={student_id}")
        if campus:
            params.append(f"campus={campus}")
        if term:
            params.append(f"term={term}")
        if course:
            params.append(f"course={course}")

        url = ATTENDANCE_URL + ('?' + '&'.join(params) if params else '')

        # Navigate to attendance page
        html = await self._auth.fetch_page(url)

        # If failed and auto-refresh enabled, refresh and retry
        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                logger.info("✅ Session refreshed - retrying attendance fetch...")
                html = await self._auth.fetch_page(url)

        return html
```

### FAPAutoLogin Extension

**Add to `scraper/auto_login_feid.py`:**

```python
async def fetch_page(self, url: str) -> str:
    """
    Generic page fetcher using saved cookies

    Args:
        url: URL to fetch

    Returns:
        HTML content or None
    """
    if not Path(self.COOKIES_FILE).exists():
        return None

    # Load cookies and navigate
    # (similar to existing fetch_schedule method)
    ...
```

---

## Implementation Sequence

### Phase 1: Foundation (Week 1)

1. **Data Models** - Create all dataclass models
   - `AttendanceItem`, `AttendancePercentage`, `AbsenceWarning`
   - `GradeItem`, `GPASummary`, `GradeSummary`

2. **Database Schema** - Create tables
   - `attendance_cache`
   - `grades_cache`
   - `grade_notifications`

3. **FAPAuth Extension** - Add fetch methods
   - `fetch_grades()`
   - `fetch_attendance()`

### Phase 2: Parsers (Week 1-2)

4. **AttendanceParser** - Implement parsing
   - Parse attendance from schedule HTML
   - Calculate percentages
   - Generate warnings

5. **GradeParser** - Implement parsing
   - Parse grades from grade HTML
   - Calculate GPA
   - Format summary

### Phase 3: Services (Week 2)

6. **AttendanceService** - Implement service
   - Get attendance data
   - Calculate statistics
   - Generate warnings

7. **GradeService** - Implement service
   - Get grades
   - Calculate GPA
   - Detect new grades

### Phase 4: Commands (Week 2-3)

8. **Attendance Commands** - Implement slash commands
   - `/attendance` - Interactive menu with 10 recent terms + course selection
   - `/attendance-this-term` - **Quick view: aggregate attendance for current term**
   - `/attendance-percentage [term]` - View attendance percentage by term
   - `/absence-warning` - Check for excessive absences

9. **Grade Commands** - Implement slash commands
   - `/grades [term]` - View grades with interactive term selection
   - `/grades-this-term` - **Quick view: grades for current term**
   - `/gpa [term] [--exclude]` - Calculate GPA with exclusion options
   - `/grade-summary [term]`

### Phase 5: Background Tasks (Week 3)

10. **GradeMonitor** - Implement background task
    - Check hourly for new grades
    - Send notifications

11. **AttendanceWarningMonitor** - Implement background task
    - Check daily for warnings
    - Send notifications

### Phase 6: Testing & Deployment (Week 3-4)

12. **Testing** - Test all features
    - Unit tests for parsers
    - Integration tests for services
    - Manual Discord testing

13. **Documentation** - Update documentation
    - README.md with new commands
    - Architecture diagrams
    - Deployment guide

---

## Appendix

### A. URL Reference

| Page | URL Pattern | Parameters | Example |
|------|-------------|------------|---------|
| Grade Report | `https://fap.fpt.edu.vn/Grade/StudentGrade.aspx` | `rollNumber`, `term`, `course` | `?rollNumber=SE203055&term=Fall2025&course=55959` |
| Attendance Report | `https://fap.fpt.edu.vn/Report/ViewAttendstudent.aspx` | `id`, `campus`, `term`, `course` | `?id=SE203055&campus=4&term=60&course=57599` |
| Schedule | `https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx` | `week`, `year` | `?week=10&year=2026` |
| Exam Schedule | `https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx` | None | Direct access |

### Parameter Mapping

**Term ID to Term Name:**
| Term ID | Term Name |
|---------|-----------|
| 59 | Fall2025 |
| 60 | Spring2026 |
| 58 | Summer2025 |
| 57 | Spring2025 |
| 56 | Fall2024 |
| ... | ... |

**Campus ID:**
| Campus ID | Campus Name |
|-----------|-------------|
| 4 | FPTU-Hồ Chí Minh |
| 3 | FPTU-Hòa Lạc |
| ... | ... |

### B. GPA Scale Reference

| 10-point Scale | 4.0 Scale | Letter Grade |
|----------------|-----------|--------------|
| 9.0 - 10.0 | 4.0 | A+ |
| 8.5 - 8.9 | 3.7 | A |
| 8.0 - 8.4 | 3.5 | B+ |
| 7.0 - 7.9 | 3.0 | B |
| 6.0 - 6.9 | 2.0 | C |
| 5.0 - 5.9 | 1.0 | D |
| Below 5.0 | 0.0 | F |

### C. Attendance Thresholds

| Percentage | Status | Action |
|------------|--------|--------|
| 80%+ | ✅ Good | Maintain |
| 60-79% | ⚠️ Warning | Be careful |
| Below 60% | ❌ Critical | Contact lecturer |

---

**Document Status:** ✅ Ready for Implementation
**Estimated Effort:** 2-3 weeks
**Dependencies:** Existing auth system, schedule parser, exam parser
**Next Steps:** Review with user → Begin Phase 1 (Foundation)
