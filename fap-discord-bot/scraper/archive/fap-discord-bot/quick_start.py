#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start Script - Test FAP connection first
"""
import asyncio
import sys
import os
import io

# Set UTF-8 encoding for Windows
if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from dotenv import load_dotenv
from scraper.auth import FAPAuth
from scraper.parser import FAPParser

async def test_fap_connection():
    """Test FAP login and schedule fetching"""
    print("=" * 50)
    print("FAP Bot - Quick Start Test")
    print("=" * 50)

    # Load environment
    load_dotenv()
    username = os.getenv('FAP_USERNAME')
    password = os.getenv('FAP_PASSWORD')

    if not username or not password:
        print("[!] FAP credentials not found in .env file!")
        return False

    print(f"[+] FAP Username: {username}")
    print("[.] Connecting to FAP...")

    # Create auth instance
    auth = FAPAuth(
        username=username,
        password=password,
        headless=True,
        data_dir='data'
    )

    try:
        # Test login
        print("[.] Logging in to FAP...")
        page = await auth.get_session()

        if not page:
            print("[X] Login failed! Please check your credentials.")
            return False

        print("[+] Login successful!")

        # Fetch schedule
        print("[.] Fetching schedule...")
        html = await auth.fetch_schedule()

        if not html:
            print("[X] Failed to fetch schedule.")
            return False

        # Parse schedule
        parser = FAPParser()
        items = parser.parse_schedule(html)

        print(f"[+] Schedule fetched successfully!")
        print(f"[+] Found {len(items)} classes")

        if items:
            print("\n" + "=" * 50)
            print("Sample Classes:")
            print("=" * 50)
            for item in items[:3]:
                print(f"  {item.subject_code} | {item.day} {item.date} | {item.room}")

            today = parser.get_today_schedule(items)
            print(f"\n[+] Today's classes: {len(today)}")

        print("\n" + "=" * 50)
        print("[+] FAP connection test PASSED!")
        print("=" * 50)
        print("\n[!] Next steps:")
        print("1. Add your Discord bot token to .env file")
        print("2. Run: python main.py")
        print("3. Invite bot to your server")
        print("\n[*] Get your token from:")
        print("https://discord.com/developers/applications/1479739776751108216/bot")

        return True

    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await auth.close()

if __name__ == "__main__":
    success = asyncio.run(test_fap_connection())
    sys.exit(0 if success else 1)
