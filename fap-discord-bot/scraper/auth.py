"""
FAP Authentication Adapter with Auto-Refresh

Adapter class that provides FAPAuth interface using saved cookies.
Session refresh is handled by SessionValidator via patchright.
"""
import os
import logging
import asyncio
from typing import Optional
from datetime import datetime
from pathlib import Path
from .auto_login_feid import FAPAutoLogin
from .session_validator import SessionValidator

logger = logging.getLogger(__name__)

# Lock to prevent concurrent session refresh (browser-based)
_refresh_lock = asyncio.Lock()


class FAPAuth:
    """
    FAP Authentication Adapter with Auto-Refresh

    Provides FAPAuth-compatible interface for bot code.
    Uses FAPAutoLogin for aiohttp-based data fetching.
    Session refresh is handled by SessionValidator via patchright.
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
        self.cookies_file = Path(self.data_dir) / "fap_cookies.json"

        self._auth: Optional[FAPAutoLogin] = None
        self._validator: Optional[SessionValidator] = None
        self._refreshing = False
        self._last_diagnostic = {
            "timestamp": None,
            "operation": "startup",
            "status": "unknown",
            "code": "not_checked",
            "detail": "No auth activity recorded yet.",
        }

    def _record_diagnostic(self, operation: str, status: str, code: str, detail: str):
        """Store the latest auth diagnostic for status checks and error messages."""
        self._last_diagnostic = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "operation": operation,
            "status": status,
            "code": code,
            "detail": detail,
        }
        log_method = logger.error if status == "error" else logger.warning if status == "warning" else logger.info
        log_method(f"[{operation}] {code}: {detail}")

    def get_diagnostic_snapshot(self) -> dict:
        """Return the latest auth state for status reporting."""
        cookies_exist = self.cookies_file.exists()
        cookie_age_minutes = None
        if cookies_exist:
            age_seconds = max((datetime.now().timestamp() - self.cookies_file.stat().st_mtime), 0)
            cookie_age_minutes = int(age_seconds // 60)

        return {
            "username_configured": bool(self.username),
            "auto_refresh": self.auto_refresh,
            "headless": self.headless,
            "cookies_exist": cookies_exist,
            "cookie_age_minutes": cookie_age_minutes,
            "last_diagnostic": dict(self._last_diagnostic),
        }

    def format_last_failure(self, operation: str) -> str:
        """Convert the latest diagnostic into a concise user-facing error."""
        diag = self._last_diagnostic
        if diag["operation"] != operation or diag["status"] not in {"warning", "error"}:
            return f"Failed to fetch {operation}. Please try again later."

        failure_map = {
            "cookies_missing": f"Failed to fetch {operation}: no saved FAP session. Re-login is required.",
            "session_invalid": f"Failed to fetch {operation}: FAP session expired and refresh failed.",
            "refresh_failed": f"Failed to fetch {operation}: session refresh failed.",
            "refresh_retry_failed": f"Failed to fetch {operation}: refresh retry still could not access FAP.",
            "missing_credentials": f"Failed to fetch {operation}: FAP credentials are missing on the server.",
            "page_unavailable": f"Failed to fetch {operation}: FAP returned a login or unexpected page.",
        }
        return failure_map.get(diag["code"], f"Failed to fetch {operation}: {diag['detail']}")

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

        cookies_file = self.cookies_file

        if not cookies_file.exists():
            self._record_diagnostic(
                operation="session",
                status="warning",
                code="cookies_missing",
                detail=f"Cookie jar not found at {cookies_file}",
            )
            if self.auto_refresh and self.username and self.password:
                logger.info("Auto-refresh enabled - attempting login...")
                if await self._refresh_session_once():
                    self._record_diagnostic(
                        operation="session",
                        status="ok",
                        code="session_bootstrapped",
                        detail="Session recreated because cookies were missing.",
                    )
                    return self
                else:
                    return None
            else:
                detail = "Auto-refresh disabled or credentials unavailable."
                if not self.username or not self.password:
                    self._record_diagnostic("session", "error", "missing_credentials", detail)
                logger.warning("Please run login first:")
                logger.warning("  python scraper/auto_login_feid.py login <feid> <password>")
                return None

        # Validate and refresh if needed
        if force_refresh or self.auto_refresh:
            if not await self._validator.check_session_health(fast_check=fast_check):
                self._record_diagnostic(
                    operation="session",
                    status="warning",
                    code="session_invalid",
                    detail="Existing cookies failed the session health check.",
                )
                if not await self._refresh_session_once():
                    logger.warning("Session validation failed")
                    return None
                self._record_diagnostic(
                    operation="session",
                    status="ok",
                    code="session_refreshed",
                    detail="Session health check failed, but refresh succeeded.",
                )

        self._record_diagnostic(
            operation="session",
            status="ok",
            code="session_ready",
            detail="Session is ready for use.",
        )

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
            is_healthy = await self._validator.check_session_health()
            self._record_diagnostic(
                operation="refresh",
                status="ok" if is_healthy else "warning",
                code="refresh_wait_complete" if is_healthy else "refresh_wait_unhealthy",
                detail="Waited for another refresh attempt to finish.",
            )
            return is_healthy

        self._refreshing = True
        try:
            logger.warning("Session expired, attempting auto-refresh...")

            async with _refresh_lock:
                await self._ensure_validator()
                headless = os.getenv("HEADLESS", "false").lower() == "true"
                success = await self._validator.refresh_session(headless=headless)

            if success:
                self._record_diagnostic(
                    operation="refresh",
                    status="ok",
                    code="refresh_ok",
                    detail="Session refreshed successfully.",
                )
            else:
                self._record_diagnostic(
                    operation="refresh",
                    status="error",
                    code="refresh_failed",
                    detail="Session refresh failed via patchright.",
                )

            return success
        finally:
            self._refreshing = False

    async def fetch_schedule(self, week: Optional[int] = None, year: Optional[int] = None) -> Optional[str]:
        """Fetch schedule HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        html = await self._auth.fetch_schedule(week=week, year=year)

        if not html and self.auto_refresh:
            self._record_diagnostic(
                operation="schedule",
                status="warning",
                code="page_unavailable",
                detail="Initial schedule fetch returned no usable HTML.",
            )
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_schedule(week=week, year=year)
                if html:
                    self._record_diagnostic(
                        operation="schedule",
                        status="ok",
                        code="refresh_recovered",
                        detail="Schedule fetch succeeded after session refresh.",
                    )
                else:
                    self._record_diagnostic(
                        operation="schedule",
                        status="error",
                        code="refresh_retry_failed",
                        detail="Schedule fetch still failed after session refresh.",
                    )
            else:
                self._record_diagnostic(
                    operation="schedule",
                    status="error",
                    code="refresh_failed",
                    detail="Schedule fetch failed and session refresh did not recover it.",
                )
        elif html:
            self._record_diagnostic(
                operation="schedule",
                status="ok",
                code="fetch_ok",
                detail="Schedule fetch succeeded.",
            )

        return html

    async def fetch_exam_schedule(self) -> Optional[str]:
        """Fetch exam schedule HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        html = await self._auth.fetch_exam_schedule()

        if not html and self.auto_refresh:
            self._record_diagnostic(
                operation="exam schedule",
                status="warning",
                code="page_unavailable",
                detail="Initial exam schedule fetch returned no usable HTML.",
            )
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_exam_schedule()
                if html:
                    self._record_diagnostic(
                        operation="exam schedule",
                        status="ok",
                        code="refresh_recovered",
                        detail="Exam schedule fetch succeeded after session refresh.",
                    )
                else:
                    self._record_diagnostic(
                        operation="exam schedule",
                        status="error",
                        code="refresh_retry_failed",
                        detail="Exam schedule fetch still failed after session refresh.",
                    )
            else:
                self._record_diagnostic(
                    operation="exam schedule",
                    status="error",
                    code="refresh_failed",
                    detail="Exam schedule fetch failed and session refresh did not recover it.",
                )
        elif html:
            self._record_diagnostic(
                operation="exam schedule",
                status="ok",
                code="fetch_ok",
                detail="Exam schedule fetch succeeded.",
            )

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
            self._record_diagnostic(
                operation="attendance",
                status="warning",
                code="page_unavailable",
                detail="Initial attendance fetch returned no usable HTML.",
            )
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_attendance(
                    student_id=student_id,
                    campus=campus,
                    term=term,
                    course=course
                )
                if html:
                    self._record_diagnostic(
                        operation="attendance",
                        status="ok",
                        code="refresh_recovered",
                        detail="Attendance fetch succeeded after session refresh.",
                    )
                else:
                    self._record_diagnostic(
                        operation="attendance",
                        status="error",
                        code="refresh_retry_failed",
                        detail="Attendance fetch still failed after session refresh.",
                    )
            else:
                self._record_diagnostic(
                    operation="attendance",
                    status="error",
                    code="refresh_failed",
                    detail="Attendance fetch failed and session refresh did not recover it.",
                )
        elif html:
            self._record_diagnostic(
                operation="attendance",
                status="ok",
                code="fetch_ok",
                detail="Attendance fetch succeeded.",
            )

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
            self._record_diagnostic(
                operation="grades",
                status="warning",
                code="page_unavailable",
                detail="Initial grade fetch returned no usable HTML.",
            )
            if await self._refresh_session_once():
                logger.info("Session refreshed - retrying fetch...")
                html = await self._auth.fetch_grades(
                    student_id=student_id,
                    term=term,
                    course=course
                )
                if html:
                    self._record_diagnostic(
                        operation="grades",
                        status="ok",
                        code="refresh_recovered",
                        detail="Grade fetch succeeded after session refresh.",
                    )
                else:
                    self._record_diagnostic(
                        operation="grades",
                        status="error",
                        code="refresh_retry_failed",
                        detail="Grade fetch still failed after session refresh.",
                    )
            else:
                self._record_diagnostic(
                    operation="grades",
                    status="error",
                    code="refresh_failed",
                    detail="Grade fetch failed and session refresh did not recover it.",
                )
        elif html:
            self._record_diagnostic(
                operation="grades",
                status="ok",
                code="fetch_ok",
                detail="Grade fetch succeeded.",
            )

        return html

    async def fetch_application(self) -> Optional[str]:
        """Fetch application HTML (aiohttp, non-blocking)"""
        await self._ensure_auth()

        try:
            html = await self._auth.fetch_application()

            if not html and self.auto_refresh:
                self._record_diagnostic(
                    operation="application",
                    status="warning",
                    code="page_unavailable",
                    detail="Initial application fetch returned no usable HTML.",
                )
                if await self._refresh_session_once():
                    logger.info("Session refreshed - retrying fetch...")
                    html = await self._auth.fetch_application()
                    if html:
                        self._record_diagnostic(
                            operation="application",
                            status="ok",
                            code="refresh_recovered",
                            detail="Application fetch succeeded after session refresh.",
                        )
                    else:
                        self._record_diagnostic(
                            operation="application",
                            status="error",
                            code="refresh_retry_failed",
                            detail="Application fetch still failed after session refresh.",
                        )
                else:
                    self._record_diagnostic(
                        operation="application",
                        status="error",
                        code="refresh_failed",
                        detail="Application fetch failed and session refresh did not recover it.",
                    )
            elif html:
                self._record_diagnostic(
                    operation="application",
                    status="ok",
                    code="fetch_ok",
                    detail="Application fetch succeeded.",
                )

            return html
        except AttributeError:
            self._record_diagnostic(
                operation="application",
                status="warning",
                code="not_implemented",
                detail="fetch_application is not implemented in FAPAutoLogin.",
            )
            return None

    async def close(self):
        """Close browser and cleanup"""
        pass
