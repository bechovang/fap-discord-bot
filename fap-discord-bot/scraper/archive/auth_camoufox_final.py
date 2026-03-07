"""
FAP Authentication using Camoufox (2026)
Login flow: FEID (feid.fpt.edu.vn) -> FAP (fap.fpt.edu.vn)
"""
import asyncio
import logging
import os
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from camoufox.async_api import AsyncCamoufox
    HAS_CAMOUFOX = True
except ImportError:
    HAS_CAMOUFOX = False
    AsyncCamoufox = None

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FAPAuthCamoufox:
    """FAP Authentication using Camoufox stealth browser"""

    BASE_URL = "https://fap.fpt.edu.vn"
    FEID_LOGIN_URL = "https://feid.fpt.edu.vn/Account/Login"
    SCHEDULE_URL = f"{BASE_URL}/Report/ScheduleOfWeek.aspx"
    SESSION_TIMEOUT = timedelta(hours=2)

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = False,
        data_dir: str = "data"
    ):
        if not HAS_CAMOUFOX:
            raise ImportError("Camoufox not installed! Run: pip install camoufox")

        self.username = username
        self.password = password
        self.headless = headless
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self._browser = None
        self._page = None
        self._session_expiry: Optional[datetime] = None
        self._is_logged_in = False

    async def _init_browser(self) -> None:
        """Initialize Camoufox browser"""
        if self._browser:
            return

        logger.info("Starting Camoufox...")

        # Create and start Camoufox browser
        camoufox = AsyncCamoufox(
            headless=self.headless,
        )
        self._browser = await camoufox.start()

        # Get or create page - Camoufox uses contexts
        try:
            contexts = self._browser.contexts
            if contexts and len(contexts) > 0:
                context = contexts[0]
                pages = context.pages
                if pages and len(pages) > 0:
                    self._page = pages[0]
                else:
                    self._page = await context.new_page()
            else:
                self._page = await self._browser.new_page()
        except:
            self._page = await self._browser.new_page()

        logger.info("Camoufox browser started")

    async def login_with_google(self) -> bool:
        """
        Login to FAP using Google account
        Returns True if successful
        """
        try:
            await self._init_browser()

            logger.info("Navigating to FAP schedule page...")
            await self._page.goto(self.SCHEDULE_URL, timeout=60000)
            await asyncio.sleep(5)

            current_url = str(self._page.url)
            logger.info(f"Current URL: {current_url}")

            # Check if we need to login
            if 'feid.fpt.edu.vn' in current_url or 'Login' in current_url:
                logger.info("Login required - waiting for Google login button...")

                # Look for Google login button
                await asyncio.sleep(3)

                # Try to find and click Google login button
                try:
                    # Wait for any button with "Google" text
                    google_btn = await self._page.wait_for_selector('button:has-text("Google"), .btn-google, a[href*="google"]', timeout=15000)
                    if google_btn:
                        logger.info("Found Google login button - clicking...")
                        await google_btn.click()
                        logger.info("Google login clicked - please complete authentication in browser...")
                except:
                    logger.info("Google button not found, showing login page...")

                # Wait for user to complete login
                logger.info("=" * 50)
                logger.info("PLEASE COMPLETE LOGIN IN THE BROWSER WINDOW")
                logger.info("1. Select your Google account")
                logger.info("2. Complete authentication if needed")
                logger.info("3. Wait for redirect to FAP")
                logger.info("=" * 50)

                # Wait up to 120 seconds for user to complete login
                for i in range(120):
                    await asyncio.sleep(1)
                    current_url = str(self._page.url)

                    if 'fap.fpt.edu.vn' in current_url and 'Login' not in current_url:
                        logger.info(f"Login successful! Redirected to: {current_url}")
                        self._is_logged_in = True
                        self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                        return True

                    if i % 10 == 0:
                        logger.info(f"Waiting for login... {i}s")

                logger.error("Login timeout - user did not complete login in time")
                return False

            else:
                logger.info("Already logged in or no login required!")
                self._is_logged_in = True
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                return True

        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fetch_schedule(self, week: Optional[int] = None, year: int = None) -> Optional[str]:
        """Fetch schedule HTML"""
        try:
            if not self._is_logged_in:
                if not await self.login_with_google():
                    return None

            logger.info("Fetching schedule...")
            await self._page.goto(self.SCHEDULE_URL, timeout=30000)
            await asyncio.sleep(3)

            # Select week if specified
            if week is not None:
                await self._page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))

            if year is not None:
                await self._page.select_option('#ctl00_mainContent_drpYear', str(year))

            await asyncio.sleep(2)

            content = await self._page.content()
            self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
            return content

        except Exception as e:
            logger.error(f"Fetch schedule error: {e}")
            return None

    async def close(self) -> None:
        """Close browser"""
        if self._browser:
            try:
                await self._browser.close()
            except:
                pass  # Camoufox returns Playwright browser, use close()
            self._browser = None
            self._page = None
            self._is_logged_in = False
            logger.info("Browser closed")

    async def __aenter__(self):
        await self.login_with_google()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Test function
async def test_camoufox():
    """Test Camoufox with FAP"""
    print("=" * 50)
    print("FAP Authentication Test - Camoufox (2026)")
    print("=" * 50)

    from dotenv import load_dotenv
    load_dotenv()

    auth = FAPAuthCamoufox(
        username=os.getenv('FAP_USERNAME'),
        password=os.getenv('FAP_PASSWORD'),
        headless=False,  # Show browser for Google login
        data_dir='data'
    )

    try:
        print("[.] Starting authentication...")
        success = await auth.login_with_google()

        if success:
            print("[+] Login successful!")

            html = await auth.fetch_schedule()
            if html:
                # Save HTML for debugging
                with open('camoufox_schedule.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("[+] Saved HTML to camoufox_schedule.html")

                # Try to parse if available
                try:
                    from scraper.parser import FAPParser
                    parser = FAPParser()
                    items = parser.parse_schedule(html)
                    print(f"[+] Found {len(items)} classes!")

                    if items:
                        print("\n[Sample Classes]:")
                        for item in items[:5]:
                            print(f"  - {item.subject_code} | {item.day} {item.date} | {item.room}")
                except ImportError:
                    print("[!] Parser module not available, but schedule HTML was saved successfully!")
        else:
            print("[X] Login failed or timed out")

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[.] Press Enter to close browser...")
        input()
        await auth.close()

if __name__ == "__main__":
    asyncio.run(test_camoufox())
