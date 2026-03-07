"""
FAP Authentication using Camoufox (2026)
Camoufox is a stealth browser that can bypass Cloudflare
Login flow: FEID (feid.fpt.edu.vn) -> FAP (fap.fpt.edu.vn)
"""
import asyncio
import logging
import os
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

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

        logger.info("Camoufox browser started")

    async def _full_login_flow(self) -> bool:
        """
        Perform login through FEID
        Flow: FEID Login -> Google/FEID Auth -> Redirect to FAP
        """
        try:
            logger.info(f"Starting login for: {self.username}")

            # Get the first page
            page = self._browser.pages[0] if self._browser.pages else await self._browser.new_page()

            # Go to FEID login page
            logger.info("Navigating to FEID login page...")
            await page.goto(
                "https://feid.fpt.edu.vn/Account/Login",
                timeout=60000
            )

            # Wait for page to load
            await asyncio.sleep(5)

            logger.info(f"Current URL: {page.url}")

            # Check if there's a Google login button
            try:
                # Look for Google login button
                google_btn = await page.query_selector('button:has-text("Google"), .google-login, a[href*="google"]')
                if google_btn:
                    logger.info("Found Google login button")
                    await google_btn.click()
                    logger.info("Clicked Google login - waiting for redirect...")
                    await asyncio.sleep(10)
            except:
                logger.info("No Google login button found, trying direct login")

            # Check for username/password fields
            current_url = str(page.url)
            logger.info(f"After click URL: {current_url}")

            # If still on login page, try direct login
            if 'feid.fpt.edu.vn' in current_url and 'Login' in current_url:
                logger.info("Attempting direct login with FEID credentials...")

                # Try to find username field
                username_selectors = [
                    'input[name="Email"]',
                    'input[name="UserName"]',
                    'input[name="username"]',
                    'input[type="email"]',
                    '#Email',
                    '#UserName',
                ]

                username_field = None
                for selector in username_selectors:
                    try:
                        username_field = await page.query_selector(selector)
                        if username_field:
                            logger.info(f"Found username field with selector: {selector}")
                            break
                    except:
                        continue

                if username_field:
                    await username_field.fill(self.username)
                    logger.info("Username entered")

                    # Find password field
                    password_selectors = [
                        'input[name="Password"]',
                        'input[name="password"]',
                        'input[type="password"]',
                        '#Password',
                    ]

                    password_field = None
                    for selector in password_selectors:
                        try:
                            password_field = await page.query_selector(selector)
                            if password_field:
                                logger.info(f"Found password field with selector: {selector}")
                                break
                        except:
                            continue

                    if password_field:
                        await password_field.fill(self.password)
                        logger.info("Password entered")

                        # Find and click login button
                        login_selectors = [
                            'button[type="submit"]',
                            'input[type="submit"]',
                            'button:has-text("Login")',
                            'button:has-text("Sign in")',
                            '#btnLogin',
                        ]

                        for selector in login_selectors:
                            try:
                                login_btn = await page.query_selector(selector)
                                if login_btn:
                                    logger.info(f"Clicking login button: {selector}")
                                    await login_btn.click()
                                    break
                            except:
                                continue

            # Wait for redirect to FAP
            logger.info("Waiting for redirect to FAP...")
            await asyncio.sleep(15)

            # Check if we're on FAP now
            current_url = str(page.url)
            logger.info(f"Final URL: {current_url}")

            if 'fap.fpt.edu.vn' in current_url:
                logger.info("Successfully logged in and redirected to FAP!")
                self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                self._is_logged_in = True
                return True
            else:
                logger.warning(f"Not on FAP yet. Current URL: {current_url}")
                # Still might be logged in, let's check by navigating to schedule
                await page.goto(self.SCHEDULE_URL, timeout=30000)
                await asyncio.sleep(5)

                current_url = str(page.url)
                if 'Login' not in current_url:
                    logger.info("Successfully accessed FAP schedule page!")
                    self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
                    self._is_logged_in = True
                    return True

                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fetch_schedule(self, week: Optional[int] = None, year: int = None) -> Optional[str]:
        """Fetch schedule HTML"""
        try:
            if not self._is_logged_in:
                if not await self._full_login_flow():
                    return None

            logger.info("Fetching schedule...")
            page = self._browser.pages[0] if self._browser.pages else await self._browser.new_page()

            await page.goto(self.SCHEDULE_URL, timeout=30000)
            await asyncio.sleep(3)

            # Select week if specified
            if week is not None:
                await page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))

            if year is not None:
                await page.select_option('#ctl00_mainContent_drpYear', str(year))

            await asyncio.sleep(2)

            content = await page.content()
            self._session_expiry = datetime.now() + self.SESSION_TIMEOUT
            return content

        except Exception as e:
            logger.error(f"Fetch schedule error: {e}")
            return None

    async def close(self) -> None:
        """Close browser"""
        if self._browser:
            await self._browser.stop()
            self._browser = None
            self._is_logged_in = False
            logger.info("Browser closed")

    async def __aenter__(self):
        await self._full_login_flow()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Test function
async def test_camoufox():
    """Test Camoufox with FAP"""
    print("=" * 50)
    print("Testing FAP with Camoufox (2026)")
    print("=" * 50)

    from dotenv import load_dotenv
    load_dotenv()

    auth = FAPAuthCamoufox(
        username=os.getenv('FAP_USERNAME'),
        password=os.getenv('FAP_PASSWORD'),
        headless=False,  # Show browser
        data_dir='data'
    )

    try:
        print("[.] Connecting to FAP via Camoufox...")
        success = await auth._full_login_flow()

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

                # Save HTML for debugging
                with open('camoufox_schedule.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("\n[+] Saved HTML to camoufox_schedule.html")
        else:
            print("[X] Login failed")

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await auth.close()

if __name__ == "__main__":
    asyncio.run(test_camoufox())
