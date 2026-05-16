# FAP Discord Bot

Bot Discord tự động lấy và hiển thị dữ liệu học tập từ FPT University — lịch học, lịch thi, điểm số, và điểm danh — trực tiếp trên Discord qua slash commands.

Bot xác thực với FAP (FPT Academic Portal) thông qua FeID OAuth, vượt Cloudflare Turnstile bằng Camoufox (trình duyệt Firefox chống detect), và duy trì phiên trình duyệt để lấy dữ liệu theo yêu cầu.

---

## Tính năng

- **Lịch học** — Xem lịch hôm nay hoặc cả tuần
- **Lịch thi** — Xem lịch thi và các kỳ thi sắp tới
- **Điểm số** — Xem điểm theo kỳ, tính GPA tích lũy
- **Điểm danh** — Theo dõi điểm danh theo môn và kỳ
- **Tự động làm mới** — Phiên tự động refresh khi hết hạn
- **Background jobs** — Giám sát điểm danh (15 phút), báo cáo thay đổi hàng tuần (CN 22:00), giữ phiên (4 giờ)
- **Vượt Cloudflare** — Camoufox với click Turnstile checkbox + Firefox profile cố định

---

## Lệnh (Commands)

| Lệnh | Mô tả |
|---|---|
| `/schedule today` | Lịch học hôm nay |
| `/schedule week [week] [year]` | Lịch học cả tuần |
| `/exam schedule` | Lịch thi đầy đủ |
| `/exam upcoming` | Các kỳ thi sắp tới |
| `/grade view` | Xem điểm tương tác |
| `/grade this-term` | Điểm kỳ hiện tại |
| `/grade gpa` | Tính GPA tích lũy |
| `/attendance view` | Xem điểm danh tương tác |
| `/attendance this-term` | Điểm danh kỳ hiện tại |
| `/status` | Trạng thái bot và phiên |
| `/ping` | Kiểm tra kết nối |
| `/config channel` | Cài đặt kênh thông báo |
| `/config status` | Xem cấu hình hiện tại |

---

## Kiến trúc

```
Discord Slash Command
  -> bot/commands/*.py          (Lớp giao diện Discord)
  -> scraper/auth.py            (FAPAuth adapter với auto-refresh)
  -> scraper/auto_login_feid.py (Trình duyệt Camoufox: login + fetch)
  -> FAP portal HTML
  -> scraper/*_parser.py        (Các HTML parser)
  -> Discord response
```

### Các thành phần chính

| File | Vai trò |
|---|---|
| `bot/bot.py` | Discord client, load lệnh, khởi động scheduler |
| `bot/commands/` | Triển khai các slash command |
| `bot/scheduler.py` | Background jobs (điểm danh, báo cáo tuần, keepalive) |
| `scraper/auth.py` | `FAPAuth` adapter — bao bọc fetch + auto-refresh với retry |
| `scraper/auto_login_feid.py` | `FAPAutoLogin` — Tự động hóa Camoufox cho login và fetch |
| `scraper/session_validator.py` | `SessionValidator` — Kiểm tra sức khỏe phiên và refresh |
| `scraper/parser.py` | Parser lịch học HTML |
| `scraper/exam_parser.py` | Parser lịch thi |
| `scraper/grade_parser.py` | Parser điểm số + tính GPA |
| `scraper/attendance_parser.py` | Parser điểm danh |
| `scraper/cloudflare.py` | Tiện ích xử lý Turnstile |

### Quy trình xác thực

```
1. Khởi chạy Camoufox (Firefox anti-detect) với persistent profile + proxy
2. Điều hướng đến FAP -> Cloudflare Turnstile challenge
3. Tìm và click checkbox Turnstile trong iframe challenges.cloudflare.com
4. Chọn campus -> Click nút "Login With FeID"
5. Điền form FeID (username + password) -> Submit
6. Chờ OAuth redirect về FAP
7. Giữ trình duyệt mở để fetch các trang tiếp theo
8. Cookies được xuất ra data/fap_cookies.json làm backup
```

### Tại sao giữ trình duyệt mở?

