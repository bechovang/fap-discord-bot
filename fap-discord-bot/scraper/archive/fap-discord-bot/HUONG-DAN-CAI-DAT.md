# FAP Discord Bot - Hướng Dẫn Cài Đặt

## ✅ Đã Hoàn Thành

```
fap-discord-bot/
├── bot/                 # Discord bot commands
├── scraper/             # FAP scraper + parser
│   ├── auth.py          # Authentication (stealth mode)
│   ├── auth_browserless.py  # Authentication + Browserless
│   ├── parser.py        # Schedule parser ✅ TESTED
│   └── cloudflare.py    # Turnstile solver
├── utils/               # Helper modules
├── .env                 # Cấu hình (có sẵn credentials)
├── BROWSERLESS.md       # Hướng dẫn Browserless
└── start_browserless.bat # Script khởi động Browserless
```

## 🚀 Cách Dùng

### Cách 1: Bot Đơn Giản (Không cần Docker)

```bash
cd fap-discord-bot
pip install -r requirements.txt
python main.py
```

- Bot sẽ chạy với **Stealth Mode** (giả lập browser thật)
- `HEADLESS=false` trong .env để xem bot hoạt động

### Cách 2: Bot + Browserless (Khuyên nghị)

**Bước 1: Khởi động Browserless**
```bash
start_browserless.bat
```

**Bước 2: Chạy bot**
```bash
python main.py
```

## 🔧 Cấu hình Discord Bot Token

1. Vào: https://discord.com/developers/applications/1479739776751108216/bot
2. Click "Reset Token" → Copy token
3. Paste vào `.env`:
   ```
   DISCORD_TOKEN=your_token_here
   ```

## 📋 Discord Commands

| Command | Mô tả |
|---------|-------|
| `/schedule today` | Xem lịch hôm nay |
| `/schedule week` | Xem lịch tuần này |
| `/status` | Kiểm tra trạng thái bot |
| `/ping` | Kiểm tra độ trễ |

## ⚠️ Vấn đề Cloudflare

Nếu bot không login được:

1. **Chạy với HEADLESS=false** để xem browser
2. **Hoàn thành thủ công** Cloudflare challenge lần đầu
3. Bot sẽ **lưu session** cho các lần sau

```bash
# Trong .env
HEADLESS=false
```

## 📞 Hỗ Trợ

Nếu gặp lỗi:
1. Kiểm tra Docker có chạy không (nếu dùng Browserless)
2. Kiểm tra FAP credentials đúng chưa
3. Chạy với `HEADLESS=false` để debug

---

**Tóm tắt:**
- ✅ Code đã sẵn sàng
- ✅ Credentials đã cấu hình
- ⏳ Thêm Discord Token vào `.env`
- ⏳ Chạy `python main.py`
