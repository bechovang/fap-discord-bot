"""
Test Saved FAP Session
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from camoufox.async_api import AsyncCamoufox


async def test_session():
    """Test if saved session still works"""

    session_file = Path("data/fap_session.json")

    if not session_file.exists():
        print("[!] No session file found. Run save_session.py first")
        return

    with open(session_file, 'r') as f:
        session_data = json.load(f)

    saved_at = datetime.fromisoformat(session_data['saved_at'])
    elapsed = datetime.now() - saved_at

    print("=" * 60)
    print("FAP Session Test")
    print("=" * 60)
    print(f"Session saved: {saved_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Time elapsed: {elapsed}")
    print()

    # Check cf_clearance
    for cookie in session_data['cookies']:
        if cookie['name'] == 'cf_clearance':
            expires = cookie.get('expires')
            if expires and isinstance(expires, int) and expires > 0:
                expiry_date = datetime.fromtimestamp(expires)
                remaining = expiry_date - datetime.now()
                print(f"cf_clearance: {remaining.days} days remaining")
            break

    print()
    print("[.] Testing session...")

    # Test with headless=False for first run
    browser = await AsyncCamoufox(headless=False).start()
    page = await browser.new_page()

    # Load cookies
    await page.context.add_cookies(session_data['cookies'])

    # Try to access FAP
    await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=30000)

    # Wait for page to stabilize
    await asyncio.sleep(8)

    # Wait for network to be idle
    try:
        await page.wait_for_load_state('networkidle', timeout=10000)
    except:
        pass  # Continue if networkidle timeout

    current_url = str(page.url)

    # Get content with retry
    try:
        content = await page.content()
    except Exception as e:
        print(f"[!] Error getting content: {e}")
        print(f"[!] Current URL: {current_url}")
        await browser.close()
        return False

    print(f"Current URL: {current_url}")

    # Check result
    if 'Login' in current_url or 'feid.fpt.edu.vn' in current_url:
        print("[X] SESSION EXPIRED - Redirected to login")
        print(f"[!] Session lasted: {elapsed}")
        await browser.close()
        return False

    if 'Just a moment' in content:
        print("[!] Cloudflare challenge (unexpected with cf_clearance)")
        await asyncio.sleep(10)
        content = await page.content()

        if 'Login' in page.url:
            print("[X] Session expired after Cloudflare")
            await browser.close()
            return False

    if 'ctl00_mainContent_drpSelectWeek' in content:
        print("[+] SESSION WORKING!")
        print("[+] Schedule page loaded successfully!")

        # Save HTML
        with open('schedule_test.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("[+] Saved to schedule_test.html")

        await browser.close()

        print()
        print("=" * 60)
        print(f"RESULT: Session still working after {elapsed}")
        print("=" * 60)
        print()
        print("Run this test periodically to find session expiry:")
        print("  - After 30 minutes")
        print("  - After 1 hour")
        print("  - After 2 hours")
        print()
        return True
    else:
        print("[?] Unexpected page")
        await browser.close()
        return False


if __name__ == "__main__":
    asyncio.run(test_session())
