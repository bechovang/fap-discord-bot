import asyncio
import os
import sys
from dotenv import load_dotenv
from scraper.auth import FAPAuth

async def test():
    load_dotenv()
    auth = FAPAuth(
        username=os.getenv('FAP_USERNAME'),
        password=os.getenv('FAP_PASSWORD'),
        headless=False,
        data_dir='data'
    )
    
    try:
        print("Opening browser (visible mode)...")
        page = await auth.get_session()
        if page:
            print("Login successful!")
            await asyncio.sleep(5)
        else:
            print("Login failed!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await auth.close()

asyncio.run(test())
