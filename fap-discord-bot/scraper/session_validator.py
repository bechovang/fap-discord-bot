"""
Session Validator - Check and auto-refresh FAP session
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from .auto_login_feid import FAPAutoLogin
from .flaresolverr_auth import FAPFlareSolverrAuth

logger = logging.getLogger(__name__)


class SessionValidator:
    """Validate and refresh FAP session automatically"""

    def __init__(self, feid: str = None, password: str = None, data_dir: str = "data"):
        self.feid = feid or os.environ.get("FAP_FEID")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "fap_cookies.json"
        self.profile_dir = self.data_dir / "chrome_profile"
        self._flaresolverr_ready = False

    def is_session_valid(self) -> bool:
        """Check if session files exist"""
        return self.cookies_file.exists() and self.profile_dir.exists()

    def is_session_fresh(self, max_age_hours: int = 2) -> bool:
        """
        Fast check: verify cookies file is recent (within max_age_hours)
        This avoids launching Chrome just to check session validity
        """
        if not self.cookies_file.exists():
            return False

        import time
        file_age = time.time() - self.cookies_file.stat().st_mtime
        return file_age < (max_age_hours * 3600)

    async def check_session_health(self, fast_check: bool = False) -> bool:
        """
        Check if current session is actually working

        Args:
            fast_check: If True, only check file age (no browser launch)

        Returns:
            True if session can access FAP, False otherwise
        """
        if not self.is_session_valid():
            return False

        # Fast check: just verify cookies are recent (within 2 hours)
        if fast_check:
            return self.is_session_fresh(max_age_hours=2)

        # Full check: use aiohttp to verify session cookies work
        try:
            import aiohttp
            cookies_file = self.data_dir / "fap_cookies.json"
            with open(cookies_file, 'r') as f:
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
        Refresh session by re-login

        Args:
            headless: Run browser in headless mode

        Returns:
            True if refresh successful, False otherwise
        """
        if not self.feid or not self.password:
            logger.error("Cannot refresh - missing credentials")
            return False

        logger.info("Refreshing FAP session...")
        use_headless = headless if headless is not None else os.getenv("HEADLESS", "false").lower() == "true"
        prefer_flaresolverr = self._should_prefer_flaresolverr(use_headless)

        if prefer_flaresolverr:
            logger.info("Refresh strategy: FlareSolverr-first")
            flaresolverr_ok = await self._refresh_with_flaresolverr()
            if flaresolverr_ok:
                logger.info("FlareSolverr obtained Cloudflare cookies, attempting FEID login via Playwright...")
                try:
                    success = await self._refresh_with_playwright(use_headless)
                    if success:
                        logger.info("Session refreshed successfully (FlareSolverr + Playwright FEID login)")
                        return True
                except Exception as e:
                    logger.error(f"Playwright FEID login failed after FlareSolverr: {e}")
            else:
                logger.warning("FlareSolverr-first refresh failed, trying Playwright fallback...")

        success = await self._refresh_with_playwright(use_headless)
        if success:
            logger.info("Session refreshed successfully via Playwright")
            return True

        if prefer_flaresolverr:
            logger.warning("Playwright fallback failed after FlareSolverr-first strategy.")
            return False

        logger.warning("Playwright refresh failed, trying FlareSolverr fallback...")
        return await self._refresh_with_flaresolverr()

    def _should_prefer_flaresolverr(self, use_headless: bool) -> bool:
        """Prefer FlareSolverr in unattended server environments."""
        env_value = os.getenv("PREFER_FLARESOLVERR_REFRESH")
        if env_value is not None:
            return env_value.lower() == "true"
        return use_headless and bool(os.getenv("FLARESOLVERR_URL"))

    async def _refresh_with_playwright(self, use_headless: bool) -> bool:
        """Attempt a Playwright-based refresh."""
        logger.info(f"Starting Playwright FEID login (headless={use_headless})...")
        try:
            auth = FAPAutoLogin(
                headless=use_headless,
                feid=self.feid,
                password=self.password,
                interactive=False,
            )
            result = await asyncio.wait_for(auth.auto_login(), timeout=180)
            logger.info(f"Playwright FEID login result: {result}")
            return result
        except asyncio.TimeoutError:
            logger.error("Playwright FEID login timed out after 180s")
            return False
        except Exception as e:
            logger.error(f"Playwright FEID login error: {e}", exc_info=True)
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
        """
        Fall back to FlareSolverr when the direct Playwright login flow is
        blocked by Cloudflare.
        """
        flaresolverr_url = os.getenv("FLARESOLVERR_URL")
        if not flaresolverr_url:
            logger.warning("FlareSolverr fallback skipped - FLARESOLVERR_URL is not configured")
            return False

        if not await self._wait_for_flaresolverr():
            return False

        logger.info(f"Trying FlareSolverr via {flaresolverr_url}")

        def _run_flaresolverr_refresh() -> bool:
            auth = FAPFlareSolverrAuth(
                flaresolverr_url=flaresolverr_url,
                data_dir=str(self.data_dir)
            )
            return auth.refresh_cookies()

        try:
            success = await asyncio.to_thread(_run_flaresolverr_refresh)
        except Exception as e:
            logger.error(f"FlareSolverr fallback error: {e}")
            return False

        if success:
            logger.info("✅ FlareSolverr fallback refreshed shared cookies successfully")
            return True

        logger.warning(
            "FlareSolverr fallback failed. If you used FlareSolverr before, "
            "restart it and re-authenticate that session with "
            "`python scraper/flaresolverr_auth.py login`."
        )
        return False

    async def get_valid_session(self) -> bool:
        """
        Ensure we have a valid session, refresh if needed

        Returns:
            True if session is valid (or was refreshed successfully)
        """
        # First check if session exists and is healthy
        if self.is_session_valid():
            if await self.check_session_health():
                logger.info("✅ Session is valid")
                return True
            else:
                logger.warning("⚠️ Session expired, refreshing...")

        # Need to refresh or login
        return await self.refresh_session()


# Convenience function
async def ensure_valid_session(feid: str = None, password: str = None) -> bool:
    """
    Ensure FAP session is valid, refresh if needed

    Args:
        feid: FeID username
        password: FeID password

    Returns:
        True if session is valid
    """
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
