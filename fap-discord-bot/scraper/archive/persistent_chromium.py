"""
FAP Authentication - Persistent Chromium Profile
Uses Playwright Chromium with user_data_dir for persistence
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


class FAPPersistentAuth:
    """
    FAP Authentication with persistent Chromium profile
    First run: Setup profile with manual login
    Subsequent runs: Use saved profile - no Cloudflare challenge!
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    PROFILE_DIR = "data/chrome_profile"  # Persistent profile directory

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.profile_dir = Path(self.PROFILE_DIR)
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def setup_profile(self) -> bool:
        """
        FIRST RUN ONLY: Setup persistent profile with manual login
        """
        print("=" * 60)
        print("FAP Profile Setup (One-Time)")
        print("=" * 60)
        print()
        print("This will create a persistent Chromium profile.")
        print("After setup, future runs will NOT require Cloudflare challenge!")
        print()

        # Check if profile already exists (Chromium uses Network/Cookies in newer versions)
        cookies_path = self.profile_dir / "Default" / "Network" / "Cookies"
        old_cookies_path = self.profile_dir / "Default" / "Cookies"
        if cookies_path.exists() or old_cookies_path.exists():
            print("[!] Profile already exists!")
            print("[!] Run use_profile.py to use the existing profile.")
            print("[!] Or delete the profile folder to setup again:")
            print(f"   rm -rf {self.PROFILE_DIR}")
            return False

        self._playwright = await async_playwright().start()

        # Launch Chromium with persistent profile
        print(f"[.] Starting Chromium with persistent profile...")
        print(f"[.] Profile directory: {self.profile_dir.absolute()}")

        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ],
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )

        # Get the page (persistent context has one page by default)
        if len(self._browser.pages) > 0:
            self._page = self._browser.pages[0]
        else:
            self._page = await self._browser.new_page()

        # Navigate to FAP
        print("[.] Navigating to FAP schedule page...")
        await self._page.goto(self.SCHEDULE_URL, timeout=60000)

        print()
        print("=" * 60)
        print("MANUAL LOGIN REQUIRED")
        print("=" * 60)
        print("1. Complete Google login in the browser window")
        print("2. Wait for schedule page to load")
        print("3. Wait for Cloudflare to complete (if shown)")
        print("4. Make sure you see the schedule table")
        print()
        input("Press Enter AFTER you see the schedule page...")

        # Verify we're on the right page
        current_url = self._page.url
        content = await self._page.content()

        if 'ctl00_mainContent_drpSelectWeek' in content:
            print("[+] Profile setup successful!")
            print("[+] Schedule page loaded with persistent profile")
            print()
            print("=" * 60)
            print("PROFILE SAVED")
            print("=" * 60)
            print(f"[+] Profile saved to: {self.profile_dir.absolute()}")
            print("[+] This profile includes:")
            print("  - Cookies (cf_clearance, auth cookies)")
            print("  - LocalStorage")
            print("  - SessionStorage")
            print("  - Cache")
            print("  - Browser fingerprint data")
            print()
            print("[+] Next runs will use this profile - NO Cloudflare challenge!")
            print()
            print("[.] To use: python scraper/use_profile.py")

            await self._browser.close()
            await self._playwright.stop()
            return True

        else:
            print("[!] Setup failed - not on schedule page")
            print("[!] Please try again")
            await self._browser.close()
            await self._playwright.stop()
            return False

    async def use_profile(self) -> bool:
        """
        SUBSEQUENT RUNS: Use existing persistent profile
        No Cloudflare challenge needed!
        """
        print("=" * 60)
        print("FAP Authentication with Persistent Profile")
        print("=" * 60)

        # Check if profile exists (Chromium uses Network/Cookies in newer versions)
        cookies_path = self.profile_dir / "Default" / "Network" / "Cookies"
        old_cookies_path = self.profile_dir / "Default" / "Cookies"
        if not cookies_path.exists() and not old_cookies_path.exists():
            print("[!] No profile found!")
            print(f"[!] Run setup first: python scraper/setup_profile.py")
            return False

        print(f"[.] Loading profile from: {self.profile_dir.absolute()}")
        print("[.] Profile includes saved cookies and fingerprint...")

        self._playwright = await async_playwright().start()

        # Launch Chromium with SAME profile directory
        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        if len(self._browser.pages) > 0:
            self._page = self._browser.pages[0]
        else:
            self._page = await self._browser.new_page()

        # Navigate to FAP
        print("[.] Navigating to FAP schedule...")
        await self._page.goto(self.SCHEDULE_URL, timeout=30000)

        # Wait for page load
        await asyncio.sleep(8)

        current_url = self._page.url
        content = await self._page.content()

        print(f"[.] Current URL: {current_url}")

        # Check if we hit Cloudflare
        if 'Just a moment' in content or 'cloudflare' in current_url.lower():
            print("[!] Cloudflare detected (unexpected!)")
            print("[!] Profile might be corrupted or expired")
            print("[!] Consider deleting profile and running setup again:")
            print(f"   rm -rf {self.PROFILE_DIR}")
            await self._browser.close()
            await self._playwright.stop()
            return False

        # Check if we're on login page
        if 'Login' in current_url:
            print("[!] Redirected to login - session expired")
            print("[!] Auth cookies need refresh")
            await self._browser.close()
            await self._playwright.stop()
            return False

        # Check if we got the schedule page
        if 'ctl00_mainContent_drpSelectWeek' in content:
            print("[+] SUCCESS! Schedule page loaded!")
            print("[+] No Cloudflare challenge - profile working!")

            # Save HTML for verification
            with open('schedule_from_profile.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Saved to schedule_from_profile.html")

            await self._browser.close()
            await self._playwright.stop()

            print()
            print("=" * 60)
            print("RESULT: Persistent Profile WORKING!")
            print("=" * 60)
            print("[+] No manual Cloudflare bypass needed")
            print("[+] Browser fingerprint preserved across runs")
            return True

        print("[?] Unexpected page state")
        await self._browser.close()
        await self._playwright.stop()
        return False

    async def fetch_schedule(self, week: int = None, year: int = None) -> str:
        """Fetch schedule using persistent profile"""
        # Check if profile exists (Chromium uses Network/Cookies in newer versions)
        cookies_path = self.profile_dir / "Default" / "Network" / "Cookies"
        old_cookies_path = self.profile_dir / "Default" / "Cookies"
        if not cookies_path.exists() and not old_cookies_path.exists():
            print("[!] No profile found. Run setup first.")
            return None

        self._playwright = await async_playwright().start()

        # Start browser with profile
        self._browser = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        if len(self._browser.pages) > 0:
            self._page = self._browser.pages[0]
        else:
            self._page = await self._browser.new_page()

        # Navigate to schedule
        await self._page.goto(self.SCHEDULE_URL, timeout=30000)
        await asyncio.sleep(5)

        # Select week if specified
        if week is not None:
            await self._page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))
        if year is not None:
            await self._page.select_option('#ctl00_mainContent_drpYear', str(year))

        await asyncio.sleep(2)

        content = await self._page.content()

        await self._browser.close()
        await self._playwright.stop()

        return content


