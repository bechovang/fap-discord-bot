"""
Lightweight HTTP server to serve the daily report HTML.
Runs on the same asyncio event loop as the Discord bot.
"""
import logging
import os
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

REPORT_FILE = Path("data/daily_report.html")


async def handle_index(_request: web.Request) -> web.Response:
    """Serve the daily report HTML file."""
    if not REPORT_FILE.exists():
        return web.Response(
            text="<html><body><h2>Report not ready yet</h2><p>Waiting for the first daily check.</p></body></html>",
            content_type="text/html",
        )
    return web.Response(text=REPORT_FILE.read_text(encoding="utf-8"), content_type="text/html")


async def start_web_server(port: int = None) -> web.AppRunner:
    """Start the HTTP server and return the runner (caller keeps reference)."""
    port = port or int(os.environ.get("WEB_PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", handle_index)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server listening on port {port}")
    return runner
