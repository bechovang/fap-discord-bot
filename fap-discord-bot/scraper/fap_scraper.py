"""
FAP Scraper - Unified session management
Uses existing session, auto-login only when needed
"""
import asyncio
import os
import logging
from playwright.async_api import async_playwright
from pathlib import Path
from .auto_login_feid import FAPAutoLogin

logger = logging.getLogger(__name__)


class FAPScraper:
    """Unified scraper with session management"""

    def __init__(self, feid: str = None, password: str = None, data_dir: str = "data"):
        self.feid = feid or os.environ.get("FAP_FEID")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.data_dir = Path(data_dir)
        self.profile_dir = self.data_dir / "chrome_profile"

    async def fetch_page(self, url: str, max_retries: int = 2) -> str:
        """
        Fetch page with auto-login if needed

        Args:
            url: URL to fetch
            max_retries: Max login attempts

        Returns:
            HTML content or None
        """
        # Kill existing Chrome processes before launching
        import subprocess
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.sleep(1)
        except:
            pass

        for attempt in range(max_retries):
            async with async_playwright() as p:
                # Use headless for normal fetch, non-headless for login
                is_login_attempt = (attempt > 0)

                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=not is_login_attempt,  # Non-headless when re-trying after login
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )

                page = browser.pages[0] if browser.pages else await browser.new_page()

                # Navigate to target page
                await page.goto(url, timeout=30000)
                await asyncio.sleep(2)

                content = await page.content()
                current_url = page.url

                # Check if redirected to login
                if 'Login' in content or 'Default.aspx' in current_url:
                    if attempt < max_retries - 1:
                        logger.warning(f"Session expired - auto login (attempt {attempt + 1})...")
                        await browser.close()

                        # Auto login (non-headless)
                        success = await self._auto_login()
                        if not success:
                            return None

                        # Retry after login
                        continue
                    else:
                        await browser.close()
                        return None

                # Check if page has expected content
                if self._is_valid_page(content, url):
                    await browser.close()
                    return content

                await browser.close()

        return None

    def _is_valid_page(self, content: str, url: str) -> bool:
        """Check if page is valid (not login/error)"""
        # For exam page
        if 'Exam' in url or 'exam' in url.lower():
            return 'Schedule Exam' in content or 'table' in content.lower()

        # For schedule page
        if 'Schedule' in url:
            return 'ctl00_mainContent_drpSelectWeek' in content

        # Default: check if not login page
        return 'Login' not in content and 'ctl00_mainContent_divContent' in content

    async def _auto_login(self) -> bool:
        """Run auto login"""
        if not self.feid or not self.password:
            logger.error("Cannot auto-login - missing credentials")
            return False

        logger.info("Running auto_login_feid.py...")

        auth = FAPAutoLogin(
            headless=False,  # Non-headless for Cloudflare
            feid=self.feid,
            password=self.password
        )

        return await auth.auto_login()

    async def fetch_exam_schedule(self) -> str:
        """Fetch exam schedule"""
        return await self.fetch_page("https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx")

    async def fetch_class_schedule(self, week: int = None, year: int = None) -> str:
        """Fetch class schedule"""
        url = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
        if week or year:
            params = []
            if week:
                params.append(f"week={week}")
            if year:
                params.append(f"year={year}")
            # Note: FAP uses POST, not GET for week selection
            # This is simplified - would need proper POST handling

        return await self.fetch_page(url)


# Convenience functions
async def get_exam_schedule() -> str:
    """Get exam schedule"""
    scraper = FAPScraper()
    return await scraper.fetch_exam_schedule()


async def get_class_schedule(week: int = None) -> str:
    """Get class schedule"""
    scraper = FAPScraper()
    return await scraper.fetch_class_schedule(week)
