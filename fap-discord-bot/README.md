# FAP Discord Bot

**Bot Discord tự-host để xem lịch học & lịch thi từ FPT University Academic Portal (FAP).**

---

## ✨ Tính năng

- ✅ **Đăng nhập FeID tự động** - Tự động điền username/password qua Playwright
- ✅ **Bypass Cloudflare** - Sử dụng non-headless browser cho Turnstile challenge
- ✅ **Auto-refresh session** - Tự động đăng nhập lại khi session hết hạn
- ✅ **Cào lịch học** - Parse lịch học theo tuần từ FAP
- ✅ **Cào lịch thi** - Parse lịch thi cuối kỳ
- ✅ **Lưu cookie** - Lưu authentication để tái sử dụng
- ✅ **Chọn tuần** - Lấy lịch bất kỳ tuần nào
- ✅ **Parse HTML** - Trích xuất thông tin lớp (phòng, thời gian, điểm danh)
- ✅ **Tích hợp Discord Bot** - Lệnh slash để xem lịch
- ✅ **Concurrent lock** - Tránh conflict khi nhiều lệnh gọi cùng lúc

---

## 🚀 Cài đặt nhanh

### Yêu cầu

```bash
# Python 3.11+
python --version

# Chromium browser (Playwright sẽ tự tải)
```

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Đăng nhập (Chỉ 1 lần)

```bash
python scraper/auto_login_feid.py login your_feid@fe.edu.vn your_password
```

**Quá trình diễn ra:**
- Chrome mở → trang đăng nhập FAP (non-headless để bypass Cloudflare)
- Chọn cơ sở (FU-Hòa Lạc)
- Click "Login With FeID"
- Tự động điền username + password
- Lưu cookies vào `data/fap_cookies.json`
- Lưu browser profile vào `data/chrome_profile/`

**Kết quả mong đợi:**
```
✅ FEID login successful
✅ Schedule page accessible
✅ 13 cookies saved to data/fap_cookies.json
```

### 3. Test lấy lịch

```bash
# Lịch học - Tuần hiện tại
python scraper/auto_login_feid.py fetch

# Lịch học - Tuần cụ thể
python scraper/auto_login_feid.py fetch 5 2026
```

### 4. Chạy Discord Bot

```bash
# Thiết lập environment variables trước
cp .env.example .env
# Edit .env với thông tin của bạn

# Chạy bot
python main.py
```

---

## 📁 Cấu trúc Project

```
fap-discord-bot/
├── 📄 Cấu hình
│   ├── .env                    ← Environment variables (SECRET)
│   ├── .env.example            ← Mẫu
│   ├── requirements.txt        ← Python dependencies
│   ├── config.py               ← Cấu hình bot
│   ├── Dockerfile              ← Docker config
│   └── docker-compose.yml      ← Docker Compose config
│
├── 📚 Tài liệu
│   ├── README.md                       ← File này (bắt đầu từ đây!)
│   ├── CHANGELOG.md                    ← Lịch sử thay đổi
│   └── docs/                           ← Tài liệu chi tiết
│       ├── DEVELOPMENT.md              ← Hướng dẫn phát triển
│       ├── ARCHITECTURE.md             ← Kiến trúc hệ thống
│       ├── features/                   ← Tài liệu feature
│       │   └── EXAM.md                 ← Exam schedule feature
│       └── archive/                    ← Tài liệu cũ (deprecated)
│           └── FLARESOLVERR.md         ← FlareSolverr guide (đã cũ)
│
├── 🚀 Entry Points
│   ├── main.py                 ← Entry point bot
│   └── manual_login.py         ← Login thủ công
│
├── 📂 Data (Được tạo khi chạy)
│   ├── chrome_profile/         ← Persistent browser profile
│   └── fap_cookies.json        ← Cookies được export (sau login)
│
├── 💻 Source Code
│   ├── scraper/                ← Authentication & Parsing
│   │   ├── __init__.py
│   │   ├── auth.py             ← Adapter (FAPAuth interface cho bot)
│   │   ├── auto_login_feid.py  ← Auth chính (FeID + Playwright)
│   │   ├── session_validator.py← Session health check & auto-refresh
│   │   ├── parser.py           ← HTML parser (schedule)
│   │   ├── exam_parser.py      ← HTML parser (exam)
│   │   └── cloudflare.py       ← Turnstile solver
│   ├── bot/                    ← Discord bot
│   │   ├── bot.py              ← Main bot class
│   │   └── commands/
│   │       ├── schedule.py     ← Lệnh lịch học
│   │       ├── exam.py         ← Lệnh lịch thi
│   │       └── status.py       ← Lệnh trạng thái
│   └── utils/                  ← Utility functions
│
└── 📄 Debug
    ├── schedule_fetched.html    ← HTML lịch học mới fetch được
    └── exam_schedule_final.html ← HTML lịch thi
```

