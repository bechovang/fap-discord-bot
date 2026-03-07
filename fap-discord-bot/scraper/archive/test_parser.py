#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for FAP Parser
Parses sample HTML files to verify parser functionality
"""
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.parser import FAPParser

def test_parser():
    """Test parser with sample HTML file"""
    print("=" * 50)
    print("FAP Parser Test")
    print("=" * 50)

    # Path to sample HTML
    html_file = Path(__file__).parent.parent / "resource" / "week_cur.html"

    if not html_file.exists():
        print(f"❌ Sample HTML not found: {html_file}")
        return False

    print(f"📄 Reading: {html_file}")
    html_content = html_file.read_text(encoding='utf-8')

    # Parse HTML
    parser = FAPParser()
    items = parser.parse_schedule(html_content)

    print(f"\n✅ Parsed {len(items)} schedule items")

    if items:
        print("\n" + "=" * 50)
        print("Sample Items:")
        print("=" * 50)

        # Show first 5 items
        for item in items[:5]:
            print(f"\n📚 {item.subject_code}")
            print(f"   📍 Room: {item.room}")
            print(f"   📅 {item.day} {item.date}")
            print(f"   🕐 {item.start_time} - {item.end_time}")
            print(f"   ✅ Status: {item.status}")

        # Get today's schedule
        today_items = parser.get_today_schedule(items)
        print(f"\n" + "=" * 50)
        print(f"Today's Schedule ({len(today_items)} items):")
        print("=" * 50)

        if today_items:
            for item in today_items:
                print(f"   📚 {item.subject_code} at {item.room} ({item.start_time}-{item.end_time})")
        else:
            print("   No classes today!")

        # Test Discord formatting
        print(f"\n" + "=" * 50)
        print("Discord Message Format:")
        print("=" * 50)
        discord_msg = parser.format_for_discord(today_items[:3], "Today's Schedule")
        print(discord_msg)

    return True

if __name__ == "__main__":
    try:
        success = test_parser()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
