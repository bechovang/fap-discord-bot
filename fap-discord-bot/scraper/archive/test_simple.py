"""
Simple FAP Test - Direct PatchRight
"""
import asyncio
import os
from dotenv import load_dotenv
from patchright.async_api import async_playwright

load_dotenv()

async def simple_test():
    """Simple test to access FAP"""
    print("=" * 50)
    print("Simple FAP Test")
    print("=" * 50)

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
        ]
    )

    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )

    page = await context.new_page()

    try:
        print("[.] Navigating to FAP login page...")
        await page.goto('https://fap.fpt.edu.vn/Account/Login.aspx', wait_until='domcontentloaded', timeout=30000)

        print("[.] Waiting for page to load...")
        await asyncio.sleep(5)

        print(f"[.] Current URL: {page.url}")

        # Try to find username input
        username_input = await page.query_selector('input[name="ctl00$mainContent$UserName"]')
        if username_input:
            print("[+] Found username input!")

            username = os.getenv('FAP_USERNAME')
            password = os.getenv('FAP_PASSWORD')

            print(f"[.] Entering username: {username}")
            await username_input.fill(username)

            password_input = await page.query_selector('input[name="ctl00$mainContent$Password"]')
            if password_input:
                print("[+] Found password input!")
                print(f"[.] Entering password: {'*' * len(password)}")
                await password_input.fill(password)

                # Submit form
                print("[.] Submitting form...")
                await page.evaluate('''
                    () => {
                        const form = document.forms['aspnetForm'];
                        if (form) {
                            document.getElementById('__EVENTTARGET').value = 'ctl00$mainContent$btnLogin';
                            form.submit();
                        }
                    }
                ''')

                print("[.] Waiting for navigation...")
                await asyncio.sleep(8)

                print(f"[.] Current URL after login: {page.url}")

                if 'Login.aspx' not in page.url:
                    print("[+] Login appears successful!")
                else:
                    print("[X] Still on login page")
            else:
                print("[X] Password input not found")
        else:
            print("[X] Username input not found")
            # Try to see what's on the page
            content = await page.content()
            if 'Cloudflare' in content or 'challenge' in content:
                print("[!] Cloudflare challenge detected!")
            elif '403' in content or 'Forbidden' in content:
                print("[!] 403 Forbidden detected!")
            else:
                print("[?] Unknown page state")

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[.] Press Enter to close browser...")
        input()
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(simple_test())
