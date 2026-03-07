"""
Debug FAP - Save HTML to see what Cloudflare shows
"""
import asyncio
import os
from dotenv import load_dotenv
from patchright.async_api import async_playwright

load_dotenv()

async def debug_test():
    """Debug test to see what's actually on the page"""
    print("=" * 50)
    print("FAP Debug Test")
    print("=" * 50)

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
    )

    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )

    page = await context.new_page()

    try:
        print("[.] Navigating to FAP...")
        await page.goto('https://fap.fpt.edu.vn/Account/Login.aspx', wait_until='domcontentloaded', timeout=30000)

        # Wait longer for Cloudflare
        print("[.] Waiting 10 seconds for Cloudflare...")
        await asyncio.sleep(10)

        print(f"[.] Current URL: {page.url}")

        # Save HTML
        html = await page.content()
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("[+] Saved HTML to debug_page.html")

        # Check title
        title = await page.title()
        print(f"[.] Page title: {title}")

        # Check for Cloudflare indicators
        if 'cloudflare' in html.lower():
            print("[!] Cloudflare detected in HTML!")
        if 'challenge' in html.lower():
            print("[!] Challenge detected!")
        if 'turnstile' in html.lower():
            print("[!] Turnstile detected!")
        if 'checking your browser' in html.lower():
            print("[!] 'Checking your browser' message detected!")

        # Check for username input
        username_input = await page.query_selector('input[name*="UserName"]')
        if username_input:
            print("[+] Username input found!")
        else:
            print("[X] Username input NOT found!")

        # Keep browser open for inspection
        print("[.] Browser will stay open for 30 seconds for inspection...")
        await asyncio.sleep(30)

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(debug_test())