Cloudflare kiểm tra `cf_clearance` cookies dựa trên:
- **Địa chỉ IP** — phải khớp với proxy IP đã dùng khi giải challenge
- **TLS fingerprint (JA3/JA4)** — phải khớp với trình duyệt đã giải challenge
- **User-Agent** — phải khớp chính xác

Không có Python HTTP client nào (aiohttp, requests, curl_cffi) có thể tái tạo chính xác TLS fingerprint của Firefox thật. Cách duy nhất để fetch trang từ site được Cloudflare bảo vệ là dùng chính trình duyệt đó. Nên sau khi login, trình duyệt giữ mở và dùng `page.goto()` + `page.content()` để lấy dữ liệu.

---

## Triển khai (Deployment)

### Docker (Khuyến nghị)

```bash
# Clone repo
git clone https://github.com/bechovang/fap-discord-bot.git
cd fap-discord-bot

# Tạo .env từ template
cp .env.example .env
# Chỉnh .env với thông tin của bạn

# Build và chạy
docker compose up -d bot
```

Dockerfile xử lý mọi thứ:
- Python 3.11-slim base
- Firefox dependencies + Xvfb virtual display
- Tải Camoufox browser binary
- Tự động khởi động Xvfb + bot khi container chạy

### Cài thủ công

```bash
pip install -r requirements.txt
python -m camoufox fetch          # Tải Firefox binary
python fap-discord-bot/main.py
```

---

## Cấu hình

Tạo file `.env` (xem `.env.example`):

```env
# Bắt buộc
DISCORD_TOKEN=your_discord_bot_token
FAP_USERNAME=your_feid_email
FAP_PASSWORD=your_password

# Khuyến nghị
FAP_CAMPUS=4                              # Campus ID (mặc định: 4)
HEADLESS=false                            # false = Xvfb virtual display
PROXY_URL=http://user:pass@host:port      # Residential proxy (cần cho datacenter IP)

# Tùy chọn
FAP_STUDENT_ID=SE123456                   # Cần cho lệnh grade/attendance
SCHEDULER_TIMEZONE=Asia/Ho_Chi_Minh       # Múi giờ scheduler
DEFAULT_CHANNEL_ID=123456789              # Kênh thông báo mặc định
LOG_LEVEL=INFO
```

### Lưu ý: Escape mật khẩu trong Docker

Nếu mật khẩu chứa `$` (ví dụ `Eg8$Fw1$`), Docker Compose hiểu `$` là thay thế biến. Cần escape thành `$$`:

```env
FAP_PASSWORD=Eg8$$Fw1$$
```

### Yêu cầu Proxy

**Residential proxy** là bắt buộc khi chạy trên datacenter IP (DigitalOcean, AWS, v.v.). Cloudflare Turnstile kiểm tra uy tín IP và sẽ thất bại im lặng trên datacenter IP, bất kể browser fingerprinting.

Khuyến nghị: rotating residential proxies từ các nhà cung cấp như Webshare, Bright Data, hoặc Oxylabs.

---

## Cấu trúc dự án

```
fap-discord-bot/
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container build
├── docker-compose.yml          # Docker Compose config
├── .env.example                # Environment template
│
├── bot/
│   ├── bot.py                  # Discord client + startup
│   ├── scheduler.py            # Background jobs
│   ├── notifier.py             # Discord notification helper
│   ├── progress.py             # Progress tracking
│   └── commands/
│       ├── schedule.py         # /schedule today, /schedule week
│       ├── exam.py             # /exam schedule, /exam upcoming
│       ├── grade.py            # /grade view, /grade this-term, /grade gpa
│       ├── attendance.py       # /attendance view, /attendance this-term
│       ├── status.py           # /status, /ping
│       └── config.py           # /config channel, /config status
│
├── scraper/
│   ├── auth.py                 # FAPAuth adapter (auto-refresh + retry)
│   ├── auto_login_feid.py      # Camoufox browser automation
│   ├── session_validator.py    # Session health check + refresh
│   ├── cloudflare.py           # Turnstile utilities
│   ├── parser.py               # Schedule parser
│   ├── exam_parser.py          # Exam parser
│   ├── grade_parser.py         # Grade parser + GPA
│   ├── attendance_parser.py    # Attendance parser
│   └── fap_scraper.py          # Legacy scraper interface
│
└── data/                       # Runtime data (cookies, snapshots, DB)
```

