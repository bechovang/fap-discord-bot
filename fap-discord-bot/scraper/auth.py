"""
FAP Authentication Adapter with Auto-Refresh

Adapter class that provides FAPAuth interface using FAPAutoLogin implementation.
Automatically validates and refreshes session when needed.
"""
import os
import logging
import asyncio
from typing import Optional
from .auto_login_feid import FAPAutoLogin
from .session_validator import SessionValidator

logger = logging.getLogger(__name__)

# Global lock to prevent concurrent Chrome access
_auth_lock = asyncio.Lock()


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
        self._refreshing = False  # Flag to prevent concurrent refresh

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

    async def get_session(self, force_refresh: bool = False, fast_check: bool = True):
        """
        Get authenticated session with auto-refresh

        Args:
            force_refresh: Force re-authentication
            fast_check: Use fast file age check instead of browser (default: True)

        Returns:
            self if session valid, None if failed
        """
        await self._ensure_validator()

        # Check cookies file exists
        from pathlib import Path
        cookies_file = Path(self.data_dir) / "fap_cookies.json"

        if not cookies_file.exists():
            logger.warning("No cookies found.")
            if self.auto_refresh and self.username and self.password:
                logger.info("🔄 Auto-refresh enabled - attempting login...")
                if await self._refresh_session_once():
                    return self
                else:
                    return None
            else:
                logger.warning("Please run login first:")
                logger.warning("  python scraper/auto_login_feid.py login <feid> <password>")
                return None

        # Validate and refresh if needed
        if force_refresh or self.auto_refresh:
            # Fast check: just verify cookies are recent (no browser launch)
            if not await self._validator.check_session_health(fast_check=fast_check):
                if not await self._refresh_session_once():
                    logger.warning("⚠️ Session validation failed")
                    return None

        return self

    async def _refresh_session_once(self) -> bool:
        """
        Refresh session once (with lock to prevent concurrent refresh)

        Returns:
            True if session is valid (or was refreshed successfully)
        """
        # If already refreshing, wait for it to complete
        if self._refreshing:
            logger.info("[.] Refresh already in progress, waiting...")
            while self._refreshing:
                await asyncio.sleep(0.5)
            # After waiting, check if session is now valid
            await self._ensure_validator()
            return await self._validator.check_session_health()

        # Start refresh
        self._refreshing = True
        try:
            logger.warning("⚠️ Session expired, attempting auto-refresh...")

            await self._ensure_validator()
            success = await self._validator.refresh_session(headless=False)

            if success:
                logger.info("✅ Session refreshed successfully")
            else:
                logger.error("❌ Session refresh failed")

            return success
        finally:
            self._refreshing = False

    async def fetch_schedule(self, week: Optional[int] = None, year: Optional[int] = None) -> Optional[str]:
        """
        Fetch schedule HTML for given week/year with auto-refresh on failure

        Args:
            week: Week number (1-52), None for current week
            year: Year, None for current year

        Returns:
            HTML content or None if failed
        """
        async with _auth_lock:  # Prevent concurrent Chrome access
            await self._ensure_auth()

            # Try fetch first
            html = await self._auth.fetch_schedule(week=week, year=year)

            # If failed and auto-refresh enabled, refresh and retry
            if not html and self.auto_refresh:
                if await self._refresh_session_once():
                    logger.info("✅ Session refreshed - retrying fetch...")
                    html = await self._auth.fetch_schedule(week=week, year=year)
                else:
                    logger.error("❌ Fetch failed after refresh")

            return html

    async def fetch_exam_schedule(self) -> Optional[str]:
        """
        Fetch exam schedule HTML with auto-refresh on failure

        Returns:
            HTML content or None if failed
        """
        async with _auth_lock:  # Prevent concurrent Chrome access
            await self._ensure_auth()

            # Try fetch first
            html = await self._auth.fetch_exam_schedule()

            # If failed and auto-refresh enabled, refresh and retry
            if not html and self.auto_refresh:
                if await self._refresh_session_once():
                    logger.info("✅ Session refreshed - retrying fetch...")
                    html = await self._auth.fetch_exam_schedule()
                else:
                    logger.error("❌ Fetch failed after refresh")

            return html

    async def fetch_attendance(
        self,
        student_id: str = None,
        campus: int = 4,
        term: int = None,
        course: int = None
    ) -> Optional[str]:
        """
        Fetch attendance HTML with auto-refresh on failure

        Args:
            student_id: Student ID (e.g., SE203055)
            campus: Campus ID (default: 4 for FPTU-HCM)
            term: Term ID (e.g., 60 for Spring2026)
            course: Course ID (e.g., 57599)

        Returns:
            HTML content or None if failed
        """
        async with _auth_lock:  # Prevent concurrent Chrome access
            await self._ensure_auth()

            # Try fetch first
            html = await self._auth.fetch_attendance(
                student_id=student_id,
                campus=campus,
                term=term,
                course=course
            )

            # If failed and auto-refresh enabled, refresh and retry
            if not html and self.auto_refresh:
                if await self._refresh_session_once():
                    logger.info("✅ Session refreshed - retrying fetch...")
                    html = await self._auth.fetch_attendance(
                        student_id=student_id,
                        campus=campus,
                        term=term,
                        course=course
                    )
                else:
                    logger.error("❌ Fetch failed after refresh")

            return html

    async def fetch_grades(
        self,
        student_id: str = None,
        term: str = None,
        course: int = None
    ) -> Optional[str]:
        """
        Fetch grade HTML with auto-refresh on failure

        Args:
            student_id: Student ID (e.g., SE203055)
            term: Term NAME (e.g., Fall2025, Spring2026)
            course: Course ID (e.g., 55959)

        Returns:
            HTML content or None if failed
        """
        async with _auth_lock:  # Prevent concurrent Chrome access
            await self._ensure_auth()

            # Try fetch first
            html = await self._auth.fetch_grades(
                student_id=student_id,
                term=term,
                course=course
            )

            # If failed and auto-refresh enabled, refresh and retry
            if not html and self.auto_refresh:
                if await self._refresh_session_once():
                    logger.info("✅ Session refreshed - retrying fetch...")
                    html = await self._auth.fetch_grades(
                        student_id=student_id,
                        term=term,
                        course=course
                    )
                else:
                    logger.error("❌ Fetch failed after refresh")

            return html

    async def close(self):
        """Close browser and cleanup"""
        # FAPAutoLogin creates/closes browser per fetch call
        pass
