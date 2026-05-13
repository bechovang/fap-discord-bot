"""
Session Validator - Check and auto-refresh FAP session via patchright
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from .auto_login_feid import FAPAutoLogin

logger = logging.getLogger(__name__)


class SessionValidator:
    """Validate and refresh FAP session via patchright browser"""

    def __init__(self, feid: str = None, password: str = None, data_dir: str = "data"):
        self.feid = feid or os.environ.get("FAP_FEID") or os.environ.get("FAP_USERNAME")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "fap_cookies.json"

    def is_session_valid(self) -> bool:
        return self.cookies_file.exists()

    def is_session_fresh(self, max_age_hours: int = 2) -> bool:
        if not self.cookies_file.exists():
            return False
        import time
        file_age = time.time() - self.cookies_file.stat().st_mtime
        return file_age < (max_age_hours * 3600)

    async def check_session_health(self, fast_check: bool = False) -> bool:
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
        """Refresh session by running full auto-login via patchright."""
        logger.info("Refreshing FAP session via patchright...")

        if not self.feid or not self.password:
            logger.error("No FEID credentials configured")
            return False

        headless = headless or (os.getenv("HEADLESS", "false").lower() == "true")

        login = FAPAutoLogin(
            headless=headless,
            feid=self.feid,
            password=self.password,
        )

        try:
            success = await login.auto_login()
        except Exception as e:
            logger.error(f"Auto-login error: {e}", exc_info=True)
            return False

        if success:
            logger.info("Auto-login succeeded, cookies saved")
        else:
            logger.warning("Auto-login failed")

        return success

    async def get_valid_session(self) -> bool:
        if self.cookies_file.exists():
            if await self.check_session_health():
                logger.info("Session is valid")
                return True
            else:
                logger.warning("Session expired, refreshing...")

        return await self.refresh_session()


async def ensure_valid_session(feid: str = None, password: str = None) -> bool:
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
