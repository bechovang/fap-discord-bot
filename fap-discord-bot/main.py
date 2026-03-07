#!/usr/bin/env python3
"""
FAP Discord Bot - Main Entry Point

A Discord bot that authenticates with FAP portal and provides schedule notifications.
"""
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.bot import main as bot_main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot_main()
