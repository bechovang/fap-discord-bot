"""
Setup FAP Persistent Profile (One-Time)
Run this ONCE to create persistent browser profile
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.persistent_chromium import FAPPersistentAuth


async def main():
    print("=" * 60)
    print("FAP Persistent Profile Setup")
    print("=" * 60)
    print()
    print("This will create a persistent Chromium browser profile.")
    print("After setup, future runs will NOT require Cloudflare challenge!")
    print()
    print("Profile will be saved to: data/chrome_profile/")
    print()
    input("Press Enter to continue...")

    auth = FAPPersistentAuth(headless=False)
    success = await auth.setup_profile()

    if success:
        print("\n[+] Setup complete! Now run: python scraper/use_profile.py")
    else:
        print("\n[X] Setup failed. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
