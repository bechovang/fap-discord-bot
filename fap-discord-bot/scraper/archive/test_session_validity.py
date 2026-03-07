"""
Test FAP Session Validity Over Time
Run this periodically to check when session expires
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from camoufox.async_api import AsyncCamoufox


async def test_session():
    """Test if saved session still works"""

    session_file = Path("data/fap_session_check.json")

    if not session_file.exists():
        print("[!] No session file found. Run check_session_duration.py first")
        return

    with open(session_file, 'r') as f:
        session_data = json.load(f)

    saved_at = datetime.fromisoformat(session_data['saved_at'])
    elapsed = datetime.now() - saved_at

    print("=" * 60)
    print("FAP Session Validity Test")
    print("=" * 60)
    print(f"Session saved: {saved_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Time elapsed: {elapsed}")
    print()

    # Check cf_clearance expiry
    for cookie in session_data['cookies']:
        if cookie['name'] == 'cf_clearance' and cookie['expires'] != -1:
            expiry_date = datetime.fromtimestamp(cookie['expires'])
            remaining = expiry_date - datetime.now()
            print(f"cf_clearance cookie:")
            print(f"  - Expires: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  - Remaining: {remaining.days} days")
            print()

    # Test session
    print("[.] Testing session validity...")

    browser = await AsyncCamoufox(headless=False).start()
    page = await browser.new_page()

    # Load cookies
    await page.context.add_cookies(session_data['cookies'])

    # Try to access FAP
    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=30000)
    await asyncio.sleep(5)

    current_url = str(page.url)
    content = await page.content()

    # Check results
    print(f"Current URL: {current_url}")

    if 'Login' in current_url or 'feid.fpt.edu.vn' in current_url:
        print("[X] SESSION EXPIRED - Redirected to login")
        print(f"[!] Session lasted: {elapsed}")
        await browser.close()
        return False

    elif 'Just a moment' in content:
        print("[!] Cloudflare detected (shouldn't happen with cf_clearance)")
        print("[!] Waiting for challenge...")

        for i in range(30):
            await asyncio.sleep(1)
            content = await page.content()
            if 'Just a moment' not in content:
                print("[+] Cloudflare passed")
                break

        # Check again after Cloudflare
        current_url = str(page.url)
        if 'Login' in current_url:
            print("[X] Session expired after Cloudflare")
            await browser.close()
            return False

    # Check if we got the schedule page
    if 'ctl00_mainContent_drpSelectWeek' in content:
        print("[+] SESSION STILL VALID!")
        print("[+] Successfully loaded schedule page")

        # Count schedule items
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'lxml')
        tables = soup.find_all('table')
        print(f"[+] Found {len(tables)} tables on page")

        # Save sample
        with open('schedule_check.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("[+] Saved to schedule_check.html")
    else:
        print("[?] Unexpected page content")
        print(f"[!] Page title: {await page.title()}")

    await browser.close()

    print()
    print("=" * 60)
    print("RESULT: Session is still working after", elapsed)
    print("=" * 60)
    print()
    print("Run this test again later to find expiry time:")
    print("  python scraper/test_session_validity.py")

    return True


if __name__ == "__main__":
    asyncio.run(test_session())
