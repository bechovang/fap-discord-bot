# FAP Discord Bot

**Bot Discord tự-host để xem lịch học từ FPT University Academic Portal (FAP).**

---

## ✨ Tính năng

- ✅ **Đăng nhập FeID tự động** - Tự động điền username/password qua FlareSolverr
- ✅ **Bypass Cloudflare** - Sử dụng Docker container FlareSolverr
- ✅ **Cào lịch học** - Parse lịch học theo tuần từ FAP
- ✅ **Lưu cookie** - Lưu authentication để tái sử dụng
- ✅ **Chọn tuần** - Lấy lịch bất kỳ tuần nào
- ✅ **Parse HTML** - Trích xuất thông tin lớp (phòng, thời gian, điểm danh)
- ✅ **Tích hợp Discord Bot** - Lệnh slash để xem lịch

---

## 🚀 Cài đặt nhanh

### Yêu cầu

```bash
# Python 3.11+
python --version

# Docker (cho FlareSolverr)
docker --version
```

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Khởi động FlareSolverr (Lần đầu)

**Cách A: Docker (Khuyến nghị)**
```bash
# Để dùng bình thường (headless)
docker run -d -p 8191:8191 flaresolverr/flaresolverr

# Để đăng nhập lần đầu (cần browser nhìn thấy)
docker run -d -e HEADLESS=false -p 8191:8191 flaresolverr/flaresolverr
```

**Cách B: Windows Batch**
```bash
start_flaresolverr.bat
```

### 3. Đăng nhập (Chỉ 1 lần)

```bash
python scraper/auto_login_feid.py login your_feid@fe.edu.vn your_password
```

**Quá trình diễn ra:**
- FlareSolverr tự động bypass Cloudflare
- Chrome mở → trang đăng nhập FAP
- Chọn cơ sở (FU-Hòa Lạc)
- Click "Login With FeID"
- Tự động điền username + password
- Lưu cookies vào `data/fap_cookies.json`

**Kết quả mong đợi:**
```
✅ FEID login successful
✅ Schedule page accessible
✅ 13 cookies saved to data/fap_cookies.json
```

### 4. Test lấy lịch

```bash
# Tuần hiện tại
python scraper/auto_login_feid.py fetch

# Tuần cụ thể
python scraper/auto_login_feid.py fetch 5 2026
```

### 5. Chạy Discord Bot

```bash
# Thiết lập environment variables trước
cp .env.template .env
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
│   ├── .env.template           ← Mẫu
│   ├── requirements.txt        ← Python dependencies
│   └── start_flaresolverr.bat  ← FlareSolverr launcher
│
├── 📚 Tài liệu
│   ├── README.md                       ← File này
│   ├── FAP-SOLUTION-ARCHITECTURE.md    ← Kiến trúc chi tiết
│   └── FLARESOLVERR-GUIDE.md           ← Hướng dẫn FlareSolverr
│
├── 🚀 Entry Points
│   ├── main.py                 ← Entry point bot
│   └── quick_start.py          ← Test nhanh
│
├── 🧪 Tools
│   ├── cleanup_scraper.py      ← Tool dọn dẹp
│   └── cleanup_report.json     ← Báo cáo cleanup
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
│   │   ├── flaresolverr_auth.py← FlareSolverr integration
│   │   ├── cloudflare.py       ← Turnstile solver
│   │   ├── parser.py           ← HTML parser
│   │   └── archive/            ← Files experiment (đã archive)
│   ├── bot/                    ← Discord bot
│   │   ├── bot.py              ← Main bot class
│   │   └── commands/
│   │       ├── schedule.py     ← Lệnh lịch
│   │       └── status.py       ← Lệnh trạng thái
│   └── utils/                  ← Utility functions
│
└── 📄 Debug
    └── schedule_fetched.html    ← HTML mới fetch được
```

---

## 🔧 Cách hoạt động

### Kiến trúc Authentication