---

## Background Jobs

Scheduler chạy 3 jobs tự động:

| Job | Chu kỳ | Mô tả |
|---|---|---|
| **Attendance Check** | Mỗi 15 phút | Giám sát slot hiện tại cho thay đổi điểm danh, gửi alert Discord |
| **Weekly Check** | Chủ nhật 22:00 | So sánh điểm/lịch/thi với tuần trước, thông báo thay đổi |
| **Session Keepalive** | Mỗi 4 giờ | Kiểm tra phiên, trigger re-login nếu hết hạn |

---

## Quản trị Server (DigitalOcean)

Bot được deploy trên DigitalOcean Droplet (SGP1 - Singapore). Dùng `doctl` CLI để quản lý.

### Thông tin kết nối

```
Droplet: fap-bot (ID: 570186178)
IP: 68.183.233.253
SSH key: ~/.ssh/id_ed25519_fapbot
Project path: /opt/fap-bot/
```

### Các lệnh quản lý thường dùng

```bash
# SSH vào server
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot

# Xem logs
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot --ssh-command "docker logs fap-discord-bot --tail 50"

# Restart container
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot --ssh-command "cd /opt/fap-bot && docker compose up -d --force-recreate"

# Xem file .env hiện tại
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot --ssh-command "cat /opt/fap-bot/.env"
```

### Đổi Proxy trên Production

Proxy có thời hạn (thường 2 tháng). Khi cần đổi proxy mới:

```bash
# 1. Cập nhật PROXY_URL trong .env trên server
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot \
  --ssh-command "sed -i 's|PROXY_URL=.*|PROXY_URL=http://user:pass@host:port|' /opt/fap-bot/.env"

# 2. Nếu .env có các biến PROXY riêng lẻ, cập nhật cả 3:
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot \
  --ssh-command "sed -i 's|PROXY_URL=.*|PROXY_URL=http://user:pass@host:port|' /opt/fap-bot/.env && sed -i 's|PROXY_URL_HOST=.*|PROXY_URL_HOST=http://host:port|' /opt/fap-bot/.env && sed -i 's|PROXY_USERNAME=.*|PROXY_USERNAME=user|' /opt/fap-bot/.env && sed -i 's|PROXY_PASSWORD=.*|PROXY_PASSWORD=pass|' /opt/fap-bot/.env"

# 3. Restart container để áp dụng
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot \
  --ssh-command "cd /opt/fap-bot && docker compose up -d --force-recreate"

# 4. Kiểm tra logs xem proxy hoạt động không
doctl compute ssh 570186178 --ssh-key-path ~/.ssh/id_ed25519_fapbot \
  --ssh-command "docker logs fap-discord-bot --tail 30"
```

**Lưu ý quan trọng về scheme proxy:**
- Proxy loại "HTTPS" nghĩa là proxy hỗ trợ **traffic HTTPS**, nhưng bản thân kết nối đến proxy dùng `http://`
- Dùng `https://` sẽ gây lỗi SSL: `SSL: UNEXPECTED_EOF_WHILE_READING`
- Định dạng đúng: `http://user:pass@host:port` (luôn dùng `http://`)

**Các lỗi thường gặp khi đổi proxy:**

| Lỗi | Nguyên nhân | Cách fix |
|---|---|---|
| `ProxyError: SSL: UNEXPECTED_EOF_WHILE_READING` | Dùng `https://` thay vì `http://` | Đổi scheme thành `http://` |
| `InvalidProxy: Failed to connect to proxy` | Proxy hết hạn hoặc không hoạt động | Kiểm tra lại proxy, mua proxy mới |
| `session refresh failed` sau khi đổi proxy | Proxy mới chưa được apply | Restart container bằng `docker compose up -d --force-recreate` |

---

## Bài học kinh nghiệm

### 1. Cloudflare Turnstile không phải là JS challenge đơn giản

