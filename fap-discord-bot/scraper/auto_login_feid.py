"""
FAP Auto Login - FeID Flow
Automates the full login flow: Cloudflare bypass → FeID login → Schedule
"""
import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright


class FAPAutoLogin:
    """
    Automated login flow:
    1. Navigate to FAP (Cloudflare handled manually first time)
    2. Click "Login With FeID"
    3. Fill FeID form (username + password)
    4. Submit and get auth
    5. Save session for reuse
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    LOGIN_URL = "https://fap.fpt.edu.vn/Default.aspx"
    PROFILE_DIR = "data/chrome_profile"
    COOKIES_FILE = "data/fap_cookies.json"  # Export cookies to JSON

    def __init__(self, headless: bool = False, feid: str = None, password: str = None):
        self.headless = headless
        self.feid = feid or os.environ.get("FAP_FEID")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.profile_dir = Path(self.PROFILE_DIR)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = None
        self._browser = None
        self._page = None

    async def auto_login(self) -> bool:
        """
        Full automated login flow
        """
        if not self.feid or not self.password:
            raise ValueError("FEID and password required for login!")

        print("=" * 60)
        print("FAP Auto Login - FeID Flow")
        print("=" * 60)
        print(f"[.] FEID: {self.feid}")
        print(f"[.] Profile: {self.profile_dir.absolute()}")
        print()

        self._playwright = await async_playwright().start()

        # Launch with persistent profile
        print("[.] Starting Chromium with persistent profile...")

        # Check if profile exists to determine if we need to solve Cloudflare
        cookies_path = self.profile_dir / "Default" / "Network" / "Cookies"
        old_cookies_path = self.profile_dir / "Default" / "Cookies"
        profile_exists = cookies_path.exists() or old_cookies_path.exists()

        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ],
            viewport={'width': 1920, 'height': 1080},
        )

        if len(self._browser.pages) > 0:
            self._page = self._browser.pages[0]
        else:
            self._page = await self._browser.new_page()

        if not profile_exists:
            # First run - need to handle Cloudflare manually
            print("[!] First run - Cloudflare challenge expected")
            print("[!] Please complete the Cloudflare challenge if shown")
            print()

        # Navigate to FAP login page
        print("[.] Navigating to FAP login page...")
        await self._page.goto(self.LOGIN_URL, timeout=60000)
        await asyncio.sleep(3)

        # Check if we're on the schedule page (already logged in)
        content = await self._page.content()
        if 'ctl00_mainContent_drpSelectWeek' in content:
            print("[+] Already logged in! Schedule page accessible.")
            return True

        # Check if we need to select campus first
        try:
            campus_select = self._page.locator('#ctl00_mainContent_ddlCampus')
            if await campus_select.count() > 0:
                print("[.] Selecting campus (FU-Hòa Lạc)...")
                await campus_select.select_option('3')  # FU-Hòa Lạc
                await asyncio.sleep(2)
        except:
            pass

        # Click "Login With FeID" button
        print("[.] Looking for 'Login With FeID' button...")

        try:
            # Method 1: Direct click
            feid_button = self._page.locator('#ctl00_mainContent_btnloginFeId')
            if await feid_button.count() > 0:
                print("[+] Found FeID button - clicking...")
                await feid_button.click()
                await asyncio.sleep(3)
            else:
                # Method 2: Use doPostBack
                print("[.] Using doPostBack to trigger FeID login...")
                await self._page.evaluate("__doPostBack('ctl00$mainContent$btnloginFeId','')")
                await asyncio.sleep(3)

        except Exception as e:
            print(f"[!] Error clicking FeID button: {e}")
            print("[.] Please check the page state")

        # Check if redirected to FeID login
        current_url = self._page.url
        print(f"[.] Current URL: {current_url}")

        if 'feid.fpt.edu.vn' in current_url or 'identity' in current_url:
            print("[+] Redirected to FeID login page!")

            # Look for username/password form
            await self._handle_feid_login()
        else:
            print("[?] Not redirected to FeID. Checking page...")
            content = await self._page.content()

            # Save for debugging
            with open('debug_login_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("[.] Saved to debug_login_page.html")

            # Check if there's a login form directly
            if 'Password' in content or 'password' in content:
                print("[+] Found password field - attempting direct login...")
                await self._handle_direct_login()
            else:
                print("[!] No login form found. Manual intervention may be needed.")
                print("[.] Browser will stay open for manual login...")
                input("Press Enter after completing login manually...")

        # Final check
        await asyncio.sleep(5)
        content = await self._page.content()

        # If on notification page, navigate to home/schedule
        if 'Thongbao.aspx' in self._page.url:
            print("[.] On notification page, navigating to schedule...")
            await self._page.goto(self.SCHEDULE_URL, timeout=30000)
            await asyncio.sleep(5)
            content = await self._page.content()

        if 'ctl00_mainContent_drpSelectWeek' in content:
            print("[+] SUCCESS! Login successful, schedule page accessible!")
            print("[.] Exporting cookies to JSON file...")

            # Export cookies directly from the page
            cookies = await self._page.context.cookies()
            fap_cookies = [c for c in cookies if 'fpt.edu.vn' in c.get('domain', '')]

            # Save cookies to JSON
            Path(self.COOKIES_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(self.COOKIES_FILE, 'w') as f:
                json.dump(cookies, f, indent=2)

            print(f"[+] Saved {len(cookies)} cookies to {self.COOKIES_FILE}")
            print(f"[+] FAP cookies: {len(fap_cookies)}")

            # Show important cookies
            important = ['cf_clearance', 'ASP.NET_SessionId', '__AntiXsrfToken']
            for c in cookies:
                if c['name'] in important:
                    val_preview = c['value'][:30] if c.get('value') else '(empty)'
                    print(f"    - {c['name']}: {val_preview}...")

            print("[+] Session saved! You can now use fetch command.")
            await asyncio.sleep(5)
            return True
        else:
            print("[?] Login may have failed. Current URL:", self._page.url)
            print("[.] Keeping browser open for manual check...")
            input("Press Enter to close browser...")
            return False

        await self._browser.close()
        await self._playwright.stop()

    async def _handle_feid_login(self):
        """Handle FeID login page (feid.fpt.edu.vn)"""
        print("[.] Handling FeID login page...")

        # Wait for page to load
        await asyncio.sleep(2)

        # Look for common input selectors
        username_selectors = [
            'input[name="Username"]',
            'input[name="username"]',
            'input[name="email"]',
            'input[type="email"]',
            'input[id*="username"]',
            'input[id*="Email"]',
            '#Input_Email',
            '#Email',
            '#username',
        ]

        password_selectors = [
            'input[name="Password"]',
            'input[name="password"]',
            'input[type="password"]',
            'input[id*="password"]',
            '#Input_Password',
            '#Password',
            '#password',
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
            except:
                continue

        for selector in password_selectors:
            try:
                elem = self._page.locator(selector)
                if await elem.count() > 0:
                    password_input = elem.first
                    print(f"[+] Found password input: {selector}")
                    break
            except:
                continue

        if username_input and password_input:
            print("[.] Filling in login credentials...")

            await username_input.fill(self.feid)
            await password_input.fill(self.password)

            # Look for submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Đăng nhập")',
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
                except:
                    continue
        else:
            print("[!] Could not find login form inputs")
            print("[.] Page may have different structure")
            print("[.] Saving page for debugging...")

            with open('debug_feid_page.html', 'w', encoding='utf-8') as f:
                f.write(await self._page.content())

    async def _handle_direct_login(self):
        """Handle direct login form on FAP page"""
        print("[.] Handling direct login form...")

        # Try to find and fill login form
        username_input = self._page.locator('input[type="email"], input[name*="user"], input[name*="email"]')
        password_input = self._page.locator('input[type="password"]')

        if await username_input.count() > 0 and await password_input.count() > 0:
            await username_input.first.fill(self.feid)
            await password_input.first.fill(self.password)

            # Submit form
            submit_btn = self._page.locator('button[type="submit"], input[type="submit"]')
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
                print("[.] Login form submitted...")

    async def fetch_schedule(self, week: int = None, year: int = None) -> str:
        """Fetch schedule using saved cookies"""
        # Check if cookies file exists
        if not Path(self.COOKIES_FILE).exists():
            print(f"[!] No cookies found. Run login first.")
            return None

        print(f"[.] Loading cookies from {self.COOKIES_FILE}...")
        with open(self.COOKIES_FILE, 'r') as f:
            cookies = json.load(f)

        print(f"[+] Loaded {len(cookies)} cookies")

        self._playwright = await async_playwright().start()

        # Launch browser WITHOUT persistent context, then add cookies
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        self._page = await self._browser.new_page()

        # Add cookies to the browser context
        await self._page.context.add_cookies(cookies)
        print("[.] Cookies added to browser context")

        print("[.] Navigating to schedule page...")
        await self._page.goto(self.SCHEDULE_URL, timeout=60000)
        await asyncio.sleep(5)

        # Check current page
        current_url = self._page.url
        content = await self._page.content()
        print(f"[.] Current URL: {current_url}")

        # If on login page, try to navigate home first
        if 'Login' in current_url or 'Default.aspx' in current_url:
            print("[.] Not on schedule page, navigating to home...")
            await self._page.goto("https://fap.fpt.edu.vn/Default.aspx", timeout=30000)
            await asyncio.sleep(3)

            # Try schedule page again
            await self._page.goto(self.SCHEDULE_URL, timeout=30000)
            await asyncio.sleep(5)
            content = await self._page.content()

        # Check if we have schedule dropdown
        if 'ctl00_mainContent_drpSelectWeek' not in content:
            print("[!] Schedule page not loaded. Saving debug page...")
            with open('debug_fetch_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("[.] Saved to debug_fetch_page.html")

            await self._browser.close()
            await self._playwright.stop()
            return None

        # Select week if specified - select_option triggers postback automatically
        if week is not None:
            print(f"[.] Selecting week: {week}")
            try:
                await self._page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))
                # Wait for navigation after postback
                await self._page.wait_for_load_state('networkidle', timeout=10000)
                await asyncio.sleep(3)
                print("[.] Week selection completed")
            except Exception as e:
                print(f"[.] Week selection failed: {e}")

        if year is not None:
            print(f"[.] Selecting year: {year}")
            try:
                await self._page.select_option('#ctl00_mainContent_drpYear', str(year))
                # Wait for navigation after postback
                await self._page.wait_for_load_state('networkidle', timeout=10000)
                await asyncio.sleep(3)
                print("[.] Year selection completed")
            except Exception as e:
                print(f"[.] Year selection failed: {e}")

        await asyncio.sleep(3)
        content = await self._page.content()

        # Save for debugging
        with open('schedule_fetched.html', 'w', encoding='utf-8') as f:
            f.write(content)

        await self._browser.close()
        await self._playwright.stop()

        return content

    async def fetch_exam_schedule(self) -> str:
        """Fetch exam schedule using saved cookies"""
        EXAM_URL = "https://fap.fpt.edu.vn/Exam/ScheduleExams.aspx"

        # Check if cookies file exists
        if not Path(self.COOKIES_FILE).exists():
            print(f"[!] No cookies found. Run login first.")
            return None

        print(f"[.] Loading cookies from {self.COOKIES_FILE}...")
        with open(self.COOKIES_FILE, 'r') as f:
            cookies = json.load(f)

        print(f"[+] Loaded {len(cookies)} cookies")

        self._playwright = await async_playwright().start()

        # Launch browser WITHOUT persistent context, then add cookies
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

        self._page = await self._browser.new_page()

        # Add cookies to the browser context
        await self._page.context.add_cookies(cookies)
        print("[.] Cookies added to browser context")

        print("[.] Navigating to exam schedule page...")
        await self._page.goto(EXAM_URL, timeout=60000)
        await asyncio.sleep(5)

        # Check current page
        current_url = self._page.url
        content = await self._page.content()
        print(f"[.] Current URL: {current_url}")

        # If on login page, try to navigate home first
        if 'Login' in current_url or 'Default.aspx' in current_url:
            print("[.] Not on exam page, navigating to home...")
            await self._page.goto("https://fap.fpt.edu.vn/Default.aspx", timeout=30000)
            await asyncio.sleep(3)

            # Try exam page again
            await self._page.goto(EXAM_URL, timeout=30000)
            await asyncio.sleep(5)
            content = await self._page.content()

        # Check if we have exam schedule content
        if 'Schedule Exam' not in content and 'table' not in content.lower():
            print("[!] Exam page not loaded. Saving debug page...")
            with open('debug_exam_fetch_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("[.] Saved to debug_exam_fetch_page.html")

            await self._browser.close()
            await self._playwright.stop()
            return None

        print("[.] Exam schedule page loaded successfully")

        await self._browser.close()
        await self._playwright.stop()

        return content


# Convenience functions
async def login(feid: str, password: str):
    """One-time login setup"""
    auth = FAPAutoLogin(headless=False, feid=feid, password=password)
    return await auth.auto_login()


async def fetch(week: int = None, year: int = None):
    """Fetch schedule using saved profile"""
    auth = FAPAutoLogin(headless=False)  # Use non-headless to match profile
    html = await auth.fetch_schedule(week=week, year=year)

    if html:
        # Import parser from same directory
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
    import sys
    import getpass

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
            print()
            print("Or use environment variables:")
            print("  set FAP_FEID=your_feid")
            print("  set FAP_PASSWORD=your_password")
            print("  python auto_login_feid.py login")
    else:
        print("Usage:")
        print("  python auto_login_feid.py login [feid] [password]")
        print("  python auto_login_feid.py fetch [week] [year]")
        print()
        print("Example:")
        print("  python auto_login_feid.py login student123@fe.edu.vn mypass")
        print("  python auto_login_feid.py fetch 1 2026")