# Setup script - run ONCE
async def setup():
    """Setup persistent profile"""
    auth = FAPPersistentAuth(headless=False)
    await auth.setup_profile()


# Test script - run AFTER setup
async def test():
    """Test persistent profile"""
    auth = FAPPersistentAuth(headless=False)
    success = await auth.use_profile()

    if success:
        print("\n[+] SUCCESS! Profile working - no Cloudflare challenge!")
    else:
        print("\n[X] Failed - check messages above")


# Fetch schedule for bot
async def fetch():
    """Fetch schedule using persistent profile"""
    auth = FAPPersistentAuth(headless=True)  # Headless for bot
    html = await auth.fetch_schedule()

    if html:
        # Parse and return
        from scraper.parser import FAPParser
        parser = FAPParser()
        items = parser.parse_schedule(html)
        print(f"[+] Found {len(items)} classes")
        return items

    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "setup":
            asyncio.run(setup())
        elif command == "test":
            asyncio.run(test())
        elif command == "fetch":
            asyncio.run(fetch())
        else:
            print("Usage:")
            print("  python persistent_chromium.py setup  # First time only")
            print("  python persistent_chromium.py test   # Test profile")
            print("  python persistent_chromium.py fetch  # Fetch schedule")
    else:
        print("Usage:")
        print("  python persistent_chromium.py setup  # First time only")
        print("  python persistent_chromium.py test   # Test profile")
        print("  python persistent_chromium.py fetch  # Fetch schedule")
