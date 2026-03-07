"""
FAP Authentication - Persistent Camoufox Profile
Maintains SAME browser fingerprint across runs
"""
import asyncio
from pathlib import Path
from datetime import datetime
from camoufox.async_api import AsyncCamoufox


class FAPPersistentAuth:
    """
    FAP Authentication with persistent browser profile
    First run: Setup profile with manual login
    Subsequent runs: Use saved profile - no Cloudflare challenge!
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    PROFILE_DIR = "data/camoufox_profile"  # Persistent profile directory

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.profile_dir = Path(self.PROFILE_DIR)  # Use class variable
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        self._browser = None
        self._page = None

    async def setup_profile(self) -> bool:
        """
        FIRST RUN ONLY: Setup persistent profile with manual login
        This creates the profile that will be reused
        """
        print("=" * 60)
        print("FAP Profile Setup (One-Time)")
        print("=" * 60)
        print()
        print("This will create a persistent browser profile.")
        print("After setup, future runs will NOT require Cloudflare challenge!")
        print()

        # Check if profile already exists
        if (self.profile_dir / "storage.js").exists():
            print("[!] Profile already exists!")
            print("[!] Run use_profile.py to use the existing profile.")
            print("[!] Or delete the profile folder to setup again:")
            print(f"   rm -rf {self.profile_dir}")
            return False

        # Start Camoufox with persistent profile
        print("[.] Starting Camoufox with persistent profile...")
        print(f"[.] Profile directory: {self.profile_dir.absolute()}")
        print()

        browser = await AsyncCamoufox(
            headless=self.headless,
            user_data_dir=str(self.profile_dir)  # PERSISTENT!
        ).start()

        page = await browser.new_page()

        # Navigate to FAP
        print("[.] Navigating to FAP schedule page...")
        await page.goto(self.SCHEDULE_URL, timeout=60000)

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
        current_url = str(page.url)
        content = await page.content()

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

            # Keep browser open for user to verify
            print()
            input("Press Enter to close browser...")

            await browser.close()
            return True

        else:
            print("[!] Setup failed - not on schedule page")
            print("[!] Please try again")
            await browser.close()
            return False

    async def use_profile(self) -> bool:
        """
        SUBSEQUENT RUNS: Use existing persistent profile
        No Cloudflare challenge needed!
        """
        print("=" * 60)
        print("FAP Authentication with Persistent Profile")
        print("=" * 60)

        # Check if profile exists
        if not (self.profile_dir / "storage.js").exists():
            print("[!] No profile found!")
            print(f"[!] Run setup first: python scraper/setup_profile.py")
            return False

        print(f"[.] Loading profile from: {self.profile_dir.absolute()}")
        print("[.] Profile includes saved cookies and fingerprint...")

        # Start Camoufox with SAME profile directory
        browser = await AsyncCamoufox(
            headless=self.headless,
            user_data_dir=str(self.profile_dir)  # SAME PROFILE!
        ).start()

        page = await browser.new_page()

        # Navigate to FAP - should NOT see Cloudflare challenge!
        print("[.] Navigating to FAP schedule...")
        await page.goto(self.SCHEDULE_URL, timeout=30000)

        # Wait for page load
        await asyncio.sleep(5)

        current_url = str(page.url)
        content = await page.content()
        page_title = await page.title()

        print(f"[.] Current URL: {current_url}")
        print(f"[.] Page title: {page_title[:50]}...")

        # Check if we hit Cloudflare
        if 'Just a moment' in content or 'cloudflare' in current_url.lower():
            print("[!] Cloudflare detected (unexpected!)")
            print("[!] Profile might be corrupted or expired")
            print("[!] Consider deleting profile and running setup again:")
            print(f"   rm -rf {self.profile_dir}")
            await browser.close()
            return False

        # Check if we're on login page
        if 'Login' in current_url:
            print("[!] Redirected to login - session expired")
            print("[!] Auth cookies need refresh")
            print("[!] Profile still valid for Cloudflare, but need relogin")
            await browser.close()
            return False

        # Check if we got the schedule page
        if 'ctl00_mainContent_drpSelectWeek' in content:
            print("[+] SUCCESS! Schedule page loaded!")
            print("[+] No Cloudflare challenge - profile working!")
            print()

            # Save HTML for verification
            with open('schedule_from_profile.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Saved to schedule_from_profile.html")

            await browser.close()

            print()
            print("=" * 60)
            print("RESULT: Persistent Profile WORKING!")
            print("=" * 60)
            print("[+] No manual Cloudflare bypass needed")
            print("[+] Browser fingerprint preserved across runs")
            return True

        print("[?] Unexpected page state")
        await browser.close()
        return False

    async def fetch_schedule(self, week: int = None, year: int = None) -> str:
        """Fetch schedule using persistent profile"""
        # Check if profile exists
        if not (self.profile_dir / "storage.js").exists():
            print("[!] No profile found. Run setup first.")
            return None

        # Start browser with profile
        browser = await AsyncCamoufox(
            headless=self.headless,
            user_data_dir=str(self.profile_dir)
        ).start()

        page = await browser.new_page()

        # Navigate to schedule
        await page.goto(self.SCHEDULE_URL, timeout=30000)
        await asyncio.sleep(5)

        # Select week if specified
        if week is not None:
            await page.select_option('#ctl00_mainContent_drpSelectWeek', str(week))
        if year is not None:
            await page.select_option('#ctl00_mainContent_drpYear', str(year))

        await asyncio.sleep(2)

        content = await page.content()
        await browser.close()

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
            print("  python scraper/persistent_profile.py setup  # First time only")
            print("  python scraper/persistent_profile.py test   # Test profile")
            print("  python scraper/persistent_profile.py fetch  # Fetch schedule")
    else:
        print("Usage:")
        print("  python scraper/persistent_profile.py setup  # First time only")
        print("  python scraper/persistent_profile.py test   # Test profile")
        print("  python scraper/persistent_profile.py fetch  # Fetch schedule")
