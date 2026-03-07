"""
FAP Authentication Module - Browserless Integration
Uses browserless.io or stealth Playwright for Cloudflare bypass
"""
import os
import json
import logging
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
from patchright.async_api import async_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FAPAuthBrowserless:
    """
    FAP Authentication using Browserless for Cloudflare bypass

    Options:
    1. Use browserless service (Docker): Set BROWSERLESS_URL env var
    2. Use stealth mode locally: Default behavior
    """

    BASE_URL = "https://fap.fpt.edu.vn"
    LOGIN_URL = f"{BASE_URL}/Account/Login.aspx"
    SCHEDULE_URL = f"{BASE_URL}/Report/ScheduleOfWeek.aspx"
    SESSION_TIMEOUT = timedelta(minutes=20)

    def __init__(
        self,
        username: str,
        password: str,
        browserless_url: str = None,
        headless: bool = True,
        user_agent: str = None,
        data_dir: str = "data"
    ):
        self.username = username
        self.password = password
        self.browserless_url = browserless_url or os.getenv("BROWSERLESS_URL", "ws://localhost:3000")
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._session_expiry: Optional[datetime] = None
        self._is_logged_in = False
        self._use_browserless = bool(browserless_url or os.getenv("BROWSERLESS_URL"))

    async def _init_browser(self) -> None:
        """Initialize browser - using browserless or local stealth mode"""
        if self._browser:
            return

        self._playwright = await async_playwright().start()

        if self._use_browserless:
            # Connect to browserless service
            logger.info(f"Connecting to browserless at: {self.browserless_url}")
            try:
                self._browser = await self._playwright.chromium.connect(self.browserless_url)
                self._context = await self._browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.user_agent
                )
            except Exception as e:
                logger.warning(f"Cannot connect to browserless: {e}")
                logger.info("Falling back to local stealth mode")
                self._use_browserless = False
                await self._init_local_browser()
        else:
            await self._init_local_browser()

        self._page = await self._context.new_page()
        await self._load_cookies()

    async def _init_local_browser(self) -> None:
        """Initialize local browser with stealth settings"""
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Faster loading
            '--disable-javascript',  # Enable only when needed
            '--user-agent={}'.format(self.user_agent),
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )

        # Stealth context settings
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=self.user_agent,
            locale='en-US',
            timezone_id='Asia/Ho_Chi_Minh',
            permissions=['geolocation', 'notifications'],
            color_scheme='light',
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
        )

        # Inject stealth scripts
        await self._context.add_init_script("""
            // Remove webdriver traces
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Hide automation indicators
            window.chrome = {
                runtime: {}
            };

            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        logger.info("Using local stealth mode")

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
            logger.info("Saved cookies")
        except Exception as e:
            logger.warning(f"Failed to save cookies: {e}")

    async def _check_session_valid(self) -> bool:
        """Check if current session is valid"""
        try:
            response = await self._page.goto(
                self.SCHEDULE_URL,
                wait_until='domcontentloaded',
                timeout=15000
            )

            if response.status != 200:
                return False

            current_url = self._page.url
            if 'Login.aspx' in current_url:
                return False

            content = await self._page.content()
            soup = BeautifulSoup(content, 'lxml')
            user_label = soup.find('span', {'id': 'ctl00_lblLogIn'})

            if user_label and self.username.lower() in user_label.get_text().lower():
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                return True

            return False

        except Exception as e:
            logger.error(f"Session check failed: {e}")
            return False

    async def _solve_turnstile(self, timeout: int = 30000) -> Optional[str]:
        """
        Wait for and extract Turnstile token
        This is a placeholder - real Turnstile solving requires external service
        """
        try:
            # Wait for Turnstile iframe
            await self._page.wait_for_selector('iframe[src*="challenges.cloudflare.com"]', timeout=timeout)

            # Wait for response input
            await self._page.wait_for_selector('input[name="cf-turnstile-response"]', timeout=timeout)

            # Try to get token (may need human interaction or solving service)
            token_input = await self._page.query_selector('input[name="cf-turnstile-response"]')
            if token_input:
                token = await token_input.get_attribute('value')
                if token and len(token) > 10:
                    logger.info("Turnstile solved!")
                    return token

            logger.warning("Turnstile not auto-solved - may need manual interaction")
            return None

        except Exception as e:
            logger.warning(f"Turnstile detection failed: {e}")
            return None

    async def _full_login_flow(self) -> bool:
        """Perform login with Turnstile handling"""
        try:
            logger.info(f"Starting login for: {self.username}")

            await self._page.goto(self.LOGIN_URL, wait_until='domcontentloaded', timeout=30000)

            # Wait for form
            await self._page.wait_for_selector('form[name="aspnetForm"]', timeout=10000)

            # Try to solve Turnstile (may fail without external service)
            await asyncio.sleep(2)  # Wait for page to fully load
            turnstile_token = await self._solve_turnstile(timeout=10000)

            # Fill credentials
            await self._page.fill('input[name="ctl00$mainContent$UserName"]', self.username)
            await self._page.fill('input[name="ctl00$mainContent$Password"]', self.password)

            # Submit form
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

            # Wait for navigation
            await self._page.wait_for_url(
                lambda url: 'Login.aspx' not in url,
                timeout=30000
            )

            current_url = self._page.url
            if 'Login.aspx' not in current_url:
                logger.info("Login successful!")
                await self._save_cookies()
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                self._is_logged_in = True
                return True
            else:
                logger.error("Login failed - check credentials or Cloudflare")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def get_session(self, force_refresh: bool = False) -> Optional[Page]:
        """Get authenticated session"""
        try:
            await self._init_browser()

            if not force_refresh and self._is_logged_in:
                if self._session_expiry and datetime.now() < self._session_expiry:
                    if await self._check_session_valid():
                        return self._page
                self._is_logged_in = False

            if await self._full_login_flow():
                return self._page
            return None

        except Exception as e:
            logger.error(f"Session error: {e}")
            return None

    async def fetch_schedule(self, week: Optional[int] = None, year: int = None) -> Optional[str]:
        """Fetch schedule HTML"""
        try:
            page = await self.get_session()
            if not page:
                return None

            await page.goto(self.SCHEDULE_URL, wait_until='domcontentloaded', timeout=30000)

            if week is not None:
                await page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))
            if year is not None:
                await page.select_option('#ctl00_mainContent_drpYear', str(year))

            await page.wait_for_selector('table tbody tr', timeout=10000)
            content = await page.content()
            self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
            return content

        except Exception as e:
            logger.error(f"Fetch schedule error: {e}")
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
            self._is_logged_in = False
            logger.info("Browser closed")

    async def __aenter__(self):
        await self.get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