Turnstile kiểm tra nhiều tín hiệu ngoài `navigator.webdriver`:
- **Uy tín IP** — datacenter IP gây thất bại im lặng (không có lỗi, chỉ không bao giờ resolve)
- **TLS fingerprint (JA3/JA4)** — mỗi TLS client có fingerprint riêng
- **Browser fingerprint** — WebGL, canvas, fonts, screen resolution
- **Lịch sử di chuột** — patterns tương tác giống người

**Bài học**: Không có headless browser trick nào có thể vượt Turnstile trên datacenter IP. Cần residential proxies + anti-detect browser.

### 2. `cf_clearance` Cookies gắn với trình duyệt

Đã thử extract cookies từ browser và dùng với `aiohttp` và `curl_cffi`. Cả hai đều fail 403 vì:
- Cloudflare kiểm tra cookies với TLS fingerprint của client
- TLS fingerprint của aiohttp không giống Firefox
- Ngay cả `curl_cffi` với `impersonate="firefox"` cũng không khớp hoàn hảo với TLS của Camoufox

**Bài học**: Với site được Cloudflare bảo vệ, trình duyệt giải challenge phải là trình duyệt gửi request tiếp theo. Giữ browser mở và dùng `page.goto()` để fetch.

### 3. Escape mật khẩu trong Docker Compose

Password `Eg8$Fw1$` bị Docker Compose hiểu nhầm do thay thế biến (`$F` và `$` cuối bị cắt). FeID từ chối login với "incorrect username or password".

**Bài học**: Trong `.env` dùng bởi Docker Compose, luôn escape `$` thành `$$` cho password chứa dollar sign.

### 4. Tiêu đề Cloudflare tiếng Việt

Tiêu đề trang Cloudflare challenge là `"Chờ một chút..."` (tiếng Việt). Code chỉ kiểm tra keyword tiếng Anh `"moment"` và `"challenge"`, nên tưởng trang đã load và tương tác quá sớm.

**Bài học**: Luôn kiểm tra tiêu đề Cloudflare đã được dịch, hoặc tốt hơn là đợi nội dung trang thực tế (nút login, dropdown lịch) thay vì kiểm tra tiêu đề.

### 5. Xung đột Profile Lock

Chạy hai Camoufox instance với cùng persistent profile gây xung đột lock — instance thứ hai bị treo chờ profile, rồi timeout sau 180 giây.

Điều này xảy ra vì `FAPAuth` và `SessionValidator` mỗi cái tạo `FAPAutoLogin` instance riêng. Browser đầu tiên (từ login) vẫn mở, nhưng browser thứ hai (từ session refresh) không lấy được profile lock.

**Bài học**: Chia sẻ một browser instance cho cả login và fetch. Đóng browser cũ trước khi mở browser mới.

### 6. Hành trình FlareSolverr -> patchright -> Camoufox

- **FlareSolverr**: Lần thử đầu. Dùng service riêng để giải Cloudflare, rồi `requests` để login. Thất bại vì FlareSolverr không xử lý được chuỗi OAuth redirect (PKCE mismatch).
- **patchright** (Chromium): Lần thử thứ hai. Tự động hóa thành công login nhưng Cloudflare Turnstile không bao giờ resolve trên datacenter IP, ngay cả với `navigator.webdriver=False`.
- **Camoufox** (Firefox): Giải pháp cuối cùng. Firefox anti-detect với residential proxy + click Turnstile checkbox tường minh. Hoạt động ổn định.

**Bài học**: Cho site được Cloudflare bảo vệ trên server, dùng Firefox-based anti-detect browser với residential proxies. Chromium-based (ngay cả với anti-detection patches) dễ bị fingerprint hơn.

### 7. Xvfb Readiness Race

Khởi động Xvfb và ngay lập tức mở browser có thể gây race condition — browser cố kết nối đến display trước khi Xvfb sẵn sàng.

**Fix**: Đợi X11 lock file trước khi khởi động ứng dụng:
```bash
Xvfb :99 -screen 0 1280x720x24 & until [ -e /tmp/.X99-lock ]; do sleep 0.1; done; python main.py
```

### 8. Phát hiện phiên hết hạn — login HTML trả về như dữ liệu hợp lệ

