"""
Turnstile Solver Module
Integrated from Turnstile-Solver for Cloudflare bypass
"""
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
from patchright.async_api import async_playwright

logger = logging.getLogger(__name__)


@dataclass
class TurnstileResult:
    """Result of Turnstile solve attempt"""
    token: Optional[str]
    elapsed_time: float
    success: bool
    reason: Optional[str] = None


class TurnstileSolver:
    """
    Cloudflare Turnstile Solver using PatchRight
    Handles detection and solving of Turnstile challenges
    """

    def __init__(self, headless: bool = True, user_agent: Optional[str] = None):
        self.headless = headless
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    async def solve_turnstile(self, page, timeout: int = 30000) -> Optional[str]:
        """
        Wait for and extract Turnstile token from page

        Args:
            page: PatchRight Page object
            timeout: Maximum time to wait in milliseconds

        Returns:
            Turnstile token string or None if failed
        """
        try:
            # Wait for Turnstile iframe to appear
            iframe = page.wait_for_selector('iframe[src*="challenges.cloudflare.com"]', timeout=timeout)

            if not iframe:
                logger.warning("No Turnstile iframe found - may not be challenged")
                return None

            # Wait for the token to be generated
            await page.wait_for_selector('input[name="cf-turnstile-response"]', timeout=timeout)

            # Extract the token
            token_input = await page.query_selector('input[name="cf-turnstile-response"]')
            if token_input:
                token = await token_input.get_attribute('value')
                if token and len(token) > 10:
                    logger.info(f"Turnstile solved: {token[:20]}...")
                    return token

        except Exception as e:
            logger.warning(f"Turnstile detection/solve failed: {e}")

        return None

    async def solve_with_browser(self, url: str, sitekey: Optional[str] = None) -> TurnstileResult:
        """
        Solve Turnstile by navigating to URL with browser

        Args:
            url: URL containing Turnstile
            sitekey: Optional sitekey for verification

        Returns:
            TurnstileResult with token or error
        """
        import time
        start_time = time.time()

        try:
            playwright = await async_playwright().start()
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                f'--user-agent={self.user_agent}'
            ]

            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.user_agent
            )

            page = await context.new_page()
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Try to solve Turnstile
            token = await self.solve_turnstile(page)

            await browser.close()
            await playwright.stop()

            elapsed = time.time() - start_time

            if token:
                return TurnstileResult(token=token, elapsed_time=elapsed, success=True)
            else:
                return TurnstileResult(
                    token=None,
                    elapsed_time=elapsed,
                    success=False,
                    reason="Could not extract Turnstile token"
                )

        except Exception as e:
            elapsed = time.time() - start_time
            return TurnstileResult(
                token=None,
                elapsed_time=elapsed,
                success=False,
                reason=str(e)
            )


async def get_turnstile_token(url: str, headless: bool = True, user_agent: str = None) -> Optional[str]:
    """
    Convenience function to get Turnstile token

    Args:
        url: URL to solve Turnstile on
        headless: Run browser in headless mode
        user_agent: Custom user agent string

    Returns:
        Turnstile token or None
    """
    solver = TurnstileSolver(headless=headless, user_agent=user_agent)
    result = await solver.solve_with_browser(url)
    return result.token if result.success else None
