"""
FAP Authentication - FlareSolverr
Uses FlareSolverr proxy to bypass Cloudflare challenges
"""
import asyncio
import requests
import json
from typing import Optional, Dict, List


class FAPFlareSolverrAuth:
    """
    FAP Authentication using FlareSolverr to bypass Cloudflare

    FlareSolverr runs as a proxy server that:
    1. Uses undetected-chromedriver to create a Chrome browser
    2. Opens URL and waits for Cloudflare challenge to solve
    3. Returns HTML + cookies that can be used in subsequent requests

    Requires FlareSolverr running: docker run -p 8191:8191 flaresolverr/flaresolverr
    """

    SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    FLARESOLVERR_URL = "http://localhost:8191/v1"
    SESSION_ID = "fap_session"  # Persistent session ID

    def __init__(self, flaresolverr_url: str = None):
        self.flaresolverr_url = flaresolverr_url or self.FLARESOLVERR_URL
        self.session_id = self.SESSION_ID
        self._session_created = False

    def _request(self, payload: dict) -> dict:
        """Send request to FlareSolverr API"""
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                self.flaresolverr_url,
                headers=headers,
                json=payload,
                timeout=120  # 2 minutes timeout for Cloudflare solving
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"[!] Cannot connect to FlareSolverr at {self.flaresolverr_url}")
            print("[!] Make sure FlareSolverr is running:")
            print("    docker run -d -p 8191:8191 flaresolverr/flaresolverr")
            raise
        except requests.exceptions.RequestException as e:
            print(f"[!] FlareSolverr request failed: {e}")
            raise

    def create_session(self) -> bool:
        """Create a persistent browser session (maintains cookies)"""
        print(f"[.] Creating FlareSolverr session: {self.session_id}")

        payload = {
            "cmd": "sessions.create",
            "session": self.session_id
        }

        try:
            result = self._request(payload)

            if result.get("status") == "ok":
                print(f"[+] Session created: {self.session_id}")
                self._session_created = True
                return True
            else:
                print(f"[!] Failed to create session: {result}")
                return False

        except Exception as e:
            print(f"[!] Session creation failed: {e}")
            return False

    def destroy_session(self) -> bool:
        """Destroy the browser session and free resources"""
        if not self._session_created:
            return True

        print(f"[.] Destroying session: {self.session_id}")

        payload = {
            "cmd": "sessions.destroy",
            "session": self.session_id
        }

        try:
            result = self._request(payload)
            self._session_created = False

            if result.get("status") == "ok":
                print(f"[+] Session destroyed")
                return True
            return False

        except Exception as e:
            print(f"[!] Session destroy failed: {e}")
            return False

    def fetch_schedule(self, week: int = None, year: int = None) -> Optional[str]:
        """
        Fetch schedule using FlareSolverr

        FlareSolverr will:
        1. Launch Chrome browser
        2. Navigate to FAP (bypass Cloudflare automatically)
        3. Wait for page to load
        4. Return HTML content + cookies
        """
        print("=" * 60)
        print("FAP Authentication via FlareSolverr")
        print("=" * 60)

        # Create session if not exists
        if not self._session_created:
            if not self.create_session():
                return None

        # Build URL with parameters if needed
        url = self.SCHEDULE_URL

        print(f"[.] Fetching: {url}")

        payload = {
            "cmd": "request.get",
            "url": url,
            "session": self.session_id,
            "maxTimeout": 60000,  # 60 seconds
            "waitInSeconds": 3,   # Wait for dynamic content
        }

        try:
            print("[.] FlareSolverr solving Cloudflare challenge...")
            result = self._request(payload)

            if result.get("status") != "ok":
                print(f"[!] FlareSolverr error: {result.get('message')}")
                return None

            solution = result.get("solution", {})
            status = solution.get("status")

            print(f"[.] Response status: {status}")

            # Check for Cloudflare errors
            if "Cloudflare" in solution.get("response", "")[:500]:
                print("[!] Cloudflare challenge detected (FlareSolverr may need update)")
                return None

            # Check if we got the schedule page
            html = solution.get("response", "")

            # Save HTML for debugging regardless of content
            with open('schedule_from_flaresolverr.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("[+] Saved HTML to schedule_from_flaresolverr.html")

            # Print URL we ended up at
            final_url = solution.get("url", "")
            print(f"[.] Final URL: {final_url}")

            # Check for login page
            if 'Login' in html or 'sign in' in html.lower() or 'login.aspx' in final_url.lower():
                print()
                print("[!] Redirected to login page")
                print("[!] Session needs authentication")
                print("[!] Use login_with_session() to complete Google login first")
                print(f"[.] Cookies: {len(solution.get('cookies', []))} cookies")

                # Check for cf_clearance
                cookies = solution.get("cookies", [])
                cf_clearance = next((c for c in cookies if c.get("name") == "cf_clearance"), None)
                if cf_clearance:
                    print(f"[+] cf_clearance found: {cf_clearance.get('value')[:20]}... (Cloudflare bypassed!)")
                else:
                    print("[.] No cf_clearance cookie (Cloudflare may still be active)")

                return html

            # Check if we got the schedule page
            if 'ctl00_mainContent_drpSelectWeek' in html:
                print("[+] SUCCESS! Schedule page loaded!")
                print(f"[+] Cookies received: {len(solution.get('cookies', []))} cookies")

                # Save cookies for inspection
                cookies = solution.get("cookies", [])
                cf_clearance = next((c for c in cookies if c.get("name") == "cf_clearance"), None)
                if cf_clearance:
                    print(f"[+] cf_clearance: {cf_clearance.get('value')[:20]}...")

                return html

            else:
                print("[?] Unexpected page content")
                print(f"[.] First 500 chars: {html[:500]}")
                return None

        except Exception as e:
            print(f"[!] Fetch failed: {e}")
            return None

    def login_with_session(self) -> bool:
        """
        Interactive login using FlareSolverr session

        This requires FlareSolverr to run in non-headless mode (HEADLESS=false)
        User will complete Google login in the visible browser window
        """
        print("=" * 60)
        print("FAP Login via FlareSolverr")
        print("=" * 60)
        print()
        print("[!] This requires FlareSolverr with HEADLESS=false")
        print("[!] Restart FlareSolverr: docker run -e HEADLESS=false -p 8191:8191 flaresolverr/flaresolverr")
        print()

        if not self._session_created:
            if not self.create_session():
                return False

        print("[.] Opening browser for manual login...")
        print("[!] Complete the Google login in the browser window")
        print()

        payload = {
            "cmd": "request.get",
            "url": self.SCHEDULE_URL,
            "session": self.session_id,
            "maxTimeout": 300000,  # 5 minutes - give time for manual login
            "waitInSeconds": 60,   # Wait long enough for user to complete login
        }

        try:
            result = self._request(payload)
            solution = result.get("solution", {})
            html = solution.get("response", "")

            if 'ctl00_mainContent_drpSelectWeek' in html:
                print("[+] Login successful! Schedule page loaded")
                print("[+] Session is now authenticated")
                return True
            else:
                print("[!] Login may have failed")
                return False

        except Exception as e:
            print(f"[!] Login failed: {e}")
            return False

    def list_sessions(self) -> List[str]:
        """List all active FlareSolverr sessions"""
        payload = {"cmd": "sessions.list"}

        try:
            result = self._request(payload)
            return result.get("sessions", [])
        except Exception:
            return []

    def get_cookies(self) -> List[Dict]:
        """Get cookies from the current session"""
        if not self._session_created:
            return []

        # Make a request to get current cookies
        payload = {
            "cmd": "request.get",
            "url": self.SCHEDULE_URL,
            "session": self.session_id,
            "maxTimeout": 60000,
            "returnOnlyCookies": True,  # Only return cookies, not full HTML
        }

        try:
            result = self._request(payload)
            solution = result.get("solution", {})
            return solution.get("cookies", [])
        except Exception:
            return []


# Standalone functions
def test_flaresolverr():
    """Test FlareSolverr connection"""
    auth = FAPFlareSolverrAuth()

    # List sessions
    sessions = auth.list_sessions()
    print(f"Active sessions: {sessions}")

    # Try to fetch schedule
    html = auth.fetch_schedule()

    if html:
        print("\n[+] SUCCESS! FlareSolverr bypassed Cloudflare")
        print("[+] Session maintains cookies for subsequent requests")
        return True
    else:
        print("\n[X] Failed - check messages above")
        return False


def login_first():
    """First-time login with FlareSolverr (requires HEADLESS=false)"""
    auth = FAPFlareSolverrAuth()

    success = auth.login_with_session()

    if success:
        print("\n[+] Login successful! Session is authenticated")
        print("[+] Now you can use fetch_schedule() without login")
    else:
        print("\n[X] Login failed")

    return success


def fetch_with_auth():
    """Fetch schedule using authenticated FlareSolverr session"""
    auth = FAPFlareSolverrAuth()
    html = auth.fetch_schedule()

    if html:
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

        if command == "test":
            test_flaresolverr()
        elif command == "login":
            login_first()
        elif command == "fetch":
            fetch_with_auth()
        else:
            print("Usage:")
            print("  python flaresolverr_auth.py test   # Test FlareSolverr connection")
            print("  python flaresolverr_auth.py login  # First-time login (needs HEADLESS=false)")
            print("  python flaresolverr_auth.py fetch  # Fetch schedule")
    else:
        print("Usage:")
        print("  python flaresolverr_auth.py test   # Test FlareSolverr connection")
        print("  python flaresolverr_auth.py login  # First-time login (needs HEADLESS=false)")
        print("  python flaresolverr_auth.py fetch  # Fetch schedule")