Khi FAP session hết hạn, server redirect về `Default.aspx` (trang login). Nhưng code `_fetch_page()` chỉ kiểm tra URL chứa "Login" — `Default.aspx` không có chữ "Login" nên HTML của trang login được trả về như dữ liệu hợp lệ. Parser không tìm thấy schedule table hay grade container, trả về rỗng, và user thấy "No classes scheduled!" hay "No terms found" dù fetch "thành công".

**Fix**: Thêm 4 kiểm tra trong `_fetch_page()`:
1. URL redirect về `Default.aspx` (không phải URL request ban đầu)
2. URL chứa "Login" (nhưng không phải ScheduleOfWeek)
3. Page content chứa `btnloginFeId` (nút login)
4. Tiêu đề vẫn là Cloudflare challenge

Khi trả về `None`, `auth.py` tự động trigger session refresh và retry fetch.

**Bài học**: Khi fetch dữ liệu từ site yêu cầu xác thực, luôn kiểm tra rằng nội dung trả về **là dữ liệu thật**, không chỉ là "không lỗi HTTP". Redirect lên trang login là dấu hiệu session hết hạn phổ biến nhất.

### 9. Xóa Firefox profile trước khi login — tránh Cloudflare flagging

Firefox persistent profile tích lũy cookies, history, và fingerprints theo thời gian. Cloudflare sử dụng những dấu vết này để đánh dấu trình duyệt là bot. Tương tự như việc mở tab ẩn danh (incognito) để login thủ công sẽ không bị lỗi Turnstile.

**Fix**: Xóa toàn bộ profile directory trước mỗi lần login:
```python
if self.profile_dir.exists():
    shutil.rmtree(self.profile_dir, ignore_errors=True)
self.profile_dir.mkdir(parents=True, exist_ok=True)
```

**Bài học**: Với anti-detect browser, profile "sạch" (fresh) luôn đáng tin cậy hơn profile persistent. Persistent profile có lợi cho giữ session giữa các lần chạy, nhưng tăng nguy cơ bị fingerprint.

### 10. Xung đột DISPLAY giữa Xvfb ngoài và Camoufox virtual mode

Camoufox hỗ trợ `headless="virtual"` — dùng built-in Xvfb (virtual display). Nhưng `DISPLAY=:99` env var (cho Xvfb ngoài trong Dockerfile CMD) xung đột với virtual display nội bộ của Camoufox, gây lỗi `cannot open display: :99` hoặc crash.

**Fix**: Xóa DISPLAY env var khi dùng virtual mode:
```python
if headless_mode == "virtual":
    os.environ.pop("DISPLAY", None)
```

**Bài học**: Khi container chạy cả Xvfb riêng (trong CMD) và Camoufox virtual mode, hai display server cạnh tranh. Nên chọn một: hoặc Xvfb ngoài + `headless=False`, hoặc không Xvfb + `headless="virtual"`.

### 11. `docker restart` không áp dụng thay đổi `.env`

`docker restart` chỉ restart container hiện tại với environment cũ. Thay đổi trong `.env` chỉ được load khi tạo container mới.

**Fix**: Dùng `docker compose up -d --force-recreate` thay vì `docker restart`:
```bash
cd /opt/fap-bot && docker compose up -d --force-recreate
```

**Bài học**: Sau khi sửa `.env`, luôn recreate container. `docker restart` = restart process, `docker compose up -d --force-recreate` = tạo container mới với env mới.

### 12. `.env` file: `$` KHÔNG cần escape (khác với `docker-compose.yml`)

Docker Compose xử lý `$` khác nhau tùy ngữ cảnh:
- **`docker-compose.yml`**: `$VAR` là biến substitution → phải escape `$$` cho literal `$`
- **`.env` file**: Giá trị được đọc nguyên văn (literal) → `$` không cần escape

Ví dụ: mật khẩu `Eg8$Fw1$`:
- `.env` file: `FAP_PASSWORD=Eg8$Fw1$` (đúng)
- `docker-compose.yml` environment section: `FAP_PASSWORD=Eg8$$Fw1$$` (phải escape)

**Bài học**: Hiểu rõ ngữ cảnh: `.env` file values là literal strings, `docker-compose.yml` values undergo variable substitution.

### 13. Scheme Proxy HTTPS vs HTTP

