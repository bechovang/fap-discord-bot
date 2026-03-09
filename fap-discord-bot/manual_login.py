"""Manual FAP Login - Open browser for manual FeID login once."""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import os

async def manual_login():
    """Open browser for manual login and save cookies."""
    print("=" * 60)
    print("FAP Manual Login - FeID Authentication")
    print("=" * 60)
    print("\nThis will:")
    print("1. Open Chrome browser at FAP login page")
    print("2. You manually login with FeID (Google)")
    print("3. After successful login, press Enter")
    print("4. Bot will save cookies for automated use\n")

    feid = "phuchcm2006@gmail.com"
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    profile_dir = data_dir / "chrome_profile"

    async with async_playwright() as p:
        print(f"[.] Opening browser with profile: {profile_dir}")
        browser = await p.chromium.launch(
            headless=False,  # Show browser for manual login
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        # Navigate to FAP
        print("[.] Navigating to FAP...")
        await page.goto('https://fap.fpt.edu.vn', wait_until='networkidle')

        print("\n" + "=" * 60)
        print("BROWSER IS NOW OPEN - PLEASE LOGIN MANUALLY")
        print("=" * 60)
        print("\nSteps:")
        print("1. Find and click 'Login With FeID' button")
        print("2. Login with your Google account")
        print("3. Complete any verification if needed")
        print("4. Make sure you see the FAP dashboard/schedule page")
        print("5. Come back here and press Enter\n")

        input("Press Enter after you have successfully logged in to FAP...")

        # Check if logged in
        current_url = page.url
        print(f"\n[.] Current URL: {current_url}")

        if "Login.aspx" not in current_url and "feid" not in current_url.lower():
            print("[+] Appears to be logged in! Saving cookies...")

            # Save cookies
            cookies = await context.cookies()
            import json
            from datetime import datetime

            cookie_data = {
                "timestamp": datetime.now().isoformat(),
                "url": current_url,
                "cookies": cookies
            }

            cookie_file = data_dir / "fap_cookies.json"
            with open(cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)

            print(f"[+] Saved {len(cookies)} cookies to {cookie_file}")
            print("[+] Login session saved! Bot can now use this session.")
        else:
            print("[!] Still on login page. Cookies not saved.")
            print("[!] Please try again and make sure to complete the login process.")

        print("\n[.] Closing browser...")
        await browser.close()

    print("\n" + "=" * 60)
    print("Done! You can now run the bot and use /schedule commands")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(manual_login())
