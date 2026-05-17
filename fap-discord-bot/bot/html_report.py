"""
HTML Dashboard Renderer for FAP Daily Report
Renders academic data as a single self-contained HTML page.
"""
import json
from datetime import datetime
from pathlib import Path


def render_daily_report(data: dict) -> str:
    """Render daily academic report as a full HTML page."""
    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    student_id = data.get("student_id", "N/A")
    grades = data.get("grades", [])
    schedule = data.get("schedule", [])
    exams = data.get("exams", [])
    attendance = data.get("attendance", [])
    gpa_summary = data.get("gpa_summary", {})

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FAP Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0f1117;color:#e1e4e8;padding:20px;max-width:1200px;margin:0 auto}}
.header{{display:flex;justify-content:space-between;align-items:center;padding:20px 0;border-bottom:1px solid #30363d;margin-bottom:24px}}
.header h1{{font-size:1.5rem;color:#58a6ff}}
.header .meta{{text-align:right;color:#8b949e;font-size:0.85rem}}
.header .meta .student-id{{font-size:1.1rem;color:#f0f6fc;font-weight:600}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:32px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px}}
.card .label{{color:#8b949e;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px}}
.card .value{{font-size:1.8rem;font-weight:700;color:#f0f6fc}}
.card .sub{{color:#8b949e;font-size:0.8rem;margin-top:4px}}
.card.green .value{{color:#3fb950}}
.card.blue .value{{color:#58a6ff}}
.card.gold .value{{color:#d29922}}
.card.red .value{{color:#f85149}}
.section{{margin-bottom:32px}}
.section h2{{font-size:1.2rem;color:#f0f6fc;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #21262d;display:flex;align-items:center;gap:8px}}
.section h2 .icon{{font-size:1.4rem}}
table{{width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;overflow:hidden}}
th{{background:#21262d;color:#8b949e;font-weight:600;text-align:left;padding:12px 16px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px}}
td{{padding:10px 16px;border-top:1px solid #21262d;font-size:0.9rem}}
tr:hover{{background:#1c2128}}
.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600}}
.badge.pass{{background:#1b4332;color:#3fb950}}
.badge.fail{{background:#4c1d1d;color:#f85149}}
.badge.progress{{background:#1a3a5c;color:#58a6ff}}
.badge.present{{background:#1b4332;color:#3fb950}}
.badge.absent{{background:#4c1d1d;color:#f85149}}
.badge.future{{background:#30363d;color:#8b949e}}
.today-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
.today-card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;transition:border-color 0.2s}}
.today-card:hover{{border-color:#58a6ff}}
.today-card .time{{color:#58a6ff;font-size:0.85rem;font-weight:600}}
.today-card .subject{{color:#f0f6fc;font-size:1rem;font-weight:600;margin:4px 0}}
.today-card .room{{color:#8b949e;font-size:0.85rem}}
.chart-container{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;margin-top:16px}}
.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.empty{{color:#8b949e;font-style:italic;padding:20px;text-align:center}}
.footer{{text-align:center;color:#484f58;font-size:0.8rem;margin-top:40px;padding-top:20px;border-top:1px solid #21262d}}
@media(max-width:768px){{
.chart-row{{grid-template-columns:1fr}}
.cards{{grid-template-columns:repeat(2,1fr)}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>FAP Dashboard</h1>
  <div class="meta">
    <div class="student-id">{student_id}</div>
    <div>Cap nhat: {now}</div>
  </div>
</div>

{_render_summary_cards(data)}

{_render_today_schedule(schedule)}

{_render_weekly_schedule(schedule)}

{_render_grades_section(grades, gpa_summary)}

{_render_attendance_section(attendance)}

{_render_exams_section(exams)}

<div class="footer">
  Powered by FAP Discord Bot &bull; Tu dong cap nhat hang ngay 22:07
</div>

<script>
{_render_grade_chart_js(grades)}
{_render_attendance_chart_js(attendance)}
</script>
</body>
</html>"""


def _render_summary_cards(data: dict) -> str:
    grades = data.get("grades", [])
    exams = data.get("exams", [])
    attendance = data.get("attendance", [])
    gpa = data.get("gpa_summary", {})

    gpa_val = gpa.get("term_gpa") or gpa.get("cumulative_gpa") or 0
    passed = sum(1 for g in grades if g.get("status") == "Passed")
    total = len(grades)

    att_present = sum(1 for a in attendance if a.get("status") == "present")
    att_done = sum(1 for a in attendance if a.get("status") in ("present", "absent"))
    att_pct = round(att_present / att_done * 100, 1) if att_done else 0

    upcoming = len(exams)

    return f"""
<div class="cards">
  <div class="card blue">
    <div class="label">GPA</div>
    <div class="value">{gpa_val}</div>
    <div class="sub">{passed}/{total} mon qua</div>
  </div>
  <div class="card green">
    <div class="label">Diem danh</div>
    <div class="value">{att_pct}%</div>
    <div class="sub">{att_present}/{att_done} buoi</div>
  </div>
  <div class="card gold">
    <div class="label">Lich thi</div>
    <div class="value">{upcoming}</div>
    <div class="sub">Ky thi sap toi</div>
  </div>
  <div class="card {'green' if passed == total and total > 0 else 'blue'}">
    <div class="label">Mon hoc</div>
    <div class="value">{total}</div>
    <div class="sub">Ky hien tai</div>
  </div>
</div>"""


def _render_today_schedule(schedule: list) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    today_items = [s for s in schedule if s.get("date") == today]
    if not today_items:
        return """
<div class="section">
  <h2><span class="icon">&#128197;</span> Lich hom nay</h2>
  <div class="empty">Hom nay khong co lich hoc</div>
</div>"""

    cards = ""
    for item in sorted(today_items, key=lambda x: x.get("slot", 0)):
        cards += f"""
    <div class="today-card">
      <div class="time">Slot {item.get('slot', '?')} &bull; {item.get('start_time', '')} - {item.get('end_time', '')}</div>
      <div class="subject">{item.get('code', '')} - {item.get('name', '')}</div>
      <div class="room">Phong {item.get('room', '?')} &bull; {item.get('instructor', '')}</div>
    </div>"""

    return f"""
<div class="section">
  <h2><span class="icon">&#128197;</span> Lich hom nay</h2>
  <div class="today-grid">{cards}
  </div>
</div>"""


def _render_weekly_schedule(schedule: list) -> str:
    if not schedule:
        return """
<div class="section">
  <h2><span class="icon">&#128198;</span> Lich tuan</h2>
  <div class="empty">Chua co du lieu lich hoc</div>
</div>"""

    days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    day_vn = {"Mon": "T2", "Tue": "T3", "Wed": "T4", "Thu": "T5", "Fri": "T6", "Sat": "T7"}
    slots = sorted(set(s.get("slot", 0) for s in schedule))
    by_day = {}
    for item in schedule:
        day = item.get("day", "")
        by_day.setdefault(day, []).append(item)

    rows = ""
    for slot in slots:
        cells = ""
        for day in days_order:
            items = [i for i in by_day.get(day, []) if i.get("slot") == slot]
            if items:
                item = items[0]
                cells += f'<td><strong>{item.get("code", "")}</strong><br><span style="color:#8b949e;font-size:0.8rem">{item.get("room", "")}</span></td>'
            else:
                cells += "<td></td>"
        rows += f"<tr><td><strong>Slot {slot}</strong></td>{cells}</tr>"

    header = "<th>Slot</th>" + "".join(f"<th>{day_vn.get(d, d)}</th>" for d in days_order)

    return f"""
<div class="section">
  <h2><span class="icon">&#128198;</span> Lich tuan</h2>
  <div style="overflow-x:auto">
  <table>
    <tr>{header}</tr>
    {rows}
  </table>
  </div>
</div>"""


def _render_grades_section(grades: list, gpa: dict) -> str:
    if not grades:
        return """
<div class="section">
  <h2><span class="icon">&#127942;</span> Diem so</h2>
  <div class="empty">Chua co du lieu diem</div>
</div>"""

    rows = ""
    for g in grades:
        status = g.get("status", "")
        badge_class = "pass" if status == "Passed" else "fail" if "Suspend" in status else "progress"
        total = g.get("total")
        total_str = f"{total:.1f}" if total else "-"
        rows += f"""
    <tr>
      <td><strong>{g.get('code', '')}</strong></td>
      <td>{g.get('name', '')}</td>
      <td>{g.get('credits', '-')}</td>
      <td>{g.get('midterm', '-') or '-'}</td>
      <td>{g.get('final', '-') or '-'}</td>
      <td><strong>{total_str}</strong></td>
      <td><span class="badge {badge_class}">{status}</span></td>
    </tr>"""

    gpa_row = ""
    if gpa:
        gpa_row = f"""
  <div class="chart-container">
    <div style="display:flex;gap:40px;align-items:center;flex-wrap:wrap">
      <div><span style="color:#8b949e;font-size:0.8rem">GPA Ky</span><br><span style="font-size:2rem;font-weight:700;color:#58a6ff">{gpa.get('term_gpa', '-') or '-'}</span></div>
      <div><span style="color:#8b949e;font-size:0.8rem">GPA Tich luy</span><br><span style="font-size:2rem;font-weight:700;color:#3fb950">{gpa.get('cumulative_gpa', '-') or '-'}</span></div>
      <div><span style="color:#8b949e;font-size:0.8rem">Tin chi</span><br><span style="font-size:2rem;font-weight:700;color:#d29922">{gpa.get('earned_credits', '-')}/{gpa.get('total_credits', '-')}</span></div>
      <div style="flex:1;min-width:300px"><canvas id="gradeChart"></canvas></div>
    </div>
  </div>"""

    return f"""
<div class="section">
  <h2><span class="icon">&#127942;</span> Diem so</h2>
  <table>
    <tr><th>Ma mon</th><th>Ten mon</th><th>TC</th><th>GK</th><th>CK</th><th>Tong</th><th>TT</th></tr>
    {rows}
  </table>
  {gpa_row}
</div>"""


def _render_attendance_section(attendance: list) -> str:
    if not attendance:
        return """
<div class="section">
  <h2><span class="icon">&#9989;</span> Diem danh</h2>
  <div class="empty">Chua co du lieu diem danh</div>
</div>"""

    rows = ""
    for a in attendance:
        status = a.get("status", "future")
        badge_class = status
        label = {"present": "Co mat", "absent": "Vang", "future": "Chua hoc"}.get(status, status)
        rows += f"""
    <tr>
      <td><strong>{a.get('code', '')}</strong></td>
      <td>{a.get('name', '')}</td>
      <td>{a.get('date', '')}</td>
      <td>Slot {a.get('slot', '?')}</td>
      <td>{a.get('room', '')}</td>
      <td><span class="badge {badge_class}">{label}</span></td>
    </tr>"""

    # Summary per subject
    subjects = {}
    for a in attendance:
        code = a.get("code", "")
        if code not in subjects:
            subjects[code] = {"name": a.get("name", ""), "present": 0, "absent": 0, "future": 0}
        subjects[code][a.get("status", "future")] += 1

    summary_rows = ""
    for code, s in subjects.items():
        done = s["present"] + s["absent"]
        pct = round(s["present"] / done * 100, 1) if done else 0
        bar_color = "#3fb950" if pct >= 80 else "#d29922" if pct >= 50 else "#f85149"
        summary_rows += f"""
    <tr>
      <td><strong>{code}</strong></td>
      <td>{s['name']}</td>
      <td>{s['present']}</td>
      <td>{s['absent']}</td>
      <td>{s['future']}</td>
      <td>
        <div style="background:#21262d;border-radius:4px;height:8px;width:100%">
          <div style="background:{bar_color};height:8px;border-radius:4px;width:{pct}%"></div>
        </div>
        <span style="font-size:0.8rem;color:#8b949e">{pct}%</span>
      </td>
    </tr>"""

    return f"""
<div class="section">
  <h2><span class="icon">&#9989;</span> Diem danh</h2>
  <div class="chart-row">
    <div>
      <h3 style="color:#8b949e;font-size:0.9rem;margin-bottom:12px">Tong hop theo mon</h3>
      <table>
        <tr><th>Mon</th><th>Ten</th><th>Di</th><th>Vang</th><th>Sau</th><th>Ti le</th></tr>
        {summary_rows}
      </table>
    </div>
    <div class="chart-container">
      <canvas id="attendanceChart"></canvas>
    </div>
  </div>
  <h3 style="color:#8b949e;font-size:0.9rem;margin:16px 0 12px">Chi tiet</h3>
  <table>
    <tr><th>Mon</th><th>Ten</th><th>Ngay</th><th>Slot</th><th>Phong</th><th>Trang thai</th></tr>
    {rows}
  </table>
</div>"""


def _render_exams_section(exams: list) -> str:
    if not exams:
        return """
<div class="section">
  <h2><span class="icon">&#128221;</span> Lich thi</h2>
  <div class="empty">Khong co lich thi sap toi</div>
</div>"""

    rows = ""
    for e in exams:
        exam_type = e.get("exam_type", "")
        type_label = {"PE": "Thuc hanh", "FE": "Ket thuc ky"}.get(exam_type, exam_type)
        rows += f"""
    <tr>
      <td><strong>{e.get('subject', '')}</strong></td>
      <td>{e.get('subject_name', '')}</td>
      <td>{e.get('date', '')}</td>
      <td>{e.get('time', '')}</td>
      <td>{e.get('room', '')}</td>
      <td><span class="badge progress">{type_label}</span></td>
    </tr>"""

    return f"""
<div class="section">
  <h2><span class="icon">&#128221;</span> Lich thi</h2>
  <table>
    <tr><th>Ma mon</th><th>Ten mon</th><th>Ngay</th><th>Gio</th><th>Phong</th><th>Loai</th></tr>
    {rows}
  </table>
</div>"""


def _render_grade_chart_js(grades: list) -> str:
    if not grades:
        return ""
    codes = [g.get("code", "") for g in grades]
    totals = [g.get("total", 0) or 0 for g in grades]
    colors = []
    for t in totals:
        if t >= 8:
            colors.append("'#3fb950'")
        elif t >= 6:
            colors.append("'#58a6ff'")
        elif t >= 5:
            colors.append("'#d29922'")
        else:
            colors.append("'#f85149'")

    return f"""
new Chart(document.getElementById('gradeChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(codes)},
    datasets: [{{data: {json.dumps(totals)}, backgroundColor: [{','.join(colors)}], borderRadius: 4}}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{legend: {{display: false}}}},
    scales: {{
      y: {{max: 10, grid: {{color: '#21262d'}}, ticks: {{color: '#8b949e'}}}},
      x: {{grid: {{display: false}}, ticks: {{color: '#8b949e', maxRotation: 45}}}}
    }}
  }}
}});"""


def _render_attendance_chart_js(attendance: list) -> str:
    if not attendance:
        return ""
    present = sum(1 for a in attendance if a.get("status") == "present")
    absent = sum(1 for a in attendance if a.get("status") == "absent")
    future = sum(1 for a in attendance if a.get("status") == "future")
    return f"""
new Chart(document.getElementById('attendanceChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['Co mat', 'Vang', 'Chua hoc'],
    datasets: [{{data: [{present}, {absent}, {future}], backgroundColor: ['#3fb950', '#f85149', '#484f58'], borderWidth: 0}}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{position: 'bottom', labels: {{color: '#8b949e', padding: 16}}}}
    }}
  }}
}});"""
