"""
Check FAP Session Cookie Duration
Test how long FAP session actually lasts
"""
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from camoufox.async_api import AsyncCamoufox


async def check_session_duration():
    """Test how long FAP session stays valid"""

    print("=" * 60)
    print("FAP Session Duration Checker")
    print("=" * 60)
    print()
    print("STEP 1: Login and save session")
    print("-" * 60)

    # Initialize browser
    browser = await AsyncCamoufox(headless=False).start()
    page = await browser.new_page()

    # Go to FAP schedule
    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=60000)

    print("\n[!] PLEASE LOGIN NOW:")
    print("1. Click Google login")
    print("2. Complete authentication")
    print("3. Wait for schedule page to load")
    print()
    input("Press Enter AFTER you see the schedule page...")

    # Save session with cookie info
    cookies = await page.context.cookies()

    # Find session cookies and their expiry
    session_info = {
        'cookies': [],
        'saved_at': datetime.now().isoformat(),
        'login_time': datetime.now().isoformat()
    }

    print("\n[.] Analyzing cookies...")
    for cookie in cookies:
        if '.fpt.edu.vn' in cookie.get('domain', ''):
            cookie_info = {
                'name': cookie['name'],
                'domain': cookie['domain'],
                'expires': cookie.get('expires'),
                'session': cookie.get('expires') is None  # True = session cookie (expires when browser closes)
            }
            session_info['cookies'].append(cookie_info)

            # Print cookie info
            expires_str = "Session cookie (browser close)" if cookie_info['session'] else str(cookie_info['expires'])
            print(f"  - {cookie['name']}: {expires_str}")

    # Save to file
    session_file = Path("data/fap_session_check.json")
    session_file.parent.mkdir(exist_ok=True)

    with open(session_file, 'w') as f:
        json.dump(session_info, f, indent=2)

    print(f"\n[+] Session info saved to {session_file}")

    # Test if session works
    print("\n[.] Testing if session works...")
    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=30000)
    await asyncio.sleep(3)

    current_url = page.url
    content = await page.content()

    if 'Login' not in current_url and 'Just a moment' not in content:
        print("[+] Session is WORKING!")
    else:
        print("[!] Session NOT working")

    await browser.close()

    print("\n" + "=" * 60)
    print("SESSION COOKIE ANALYSIS")
    print("=" * 60)

    # Analyze cookies
    has_persistent = False
    has_session = False

    for cookie in session_info['cookies']:
        if cookie['session']:
            has_session = True
        else:
            has_persistent = True
            if cookie['expires']:
                expiry = datetime.fromisoformat(cookie['expires'].replace('Z', '+00:00'))
                remaining = expiry - datetime.now()
                print(f"\n{cookie['name']}:")
                print(f"  - Expires: {cookie['expires']}")
                print(f"  - Remaining: {remaining}")

    print("\n" + "-" * 60)
    print("CONCLUSION:")
    print("-" * 60)

    if has_persistent:
        print("[+] Has persistent cookies - session lasts HOURS/DAYS")
        print("    → Check expiry times above")
    elif has_session:
        print("[!] Only session cookies - expires when browser closes")
        print("    → Need to save/restore cookies manually")
    else:
        print("[?] No FAP cookies found")

    print("\n[.] NEXT: Run test_session_validity.py periodically")
    print("    to check when session actually expires")


async def test_session_validity():
    """Test if saved session is still valid"""

    session_file = Path("data/fap_session_check.json")

    if not session_file.exists():
        print("[!] No session file found. Run check_session_duration() first.")
        return

    with open(session_file, 'r') as f:
        session_data = json.load(f)

    print("=" * 60)
    print("Testing Session Validity")
    print("=" * 60)
    print(f"Session saved: {session_data['saved_at']}")
    print(f"Time elapsed: {datetime.now() - datetime.fromisoformat(session_data['saved_at'])}")
    print()

    # Try to use saved session
    browser = await AsyncCamoufox(headless=False).start()
    page = await browser.new_page()

    # Load cookies
    await page.context.add_cookies(session_data['cookies'])

    # Try to access FAP
    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=30000)
    await asyncio.sleep(3)

    current_url = page.url
    content = await page.content()

    print(f"Current URL: {current_url}")

    if 'Login' in current_url or 'feid.fpt.edu.vn' in current_url:
        print("[X] Session EXPIRED - redirected to login")
        await browser.close()
        return False
    elif 'Just a moment' in content:
        print("[!] Cloudflare challenge - waiting...")
        for i in range(30):
            await asyncio.sleep(1)
            content = await page.content()
            if 'Just a moment' not in content:
                break

        content = await page.content()
        if 'Login' in page.url:
            print("[X] Session EXPIRED after Cloudflare")
            await browser.close()
            return False

    print("[+] Session is STILL VALID!")
    print("[+] Successfully accessed FAP")

    # Try to get schedule data
    await asyncio.sleep(2)
    content = await page.content()

    if 'ctl00_mainContent_drpSelectWeek' in content:
        print("[+] Schedule page loaded successfully!")

        # Save sample
        with open('schedule_test.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("[+] Saved to schedule_test.html")
    else:
        print("[!] Unexpected page content")

    await browser.close()
    return True


async def main():
    """Main menu"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        await test_session_validity()
    else:
        await check_session_duration()

        print("\n" + "=" * 60)
        print("TO TEST SESSION LATER:")
        print("=" * 60)
        print("Run this command periodically:")
        print("  python scraper/check_session_duration.py test")
        print()
        print("This will tell you when the session actually expires.")


if __name__ == "__main__":
    asyncio.run(main())
