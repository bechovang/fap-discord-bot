"""
FAP Auto Login - FeID Flow
Automates the full login flow: Cloudflare bypass -> FeID login -> Schedule.
"""
import asyncio
import json
import os
from pathlib import Path

import aiohttp
from playwright.async_api import async_playwright


class FAPAutoLogin:
    """
    Automated login flow:
    1. Navigate to FAP
    2. Click "Login With FeID"
    3. Fill FeID form (username + password)
    4. Submit and get auth
    5. Save session for reuse
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    LOGIN_URL = "https://fap.fpt.edu.vn/Default.aspx"
    PROFILE_DIR = "data/chrome_profile"
    COOKIES_FILE = "data/fap_cookies.json"

    def __init__(
        self,
        headless: bool = False,
        feid: str = None,
        password: str = None,
        interactive: bool = True,
    ):
        self.headless = headless
        self.feid = feid or os.environ.get("FAP_FEID")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.interactive = interactive
        self.profile_dir = Path(self.PROFILE_DIR)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = None
        self._browser = None
        self._page = None

    async def auto_login(self) -> bool:
        """Execute the login flow and persist cookies when successful."""
        if not self.feid or not self.password:
            raise ValueError("FEID and password required for login")

        print("=" * 60)
        print("FAP Auto Login - FeID Flow")
        print("=" * 60)
        print(f"[.] FEID: {self.feid}")
        print(f"[.] Profile: {self.profile_dir.absolute()}")
        print()

        try:
            self._playwright = await async_playwright().start()
            await self._launch_browser()

            if not await self._open_login_page():
                return False

            if await self._is_schedule_page():
                print("[+] Already logged in! Schedule page accessible.")
                return await self._persist_cookies()

            await self._select_campus_if_needed()
            await self._trigger_feid_login()

            current_url = self._page.url
            print(f"[.] Current URL: {current_url}")

            if "feid.fpt.edu.vn" in current_url or "identity" in current_url:
                print("[+] Redirected to FeID login page!")
                await self._handle_feid_login()
            else:
                if not await self._handle_non_redirected_login():
                    return False

            await asyncio.sleep(5)

            if "Thongbao.aspx" in self._page.url:
                print("[.] On notification page, navigating to schedule...")
                await self._page.goto(self.SCHEDULE_URL, timeout=30000)
                await asyncio.sleep(5)

            if await self._is_schedule_page():
                print("[+] SUCCESS! Login successful, schedule page accessible!")
                return await self._persist_cookies()

            print(f"[?] Login may have failed. Current URL: {self._page.url}")
            if self.interactive:
                print("[.] Keeping browser open for manual check...")
                input("Press Enter to close browser...")
            return False
        finally:
            await self.close()

    async def _launch_browser(self):
        """Start Playwright with a persistent Chromium profile."""
        print("[.] Starting Chromium with persistent profile...")

        cookies_path = self.profile_dir / "Default" / "Network" / "Cookies"
        old_cookies_path = self.profile_dir / "Default" / "Cookies"
        profile_exists = cookies_path.exists() or old_cookies_path.exists()

        launch_opts = dict(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            viewport={"width": 1920, "height": 1080},
        )

        proxy_url = os.environ.get("PROXY_URL")
        if proxy_url:
            print(f"[.] Using proxy: {proxy_url.split('@')[-1]}")
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            launch_opts["proxy"] = {
                "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
                "username": parsed.username or "",
                "password": parsed.password or "",
            }

        self._browser = await self._playwright.chromium.launch_persistent_context(**launch_opts)

        if self._browser.pages:
            self._page = self._browser.pages[0]
        else:
            self._page = await self._browser.new_page()

        if not profile_exists:
            print("[!] First run - Cloudflare challenge expected")
            print("[!] Please complete the Cloudflare challenge if shown")
            print()

    async def _open_login_page(self) -> bool:
        """Open the FAP login page."""
        print("[.] Navigating to FAP login page...")
        try:
            await self._page.goto(self.LOGIN_URL, timeout=60000)
        except Exception as exc:
            print(f"[!] Failed to open login page: {exc}")
            return False

        await asyncio.sleep(3)
        return True

    async def _is_schedule_page(self) -> bool:
        """Check whether the current page is the schedule page."""
        content = await self._page.content()
        return "ctl00_mainContent_drpSelectWeek" in content

    async def _select_campus_if_needed(self):
        """Select the campus if the FAP landing page requires it."""
        try:
            campus_select = self._page.locator("#ctl00_mainContent_ddlCampus")
            if await campus_select.count() > 0:
                print("[.] Selecting campus (FU-Hoa Lac)...")
                await campus_select.select_option("3")
                await asyncio.sleep(2)
        except Exception:
            pass

    async def _trigger_feid_login(self):
        """Click the FeID login button or fall back to postback."""
        print("[.] Looking for 'Login With FeID' button...")

        try:
            feid_button = self._page.locator("#ctl00_mainContent_btnloginFeId")
            if await feid_button.count() > 0:
                print("[+] Found FeID button - clicking...")
                await feid_button.click()
                await asyncio.sleep(3)
                return

            text_button = self._page.locator("text=Login With FeID")
            if await text_button.count() > 0:
                print("[+] Found FeID button by text - clicking...")
                await text_button.first.click()
                await asyncio.sleep(3)
                return

            print("[.] Trying __doPostBack fallback for FeID login...")
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
            print(f"[!] Error clicking FeID button: {exc}")
            if self.interactive:
                print("[.] Please check the page state")

    async def _handle_non_redirected_login(self) -> bool:
        """Try direct login or fail fast in non-interactive mode."""
        print("[?] Not redirected to FeID. Checking page...")
        content = await self._page.content()

        with open("debug_login_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("[.] Saved to debug_login_page.html")

        if "Password" in content or "password" in content:
            print("[+] Found password field - attempting direct login...")
            await self._handle_direct_login()
            return True

        if self.interactive:
            print("[!] No login form found. Manual intervention may be needed.")
            print("[.] Browser will stay open for manual login...")
            input("Press Enter after completing login manually...")
            return True

        print("[!] No login form found in non-interactive mode.")
        return False

    async def _persist_cookies(self) -> bool:
        """Export current browser cookies to the shared JSON file."""
        print("[.] Exporting cookies to JSON file...")
        cookies = await self._page.context.cookies()
        fap_cookies = [c for c in cookies if "fpt.edu.vn" in c.get("domain", "")]

        Path(self.COOKIES_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(self.COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        print(f"[+] Saved {len(cookies)} cookies to {self.COOKIES_FILE}")
        print(f"[+] FAP cookies: {len(fap_cookies)}")

        important = ["cf_clearance", "ASP.NET_SessionId", "__AntiXsrfToken"]
        for cookie in cookies:
            if cookie["name"] in important:
                value = cookie.get("value") or ""
                preview = value[:30] if value else "(empty)"
                print(f"    - {cookie['name']}: {preview}...")

        print("[+] Session saved! You can now use fetch command.")
        return True

    async def _handle_feid_login(self):
        """Handle the FeID login page."""
        print("[.] Handling FeID login page...")
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
                    print(f"[+] Found username input: {selector}")
                    break
            except Exception:
                continue

        for selector in password_selectors:
            try:
                elem = self._page.locator(selector)
                if await elem.count() > 0:
                    password_input = elem.first
                    print(f"[+] Found password input: {selector}")
                    break
            except Exception:
                continue

        if username_input and password_input:
            print("[.] Filling in login credentials...")
            await username_input.fill(self.feid)
            await password_input.fill(self.password)

            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Dang nhap")',
            ]

            for selector in submit_selectors:
                try:
                    btn = self._page.locator(selector)
                    if await btn.count() > 0:
                        print(f"[+] Found submit button: {selector}")
                        await btn.click()
                        print("[.] Login form submitted...")
                        await asyncio.sleep(5)
                        break
                except Exception:
                    continue
            return

        print("[!] Could not find login form inputs")
        print("[.] Page may have different structure")
        with open("debug_feid_page.html", "w", encoding="utf-8") as f:
            f.write(await self._page.content())

    async def _handle_direct_login(self):
        """Handle a direct login form on the FAP page."""
        print("[.] Handling direct login form...")

        username_input = self._page.locator('input[type="email"], input[name*="user"], input[name*="email"]')
        password_input = self._page.locator('input[type="password"]')

        if await username_input.count() > 0 and await password_input.count() > 0:
            await username_input.first.fill(self.feid)
            await password_input.first.fill(self.password)

            submit_btn = self._page.locator('button[type="submit"], input[type="submit"]')
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
                print("[.] Login form submitted...")

    def _load_cookies_dict(self) -> dict:
        """Load cookies from JSON file into a {name: value} dict for aiohttp."""
        if not Path(self.COOKIES_FILE).exists():
            return {}
        with open(self.COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        return {
            c["name"]: c["value"]
            for c in cookies
            if "fpt.edu.vn" in c.get("domain", "") or "fap" in c.get("domain", "")
        }

    async def _http_get(self, url: str, timeout: int = 30) -> str:
        """Fetch a URL using aiohttp with saved cookies."""
        cookies = self._load_cookies_dict()
        if not cookies:
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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

    async def fetch_schedule(self, week: int = None, year: int = None) -> str:
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

    async def fetch_exam_schedule(self) -> str:
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
    ) -> str:
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
    ) -> str:
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
        """Application fetch is not implemented for this auth flow."""
        raise AttributeError("fetch_application is not implemented")

    async def close(self):
        """Close browser and Playwright handles safely."""
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        self._page = None


async def login(feid: str, password: str):
    """One-time login setup."""
    auth = FAPAutoLogin(headless=False, feid=feid, password=password, interactive=True)
    return await auth.auto_login()


async def fetch(week: int = None, year: int = None):
    """Fetch schedule using saved profile."""
    auth = FAPAutoLogin(headless=False, interactive=False)
    html = await auth.fetch_schedule(week=week, year=year)

    if html:
        import importlib.util

        spec = importlib.util.spec_from_file_location("parser", "scraper/parser.py")
        parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser_module)

        parser = parser_module.FAPParser()
        items = parser.parse_schedule(html)
        print(f"[+] Found {len(items)} classes")
        return items

    return None


if __name__ == "__main__":
    import getpass
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "login":
            feid = sys.argv[2] if len(sys.argv) > 2 else input("FEID: ")
            password = sys.argv[3] if len(sys.argv) > 3 else getpass.getpass("Password: ")
            asyncio.run(login(feid, password))
        elif command == "fetch":
            week = int(sys.argv[2]) if len(sys.argv) > 2 else None
            year = int(sys.argv[3]) if len(sys.argv) > 3 else None
            asyncio.run(fetch(week, year))
        else:
            print("Usage:")
            print("  python auto_login_feid.py login [feid] [password]")
            print("  python auto_login_feid.py fetch [week] [year]")
    else:
        print("Usage:")
        print("  python auto_login_feid.py login [feid] [password]")
        print("  python auto_login_feid.py fetch [week] [year]")
