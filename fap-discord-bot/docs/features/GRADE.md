# Grade Feature Documentation

## Overview

Bot Discord hỗ trợ xem điểm số từ FAP Portal với các lệnh:
- `/grade this-term` - Xem điểm học kỳ hiện tại (Dashboard view)
- `/grade view` - Xem chi tiết điểm theo kỳ (có menu chọn kỳ)
- `/grade gpa` - Xem GPA tổng kết

---

## Cách hoạt động

### Grade Fetching Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Discord Bot                                               │
│  User gõ: /grade this-term                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPAuth (Adapter) - scraper/auth.py                       │
│  - Global lock để tránh concurrent Chrome access            │
│  - Auto-refresh session khi expired                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Grade Commands - bot/commands/grade.py                     │
│  1. Fetch base page (rollNumber=student_id)                │
│  2. Extract term names & course list                       │
│  3. For EACH course: fetch with course parameter           │
│  4. Parse detailed grade table for each course             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  GradeParser - scraper/grade_parser.py                      │
│  - parse_grades(): Parse HTML → GradeItem[]                │
│  - calculate_gpa(): Tính GPA từ danh sách điểm             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Discord Embed Response                                     │
│  - Dashboard: Group by subject, color-coded by grade       │
│  - GPA: Term + Cumulative with grade breakdown             │
└─────────────────────────────────────────────────────────────┘
```

### Grade Table Types

FAP Portal có 2 loại bảng điểm:

1. **Detailed Grade Table** (Course-specific)
   - URL: `Grade/StudentGrade.aspx?rollNumber=XXX&course=YYY`
   - Structure: Grade breakdown by component (Labs, Tests, Assignment...)
   - Footer: Average (total grade) + Status

2. **Summary Grade Table** (Term overview)
   - URL: `Grade/StudentGrade.aspx?rollNumber=XXX&term=ZZZ`
   - Structure: List of subjects with mid/final/total
   - Headers: No | Code | Name | Credits | Mid | Final | Total | Status

---

## Data Structures

### GradeItem

```python
@dataclass
class GradeItem:
    no: int                 # Số thứ tự
    subject_code: str       # "MAD101"
    subject_name: str       # "Discrete mathematics"
    credits: int            # Số tín chỉ
    mid_term: float        # Điểm giữa kỳ (0-10)
    final: float           # Điểm cuối kỳ (0-10)
    total: float           # Điểm tổng kết (0-10)
    status: str            # "Passed", "Is Suspended", "In Progress"
    grade_4scale: float    # Điểm thang 4.0
```

### GPASummary

```python
@dataclass
class GPASummary:
    term: Optional[str]           # Tên kỳ (Fall2025)
    term_gpa: Optional[float]     # GPA kỳ học
    cumulative_gpa: float         # GPA tích lũy
    total_credits: int            # Tổng số tín chỉ
    earned_credits: int           # Số tín chỉ đã đạt
    subjects_passed: int          # Số môn qua
    subjects_failed: int          # Số môn rớt
    grade_breakdown: Dict[str, int]  # Đếm theo loại (A, B, C, D, F)
    by_term: Dict[str, TermGPA]   # GPA theo từng kỳ
    excluded_subjects: List[str]  # Môn không tính GPA
```

---

## Grade Scale Conversion

Thang điểm 10 → Thang điểm 4.0:

| Điểm (10) | Điểm (4.0) | Loại |
|-----------|------------|------|
| 9-10      | 4.0        | A    |
| 8         | 3.5        | B+   |
| 7         | 3.0        | B    |
| 6         | 2.0        | C    |
| 5         | 1.0        | D    |
| 4         | 0.5        | F    |
| 0-3       | 0.0        | F    |

### Môn không tính GPA

Các môn sau **không** được tính vào GPA:
- `PE` - Physical Education
- `MUSIC` - Music
- `ENG` / `EN` - English
- `PHYSICAL_EDUCATION`

---

## Commands Reference

### `/grade this-term`

Xem điểm học kỳ hiện tại với Dashboard view:

**Features:**
- Hiển thị Term GPA & Credits
- Group by subject code
- Color-coded by grade:
  - 🟢 8.5+ (A) - Green
  - 🟡 7.0+ (B) - Yellow
  - 🟠 5.5+ (C) - Orange
  - 🔴 4.0+ (D) - Red
  - ⚫ < 4.0 (F) - Black

**Example Output:**
```
📊 Grade Dashboard - Fall2025
🎯 Term GPA: 3.20/4.0 | 📚 Credits: 12/15 | ✅ Passed: 5 | ❌ Failed: 1

