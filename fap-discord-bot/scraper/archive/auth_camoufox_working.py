"""
FAP Authentication using Camoufox (2026)
Handles Cloudflare Turnstile challenge properly
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

logger = logging.getLogger(__name__)


class FAPAuthCamoufox:
    """FAP Authentication using Camoufox stealth browser"""

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    SESSION_TIMEOUT = timedelta(hours=2)

    def __init__(
        self,
        headless: bool = False,
        data_dir: str = "data"
    ):
        if not HAS_CAMOUFOX:
            raise ImportError("Camoufox not installed! Run: pip install camoufox")

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
        camoufox = AsyncCamoufox(headless=self.headless)
        self._browser = await camoufox.start()

        # Get or create page
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

    async def _wait_for_cloudflare(self, timeout: int = 60) -> bool:
        """Wait for Cloudflare challenge to complete"""
        logger.info("Waiting for Cloudflare challenge...")

        for i in range(timeout):
            await asyncio.sleep(1)

            # Check current URL
            current_url = str(self._page.url)

            # If we're no longer on Cloudflare challenge page
            if 'Just a moment' not in await self._page.title() and 'cloudflare' not in current_url.lower():
                logger.info(f"Cloudflare bypassed! Current URL: {current_url}")
                return True

            if i % 10 == 0:
                logger.info(f"Still waiting for Cloudflare... {i}s")

        logger.error("Cloudflare challenge timeout")
        return False

    async def _wait_for_login_redirect(self, timeout: int = 120) -> bool:
        """Wait for user to complete Google login and redirect to FAP"""
        logger.info("=" * 50)
        logger.info("PLEASE COMPLETE LOGIN IN THE BROWSER WINDOW")
        logger.info("1. Click Google login button")
        logger.info("2. Select your account")
        logger.info("3. Complete authentication")
        logger.info("=" * 50)

        for i in range(timeout):
            await asyncio.sleep(1)

            current_url = str(self._page.url)

            # Check if we've been redirected to FAP main page (not login)
            if 'fap.fpt.edu.vn' in current_url and 'Login' not in current_url:
                logger.info(f"Login successful! Redirected to: {current_url}")

                # Wait a bit more for page to stabilize
                await asyncio.sleep(3)
                return True

            if i % 15 == 0:
                logger.info(f"Waiting for login... {i}s")
                current_title = await self._page.title()
                logger.info(f"  Current: {current_title[:50]}...")

        logger.error("Login timeout")
        return False

    async def login(self) -> bool:
        """Login to FAP using Google account"""
        try:
            await self._init_browser()

            # Navigate to schedule page - this will trigger redirect to login
            logger.info("Navigating to FAP schedule page...")
            await self._page.goto(self.SCHEDULE_URL, timeout=60000)
            await asyncio.sleep(3)

            current_url = str(self._page.url)
            logger.info(f"Current URL: {current_url}")

            # Step 1: Wait for Cloudflare if present
            page_content = await self._page.content()
            if 'Just a moment' in page_content or 'cloudflare' in page_content.lower():
                if not await self._wait_for_cloudflare(timeout=60):
                    return False
                await asyncio.sleep(2)

            # Step 2: Check if login is required
            current_url = str(self._page.url)

            if 'feid.fpt.edu.vn' in current_url or 'Login' in current_url:
                # Need to login
                if not await self._wait_for_login_redirect(timeout=120):
                    return False
            else:
                logger.info("Already logged in or no login required!")

            # Step 3: Verify we can access schedule
            # Navigate to schedule page again to be sure
            await self._page.goto(self.SCHEDULE_URL, timeout=30000)
            await asyncio.sleep(5)

            current_url = str(self._page.url)
            page_content = await self._page.content()

            # Final check - make sure we're not on Cloudflare or login page
            if 'Just a moment' in page_content:
                logger.error("Still on Cloudflare page after login!")
                return False

            if 'Login' in current_url:
                logger.error("Still on login page!")
                return False

            logger.info("Successfully accessed FAP!")
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
                if not await self.login():
                    return None

            logger.info("Fetching schedule...")
            await self._page.goto(self.SCHEDULE_URL, timeout=30000)

            # Wait for page to load (might hit Cloudflare again)
            await asyncio.sleep(5)

            # Check if we hit Cloudflare again
            page_content = await self._page.content()
            if 'Just a moment' in page_content:
                logger.info("Cloudflare detected, waiting...")
                if not await self._wait_for_cloudflare():
                    return None
                await asyncio.sleep(2)

            # Select week if specified
            if week is not None:
                await self._page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))

            if year is not None:
                await self._page.select_option('#ctl00_mainContent_drpYear', str(year))

            await asyncio.sleep(3)

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
                pass
            self._browser = None
            self._page = None
            self._is_logged_in = False
            logger.info("Browser closed")


# Test function
async def test_camoufox():
    """Test Camoufox with FAP"""
    print("=" * 50)
    print("FAP Authentication Test - Camoufox (2026)")
    print("=" * 50)

    auth = FAPAuthCamoufox(
        headless=False,  # Show browser for login
        data_dir='data'
    )

    try:
        print("[.] Starting authentication...")
        success = await auth.login()

        if success:
            print("[+] Login successful!")

            html = await auth.fetch_schedule()
            if html:
                # Save HTML
                with open('fap_schedule.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("[+] Saved HTML to fap_schedule.html")

                # Check if it's real schedule or Cloudflare
                if 'Just a moment' in html:
                    print("[!] Still got Cloudflare page - need to wait longer")
                elif 'ctl00_mainContent_drpSelectWeek' in html:
                    print("[+] Got real FAP schedule page!")

                    # Try to parse
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
                        print("[!] Parser not available, but schedule HTML was saved!")
                else:
                    print("[?] Unknown page content")
        else:
            print("[X] Login failed or timed out")

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[.] Keeping browser open for 30 seconds for inspection...")
        await asyncio.sleep(30)
        await auth.close()

if __name__ == "__main__":
    asyncio.run(test_camoufox())
