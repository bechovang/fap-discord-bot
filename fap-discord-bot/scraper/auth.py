"""
FAP Authentication Adapter with Auto-Refresh

Adapter class that provides FAPAuth interface using saved cookies.
Session refresh is handled by SessionValidator via Camoufox.
"""
import os
import logging
import asyncio
from typing import Awaitable, Callable, Optional
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
    Session refresh is handled by SessionValidator via Camoufox.
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
        self._event_callback: Optional[Callable[[dict], Awaitable[None]]] = None
        self._consecutive_refresh_failures: int = 0
        self._last_refresh_failure_time: Optional[datetime] = None
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

    def set_event_callback(self, callback: Callable[[dict], Awaitable[None]]):
        """Register async callback for auth lifecycle events."""
        self._event_callback = callback

    async def _emit_event(self, event_type: str, status: str, detail: str, **extra):
        """Send auth event to callback when configured."""
        if not self._event_callback:
            return

        payload = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "event_type": event_type,
            "status": status,
            "detail": detail,
            **extra,
        }
        try:
            await self._event_callback(payload)
        except Exception as exc:
            logger.error(f"Auth event callback failed: {exc}")

    def _browser_ready(self) -> bool:
        """Whether the shared browser instance is still available for fetches."""
        return bool(
            self._auth is not None
            and getattr(self._auth, "_context", None) is not None
            and getattr(self._auth, "_page", None) is not None
        )

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
            "backoff_active": f"Session lỗi, sẽ thử lại sau ~{self.get_backoff_remaining_minutes()} phút.",
        }
        return failure_map.get(diag["code"], f"Failed to fetch {operation}: {diag['detail']}")

    def should_attempt_refresh(self) -> bool:
        """Check if enough cooldown has passed since last refresh failure (for background keepalive)."""
        if self._consecutive_refresh_failures <= 1:
            return True
        if not self._last_refresh_failure_time:
            return True
        backoff_minutes = {2: 30, 3: 60, 4: 120}
        backoff_secs = backoff_minutes.get(self._consecutive_refresh_failures, 240) * 60
        elapsed = (datetime.utcnow() - self._last_refresh_failure_time).total_seconds()
        return elapsed >= backoff_secs

    def get_backoff_remaining_minutes(self) -> int:
        """Return minutes until next refresh attempt is allowed."""
        if self._consecutive_refresh_failures <= 1 or not self._last_refresh_failure_time:
            return 0
        backoff_minutes = {2: 30, 3: 60, 4: 120}
        backoff_secs = backoff_minutes.get(self._consecutive_refresh_failures, 240) * 60
        elapsed = (datetime.utcnow() - self._last_refresh_failure_time).total_seconds()
        remaining = max(0, backoff_secs - elapsed)
        return int(remaining // 60)

    async def _ensure_auth(self):
        """Ensure FAPAutoLogin instance is created"""
        if self._auth is None:
            self._auth = FAPAutoLogin(
                headless=self.headless,
                feid=self.username,
                password=self.password
            )

    async def _ensure_validator(self):
        """Ensure SessionValidator instance is created, sharing the same FAPAutoLogin."""
        if self._validator is None:
            await self._ensure_auth()
            self._validator = SessionValidator(
                feid=self.username,
                password=self.password,
                data_dir=self.data_dir,
                login_instance=self._auth,
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
                if await self._refresh_session_once(reason="missing_cookies"):
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
                if not await self._refresh_session_once(reason="session_invalid"):
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

    async def _refresh_session_once(self, reason: str = "unknown") -> bool:
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
                self._consecutive_refresh_failures = 0
                self._last_refresh_failure_time = None
                self._record_diagnostic(
                    operation="refresh",
                    status="ok",
                    code="refresh_ok",
                    detail="Session refreshed successfully.",
                )
                await self._emit_event(
                    event_type="login_result",
                    status="success",
                    detail="FAP login/refresh succeeded.",
                    reason=reason,
                    operation="refresh",
                    code="refresh_ok",
                )
            else:
                self._consecutive_refresh_failures += 1
                self._last_refresh_failure_time = datetime.utcnow()
                self._record_diagnostic(
                    operation="refresh",
                    status="error",
                    code="refresh_failed",
                    detail="Session refresh failed via Camoufox.",
                )
                await self._emit_event(
                    event_type="login_result",
                    status="error",
                    detail="FAP login/refresh failed.",
                    reason=reason,
                    operation="refresh",
                    code="refresh_failed",
                )

            return success
        finally:
            self._refreshing = False

    async def _fetch_with_recovery(
        self,
        operation: str,
        fetcher: Callable[[], Awaitable[Optional[str]]],
    ) -> Optional[str]:
        """Fetch once, then validate session and re-login once if needed."""
        await self._ensure_auth()

        html = await fetcher()
        if html:
            self._record_diagnostic(
                operation=operation,
                status="ok",
                code="fetch_ok",
                detail=f"{operation.capitalize()} fetch succeeded.",
            )
            return html

        if not self.auto_refresh:
            self._record_diagnostic(
                operation=operation,
                status="error",
                code="page_unavailable",
                detail=f"{operation.capitalize()} fetch returned no usable HTML and auto-refresh is disabled.",
            )
            return None

        self._record_diagnostic(
            operation=operation,
            status="warning",
            code="page_unavailable",
            detail=f"Initial {operation} fetch returned no usable HTML.",
        )

        if not self.should_attempt_refresh():
            remaining = self.get_backoff_remaining_minutes()
            logger.info(
                f"{operation}: session refresh in cooldown (~{remaining}m remaining, "
                f"{self._consecutive_refresh_failures} consecutive failures)"
            )
            self._record_diagnostic(
                operation=operation,
                status="warning",
                code="backoff_active",
                detail=f"Session refresh cooldown active. Will retry in ~{remaining} minutes.",
            )
            await self._emit_event(
                event_type="backoff_active",
                status="warning",
                detail=f"Session refresh cooldown active after {self._consecutive_refresh_failures} failures.",
                remaining_minutes=remaining,
            )
            return None

        if not self._browser_ready():
            logger.warning(f"{operation} fetch failed because browser context is unavailable; forcing re-login.")
            recovered = await self._refresh_session_once(reason=f"{operation}_browser_unavailable")
        else:
            session = await self.get_session(force_refresh=False, fast_check=False)
            recovered = bool(session)

        if not recovered:
            self._record_diagnostic(
                operation=operation,
                status="error",
                code="refresh_failed",
                detail=f"{operation.capitalize()} fetch failed because session recovery did not succeed.",
            )
            return None

        html = await fetcher()
        if html:
            self._record_diagnostic(
                operation=operation,
                status="ok",
                code="refresh_recovered",
                detail=f"{operation.capitalize()} fetch succeeded after session recovery.",
            )
            return html

        self._record_diagnostic(
            operation=operation,
            status="error",
            code="refresh_retry_failed",
            detail=f"{operation.capitalize()} fetch still failed after session recovery.",
        )
        return None

    async def fetch_schedule(self, week: Optional[int] = None, year: Optional[int] = None) -> Optional[str]:
        """Fetch schedule HTML (aiohttp, non-blocking)"""
        return await self._fetch_with_recovery(
            "schedule",
            lambda: self._auth.fetch_schedule(week=week, year=year),
        )

    async def fetch_exam_schedule(self) -> Optional[str]:
        """Fetch exam schedule HTML (aiohttp, non-blocking)"""
        return await self._fetch_with_recovery(
            "exam schedule",
            lambda: self._auth.fetch_exam_schedule(),
        )

    async def fetch_attendance(
        self,
        student_id: str = None,
        campus: int = 4,
        term: int = None,
        course: int = None
    ) -> Optional[str]:
        """Fetch attendance HTML (aiohttp, non-blocking)"""
        return await self._fetch_with_recovery(
            "attendance",
            lambda: self._auth.fetch_attendance(
                student_id=student_id,
                campus=campus,
                term=term,
                course=course,
            ),
        )

    async def fetch_grades(
        self,
        student_id: str = None,
        term: str = None,
        course: int = None
    ) -> Optional[str]:
        """Fetch grade HTML (aiohttp, non-blocking)"""
        return await self._fetch_with_recovery(
            "grades",
            lambda: self._auth.fetch_grades(
                student_id=student_id,
                term=term,
                course=course,
            ),
        )

    async def fetch_application(self) -> Optional[str]:
        """Fetch application HTML (aiohttp, non-blocking)"""
        try:
            await self._ensure_auth()
            return await self._fetch_with_recovery(
                "application",
                lambda: self._auth.fetch_application(),
            )
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
        if self._auth is not None:
            try:
                await self._auth.close()
            except Exception as exc:
                logger.error(f"Error while closing auth browser: {exc}")
        self._auth = None
        self._validator = None
