"""
Use FAP Persistent Profile
Run this AFTER setup to test/use the persistent profile
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.persistent_chromium import FAPPersistentAuth


async def main():
    auth = FAPPersistentAuth(headless=False)
    success = await auth.use_profile()

    if success:
        print("\n[+] SUCCESS! Profile working - no Cloudflare challenge!")
        print("[+] You can now use this in your Discord bot")
    else:
        print("\n[X] Failed - check messages above")
        print("[!] Make sure you ran setup_profile.py first")


if __name__ == "__main__":
    asyncio.run(main())
