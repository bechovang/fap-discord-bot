"""
FAP Authentication - Save & Reuse Session
1. First run: Login manually once, script saves cookies
2. Subsequent runs: Uses saved cookies (no login needed!)
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from camoufox.async_api import AsyncCamoufox
    HAS_CAMOUFOX = True
except ImportError:
    HAS_CAMOUFOX = False
    AsyncCamoufox = None

logger = logging.getLogger(__name__)


class FAPSessionAuth:
    """FAP Authentication with session persistence"""

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    SESSION_FILE = "data/fap_session.json"
    SESSION_TIMEOUT = timedelta(hours=2)

    def __init__(self, headless: bool = False):
        if not HAS_CAMOUFOX:
            raise ImportError("Camoufox not installed! Run: pip install camoufox")

        self.headless = headless
        self._browser = None
        self._page = None
        self._session_data = None

    async def _init_browser(self, load_cookies: bool = True) -> None:
        """Initialize browser with optional cookies"""
        self._browser = await AsyncCamoufox(headless=self.headless).start()
        self._page = await self._browser.new_page()

        # Load saved cookies if available
        if load_cookies and self._session_data:
            try:
                await self._page.context.add_cookies(self._session_data['cookies'])
                logger.info("Loaded saved session cookies")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

    async def _save_session(self):
        """Save current session to file"""
        try:
            cookies = await self._page.context.cookies()
            session_data = {
                'cookies': cookies,
                'saved_at': datetime.now().isoformat(),
                'url': self._page.url
            }

            session_file = Path(self.SESSION_FILE)
            session_file.parent.mkdir(exist_ok=True)

            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)

            logger.info(f"Session saved to {self.SESSION_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def _load_session(self):
        """Load session from file"""
        try:
            session_file = Path(self.SESSION_FILE)
            if not session_file.exists():
                return None

            with open(session_file, 'r') as f:
                self._session_data = json.load(f)

            # Check if session is still valid
            saved_at = datetime.fromisoformat(self._session_data['saved_at'])
            if datetime.now() - saved_at > self.SESSION_TIMEOUT:
                logger.info("Session expired, need to login again")
                return None

            logger.info("Loaded valid session from file")
            return self._session_data
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")
            return None

    async def login_and_save(self) -> bool:
        """
        Login manually and save session
        Opens browser -> You login -> Saves cookies
        """
        try:
            await self._init_browser(load_cookies=False)

            print("=" * 60)
            print("MANUAL LOGIN REQUIRED")
            print("=" * 60)
            print("1. Browser window will open")
            print("2. Complete the Google login")
            print("3. Wait for redirect to FAP")
            print("4. Script will automatically save your session")
            print("=" * 60)

            # Go to FAP
            await self._page.goto(self.SCHEDULE_URL, timeout=60000)

            # Wait for user to complete login
            print("\nWaiting for you to complete login...")
            print("(I'll detect when you reach FAP)")

            for i in range(180):  # Wait up to 3 minutes
                await asyncio.sleep(1)

                current_url = str(self._page.url)

                # Check if we've successfully logged in
                if 'fap.fpt.edu.vn' in current_url and 'Login' not in current_url:
                    page_content = await self._page.content()

                    # Make sure we're not on Cloudflare page
                    if 'Just a moment' not in page_content:
                        print("\n[+] Login detected! Saving session...")

                        if await self._save_session():
                            print("[+] Session saved successfully!")
                            print("[+] Next time you run this, it will use the saved session")
                            return True

                if i % 30 == 0 and i > 0:
                    print(f"Still waiting... {i}s")

            print("\n[X] Login timeout - please try again")
            return False

        except Exception as e:
            print(f"[X] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fetch_schedule_with_session(self) -> Optional[str]:
        """
        Fetch schedule using saved session
        Returns HTML or None if session expired/invalid
        """
        try:
            # Try to load saved session
            if not self._load_session():
                print("[!] No valid session found. Please run login first.")
                return None

            # Initialize browser with saved cookies
            await self._init_browser(load_cookies=True)

            print("[.] Fetching schedule with saved session...")
            await self._page.goto(self.SCHEDULE_URL, timeout=30000)
            await asyncio.sleep(5)

            # Check if session is still valid
            page_content = await self._page.content()

            if 'Login' in self._page.url or 'feid.fpt.edu.vn' in self._page.url:
                print("[!] Session expired. Please login again.")
                return None

            if 'Just a moment' in page_content:
                print("[!] Cloudflare detected. Waiting...")
                for i in range(30):
                    await asyncio.sleep(1)
                    page_content = await self._page.content()
                    if 'Just a moment' not in page_content:
                        break

            print("[+] Schedule fetched successfully!")
            return page_content

        except Exception as e:
            print(f"[X] Error: {e}")
            return None

    async def close(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None


# Main test
async def main():
    """Test session-based authentication"""
    print("=" * 60)
    print("FAP Session Authentication")
    print("=" * 60)

    auth = FAPSessionAuth(headless=False)

    # Check if we have a valid session
    session_data = auth._load_session()

    if session_data:
        print("[+] Found saved session - trying to use it...")
        html = await auth.fetch_schedule_with_session()

        if html:
            # Save HTML
            with open('fap_schedule.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("[+] Saved to fap_schedule.html")

            # Try to parse
            try:
                from scraper.parser import FAPParser
                parser = FAPParser()
                items = parser.parse_schedule(html)
                print(f"[+] Found {len(items)} classes!")
            except:
                print("[!] Parser not available")
        else:
            print("\n[!] Session didn't work. Let's login and save a new one...")
            await auth.login_and_save()
    else:
        print("[!] No saved session found. Let's login and save one...")
        success = await auth.login_and_save()

        if success:
            print("\n[+] Now you can fetch schedule anytime without logging in!")

    await auth.close()


if __name__ == "__main__":
    asyncio.run(main())
