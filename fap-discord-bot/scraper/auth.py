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

# Lock to prevent concurrent session refresh (browser-based)
_refresh_lock = asyncio.Lock()


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
        self.username = username
        self.password = password
        self.headless = headless
        self.data_dir = data_dir
        self.auto_refresh = auto_refresh

        self._auth: Optional[FAPAutoLogin] = None
        self._validator: Optional[SessionValidator] = None
        self._refreshing = False

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

        from pathlib import Path
        cookies_file = Path(self.data_dir) / "fap_cookies.json"

        if not cookies_file.exists():
            logger.warning("No cookies found.")
            if self.auto_refresh and self.username and self.password:
                logger.info("Auto-refresh enabled - attempting login...")
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
            if not await self._validator.check_session_health(fast_check=fast_check):
                if not await self._refresh_session_once():
                    logger.warning("Session validation failed")
                    return None

        return self

    async def _refresh_session_once(self) -> bool:
        """
        Refresh session once (with lock to prevent concurrent refresh)
        """
        if self._refreshing:
            logger.info("Refresh already in progress, waiting...")
            while self._refreshing:
                await asyncio.sleep(0.5)
            await self._ensure_validator()
            return await self._validator.check_session_health()

        self._refreshing = True
        try:
            logger.warning("Session expired, attempting auto-refresh...")

            async with _refresh_lock:
                await self._ensure_validator()
                headless = os.getenv("HEADLESS", "false").lower() == "true"
                success = await self._validator.refresh_session(headless=headless)

            if success:
                logger.info("Session refreshed successfully")
            else:
                logger.error("Session refresh failed")

            return success
        finally:
            self._refreshing = False

    async def fetch_schedule(self, week: Optional[int] = None, year: Optional[int] = None) -> Optional[str]:
        """Fetch schedule HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        html = await self._auth.fetch_schedule(week=week, year=year)

        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_schedule(week=week, year=year)
            else:
                logger.error("Fetch failed after refresh")

        return html

    async def fetch_exam_schedule(self) -> Optional[str]:
        """Fetch exam schedule HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        html = await self._auth.fetch_exam_schedule()

        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_exam_schedule()
            else:
                logger.error("Fetch failed after refresh")

        return html

    async def fetch_attendance(
        self,
        student_id: str = None,
        campus: int = 4,
        term: int = None,
        course: int = None
    ) -> Optional[str]:
        """Fetch attendance HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        html = await self._auth.fetch_attendance(
            student_id=student_id,
            campus=campus,
            term=term,
            course=course
        )

        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_attendance(
                    student_id=student_id,
                    campus=campus,
                    term=term,
                    course=course
                )
            else:
                logger.error("Fetch failed after refresh")

        return html

    async def fetch_grades(
        self,
        student_id: str = None,
        term: str = None,
        course: int = None
    ) -> Optional[str]:
        """Fetch grade HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        html = await self._auth.fetch_grades(
            student_id=student_id,
            term=term,
            course=course
        )

        if not html and self.auto_refresh:
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_grades(
                    student_id=student_id,
                    term=term,
                    course=course
                )
            else:
                logger.error("Fetch failed after refresh")

        return html

    async def fetch_application(self) -> Optional[str]:
        """Fetch application HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        try:
            html = await self._auth.fetch_application()

            if not html and self.auto_refresh:
                if await self._refresh_session_once():
                    logger.info("Session refreshed - retrying fetch...")
                    html = await self._auth.fetch_application()
                else:
                    logger.error("Fetch failed after refresh")

            return html
        except AttributeError:
            logger.warning("fetch_application not yet implemented in FAPAutoLogin")
            return None

    async def close(self):
        """Close browser and cleanup"""
        pass
