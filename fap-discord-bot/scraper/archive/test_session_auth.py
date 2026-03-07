"""
Test Chrome Session Approach
Instructions:
1. Open Chrome and login to https://fap.fpt.edu.vn
2. Verify you can access the schedule page
3. Close Chrome
4. Run this script
"""
import asyncio
import os
from pathlib import Path
from patchright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def test_chrome_session():
    """Test using Chrome session"""
    print("=" * 50)
    print("FAP Session Test - Chrome Profile")
    print("=" * 50)
    print("")
    print("INSTRUCTIONS:")
    print("1. Open Chrome browser")
    print("2. Go to https://fap.fpt.edu.vn")
    print("3. Login with your Google account")
    print("4. Verify you can see the schedule")
    print("5. Close Chrome")
    print("6. Then run this script")
    print("")
    print("=" * 50)

    input("Press Enter after you have logged in and closed Chrome...")

    playwright = await async_playwright().start()

    # Create a persistent context with Chrome profile
    user_data_dir = Path("data/chrome_profile")
    user_data_dir.mkdir(parents=True, exist_ok=True)

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=False,
        args=['--no-sandbox']
    )

    try:
        # Create a new page or use existing
        if len(context.pages) > 0:
            page = context.pages[0]
        else:
            page = await context.new_page()

        print("[.] Going to FAP schedule page...")
        await page.goto('https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx', wait_until='domcontentloaded', timeout=30000)

        await asyncio.sleep(3)

        print(f"[.] Current URL: {page.url}")

        # Check if we're logged in
        content = await page.content()

        if 'Login.aspx' in page.url or 'login' in page.url.lower():
            print("[X] Not logged in - session not found")
            print("")
            print("Please follow these steps:")
            print("1. Open a NEW Chrome window (not incognito)")
            print("2. Go to https://fap.fpt.edu.vn")
            print("3. Login with your account")
            print("4. Wait for the page to fully load")
            print("5. Close ALL Chrome windows")
            print("6. Run this script again")
        else:
            print("[+] Successfully loaded page!")

            # Save the HTML
            with open('schedule_fetched.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("[+] Saved HTML to schedule_fetched.html")

            # Try to parse
            from scraper.parser import FAPParser
            parser = FAPParser()
            items = parser.parse_schedule(content)
            print(f"[+] Parsed {len(items)} schedule items!")

            if items:
                print("\n[Sample Classes]:")
                for item in items[:3]:
                    print(f"  - {item.subject_code} | {item.day} {item.date}")

        print("\n[.] Press Enter to close...")
        input()

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_chrome_session())
