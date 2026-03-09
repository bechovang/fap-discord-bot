# FAP Discord Bot

**Bot Discord tự-host để xem lịch học từ FPT University Academic Portal (FAP).**

**Status:** ✅ **DEPLOYED & WORKING** - Bot `FAP_FPT_BOT#3123` online since 2026-03-09

---

## ✨ Tính năng

- ✅ **Đăng nhập FeID tự động** - Tự động điền username/password qua FlareSolverr
- ✅ **Bypass Cloudflare** - Sử dụng Docker container FlareSolverr
- ✅ **Cào lịch học** - Parse lịch học theo tuần từ FAP (đã test: 10 classes found)
- ✅ **Lưu cookie** - Lưu authentication để tái sử dụng
- ✅ **Chọn tuần** - Lấy lịch bất kỳ tuần nào
- ✅ **Parse HTML** - Trích xuất thông tin lớp (phòng, thời gian, điểm danh)
- ✅ **Tích hợp Discord Bot** - Lệnh slash để xem lịch
- ✅ **DEPLOYED** - Bot đang chạy trên Discord server

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

# Keep-Alive Heartbeat (giữ session FAP sống)
HEARTBEAT_INTERVAL_MINUTES=12          # Tần suất heartbeat (mặc định: 12 phút)
HEARTBEAT_TIMEOUT_SECONDS=30           # Timeout cho heartbeat (mặc định: 30 giây)
HEARTBEAT_MAX_RETRIES=2                # Số lần retry khi thất bại (mặc định: 2)
HEARTBEAT_RETRY_DELAY_SECONDS=5        # Delay giữa các retry (mặc định: 5 giây)
HEARTBEAT_CIRCUIT_BREAKER_THRESHOLD=3  # Số lỗi liên tục trước khi mở circuit breaker
HEARTBEAT_CIRCUIT_BREAKER_TIMEOUT_SECONDS=300  # Thời gian circuit breaker mở (mặc định: 5 phút)
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

## 💓 Keep-Alive Heartbeat

Bot sử dụng **heartbeat** để duy trì session FAP và tránh timeout (ASP.NET session hết hạn sau 20-60 phút không hoạt động).

**Cách hoạt động:**
- Mỗi 12 phút (có thể cấu hình qua `HEARTBEAT_INTERVAL_MINUTES`)
- Bot gửi yêu cầu nhẹ đến FAP để kiểm tra session còn hợp lệ
- Nếu session hết hạn, bot sẽ tự động đăng nhập lại khi có request tiếp theo

**Circuit Breaker:**
- Sau 3 lần thất bại liên tục, heartbeat sẽ tạm dừng trong 5 phút để tránh spam FAP
- Giúp bảo vệ bot khi FAP đang gặp sự cố hoặc bảo trì

**Theo dõi:**
- Bot log số lần thành công/thất bại của mỗi heartbeat
- Xem logs để biết sức khỏe của session

---

## 📈 Trạng thái phát triển

- [x] Authentication Module (FeID + FlareSolverr)
- [x] HTML Parser
- [x] Cookie Persistence
- [x] Discord Bot Commands
- [x] Week Selection
- [x] **Keep-Alive Heartbeat** ⚡ (Giữ session FAP sống mỗi 12 phút)
- [x] **Notification System** 🔔 (Nhắc lịch, thông báo điểm danh, thay đổi lịch)
- [ ] Multi-user Support (Phase 2)

---

## 🧹 Lịch sử Cleanup

Project đã được dọn dẹp để loại bỏ code experiment. Xem `cleanup_report.json` để chi tiết.

**Đã archive:** 29 files experiment, 3 thư mục dư thừa
**Giữ lại:** 6 files hoạt động + adapter pattern cho bot

---

## 📄 License

MIT License - Xem LICENSE file để chi tiết

---

*Cập nhật lần cuối: 2026-03-09*
*Trạng thái: ✅ Deployed & Working (Production)*
*Deployed at: FAP_FPT_BOT#3123*
*Kiến trúc: FlareSolverr + FeID + Playwright*

---

## 🎉 Deployment Summary (2026-03-09)

**✅ Completed Tasks:**
- Discord Bot `FAP_FPT_BOT#3123` successfully deployed
- FeID authentication working (14 cookies saved)
- Schedule fetch verified (10 classes retrieved)
- FlareSolverr integration tested and working
- All slash commands synced and functional

**📋 Bot Commands Available:**
- `/schedule today` - View today's class schedule
- `/schedule week` - View this week's schedule
- `/schedule week [number]` - View specific week
- `/ping` - Check bot latency
- `/status` - View bot health status

**🔧 Configuration:**
- Application ID: `1479739776751108216`
- Privileged Intents: ✅ Enabled (Presence, Server Members, Message Content)
- FlareSolverr: Running on port 8191
- Authentication: FeID (Google OAuth) with session persistence
