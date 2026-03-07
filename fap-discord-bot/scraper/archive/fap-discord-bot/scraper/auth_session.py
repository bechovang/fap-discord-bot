"""
FAP Authentication - Using Saved Session (Simplest Solution)
Skip login entirely - use your existing browser session
"""
import asyncio
import logging
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from patchright.async_api import async_playwright
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FAPAuthSession:
    """
    FAP Authentication using saved browser session
    This bypasses Cloudflare by using your real browser cookies
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    SESSION_TIMEOUT = timedelta(hours=2)

    def __init__(
        self,
        headless: bool = True,
        user_data_dir: str = "data"
    ):
        self.headless = headless
        self.user_data_dir = Path(user_data_dir)
        self.user_data_dir.mkdir(exist_ok=True)

        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def _init_browser(self) -> None:
        """Initialize browser with user session"""
        if self._browser:
            return

        self._playwright = await async_playwright().start()

        # Use existing Chrome user data directory
        user_data_dir = self.user_data_dir / "chrome_profile"

        self._browser = await _playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=self.headless,
            args=['--no-sandbox']
        )

        self._context = self._browser
        self._page = await self._context.new_page()

    async def fetch_schedule(self, week: Optional[int] = None, year: int = None) -> Optional[str]:
        """Fetch schedule using saved session"""
        try:
            await self._init_browser()

            logger.info("Fetching schedule with saved session...")

            # Go to schedule page
            await self._page.goto(self.SCHEDULE_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            # Check if we're logged in
            content = await self._page.content()
            soup = BeautifulSoup(content, 'lxml')

            user_label = soup.find('span', {'id': 'ctl00_lblLogIn'})
            if not user_label or 'logout' not in content:
                logger.error("Not logged in! Please login in Chrome first:")
                logger.error("1. Open Chrome")
                logger.error("2. Go to https://fap.fpt.edu.vn")
                logger.error("3. Login with your Google account")
                logger.error("4. Close Chrome")
                logger.error("")
                logger.error("Then run this script again.")
                return None

            logger.info(f"Logged in as: {user_label.get_text()}")

            # Select week if specified
            if week is not None:
                await self._page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))

            if year is not None:
                await self._page.select_option('#ctl00_mainContent_drpYear', str(year))

            await asyncio.sleep(2)
            content = await self._page.content()

            logger.info("Schedule fetched successfully!")
            return content

        except Exception as e:
            logger.error(f"Fetch schedule error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def close(self) -> None:
        """Close browser"""
        if self._browser:
            await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._browser = None
            self._context = None
            self._page = None
            self._playwright = None
            logger.info("Browser closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Simple test
async def test_session():
    """Test using saved session"""
    print("=" * 50)
    print("FAP Bot - Using Saved Session")
    print("=" * 50)

    auth = FAPAuthSession(
        headless=False,  # Show browser
        user_data_dir='data'
    )

    try:
        print("[.] Fetching schedule with saved session...")
        html = await auth.fetch_schedule()

        if html:
            from scraper.parser import FAPParser
            parser = FAPParser()
            items = parser.parse_schedule(html)

            print(f"[+] Found {len(items)} classes!")

            if items:
                print("\n[Sample Classes]:")
                for item in items[:5]:
                    print(f"  - {item.subject_code} | {item.day} {item.date} | {item.room}")

            print("\n[+] SUCCESS! Your saved session works!")
        else:
            print("[X] Failed - need to login in Chrome first")

    except Exception as e:
        print(f"[X] Error: {e}")
    finally:
        await auth.close()


if __name__ == "__main__":
    asyncio.run(test_session())
