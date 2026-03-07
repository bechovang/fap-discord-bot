import asyncio
import os
import sys
import io

if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from scraper.auth_browserless import FAPAuthBrowserless

async def test():
    print("=" * 50)
    print("Testing FAP with Browserless")
    print("=" * 50)
    print(f"[+] Browserless URL: {os.getenv('BROWSERLESS_URL')}")
    print(f"[+] FAP Username: {os.getenv('FAP_USERNAME')}")
    print()
    print("[.] Connecting to FAP via Browserless...")
    
    auth = FAPAuthBrowserless(
        username=os.getenv('FAP_USERNAME'),
        password=os.getenv('FAP_PASSWORD'),
        browserless_url=os.getenv('BROWSERLESS_URL'),
        headless=False,  # Show browser for debugging
        data_dir='data'
    )
    
    try:
        page = await auth.get_session()
        
        if page:
            print("[+] Login successful!")
            print("[.] Fetching schedule...")
            
            html = await auth.fetch_schedule()
            
            if html:
                print("[+] Schedule fetched!")
                print("[.] Parsing...")
                
                from scraper.parser import FAPParser
                parser = FAPParser()
                items = parser.parse_schedule(html)
                
                print(f"[+] Found {len(items)} classes!")
                
                if items:
                    print("\n[Sample Classes]:")
                    for item in items[:3]:
                        print(f"  - {item.subject_code} | {item.day} {item.date}")
                
                print("\n[+] Browserless + FAP: SUCCESS!")
            else:
                print("[X] Failed to fetch schedule")
        else:
            print("[X] Login failed - check credentials or Cloudflare")
    
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await auth.close()

asyncio.run(test())
