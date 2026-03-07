"""
Keep-Alive Heartbeat Manager
Maintains FAP session by periodic navigation
"""
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta
from ..scraper.auth import FAPAuth

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    Manages periodic heartbeat requests to keep FAP session alive
    """

    # Default heartbeat interval (10 minutes)
    DEFAULT_INTERVAL = timedelta(minutes=10)

    def __init__(
        self,
        auth: FAPAuth,
        interval: timedelta = None,
        on_heartbeat: Optional[Callable] = None
    ):
        """
        Initialize heartbeat manager

        Args:
            auth: FAPAuth instance
            interval: Time between heartbeats
            on_heartbeat: Optional callback after each heartbeat
        """
        self.auth = auth
        self.interval = interval or self.DEFAULT_INTERVAL
        self.on_heartbeat = on_heartbeat
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_heartbeat: Optional[datetime] = None
        self._success_count = 0
        self._failure_count = 0

    async def _heartbeat_loop(self):
        """Main heartbeat loop"""
        while self._running:
            try:
                await asyncio.sleep(self.interval.total_seconds())

                if not self._running:
                    break

                await self._do_heartbeat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self._failure_count += 1

    async def _do_heartbeat(self):
        """Perform a single heartbeat"""
        try:
            # Perform a lightweight navigation
            if self.auth._page and self.auth._is_logged_in:
                await self.auth._page.goto(
                    self.auth.SCHEDULE_URL,
                    wait_until='domcontentloaded',
                    timeout=15000
                )
                self._success_count += 1
                logger.debug(f"Heartbeat successful ({self._success_count} total)")
            else:
                logger.warning("Skipping heartbeat - not logged in")

            self._last_heartbeat = datetime.now()

            # Call callback if provided
            if self.on_heartbeat:
                await self.on_heartbeat(self._last_heartbeat)

        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            self._failure_count += 1

    async def start(self):
        """Start the heartbeat loop"""
        if self._running:
            logger.warning("Heartbeat already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat started (interval: {self.interval.total_seconds()}s)")

    async def stop(self):
        """Stop the heartbeat loop"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Heartbeat stopped")

    def get_stats(self) -> dict:
        """Get heartbeat statistics"""
        return {
            'running': self._running,
            'last_heartbeat': self._last_heartbeat,
            'success_count': self._success_count,
            'failure_count': self._failure_count,
            'interval_seconds': self.interval.total_seconds()
        }

    @property
    def is_running(self) -> bool:
        """Check if heartbeat is running"""
        return self._running
