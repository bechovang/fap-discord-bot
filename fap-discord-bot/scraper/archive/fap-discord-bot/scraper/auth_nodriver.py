"""
FAP Authentication Module - Nodriver Integration (2026 Recommended)
Nodriver API: https://github.com/ultrafunkamsterdam/nodriver
"""
import asyncio
import logging
import json
import os
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

try:
    import nodriver as uc
    HAS_NODRIVER = True
except ImportError:
    HAS_NODRIVER = False
    uc = None

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FAPAuthNodriver:
    """FAP Authentication using Nodriver for Cloudflare bypass"""

    BASE_URL = "https://fap.fpt.edu.vn"
    LOGIN_URL = f"{BASE_URL}/Account/Login.aspx"
    SCHEDULE_URL = f"{BASE_URL}/Report/ScheduleOfWeek.aspx"
    SESSION_TIMEOUT = timedelta(minutes=20)

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        user_agent: str = None,
        data_dir: str = "data"
    ):
        if not HAS_NODRIVER:
            raise ImportError("Nodriver not installed! Run: pip install nodriver")

        self.username = username
        self.password = password
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self._browser = None
        self._session_expiry: Optional[datetime] = None
        self._is_logged_in = False

    async def _init_browser(self) -> None:
        """Initialize Nodriver browser"""
        if self._browser:
            return

        logger.info("Starting Nodriver...")

        # Nodriver browser options
        browser = await uc.start(
            headless=self.headless,
            browser_args=[
                '--no-sandbox',
            ],
            user_agent=self.user_agent
        )

        self._browser = browser
        logger.info("Nodriver browser started")

    async def _check_session_valid(self) -> bool:
        """Check if current session is valid"""
        try:
            page = await self._browser.get(self.SCHEDULE_URL)
            await asyncio.sleep(2)

            current_url = page.url
            if 'Login.aspx' in current_url:
                return False

            content = await page.get_content()
            soup = BeautifulSoup(content, 'lxml')
            user_label = soup.find('span', {'id': 'ctl00_lblLogIn'})

            if user_label and self.username.lower() in user_label.get_text().lower():
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                return True

            return False

        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False

    async def _full_login_flow(self) -> bool:
        """Perform login with Cloudflare handling"""
        try:
            logger.info(f"Starting login for: {self.username}")

            # Navigate to login page
            page = await self._browser.get(self.LOGIN_URL)
            await asyncio.sleep(3)  # Wait for Cloudflare

            # Check for Cloudflare challenge
            current_url = page.url
            if 'challenge' in current_url or 'turnstile' in current_url:
                logger.warning("Cloudflare detected - waiting for auto-bypass...")
                await asyncio.sleep(5)

            # Fill credentials using nodriver API
            logger.info("Filling credentials...")

            # Select username input and send keys
            username_input = await page.select('input[name="ctl00$mainContent$UserName"]')
            await asyncio.sleep(0.5)
            await username_input.send_keys(self.username)

            # Select password input and send keys
            password_input = await page.select('input[name="ctl00$mainContent$Password"]')
            await password_input.send_keys(self.password)

            # Submit form
            logger.info("Submitting login form...")
            await page.evaluate('''
                () => {
                    const form = document.forms['aspnetForm'];
                    if (form) {
                        document.getElementById('__EVENTTARGET').value = 'ctl00$mainContent$btnLogin';
                        document.getElementById('__EVENTARGUMENT').value = '';
                        form.submit();
                    }
                }
            ''')

            # Wait for navigation
            await asyncio.sleep(5)

            current_url = page.url
            if 'Login.aspx' not in current_url:
                logger.info("Login successful!")
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                self._is_logged_in = True
                return True
            else:
                logger.error("Login failed")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def get_session(self, force_refresh: bool = False) -> bool:
        """Get authenticated session"""
        try:
            await self._init_browser()

            if not force_refresh and self._is_logged_in:
                if self._session_expiry and datetime.now() < self._session_expiry:
                    if await self._check_session_valid():
                        return True
                self._is_logged_in = False

            if await self._full_login_flow():
                return True
            return False

        except Exception as e:
            logger.error(f"Session error: {e}")
            return False

    async def fetch_schedule(self, week: Optional[int] = None, year: int = None) -> Optional[str]:
        """Fetch schedule HTML"""
        try:
            if not await self.get_session():
                return None

            logger.info("Fetching schedule...")
            page = await self._browser.get(self.SCHEDULE_URL)
            await asyncio.sleep(2)

            content = await page.get_content()
            self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
            return content

        except Exception as e:
            logger.error(f"Fetch schedule error: {e}")
            return None

    def close(self) -> None:
        """Close browser"""
        if self._browser:
            self._browser.stop()
            self._browser = None
            self._is_logged_in = False
            logger.info("Browser closed")

    async def __aenter__(self):
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self.close()


# Test function
async def test_nodriver():
    """Test Nodriver with FAP"""
    print("=" * 50)
    print("Testing FAP with Nodriver (2026)")
    print("=" * 50)

    from dotenv import load_dotenv
    load_dotenv()

    auth = FAPAuthNodriver(
        username=os.getenv('FAP_USERNAME'),
        password=os.getenv('FAP_PASSWORD'),
        headless=False,  # Show browser
        data_dir='data'
    )

    try:
        print("[.] Connecting to FAP via Nodriver...")
        success = await auth.get_session()

        if success:
            print("[+] Login successful!")

            html = await auth.fetch_schedule()
            if html:
                from scraper.parser import FAPParser
                parser = FAPParser()
                items = parser.parse_schedule(html)
                print(f"[+] Found {len(items)} classes!")

                if items:
                    print("\n[Sample Classes]:")
                    for item in items[:3]:
                        print(f"  - {item.subject_code} | {item.day} {item.date}")
        else:
            print("[X] Login failed")

    except Exception as e:
        print(f"[X] Error: {e}")
    finally:
        await auth.close()


if __name__ == "__main__":
    asyncio.run(test_nodriver())
