"""
Save FAP Session with Full Cookie Data
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from camoufox.async_api import AsyncCamoufox


async def save_session():
    """Login and save complete session"""

    print("=" * 60)
    print("FAP Session Saver")
    print("=" * 60)
    print()

    # Initialize browser
    browser = await AsyncCamoufox(headless=False).start()
    page = await browser.new_page()

    # Go to FAP schedule
    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=60000)

    print("\n[!] PLEASE LOGIN NOW:")
    print("1. Click Google login button")
    print("2. Complete authentication")
    print("3. Wait for schedule page to load")
    print()
    input("Press Enter AFTER you see the schedule page...")

    # Get all cookies with full data
    cookies = await page.context.cookies()

    # Filter FAP-related cookies only
    fap_cookies = [c for c in cookies if '.fpt.edu.vn' in c.get('domain', '')]

    print(f"\n[.] Found {len(fap_cookies)} FAP cookies:")

    for cookie in fap_cookies:
        expires_info = cookie.get('expires')
        if expires_info:
            if isinstance(expires_info, int):
                if expires_info > 0:
                    expiry_date = datetime.fromtimestamp(expires_info)
                    remaining = expiry_date - datetime.now()
                    print(f"  - {cookie['name']}: {remaining.days} days remaining")
                else:
                    print(f"  - {cookie['name']}: Server-side session")
            else:
                print(f"  - {cookie['name']}: {expires_info}")
        else:
            print(f"  - {cookie['name']}: Session cookie")

    # Save to file
    session_data = {
        'cookies': fap_cookies,
        'saved_at': datetime.now().isoformat()
    }

    session_file = Path("data/fap_session.json")
    session_file.parent.mkdir(exist_ok=True)

    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)

    print(f"\n[+] Saved {len(fap_cookies)} cookies to {session_file}")

    # Test if session works
    print("\n[.] Testing if session works...")

    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=30000)
    await asyncio.sleep(3)

    content = await page.content()

    if 'ctl00_mainContent_drpSelectWeek' in content:
        print("[+] Session is WORKING! Schedule page loaded.")
    elif 'Login' in page.url:
        print("[!] Session NOT working - on login page")
    else:
        print("[?] Unknown state")

    await browser.close()

    print("\n" + "=" * 60)
    print("Session saved! Now test it with:")
    print("  python scraper/test_session.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(save_session())