---

## 🔧 Cách hoạt động

### Kiến trúc Authentication

```
┌─────────────────────────────────────────────────────────────┐
│  Discord Bot                                               │
│  User gõ: /schedule today hoặc /exam schedule               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPAuth (Adapter) - scraper/auth.py                       │
│  - Global lock để tránh concurrent Chrome access            │
│  - Auto-refresh session khi expired                         │
│  - Flag để tránh duplicate refresh                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPAutoLogin - scraper/auto_login_feid.py                 │
│  - fetch_schedule() - Lấy lịch học                          │
│  - fetch_exam_schedule() - Lấy lịch thi                     │
│  - Sử dụng cookies từ fap_cookies.json                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAP Portal (fap.fpt.edu.vn)                                │
│  - Trả về HTML                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPParser / ExamParser                                     │
│  - Parse HTML table → ScheduleItem[] hoặc ExamItem[]        │
└─────────────────────────────────────────────────────────────┘
```

### Session Refresh Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Bot Startup                                                │
│  └─► FAPAuth.get_session()                                 │
│      └─► SessionValidator.check_session_health()           │
│          ├─► Valid → Ready                                  │
│          └─► Expired → refresh_session(headless=False)      │
│                       (Chrome opens for Cloudflare)         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  User Command (/schedule today)                             │
│  └─► FAPAuth.fetch_schedule() [WITH LOCK]                  │
│      ├─► Try fetch with current session                    │
│      ├─► Failed? → _refresh_session_once() [NO LOCK]       │
│      │          └─► Other commands wait if refreshing      │
│      └─► Retry fetch                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Định dạng dữ liệu

### ScheduleItem (Lịch học)

```python
@dataclass
class ScheduleItem:
    subject_code: str      # "COM101"
    subject_name: str = "" # "Introduction to Computing"
    room: str = ""         # "A301"
    day: str = ""          # "Mon", "Tue", "Wed"...
    date: str = ""         # "02/03/2026"
    slot: int = 0         # 1-8
    start_time: str = ""  # "7:00"
    end_time: str = ""    # "9:15"
    status: str = ""       # "attended", "absent", "-"
```

### ExamItem (Lịch thi)

```python
@dataclass
class ExamItem:
    no: int                 # Số thứ tự
    subject_code: str       # "DBI202"
    subject_name: str       # "Database Systems"
    date: str              # "22/03/2026"
    room: str              # "115"
    time: str              # "07h00-09h00"
    exam_form: str         # "PRACTICAL_EXAM"
    exam_type: str         # "PE"
    publication_date: str  # "09/03/2026"
```

---

## 🗄️ Tham chiếu lệnh

### Authentication

```bash
# Login với tham số
python scraper/auto_login_feid.py login your_feid@fe.edu.vn password123

# Login với environment variables
set FAP_FEID=your_feid@fe.edu.vn
set FAP_PASSWORD=password123
python scraper/auto_login_feid.py login
```

### Session Validator

```bash
# Check session health
python scraper/session_validator.py check

# Refresh session
python scraper/session_validator.py refresh

# Ensure valid session
python scraper/session_validator.py ensure
```

### Lấy lịch

```bash
# Lịch học - Tuần hiện tại (mặc định)
python scraper/auto_login_feid.py fetch

# Lịch học - Tuần và năm cụ thể
python scraper/auto_login_feid.py fetch 5 2026
```

### Lệnh Discord Bot

