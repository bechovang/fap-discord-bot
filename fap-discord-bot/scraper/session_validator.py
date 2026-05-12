"""
Session Validator - Check and auto-refresh FAP session via FlareSolverr
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from .flaresolverr_auth import FAPFlareSolverrAuth

logger = logging.getLogger(__name__)


class SessionValidator:
    """Validate and refresh FAP session via FlareSolverr"""

    def __init__(self, feid: str = None, password: str = None, data_dir: str = "data"):
        self.feid = feid or os.environ.get("FAP_FEID")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "fap_cookies.json"
        self._flaresolverr_ready = False

    def is_session_valid(self) -> bool:
        """Check if cookies file exists"""
        return self.cookies_file.exists()

    def is_session_fresh(self, max_age_hours: int = 2) -> bool:
        """Check if cookies file is recent (within max_age_hours)"""
        if not self.cookies_file.exists():
            return False

        import time
        file_age = time.time() - self.cookies_file.stat().st_mtime
        return file_age < (max_age_hours * 3600)

    async def check_session_health(self, fast_check: bool = False) -> bool:
        """
        Check if current session is actually working

        Args:
            fast_check: If True, only check file age (no HTTP request)

        Returns:
            True if session can access FAP, False otherwise
        """
        if not self.cookies_file.exists():
            return False

        if fast_check:
            return self.is_session_fresh(max_age_hours=2)

        try:
            import aiohttp
            with open(self.cookies_file, 'r') as f:
                cookies_list = json.load(f)
            cookies = {c['name']: c['value'] for c in cookies_list if 'fpt.edu.vn' in c.get('domain', '')}

            if not cookies:
                return False

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            async with aiohttp.ClientSession(
                cookies=cookies,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as session:
                async with session.get(
                    "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx",
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        return False
                    content = await resp.text()
                    return 'ctl00_mainContent_drpSelectWeek' in content

        except Exception as e:
            logger.error(f"Session health check error: {e}")
            return False

    async def refresh_session(self, headless: bool = None) -> bool:
        """
        Refresh session via FlareSolverr.

        Returns True if FlareSolverr session is authenticated and cookies saved.
        Returns False if FlareSolverr session is not authenticated (needs manual login).
        """
        logger.info("Refreshing FAP session via FlareSolverr...")

        success = await self._refresh_with_flaresolverr()
        if success:
            logger.info("Session refreshed successfully via FlareSolverr")
            return True

        logger.warning(
            "FlareSolverr session is not authenticated. "
            "Manual login required: restart FlareSolverr with HEADLESS=false "
            "and run `python -m scraper.flaresolverr_auth login`"
        )
        return False

    async def _wait_for_flaresolverr(self, timeout: int = 60) -> bool:
        """Wait for FlareSolverr to become ready (handles startup race condition)."""
        if self._flaresolverr_ready:
            return True

        flaresolverr_url = os.getenv("FLARESOLVERR_URL")
        if not flaresolverr_url:
            return False

        import aiohttp
        logger.info(f"Waiting for FlareSolverr at {flaresolverr_url}...")
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as session:
                    async with session.post(
                        flaresolverr_url,
                        json={"cmd": "sessions.list"},
                    ) as resp:
                        if resp.status == 200:
                            self._flaresolverr_ready = True
                            logger.info("FlareSolverr is ready")
                            return True
            except Exception:
                pass
            await asyncio.sleep(2)

        logger.warning(f"FlareSolverr not ready after {timeout}s")
        return False

    async def _refresh_with_flaresolverr(self) -> bool:
        """Refresh session using FlareSolverr."""
        flaresolverr_url = os.getenv("FLARESOLVERR_URL")
        if not flaresolverr_url:
            logger.error("FLARESOLVERR_URL is not configured")
            return False

        if not await self._wait_for_flaresolverr():
            return False

        logger.info(f"Refreshing via FlareSolverr ({flaresolverr_url})")

        def _run_refresh() -> bool:
            auth = FAPFlareSolverrAuth(
                flaresolverr_url=flaresolverr_url,
                data_dir=str(self.data_dir)
            )
            return auth.refresh_cookies()

        try:
            success = await asyncio.to_thread(_run_refresh)
        except Exception as e:
            logger.error(f"FlareSolverr refresh error: {e}")
            return False

        if success:
            logger.info("FlareSolverr session authenticated, cookies saved")
            return True

        logger.warning("FlareSolverr session not authenticated (needs manual login)")
        return False

    async def get_valid_session(self) -> bool:
        """
        Ensure we have a valid session, refresh if needed

        Returns:
            True if session is valid (or was refreshed successfully)
        """
        if self.cookies_file.exists():
            if await self.check_session_health():
                logger.info("Session is valid")
                return True
            else:
                logger.warning("Session expired, refreshing...")

        return await self.refresh_session()


async def ensure_valid_session(feid: str = None, password: str = None) -> bool:
    """Ensure FAP session is valid, refresh if needed"""
    validator = SessionValidator(feid=feid, password=password)
    return await validator.get_valid_session()


if __name__ == "__main__":
    import sys

    async def main():
        action = sys.argv[1] if len(sys.argv) > 1 else "check"

        validator = SessionValidator()

        if action == "check":
            is_valid = await validator.check_session_health()
            print(f"Session valid: {is_valid}")

        elif action == "refresh":
            success = await validator.refresh_session()
            print(f"Refresh success: {success}")

        elif action == "ensure":
            success = await validator.get_valid_session()
            print(f"Session valid: {success}")

    asyncio.run(main())
