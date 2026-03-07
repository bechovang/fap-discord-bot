"""
FAP Authentication Adapter

Adapter class that provides FAPAuth interface using FAPAutoLogin implementation.
This maintains compatibility with existing bot code while using the working auth method.
"""
import os
import logging
from typing import Optional
from .auto_login_feid import FAPAutoLogin

logger = logging.getLogger(__name__)


class FAPAuth:
    """
    FAP Authentication Adapter

    Provides FAPAuth-compatible interface for bot code.
    Internally uses FAPAutoLogin (FeID + Playwright + FlareSolverr).
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        headless: bool = True,
        user_agent: str = None,
        data_dir: str = "data"
    ):
        """
        Initialize FAP Auth

        Args:
            username: FeID email (mapped to feid parameter)
            password: FeID password
            headless: Run browser in headless mode
            user_agent: User agent string (not used in FAPAutoLogin)
            data_dir: Data directory for storing profiles/cookies
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.data_dir = data_dir

        # Create FAPAutoLogin instance
        self._auth: Optional[FAPAutoLogin] = None
        self._is_logged_in = False

    async def _ensure_auth(self):
        """Ensure FAPAutoLogin instance is created"""
        if self._auth is None:
            self._auth = FAPAutoLogin(
                headless=self.headless,
                feid=self.username,
                password=self.password
            )

    async def get_session(self, force_refresh: bool = False):
        """
        Get authenticated session

        This is a compatibility method for bot code.
        Returns the auth instance itself for compatibility.

        Args:
            force_refresh: Force re-authentication (not implemented, returns self)

        Returns:
            self (for chaining fetch_schedule calls)
        """
        await self._ensure_auth()

        # Check if we need to login (cookies file doesn't exist)
        from pathlib import Path
        cookies_file = Path(self.data_dir) / "fap_cookies.json"

        if not cookies_file.exists():
            logger.warning("No cookies found. You need to run login first:")
            logger.warning("  python scraper/auto_login_feid.py login <feid> <password>")
            return None

        return self

    async def fetch_schedule(self, week: Optional[int] = None, year: Optional[int] = None) -> Optional[str]:
        """
        Fetch schedule HTML for given week/year

        Args:
            week: Week number (1-52), None for current week
            year: Year, None for current year

        Returns:
            HTML content or None if failed
        """
        await self._ensure_auth()
        return await self._auth.fetch_schedule(week=week, year=year)

    async def close(self):
        """Close browser and cleanup (no-op for FAPAutoLogin fetch mode)"""
        # FAPAutoLogin creates/closes browser per fetch_schedule call
        # No persistent browser to close
        pass