```
/schedule today       - Xem lịch học hôm nay
/schedule week        - Xem lịch học tuần này
/schedule week 5      - Xem lịch học tuần 5
/exam schedule        - Xem lịch thi
/exam upcoming        - Xem lịch thi 7 ngày tới
/status               - Kiểm tra trạng thái bot
/ping                 - Ping bot
```

---

## 🔑 Cấu hình

### Environment Variables

Tạo file `.env` từ `.env.example`:

```bash
# Discord Bot
DISCORD_TOKEN=your_discord_bot_token_here

# FAP Credentials
FAP_USERNAME=your_feid@fe.edu.vn
FAP_PASSWORD=your_password

# Browser Settings
HEADLESS=true
USER_AGENT=Mozilla/5.0...
```

---

## 🐛 Xử lý sự cố

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| "No cookies found" | `data/fap_cookies.json` thiếu | Chạy `python scraper/auto_login_feid.py login` |
| "Session expired" | Cookies hết hạn | Bot sẽ tự refresh, hoặc chạy manual `python scraper/session_validator.py refresh` |
| "Target closed" | Chrome process conflict | Bot có lock để tránh này, restart nếu vẫn lỗi |
| "Found 0 classes" | Tuần không có lịch | Thử tuần khác |
| Bot không phản hồi | Discord token sai | Kiểm tra file `.env` |
| Lệnh exam đơ | Session đang refresh | Đợi refresh xong (~30s) hoặc test lại |

### Debug Mode

```bash
# Xem HTML raw để debug
# Sau khi chạy lệnh, check file:
cat schedule_fetched.html
cat exam_schedule_final.html
```

---

## 🛠️ Tech Stack

| Component | Technology | Mục đích |
|-----------|-----------|----------|
| Browser Automation | Playwright Chromium | Điều khiển browser |
| Cloudflare Bypass | Non-headless Chrome | Bypass Turnstile |
| HTML Parsing | BeautifulSoup4 | Trích xuất dữ liệu |
| Discord API | discord.py | Framework bot |
| Concurrency | asyncio.Lock | Tránh Chrome race condition |
| Language | Python | 3.11+ |

---

## 📈 Trạng thái phát triển

- [x] Authentication Module (FeID + Playwright)
- [x] Session Auto-Refresh
- [x] HTML Parser (Schedule)
- [x] HTML Parser (Exam)
- [x] Cookie Persistence
- [x] Discord Bot Commands (Schedule)
- [x] Discord Bot Commands (Exam)
- [x] Concurrent Access Lock
- [x] Week Selection
- [ ] Keep-Alive Heartbeat
- [ ] Notification System
- [ ] Multi-user Support

---

## 📚 Tài liệu

### Tài liệu chính

| Tài liệu | Mô tả |
|----------|-------|
| **[README.md](README.md)** | Tài liệu chính của project (file này) |
| **[CHANGELOG.md](CHANGELOG.md)** | Lịch sử thay đổi phiên bản |
| **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** | Hướng dẫn phát triển & logic chi tiết |

### Tài liệu kỹ thuật

| Tài liệu | Mô tả |
|----------|-------|
| **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** | Kiến trúc chi tiết với flow diagram |
| **[features/EXAM.md](docs/features/EXAM.md)** | Tài liệu tính năng Exam Schedule |

### Tài liệu archive (đã cũ)

| Tài liệu | Trạng thái |
|----------|------------|
| **[archive/FLARESOLVERR.md](docs/archive/FLARESOLVERR.md)** | ⚠️ Đã thay bằng non-headless Chrome |
| `scraper/archive/*.md` | Các phương pháp experiment đã archive |

### Cấu trúc nhanh

```
fap-discord-bot/
├── README.md                    ← Bắt đầu từ đây
├── CHANGELOG.md                 ← Cập nhật phiên bản
└── docs/
    ├── DEVELOPMENT.md           ← Hướng dẫn dev
    ├── ARCHITECTURE.md          ← Kiến trúc hệ thống
    └── features/
        └── EXAM.md              ← Tài liệu feature Exam
```

---

## 📄 License

MIT License

---

*Updated: 2026-03-09*
*Status: ✅ Production Ready*
*Architecture: FeID + Playwright + Auto-Refresh*
