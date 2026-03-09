"""
Session Validator - Check and auto-refresh FAP session
"""
import os
import logging
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from .auto_login_feid import FAPAutoLogin

logger = logging.getLogger(__name__)


class SessionValidator:
    """Validate and refresh FAP session automatically"""

    def __init__(self, feid: str = None, password: str = None, data_dir: str = "data"):
        self.feid = feid or os.environ.get("FAP_FEID")
        self.password = password or os.environ.get("FAP_PASSWORD")
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "fap_cookies.json"
        self.profile_dir = self.data_dir / "chrome_profile"

    def is_session_valid(self) -> bool:
        """Check if session files exist"""
        return self.cookies_file.exists() and self.profile_dir.exists()

    async def check_session_health(self) -> bool:
        """
        Check if current session is actually working

        Returns:
            True if session can access FAP, False otherwise
        """
        if not self.is_session_valid():
            return False

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=True
                )

                page = browser.pages[0] if browser.pages else await browser.new_page()

                # Try to access schedule page (lightweight check)
                await page.goto("https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx", timeout=30000)
                await asyncio.sleep(3)

                content = await page.content()

                # Check if we're logged in
                is_valid = 'ctl00_mainContent_drpSelectWeek' in content

                await browser.close()
                return is_valid

        except Exception as e:
            logger.error(f"Session health check error: {e}")
            return False

    async def refresh_session(self, headless: bool = False) -> bool:
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

        logger.info("🔄 Refreshing FAP session...")

        try:
            auth = FAPAutoLogin(headless=headless, feid=self.feid, password=self.password)
            success = await auth.auto_login()

            if success:
                logger.info("✅ Session refreshed successfully")
            else:
                logger.error("❌ Session refresh failed")

            return success

        except Exception as e:
            logger.error(f"❌ Session refresh error: {e}")
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
        return await self.refresh_session(headless=False)


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
            success = await validator.refresh_session(headless=False)
            print(f"Refresh success: {success}")

        elif action == "ensure":
            success = await validator.get_valid_session()
            print(f"Session valid: {success}")

    asyncio.run(main())
