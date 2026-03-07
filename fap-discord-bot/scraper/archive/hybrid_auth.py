"""
Hybrid Authentication Solution
Combines Persistent Profile (for login) + FlareSolverr (for automation)
"""
import asyncio
import json
from pathlib import Path
from scraper.persistent_chromium import FAPPersistentAuth
from scraper.flaresolverr_auth import FAPFlareSolverrAuth


class HybridFAPAuth:
    """
    Hybrid approach:
    1. Use persistent Chromium profile for initial login (one-time)
    2. Extract auth cookies from profile
    3. Use cookies with FlareSolverr for automated requests

    This gives you:
    - Initial login with visible browser (easy)
    - Subsequent requests via FlareSolverr (automated)
    - Both solutions bypass Cloudflare ✅
    """

    def __init__(self):
        self.persistent_auth = FAPPersistentAuth(headless=False)
        self.flaresolverr_auth = FAPFlareSolverrAuth()
        self.cookies_file = "data/fap_cookies.json"

    def extract_cookies_from_profile(self) -> list:
        """Extract cookies from persistent Chromium profile"""
        print("[.] Extracting cookies from persistent profile...")

        # Read cookies from Chromium profile
        # Chromium stores cookies in SQLite database
        import sqlite3

        cookies_db = Path("data/chrome_profile/Default/Cookies")
        if not cookies_db.exists():
            print(f"[!] Cookies database not found at {cookies_db}")
            print("[!] Run setup first: python scraper/setup_profile.py")
            return []

        # Copy database to temp location (Chrome may lock it)
        import shutil
        temp_db = "temp_cookies.db"
        try:
            shutil.copy(cookies_db, temp_db)
        except Exception as e:
            print(f"[!] Cannot copy cookies database: {e}")
            return []

        # Extract cookies
        cookies = []
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # Get FAP-related cookies
            cursor.execute("""
                SELECT name, value, host, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE host_key LIKE '%fap.fpt.edu.vn%'
            """)

            for row in cursor.fetchall():
                cookies.append({
                    "name": row[0],
                    "value": row[1],
                    "domain": row[2],
                    "path": row[3],
                    "expires": row[4],
                    "secure": bool(row[5]),
                    "httpOnly": bool(row[6])
                })

            conn.close()

            # Save to JSON
            Path(self.cookies_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)

            print(f"[+] Extracted {len(cookies)} cookies")
            print(f"[+] Saved to {self.cookies_file}")

            return cookies

        except Exception as e:
            print(f"[!] Error extracting cookies: {e}")
            return []
        finally:
            # Clean up temp file
            try:
                Path(temp_db).unlink()
            except:
                pass

    def fetch_with_flaresolverr(self, cookies: list = None) -> str:
        """Fetch using FlareSolverr with optional cookies"""
        if cookies is None:
            # Try to load from file
            if Path(self.cookies_file).exists():
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)

        payload = {
            "cmd": "request.get",
            "url": "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx",
            "session": "fap_session",
            "maxTimeout": 60000,
            "cookies": cookies if cookies else []
        }

        return self.flaresolverr_auth._request(payload)


# Convenience functions
async def setup_first_time():
    """
    First-time setup:
    1. Create persistent profile with manual login
    2. Extract cookies from profile
    3. Ready for FlareSolverr automation
    """
    print("=" * 60)
    print("Hybrid FAP Auth - First Time Setup")
    print("=" * 60)
    print()

    # Step 1: Setup persistent profile
    print("Step 1: Setting up persistent Chromium profile...")
    print("You will need to complete Google login manually.")
    print()

    auth = FAPPersistentAuth(headless=False)
    success = await auth.setup_profile()

    if not success:
        print("[!] Setup failed")
        return False

    # Step 2: Extract cookies
    print()
    print("Step 2: Extracting cookies from profile...")

    hybrid = HybridFAPAuth()
    cookies = hybrid.extract_cookies_from_profile()

    if not cookies:
        print("[!] Failed to extract cookies")
        return False

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("[+] Persistent profile: data/chrome_profile/")
    print(f"[+] Extracted cookies: {len(cookies)} cookies")
    print(f"[+] Saved to: {hybrid.cookies_file}")
    print()
    print("Now you can use FlareSolverr for automated requests!")

    return True


def fetch_automated():
    """Fetch schedule using FlareSolverr with saved cookies"""
    hybrid = HybridFAPAuth()

    if not Path(hybrid.cookies_file).exists():
        print("[!] No cookies found. Run setup first:")
        print("    python scraper/hybrid_auth.py setup")
        return None

    print("[.] Fetching schedule via FlareSolverr...")

    result = hybrid.fetch_with_flaresolverr()

    if result.get("status") == "ok":
        solution = result.get("solution", {})
        html = solution.get("response", "")

        # Save HTML
        with open('schedule_hybrid.html', 'w', encoding='utf-8') as f:
            f.write(html)

        if 'ctl00_mainContent_drpSelectWeek' in html:
            print("[+] SUCCESS! Schedule page loaded!")
            print(f"[+] URL: {solution.get('url')}")
            return html
        else:
            print("[?] Not on schedule page")
            print(f"[.] URL: {solution.get('url')}")
            print(f"[.] First 300 chars: {html[:300]}")
            return None

    print("[!] Request failed")
    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "setup":
            asyncio.run(setup_first_time())
        elif command == "fetch":
            fetch_automated()
        elif command == "extract":
            hybrid = HybridFAPAuth()
            hybrid.extract_cookies_from_profile()
        else:
            print("Usage:")
            print("  python hybrid_auth.py setup   # First-time setup with login")
            print("  python hybrid_auth.py fetch   # Fetch using FlareSolverr")
            print("  python hybrid_auth.py extract # Extract cookies from profile")
    else:
        print("Usage:")
        print("  python hybrid_auth.py setup   # First-time setup with login")
        print("  python hybrid_auth.py fetch   # Fetch using FlareSolverr")
        print("  python hybrid_auth.py extract # Extract cookies from profile")
