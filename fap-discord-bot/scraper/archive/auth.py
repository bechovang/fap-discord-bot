"""
FAP Authentication Module
Handles login, session management, and auto-recovery
"""
import os
import json
import logging
import asyncio
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta
from patchright.async_api import async_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup
from .cloudflare import TurnstileSolver

logger = logging.getLogger(__name__)


class FAPAuth:
    """
    FAP Portal Authentication Handler
    Supports username/password login with session persistence
    """

    # FAP URLs
    BASE_URL = "https://fap.fpt.edu.vn"
    LOGIN_URL = f"{BASE_URL}/Account/Login.aspx"
    SCHEDULE_URL = f"{BASE_URL}/Report/ScheduleOfWeek.aspx"

    # Session settings
    SESSION_TIMEOUT = timedelta(minutes=20)
    COOKIE_FILE = "data/cookies.json"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        user_agent: str = None,
        data_dir: str = "data"
    ):
        self.username = username
        self.password = password
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Session state
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._session_expiry: Optional[datetime] = None
        self._is_logged_in = False

        # Turnstile solver
        self.turnstile = TurnstileSolver(headless=headless, user_agent=self.user_agent)

    async def _init_browser(self) -> None:
        """Initialize browser with stealth settings"""
        if self._browser is None:
            self._playwright = await async_playwright().start()

            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]

            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )

            # Create context with persistent storage
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.user_agent,
                locale='en-US',
                timezone_id='Asia/Ho_Chi_Minh'
                
            )

            # Load saved cookies if available
            await self._load_cookies()

            self._page = await self._context.new_page()

    async def _load_cookies(self) -> None:
        """Load cookies from file"""
        cookie_file = self.data_dir / "cookies.json"
        if cookie_file.exists():
            try:
                with open(cookie_file, 'r') as f:
                    cookies = json.load(f)
                await self._context.add_cookies(cookies)
                logger.info("Loaded saved cookies")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

    async def _save_cookies(self) -> None:
        """Save cookies to file"""
        try:
            cookies = await self._context.cookies()
            cookie_file = self.data_dir / "cookies.json"
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info("Saved cookies to file")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")

    async def _check_session_valid(self) -> bool:
        """Check if current session is valid"""
        try:
            response = await self._page.goto(
                self.SCHEDULE_URL,
                wait_until='networkidle',
                timeout=15000
            )

            if response.status != 200:
                return False

            # Check if redirected to login page
            current_url = self._page.url
            if 'Login.aspx' in current_url:
                logger.info("Session expired - redirected to login")
                return False

            # Check for user indicator in page
            content = await self._page.content()
            soup = BeautifulSoup(content, 'lxml')

            # Look for user email/label
            user_label = soup.find('span', {'id': 'ctl00_lblLogIn'})
            if user_label and self.username.lower() in user_label.get_text().lower():
                logger.info(f"Session valid for user: {user_label.get_text()}")
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                return True

            return False

        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False

    async def _full_login_flow(self) -> bool:
        """
        Perform full login flow with username/password
        Handles Cloudflare Turnstile if present
        """
        try:
            logger.info(f"Starting login flow for: {self.username}")

            # Navigate to login page
            await self._page.goto(self.LOGIN_URL, wait_until='networkidle', timeout=30000)

            # Wait for form to load
            await self._page.wait_for_selector('form[name="aspnetForm"]', timeout=10000)

            # Check for Turnstile
            turnstile_token = await self.turnstile.solve_turnstile(self._page, timeout=15000)
            if turnstile_token:
                logger.info("Turnstile solved successfully")

            # Fill in credentials
            await self._page.fill('input[name="ctl00$mainContent$UserName"]', self.username)
            await self._page.fill('input[name="ctl00$mainContent$Password"]', self.password)

            # Handle ASP.NET form submission
            await self._page.evaluate('''
                () => {
                    const form = document.forms['aspnetForm'];
                    if (form) {
                        document.getElementById('__EVENTTARGET').value = 'ctl00$mainContent$btnLogin';
                        document.getElementById('__EVENTARGUMENT').value = '';
                        form.submit();
                    }
                }
            ''')

            # Wait for navigation after login
            await self._page.wait_for_url(
                lambda url: 'Login.aspx' not in url,
                timeout=30000
            )

            # Verify login success
            current_url = self._page.url
            if 'Login.aspx' not in current_url and 'LoginFailed' not in current_url:
                logger.info("Login successful!")

                # Save session
                await self._save_cookies()
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                self._is_logged_in = True
                return True
            else:
                # Check for error messages
                content = await self._page.content()
                if 'Login failed' in content or 'sai' in content.lower():
                    logger.error("Login failed: Invalid credentials")
                else:
                    logger.error("Login failed - unknown reason")
                return False

        except Exception as e:
            logger.error(f"Login flow error: {e}")
            return False

    async def get_session(self, force_refresh: bool = False) -> Optional[Page]:
        """
        Get authenticated session page

        Args:
            force_refresh: Force re-authentication even if session is valid

        Returns:
            Authenticated Page object or None if failed
        """
        try:
            await self._init_browser()

            # Check if session is still valid
            if not force_refresh and self._is_logged_in:
                if self._session_expiry and datetime.now() < self._session_expiry:
                    if await self._check_session_valid():
                        return self._page
                else:
                    logger.info("Session expired - need to re-login")
                    self._is_logged_in = False

            # Perform login
            if await self._full_login_flow():
                return self._page
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    async def fetch_schedule(self, week: Optional[int] = None, year: int = None) -> Optional[str]:
        """
        Fetch schedule HTML for given week/year

        Args:
            week: Week number (1-52), None for current week
            year: Year, None for current year

        Returns:
            HTML content or None if failed
        """
        try:
            page = await self.get_session()
            if not page:
                logger.error("Cannot fetch schedule - no valid session")
                return None

            # Navigate to schedule page
            await page.goto(self.SCHEDULE_URL, wait_until='networkidle', timeout=30000)

            # Select week if specified
            if week is not None:
                await page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))

            # Select year if specified
            if year is not None:
                await page.select_option('#ctl00_mainContent_drpYear', str(year))

            # Wait for table to load
            await page.wait_for_selector('table tbody tr', timeout=10000)

            # Get HTML content
            content = await page.content()

            # Update session expiry
            self._session_expiry = datetime.now() + self.SESSION_TIMEOUT

            return content

        except Exception as e:
            logger.error(f"Failed to fetch schedule: {e}")
            return None

    async def close(self) -> None:
        """Close browser and cleanup"""
        if self._browser:
            await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._browser = None
            self._context = None
            self._page = None
            self._is_logged_in = False
            logger.info("Browser closed")

    async def __aenter__(self):
        """Context manager entry"""
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
