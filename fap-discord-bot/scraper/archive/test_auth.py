"""
Test FAP Authentication with PatchRight
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from scraper.auth import FAPAuth
from scraper.parser import FAPParser

async def test_fap_auth():
    """Test FAP authentication"""
    print("=" * 50)
    print("FAP Authentication Test (PatchRight)")
    print("=" * 50)

    auth = FAPAuth(
        username=os.getenv('FAP_USERNAME'),
        password=os.getenv('FAP_PASSWORD'),
        headless=False,  # Show browser
        data_dir='data'
    )

    try:
        print("[.] Connecting to FAP...")
        page = await auth.get_session()

        if page:
            print("[+] Login successful!")

            html = await auth.fetch_schedule()
            if html:
                parser = FAPParser()
                items = parser.parse_schedule(html)
                print(f"[+] Found {len(items)} classes!")

                if items:
                    print("\n[Sample Classes]:")
                    for item in items[:3]:
                        print(f"  - {item.subject_code} | {item.day} {item.date}")
            else:
                print("[X] Failed to fetch schedule")
        else:
            print("[X] Login failed")

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await auth.close()

if __name__ == "__main__":
    asyncio.run(test_fap_auth())