Proxy loại "HTTPS" tạo nhầm lẫn — nó nghĩa là proxy hỗ trợ **traffic HTTPS**, không phải kết nối đến proxy bằng HTTPS.

Khi dùng `https://user:pass@host:port`, Camoufox cố thiết lập TLS handshake đến proxy server, gây lỗi:
```
SSL: UNEXPECTED_EOF_WHILE_READING
```

**Bài học**: Luôn dùng `http://` scheme để kết nối đến proxy, bất kể proxy có hỗ trợ HTTPS traffic hay không.

---

## Khắc phục sự cố

| Vấn đề | Giải pháp |
|---|---|
| `Failed to fetch schedule: refresh retry still could not access FAP` | Phiên hết hạn và re-login thất bại. Kiểm tra logs xem lỗi Turnstile hay FeID. |
| Cloudflare challenge không resolve | Cần residential proxy. Datacenter IP bị Turnstile chặn. |
| FeID login "incorrect password" | Kiểm tra password trong `.env`. **Không** escape `$` trong `.env` file (chỉ escape `$$` trong `docker-compose.yml`). |
| `TargetClosedError` khi mở browser | Thiếu Firefox dependencies. Kiểm tra Dockerfile có `libgtk-3-0 libx11-xcb1 libasound2`. |
| Browser timeout khi khởi động | Profile lock cũ. Code tự xóa profile trước login, nhưng nếu vẫn lỗi, xóa thủ công `data/firefox_profile/`. |
| `No space left on device` khi build | Docker images cũ. Chạy `docker system prune -af --volumes`. |
| Điểm danh/điểm trả về rỗng | Cài `FAP_STUDENT_ID` và `FAP_CAMPUS` trong `.env`. |
| `SSL: UNEXPECTED_EOF_WHILE_READING` | Proxy scheme sai. Dùng `http://` thay vì `https://`. |
| "No classes scheduled!" / "No terms found" dù bot hoạt động | Session FAP hết hạn. `_fetch_page()` nhận login page thay vì data. Bot tự re-login. Nếu vẫn lỗi, restart container. |
| `cannot open display: :99` | Xung đột DISPLAY. Đảm bảo `HEADLESS=true` trong `.env` để dùng Camoufox virtual mode. |
| Thay đổi `.env` không có hiệu lực | `docker restart` không reload env. Dùng `docker compose up -d --force-recreate`. |
| Cloudflare flagging liên tục | Firefox profile cũ bị fingerprint. Code tự xóa profile, nhưng đảm bảo không có process Camoufox khác đang chạy. |

---

## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Bot framework | Discord.py 2.7+ |
| Browser automation | Camoufox 0.4+ (Firefox-based anti-detect) |
| HTML parsing | BeautifulSoup4 + lxml |
| Scheduler | APScheduler 3.x |
| Data validation | Pydantic 2.x |
| Container | Docker + Docker Compose |
| Virtual display | Xvfb |
| Server | DigitalOcean Droplet (SGP1) |

---

## License

MIT

---

## 2026-05 Operational Update

The current production behavior differs from some older sections above:

- Attendance check now uses the actual weekly schedule as the source of truth and only checks from class start until 30 minutes after class end.
- The bot runs a daily check shortly after startup to warm caches and snapshot files.
- Session keepalive now runs every 15 minutes.
- Command fetch failures now go through centralized session recovery and can force re-login when the browser context is gone.
- Login and refresh attempts send Discord notifications for both success and failure.
- Attendance and daily scheduler jobs can also send Discord notifications when no change was detected.
- Runtime proxy override is supported through Discord slash commands and is stored in `data/runtime_config.json`.

New slash commands:

- `/config proxy`
- `/config proxy-clear`

Example:

```text
/config proxy host:42.117.104.123 port:34640 username:muaproxy6a0460879cc96 password:MJIRbFDty14IoFHX proxy_type:HTTPS
```

Important proxy rule:

- Even if the provider labels the proxy type as `HTTPS`, this project must still connect to the proxy using `http://user:pass@host:port`.

Important deployment rule:

- If Python code changed, use `docker compose up -d --build --force-recreate bot`.
- `docker compose up -d --force-recreate` alone is not enough for code changes because source code is baked into the image.