```
┌─────────────────────────────────────────────────────────────┐
│  Discord Bot                                               │
│  User gõ: /schedule today                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPAuth (Adapter) - scraper/auth.py                       │
│  Cung cấp interface tương thích với bot                     │
│  Nội tại dùng FAPAutoLogin                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPAutoLogin - scraper/auto_login_feid.py                 │
│  Module authentication chính                                │
│  - FeID login automation                                    │
│  - Cookie persistence                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FlareSolverr (Docker)                                      │
│  - Tự động bypass Cloudflare                                │
│  - Port 8191                                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAP Portal (fap.fpt.edu.vn)                                │
│  - Trả về HTML lịch học                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  FAPParser - scraper/parser.py                              │
│  - Parse HTML table → ScheduleItem[]                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Định dạng dữ liệu

### ScheduleItem

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

### FlareSolverr

```bash
# Test kết nối
python scraper/flaresolverr_auth.py test

# Login lần đầu (cần HEADLESS=false)
python scraper/flaresolverr_auth.py login

# Lấy lịch
python scraper/flaresolverr_auth.py fetch
```

### Lấy lịch

```bash
# Tuần hiện tại (mặc định)
python scraper/auto_login_feid.py fetch

# Tuần và năm cụ thể
python scraper/auto_login_feid.py fetch 5 2026
```

### Lệnh Discord Bot

```
/schedule today    - Xem lịch hôm nay
/schedule week     - Xem lịch tuần này
/schedule week 5   - Xem lịch tuần 5
/status            - Kiểm tra trạng thái bot
```

---

## 🔑 Cấu hình

### Environment Variables

Tạo file `.env` từ `.env.template`:

```bash
# Discord Bot
DISCORD_TOKEN=your_discord_bot_token_here

# FAP Credentials
FAP_USERNAME=your_feid@fe.edu.vn
FAP_PASSWORD=your_password

# Browser Settings
HEADLESS=true
USER_AGENT=Mozilla/5.0...

# FlareSolverr (optional, dùng default nếu không set)
FLARESOLVERR_URL=http://localhost:8191/v1
```

---

## 🐛 Xử lý sự cố

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| "No cookies found" | `data/fap_cookies.json` thiếu | Chạy `python scraper/auto_login_feid.py login` |
| "Cannot connect to FlareSolverr" | FlareSolverr không chạy | `docker run -d -p 8191:8191 flaresolverr/flaresolverr` |
| "Schedule page not loaded" | Cookies hết hạn | Login lại với lệnh `login` |
| "Found 0 classes" | Tuần không có lịch | Thử tuần khác |
| Bot không phản hồi | Discord token sai | Kiểm tra file `.env` |

---

## 📚 Tài liệu bổ sung

- **`FAP-SOLUTION-ARCHITECTURE.md`** - Kiến trúc chi tiết với flow diagram
- **`FLARESOLVERR-GUIDE.md`** - Hướng dẫn FlareSolverr
- **`scraper/archive/README.md`** - Các phương pháp experiment đã archive

---

## 🛠️ Tech Stack

| Component | Technology | Mục đích |
|-----------|-----------|----------|
| Browser Automation | Playwright Chromium | Điều khiển browser |
| Cloudflare Bypass | FlareSolverr (Docker) | Bypass anti-bot |
| HTML Parsing | BeautifulSoup4 | Trích xuất dữ liệu |
| Discord API | discord.py | Framework bot |
| Language | Python | 3.11+ |

---

## 📈 Trạng thái phát triển

- [x] Authentication Module (FeID + FlareSolverr)
- [x] HTML Parser
- [x] Cookie Persistence
- [x] Discord Bot Commands
- [x] Week Selection
- [ ] Keep-Alive Heartbeat
- [ ] Notification System
- [ ] Multi-user Support

---

## 🧹 Lịch sử Cleanup

Project đã được dọn dẹp để loại bỏ code experiment. Xem `cleanup_report.json` để chi tiết.

**Đã archive:** 29 files experiment, 3 thư mục dư thừa
**Giữ lại:** 6 files hoạt động + adapter pattern cho bot

---

## 📄 License

MIT License - Xem LICENSE file để chi tiết

---

*Cập nhật lần cuối: 2026-03-07*
*Trạng thái: ✅ Sản xuất (Production Ready)*
*Kiến trúc: FlareSolverr + FeID + Playwright*
