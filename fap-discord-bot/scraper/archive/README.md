# Các file Scraper đã lưu trữ (Archived)

Các file này được lưu trữ trong quá trình dọn dẹp ngày 2026-03-07.

---

## 📋 Tóm tắt

| Hạng mục | Số lượng |
|----------|----------|
| Modules Auth Experiment | 11 |
| Files Test | 9 |
| Files Tài liệu | 4 |
| Scripts Tiện ích | 4 |
| Thư mục Trùng lặp | 1 |
| **Tổng** | **29** |

---

## 🎯 Solution đang hoạt động

Bot giờ dùng kiến trúc sạch này:

```
scraper/
├── auth.py                 ← Adapter (interface FAPAuth tương thích bot)
├── auto_login_feid.py      ← Auth chính (FeID + Playwright + FlareSolverr)
├── flaresolverr_auth.py    ← FlareSolverr integration
├── cloudflare.py           ← Turnstile solver
└── parser.py               ← HTML parser
```

### Flow Authentication
1. **FlareSolverr** (Docker) - Tự động bypass Cloudflare
2. **FAPAutoLogin** - Tự động hóa FeID OAuth
3. **Export Cookie** - Lưu vào `data/fap_cookies.json`
4. **FAPAuth Adapter** - Interface tương thích bot

---

## 🗂️ Files đã lưu trữ

### Modules Authentication (Experiment)

| File | Phương pháp | Lý do lưu trữ |
|------|-------------|---------------|
| `auth.py` | Patchright + Turnstile | Thay thế bằng FlareSolverr |
| `auth_browserless.py` | Browserless.io | Thay thế bằng FlareSolverr |
| `auth_camoufox.py` | Camoufox stealth | Experiment, không cần |
| `auth_camoufox_final.py` | Camoufox (v2) | Experiment |
| `auth_camoufox_working.py` | Camoufox (v3) | Experiment |
| `auth_nodriver.py` | Nodriver | Experiment |
| `auth_session_simple.py` | Session-based | Đã tích hợp vào solution chính |
| `hybrid_auth.py` | Hybrid approach | Experiment |
| `persistent_chromium.py` | Persistent profile | Đã tích hợp vào solution chính |
| `persistent_profile.py` | Profile management | Đã tích hợp vào solution chính |
| `flaresolverr_auth.py` | FlareSolverr | **ĐÃ CHUYỂN LÊN PARENT** (solution hoạt động) |

### Files Test

| File | Mục đích |
|------|----------|
| `test_auth.py` | Test auth module |
| `test_camoufox_simple.py` | Test Camoufox |
| `test_debug.py` | Debug utilities |
| `test_fap.py` | Test FAP integration |
| `test_fap_browserless.py` | Test Browserless |
| `test_parser.py` | Test parser (đã chuyển lên parent) |
| `test_session.py` | Test session |
| `test_session_auth.py` | Test session auth |
| `test_session_validity.py` | Test session validity |
| `test_simple.py` | Test đơn giản |

### Scripts Tiện ích

| File | Mục đích |
|------|----------|
| `check_session_duration.py` | Kiểm tra thời gian session |
| `save_session.py` | Lưu session |
| `setup_profile.py` | Thiết lập profile |
| `use_profile.py` | Sử dụng profile |

### Tài liệu (Đã lưu trữ)

| File | Nội dung |
|------|----------|
| `FAP-AUTH-COMPARISON.md` | So sánh các phương pháp auth |
| `FAP-AUTH-COMPLETE-GUIDE.md` | Hướng dẫn auth đầy đủ |
| `FAP-AUTH-SUMMARY.md` | Tóm tắt auth |
| `PERSISTENT-PROFILE-GUIDE.md` | Hướng dẫn persistent profile |

**Lưu ý:** Tài liệu chính được giữ ở parent:
- `FAP-SOLUTION-ARCHITECTURE.md`
- `FLARESOLVERR-GUIDE.md`
- `README.md`

### Thư mục Trùng lặp

| Path | Lý do |
|------|-------|
| `fap-discord-bot/` | Trùng lặp với thư mục cha |

---

## 🔄 Quyết định

### Các phương pháp đã thử

1. **Camoufox** - Stealth browser để bypass Cloudflare
   - ❌ Không ổn định, cần can thiệp thủ công
   - ✅ Giúp hiểu hành vi Cloudflare

2. **Nodriver** - Async browser automation
   - ❌ API phức tạp, tài liệu ít
   - ✅ Học async patterns

3. **Browserless** - Remote browser service
   - ❌ Cần thêm infrastructure
   - ✅ Gợi ý FlareSolverr approach

4. **Patchright + Turnstile** - Giải Turnstile
   - ❌ Turnstile detection thay đổi
   - ✅ Hiểu về Cloudflare

5. **FlareSolverr** - Docker-based anti-bot bypass ✅
   - ✅ **NGƯỜI THẮNG** - Ổn định, được maintain, cập nhật liên tục

### Bài học chính

- **Persistent profile một mình không đủ** - Cloudflare phát hiện automation
- **Export cookie là cần thiết** - JSON export ổn định, SQLite thì không
- **FeID OAuth dễ dự đoán** - Form HTML chuẩn, không CAPTCHA
- **FlareSolverr là giải pháp** - Được maintain tích cực chống Cloudflare

---

## 🔧 Quy trình Restore

Nếu cần tham khảo hoặc khôi phục file đã lưu trữ:

```bash
# Di chuyển về thư mục cha
mv scraper/archive/auth_nodriver.py scraper/
mv scraper/archive/test_auth.py scraper/

# Hoặc restore tài liệu
mv scraper/archive/FAP-AUTH-COMPARISON.md .
```

---

## 📚 Tham khảo

Để kiến trúc và implementation hiện tại, xem:
- **README.md (parent)** - Tài liệu chính
- **FAP-SOLUTION-ARCHITECTURE.md** - Kiến trúc chi tiết
- **FLARESOLVERR-GUIDE.md** - Hướng dẫn FlareSolverr

---

*Lưu trữ ngày: 2026-03-07*
*Tool dọn dẹp: cleanup_scraper.py*
*Báo cáo: cleanup_report.json*
