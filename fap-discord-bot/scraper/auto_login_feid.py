"""
FAP Auto Login - FeID Flow via Camoufox
Automates the full login flow: Cloudflare bypass -> FeID login -> Save cookies.
Uses Camoufox (Firefox-based anti-detect browser) for Cloudflare-resistant automation.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import aiohttp
from camoufox.async_api import AsyncCamoufox

logger = logging.getLogger(__name__)


class FAPAutoLogin:
    """
    Automated login flow:
    1. Launch Firefox via Camoufox with persistent profile + proxy
    2. Navigate to FAP (Cloudflare auto-bypassed by anti-detect Firefox)
    3. Click "Login With FeID"
    4. Fill FeID form (username + password)
    5. Submit and save cookies for aiohttp
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    LOGIN_URL = "https://fap.fpt.edu.vn/Default.aspx"
    PROFILE_DIR = "data/firefox_profile"
    COOKIES_FILE = "data/fap_cookies.json"

    def __init__(
        self,
        headless: bool = False,
        feid: str = None,
        password: str = None,
    ):
        self.headless = headless
        self.feid = feid or os.environ.get("FAP_FEID") or os.environ.get("FAP_USERNAME")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.profile_dir = Path(self.PROFILE_DIR)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._camoufox = None
        self._context = None
        self._page = None

    async def auto_login(self) -> bool:
        """Execute the login flow and persist cookies when successful."""
        if not self.feid or not self.password:
            raise ValueError("FEID and password required for login")

        logger.info(f"Starting auto-login, FEID: {self.feid}")

        try:
            await self._launch_browser()

            if not await self._open_login_page():
                return False

            if await self._is_schedule_page():
                logger.info("Already logged in! Schedule page accessible.")
                return await self._persist_cookies()

            await self._select_campus_if_needed()
            await self._trigger_feid_login()

            current_url = self._page.url
            logger.info(f"After FeID trigger: {current_url[:100]}")

            if "feid.fpt.edu.vn" in current_url or "identity" in current_url:
                logger.info("Redirected to FeID login page!")
                await self._handle_feid_login()
            else:
                if not await self._handle_non_redirected_login():
                    return False

            await asyncio.sleep(5)

            if "Thongbao.aspx" in self._page.url:
                logger.info("On notification page, navigating to schedule...")
                await self._page.goto(self.SCHEDULE_URL, timeout=30000)
                await asyncio.sleep(5)

            if await self._is_schedule_page():
                logger.info("Login successful! Schedule page accessible!")
                return await self._persist_cookies()

            logger.error(f"Login may have failed. Current URL: {self._page.url}")
            return False
        finally:
            await self.close()

    async def _launch_browser(self):
        """Start Camoufox with persistent profile + proxy."""
        logger.info("Starting Camoufox (Firefox anti-detect) with persistent profile...")

        # Remove stale profile locks
        for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket", "lock"):
            lock_path = self.profile_dir / lock_name
            if lock_path.exists():
                logger.warning(f"Removing stale lock: {lock_path}")
                lock_path.unlink()

        # Build Camoufox options
        # headless="virtual" uses Xvfb virtual display for anti-detection
        headless_mode = "virtual" if self.headless else False

        camoufox_kwargs = dict(
            persistent_context=True,
            user_data_dir=str(self.profile_dir),
            headless=headless_mode,
            geoip=True,
            humanize=True,
            disable_coop=True,  # Allow clicking cross-origin iframes (Turnstile)
        )

        proxy_url = os.environ.get("PROXY_URL")
        if proxy_url:
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            logger.info(f"Using proxy: {parsed.hostname}:{parsed.port}")
            proxy_dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
            if parsed.username:
                proxy_dict["username"] = parsed.username
            if parsed.password:
                proxy_dict["password"] = parsed.password
            camoufox_kwargs["proxy"] = proxy_dict

        try:
            self._camoufox = AsyncCamoufox(**camoufox_kwargs)
            self._context = await self._camoufox.__aenter__()
        except Exception as e:
            logger.error(f"Camoufox launch failed: {e}")
            logger.error(f"  headless={headless_mode}, profile_dir={self.profile_dir}")
            logger.error(f"  DISPLAY={os.environ.get('DISPLAY', 'unset')}")
            raise

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

    async def _open_login_page(self) -> bool:
        """Open the FAP login page, waiting for Cloudflare Turnstile to pass."""
        logger.info("Navigating to FAP login page...")
        try:
            await self._page.goto(self.LOGIN_URL, timeout=60000)
        except Exception as exc:
            logger.error(f"Failed to open login page: {exc}")
            return False

        # Wait for Cloudflare challenge to resolve
        # CF titles: "Just a moment..." (EN), "Chờ một chút..." (VI), etc.
        cf_keywords = ("moment", "challenge", "chờ", "vui lòng chờ", "checking", "attention")
        turnstile_clicked = False

        for i in range(60):
            title = await self._page.title()
            title_lower = title.lower()
            is_cf_challenge = any(kw in title_lower for kw in cf_keywords)

            if not is_cf_challenge:
                content = await self._page.content()
                if "btnloginFeId" in content or "drpSelectWeek" in content or "ddlCampus" in content:
                    logger.info(f"Page loaded: {title}")
                    return True
                if i > 5:
                    logger.info(f"Title changed to: {title}")
                    return True

            # Try clicking the Turnstile checkbox inside its iframe
            if is_cf_challenge and not turnstile_clicked and i >= 3:
                turnstile_clicked = await self._click_turnstile()

            if i % 5 == 0:
                logger.info(f"Waiting for Cloudflare challenge... ({i}s) title={title}")
            await asyncio.sleep(1)

        logger.warning("Cloudflare challenge did not resolve within 60s")
        return True

    async def _click_turnstile(self) -> bool:
        """Find and click the Cloudflare Turnstile checkbox."""
        try:
            # Turnstile renders inside an iframe from challenges.cloudflare.com
            frames = self._page.frames
            for frame in frames:
                if "challenges.cloudflare.com" in (frame.url or ""):
                    logger.info("Found Turnstile iframe, clicking checkbox...")
                    # The checkbox is typically an input[type="checkbox"] or a clickable div
                    checkbox = frame.locator("input[type='checkbox']")
                    if await checkbox.count() > 0:
                        await checkbox.first.click()
                        logger.info("Clicked Turnstile checkbox")
                        await asyncio.sleep(3)
                        return True
                    # Fallback: click the main body of the Turnstile widget
                    body = frame.locator("body")
                    if await body.count() > 0:
                        box = await body.first.bounding_box()
                        if box:
                            # Click the left-center area where the checkbox usually is
                            click_x = box["x"] + 30
                            click_y = box["y"] + box["height"] / 2
                            await self._page.mouse.click(click_x, click_y)
                            logger.info("Clicked Turnstile widget area")
                            await asyncio.sleep(3)
                            return True
            logger.info("No Turnstile iframe found")
        except Exception as exc:
            logger.debug(f"Turnstile click attempt failed: {exc}")
        return False

    async def _is_schedule_page(self) -> bool:
        """Check whether the current page is the schedule page."""
        content = await self._page.content()
        return "ctl00_mainContent_drpSelectWeek" in content

    async def _select_campus_if_needed(self):
        """Select the campus if the FAP landing page requires it."""
        try:
            campus = os.environ.get("FAP_CAMPUS", "4")
            campus_select = self._page.locator("#ctl00_mainContent_ddlCampus")
            if await campus_select.count() > 0:
                logger.info(f"Selecting campus {campus}...")
                await campus_select.select_option(campus)
                await asyncio.sleep(2)
        except Exception:
            pass

    async def _trigger_feid_login(self):
        """Click the FeID login button or fall back to postback."""
        logger.info("Looking for 'Login With FeID' button...")

        try:
            feid_button = self._page.locator("#ctl00_mainContent_btnloginFeId")
            if await feid_button.count() > 0:
                logger.info("Found FeID button - clicking...")
                await feid_button.click()
                await asyncio.sleep(3)
                return

            text_button = self._page.locator("text=Login With FeID")
            if await text_button.count() > 0:
                logger.info("Found FeID button by text - clicking...")
                await text_button.first.click()
                await asyncio.sleep(3)
                return

            logger.info("Trying __doPostBack fallback for FeID login...")
            await self._page.evaluate(
                """
                () => {
                    if (typeof __doPostBack !== 'function') {
                        throw new Error('__doPostBack unavailable');
                    }
                    __doPostBack('ctl00$mainContent$btnloginFeId','');
                }
                """
            )
            await asyncio.sleep(3)
        except Exception as exc:
            logger.error(f"Error clicking FeID button: {exc}")

    async def _handle_non_redirected_login(self) -> bool:
        """Try direct login or fail."""
        logger.warning("Not redirected to FeID. Checking page...")
        content = await self._page.content()
        logger.warning(f"Page URL: {self._page.url}")
        logger.warning(f"Page title: {await self._page.title()}")

        if "Password" in content or "password" in content:
            logger.info("Found password field - attempting direct login...")
            await self._handle_direct_login()
            return True

        # Dump snippet for debugging
        body_text = await self._page.locator("body").inner_text()
        logger.error(f"No login form found. Page body: {body_text[:500]}")
        return False

    async def _persist_cookies(self) -> bool:
        """Export current browser cookies to the shared JSON file."""
        logger.info("Exporting cookies to JSON file...")
        cookies = await self._context.cookies()
        fap_cookies = [c for c in cookies if "fpt.edu.vn" in c.get("domain", "")]

        Path(self.COOKIES_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(self.COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        logger.info(f"Saved {len(cookies)} cookies ({len(fap_cookies)} FAP)")

        important = ["cf_clearance", "ASP.NET_SessionId", "__AntiXsrfToken"]
        for cookie in cookies:
            if cookie["name"] in important:
                value = cookie.get("value") or ""
                logger.info(f"  {cookie['name']}: {value[:30]}...")

        return True

    async def _handle_feid_login(self):
        """Handle the FeID login page."""
        logger.info("Handling FeID login page...")
        await asyncio.sleep(2)

        username_selectors = [
            'input[name="Username"]',
            'input[name="username"]',
            'input[name="email"]',
            'input[type="email"]',
            'input[id*="username"]',
            'input[id*="Email"]',
            "#Input_Email",
            "#Email",
            "#username",
        ]

        password_selectors = [
            'input[name="Password"]',
            'input[name="password"]',
            'input[type="password"]',
            'input[id*="password"]',
            "#Input_Password",
            "#Password",
            "#password",
        ]

        username_input = None
        password_input = None

        for selector in username_selectors:
            try:
                elem = self._page.locator(selector)
                if await elem.count() > 0:
                    username_input = elem.first
                    logger.info(f"Found username input: {selector}")
                    break
            except Exception:
                continue

        for selector in password_selectors:
            try:
                elem = self._page.locator(selector)
                if await elem.count() > 0:
                    password_input = elem.first
                    logger.info(f"Found password input: {selector}")
                    break
            except Exception:
                continue

        if username_input and password_input:
            logger.info("Filling in login credentials...")
            await username_input.fill(self.feid)
            await password_input.fill(self.password)

            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
            ]

            for selector in submit_selectors:
                try:
                    btn = self._page.locator(selector)
                    if await btn.count() > 0:
                        logger.info(f"Found submit button: {selector}")
                        await btn.click()
                        logger.info("Login form submitted...")
                        await asyncio.sleep(5)
                        break
                except Exception:
                    continue
            return

        logger.error("Could not find login form inputs")

    async def _handle_direct_login(self):
        """Handle a direct login form on the FAP page."""
        logger.info("Handling direct login form...")

        username_input = self._page.locator('input[type="email"], input[name*="user"], input[name*="email"]')
        password_input = self._page.locator('input[type="password"]')

        if await username_input.count() > 0 and await password_input.count() > 0:
            await username_input.first.fill(self.feid)
            await password_input.first.fill(self.password)

            submit_btn = self._page.locator('button[type="submit"], input[type="submit"]')
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
                logger.info("Direct login form submitted...")

    def _load_cookies_dict(self) -> dict:
        """Load cookies from JSON file into a {name: value} dict for aiohttp."""
        if not Path(self.COOKIES_FILE).exists():
            return {}
        try:
            with open(self.COOKIES_FILE, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            return {
                c["name"]: c["value"]
                for c in cookies
                if "fpt.edu.vn" in c.get("domain", "") or "fap" in c.get("domain", "")
            }
        except Exception:
            return {}

    async def _http_get(self, url: str, timeout: int = 30) -> Optional[str]:
        """Fetch a URL using aiohttp with saved cookies."""
        cookies = self._load_cookies_dict()
        if not cookies:
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with aiohttp.ClientSession(
                cookies=cookies,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        return None

                    content = await resp.text()
                    final_url = str(resp.url)
                    if "Login" in final_url or "Default.aspx" in final_url:
                        return None

                    return content
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None

    async def fetch_schedule(self, week: int = None, year: int = None) -> Optional[str]:
        """Fetch schedule using aiohttp with saved cookies."""
        url = self.SCHEDULE_URL
        params = []
        if week is not None:
            params.append(f"week={week}")
        if year is not None:
            params.append(f"year={year}")
        if params:
            url += "?" + "&".join(params)

        content = await self._http_get(url)
        if content and "ctl00_mainContent_drpSelectWeek" in content:
            return content
        return content if content and len(content) > 500 else None

    async def fetch_exam_schedule(self) -> Optional[str]:
        """Fetch exam schedule using aiohttp with saved cookies."""
        exam_url = "https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx"
        content = await self._http_get(exam_url)
        if content and ("Schedule Exam" in content or "table" in content.lower()):
            return content
        return content if content and len(content) > 500 else None

    async def fetch_attendance(
        self,
        student_id: str = None,
        campus: int = 4,
        term: int = None,
        course: int = None,
    ) -> Optional[str]:
        """Fetch attendance using aiohttp with saved cookies."""
        attendance_url = "https://fap.fpt.edu.vn/Report/ViewAttendstudent.aspx"
        params = []
        if student_id:
            params.append(f"id={student_id}")
        if campus:
            params.append(f"campus={campus}")
        if term:
            params.append(f"term={term}")
        if course:
            params.append(f"course={course}")

        url = attendance_url
        if params:
            url += "?" + "&".join(params)

        content = await self._http_get(url)
        if content and ("ViewAttendstudent" in content or "divTerm" in content):
            return content
        return content if content and len(content) > 500 else None

    async def fetch_grades(
        self,
        student_id: str = None,
        term: str = None,
        course: int = None,
    ) -> Optional[str]:
        """Fetch grades using aiohttp with saved cookies."""
        grade_url = "https://fap.fpt.edu.vn/Grade/StudentGrade.aspx"
        params = []
        if student_id:
            params.append(f"rollNumber={student_id}")
        if term:
            params.append(f"term={term}")
        if course:
            params.append(f"course={course}")

        url = grade_url
        if params:
            url += "?" + "&".join(params)

        content = await self._http_get(url)
        if content and ("StudentGrade" in content or "divTerm" in content):
            return content
        return content if content and len(content) > 500 else None

    async def fetch_application(self):
        raise AttributeError("fetch_application is not implemented")

    async def close(self):
        """Close Camoufox browser context safely."""
        if self._camoufox is not None:
            try:
                await self._camoufox.__aexit__(None, None, None)
            except Exception:
                pass
            self._camoufox = None

        self._context = None
        self._page = None
