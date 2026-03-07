"""
Simple Camoufox Test for FAP
"""
import asyncio
import os
from dotenv import load_dotenv
from camoufox.async_api import AsyncCamoufox

load_dotenv()

async def test_camoufox_simple():
    """Test Camoufox with FAP"""
    print("=" * 50)
    print("Camoufox Simple Test")
    print("=" * 50)

    try:
        print("[.] Starting Camoufox...")
        browser = await AsyncCamoufox(headless=False).start()

        print("[+] Camoufox started!")
        print(f"[.] Browser type: {type(browser)}")

        # Get a page
        if hasattr(browser, 'pages'):
            pages = browser.pages
            print(f"[.] Pages count: {len(pages)}")
            if len(pages) > 0:
                page = pages[0]
            else:
                page = await browser.new_page()
        elif hasattr(browser, 'new_page'):
            page = await browser.new_page()
        else:
            print("[X] Unknown browser API")
            return

        print("[.] Navigating to FEID login...")
        await page.goto("https://feid.fpt.edu.vn/Account/Login", timeout=60000)

        print("[.] Waiting for page load...")
        await asyncio.sleep(10)

        print(f"[.] Current URL: {page.url}")
        print(f"[.] Page title: {await page.title()}")

        # Wait for user to see the page
        print("\n[.] Browser will stay open for 60 seconds for inspection...")
        print("[.] Please login manually if needed...")
        await asyncio.sleep(60)

        print("[.] Closing browser...")
        await browser.stop()

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_camoufox_simple())
