# 🚀 FAP Bot - Nodriver Setup (2026 Recommended)

## 📦 Cài Đặt Nodriver

```bash
pip install nodriver
```

## 🔥 Nodriver vs PatchRight vs Browserless

| Tool | 2026 Status | Cloudflare Bypass | Setup |
|------|------------|-------------------|-------|
| **Nodriver** | ✅ Active | ⭐⭐⭐⭐⭐ Best | Easy |
| PatchRight | ✅ Active | ⭐⭐⭐ Good | Medium |
| Browserless | ✅ Active | ⭐⭐⭐⭐ Very Good | Complex (Docker) |

## 🎯 Tại Sao Nodriver?

✅ **Successor to undetected-chromedriver** (cùng tác giả)
✅ **No WebDriver patches needed**
✅ **Direct Chrome DevTools Protocol**
✅ **Active development** (cập nhật liên tục)
✅ **Native stealth** chống Cloudflare Turnstile

## 🧪 Test Nodriver

```bash
cd fap-discord-bot
python scraper/auth_nodriver.py
```

Hoặc chạy với visible mode (headless=False):
```bash
python scraper/auth_nodriver.py
```

## 📝 Code Ví Dụ

```python
import nodriver as uc
import asyncio

async def fap_scraper():
    # Start browser với stealth
    browser = await uc.start(headless=False)

    # Navigate to FAP
    page = await browser.get('https://fap.fpt.edu.vn/Account/Login.aspx')

    # Nodriver tự động bypass Cloudflare!
    await page.find_element('input[name="ctl00$mainContent$UserName"]').send_keys('username')
    await page.find_element('input[name="ctl00$mainContent$Password"]').send_keys('password')

    # Submit form
    # ... extraction code ...

    await browser.stop()

asyncio.run(fap_scraper())
```

## ⚙️ Config trong .env

```env
HEADLESS=false  # True = ẩn browser, False = hiện browser
```

## 🔄 So Sánh Với Turnstile-Solver

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| **Nodriver** | Tự động bypass, không cần external service | Phải cài nodriver |
| **Turnstile-Solver** | Có sẵn trong repo | Phải tự solve challenge |
| **Browserless** | Managed service | Phức tạp, cần Docker |

## 📚 References

- Nodriver GitHub: https://github.com/ultrafunkamsterdam/nodriver
- ScrapFly 2026 Cloudflare Guide: (bài viết bạn gửi)
- FAP Turnstile: Cloudflare's modern CAPTCHA

---

**Khuyến nghị**: Dùng **Nodriver** cho FAP Bot 2026!
