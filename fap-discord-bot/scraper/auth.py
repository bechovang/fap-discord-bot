"""
FAP Authentication Adapter with Auto-Refresh

Adapter class that provides FAPAuth interface using FAPAutoLogin implementation.
Automatically validates and refreshes session when needed.
"""
import os
import logging
from typing import Optional
from .auto_login_feid import FAPAutoLogin
from .session_validator import SessionValidator

logger = logging.getLogger(__name__)


class FAPAuth:
    """
    FAP Authentication Adapter with Auto-Refresh

    Provides FAPAuth-compatible interface for bot code.
    Internally uses FAPAutoLogin (FeID + Playwright).
    Automatically validates and refreshes session when expired.
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        headless: bool = True,
        user_agent: str = None,
        data_dir: str = "data",
        auto_refresh: bool = True
    ):
        """
        Initialize FAP Auth

        Args:
            username: FeID email (mapped to feid parameter)
            password: FeID password
            headless: Run browser in headless mode
            user_agent: User agent string (not used in FAPAutoLogin)
            data_dir: Data directory for storing profiles/cookies
            auto_refresh: Automatically refresh session when expired
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.data_dir = data_dir
        self.auto_refresh = auto_refresh

        # Create FAPAutoLogin instance
        self._auth: Optional[FAPAutoLogin] = None
        self._validator: Optional[SessionValidator] = None

    async def _ensure_auth(self):
        """Ensure FAPAutoLogin instance is created"""
        if self._auth is None:
            self._auth = FAPAutoLogin(
                headless=self.headless,
                feid=self.username,
                password=self.password
            )

    async def _ensure_validator(self):
        """Ensure SessionValidator instance is created"""
        if self._validator is None:
            self._validator = SessionValidator(
                feid=self.username,
                password=self.password,
                data_dir=self.data_dir
            )

    async def _validate_and_refresh_if_needed(self) -> bool:
        """
        Validate session and refresh if needed

        Returns:
            True if session is valid (or was refreshed successfully)
        """
        if not self.auto_refresh:
            return True

        if not self.username or not self.password:
            logger.warning("Auto-refresh disabled - missing credentials")
            return True  # Don't block if no credentials

        await self._ensure_validator()

        # Check if session is healthy
        if await self._validator.check_session_health():
            logger.info("✅ Session is valid")
            return True

        # Session expired - need to refresh
        logger.warning("⚠️ Session expired, attempting auto-refresh...")

        # Use non-headless for refresh (Cloudflare)
        success = await self._validator.refresh_session(headless=False)

        if success:
            logger.info("✅ Session refreshed successfully")
        else:
            logger.error("❌ Session refresh failed")

        return success

    async def get_session(self, force_refresh: bool = False):
        """
        Get authenticated session with auto-refresh

        Args:
            force_refresh: Force re-authentication

        Returns:
            self (for chaining fetch_schedule calls) or None if failed
        """
        await self._ensure_auth()

        # Check cookies file exists
        from pathlib import Path
        cookies_file = Path(self.data_dir) / "fap_cookies.json"

        if not cookies_file.exists():
            logger.warning("No cookies found.")
            if self.auto_refresh and self.username and self.password:
                logger.info("🔄 Auto-refresh enabled - attempting login...")
                if await self._validate_and_refresh_if_needed():
                    return self
                else:
                    return None
            else:
                logger.warning("Please run login first:")
                logger.warning("  python scraper/auto_login_feid.py login <feid> <password>")
                return None

        # Validate and refresh if needed
        if force_refresh or self.auto_refresh:
            if not await self._validate_and_refresh_if_needed():
                logger.warning("⚠️ Session validation failed")

        return self

    async def fetch_schedule(self, week: Optional[int] = None, year: Optional[int] = None) -> Optional[str]:
        """
        Fetch schedule HTML for given week/year with auto-refresh on failure

        Args:
            week: Week number (1-52), None for current week
            year: Year, None for current year

        Returns:
            HTML content or None if failed
        """
        await self._ensure_auth()

        # First attempt
        html = await self._auth.fetch_schedule(week=week, year=year)

        # If failed and auto-refresh is enabled, try to refresh and retry
        if not html and self.auto_refresh:
            logger.warning("⚠️ Fetch failed - attempting auto-refresh...")

            if await self._validate_and_refresh_if_needed():
                logger.info("✅ Session refreshed - retrying fetch...")
                html = await self._auth.fetch_schedule(week=week, year=year)

            if not html:
                logger.error("❌ Fetch failed after refresh")

        return html

    async def close(self):
        """Close browser and cleanup"""
        # FAPAutoLogin creates/closes browser per fetch_schedule call
        pass