MAD101 - Discrete mathematics
🟡 Total: 7.9/10 (B) | 4.0 Scale: 3.0
📖 Mid-term: 0.0 | 📝 Final: 7.9
📚 Credits: 3 | ✅ Status: Passed
```

### `/grade view`

Xem chi tiết điểm theo kỳ với menu dropdown:

**Features:**
- Select menu để chọn kỳ học
- Hiển thị danh sách môn học với điểm chi tiết
- Color-coded grade status

### `/grade gpa`

Xem GPA tổng kết:

**Features:**
- Cumulative GPA (tất cả các kỳ)
- Grade breakdown (số môn A, B, C, D, F)
- Credits earned/total
- Pass/Fail statistics

---

## Parser Logic

### extract_courses(html)

Trích xuất danh sách môn học từ trang base page:

```python
# Tìm div chứa danh sách môn học
course_div = soup.find('div', {'id': 'ctl00_mainContent_divCourse'})

# Parse từng môn từ table rows
for tr in table.find_all('tr'):
    # Link courses: có course_id trong href
    # Current course: bold tag, không có link
```

**Returns:** List of dicts with keys: `course_id`, `code`, `name`, `is_current`

### parse_grades(html)

Parse bảng điểm từ HTML:

```python
# 1. Tìm grade div
grade_div = soup.find('div', {'id': 'ctl00_mainContent_divGrade'})

if grade_div:
    # Detailed grade page (single course)
    return _parse_detailed_grade_table(table, soup)
else:
    # Summary grade page (multiple subjects)
    return _parse_summary_grade_table(table)
```

**Detailed Grade Table:**
- Headers: Grade category | Grade item | Weight | Value | Comment
- Footer: Average (total grade) | Status
- Returns: List with 1 GradeItem (total grade for course)

**Summary Grade Table:**
- Headers: No | Code | Name | Credits | Mid | Final | Total | Status
- Returns: List of GradeItem (one per subject)

### calculate_gpa(grades, by_term)

Tính GPA từ danh sách điểm:

```python
for grade in grades:
    if grade.subject_code not in EXCLUDED_SUBJECTS:
        if grade.status == "Passed":
            total_4scale += grade.grade_4scale * grade.credits
            total_credits += grade.credits
            earned_credits += grade.credits
        elif grade.status == "Is Suspended":
            total_credits += grade.credits

gpa = total_4scale / total_credits if total_credits > 0 else 0.0
```

---

## Known Issues & Limitations

1. **Credits = 0**: Detailed grade view không hiển thị số tín chỉ
   - **Workaround**: Sử dụng summary view để lấy credits
   - **Impact**: GPA calculation có thể không chính xác

2. **Course Code = UNKNOWN**: Một số môn không có course code trong HTML
   - **Workaround**: Parser set subject_code = "UNKNOWN"
   - **Impact**: Subject hiển thị là "UNKNOWN - Course Name"

3. **Interaction Timeout**: Discord interaction expire sau 3 seconds
   - **Fix**: Use `defer(ephemeral=True)` immediately
   - **Status**: ✅ Fixed

4. **Slow Fetching**: Mỗi course = 1 browser instance mới
   - **Impact**: 6 courses ≈ 30-60 seconds
   - **Future**: Reuse browser session across requests

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "No grades found for Fall2025" | Parser không tìm thấy bảng điểm | Check `debug_grade_parse_error.html` |
| "Interaction expired" | Bot quá 3s không respond | Fixed in latest version |
| Credits showing as 0 | Detailed view không có credits | Normal - use summary view for credits |
| Wrong GPA calculation | Excluded subjects not filtered | Check `EXCLUDED_SUBJECTS` list |
| Course shows "UNKNOWN" | HTML không có course code | Report issue with HTML sample |

---

## Testing

### Manual Test Commands

```bash
# Test grade parser with HTML file
python -c "
from scraper.grade_parser import GradeParser
with open('resource/Grade report pro.html', 'r', encoding='utf-8') as f:
    html = f.read()
parser = GradeParser()
grades = parser.parse_grades(html)
for grade in grades:
    print(f'{grade.subject_code}: {grade.total} - {grade.status}')
"
```

### Discord Test

```
1. /grade this-term
2. Check bot response has:
   - Term GPA
   - Subject list with grades
   - Color-coded status
3. /grade gpa
4. Check cumulative GPA is calculated
```

---

## Files Structure

```
scraper/
├── grade_parser.py      # Grade parsing logic
├── auth.py              # FAPAuth adapter
└── auto_login_feid.py   # fetch_grades() method

bot/commands/
└── grade.py             # Discord slash commands

resource/ (debug files)
├── Grade report pro.html       # Detailed grade page sample
├── Grade report.html           # Summary grade page sample
└── Grade report pro_files/     # Supporting files
```

---

*Last Updated: 2026-03-11*
*Status: ✅ Working*
