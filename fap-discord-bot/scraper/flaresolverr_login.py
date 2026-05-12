"""
Automated FeID Login using FlareSolverr for Cloudflare bypass + requests for login.

Flow:
1. FlareSolverr GET FAP → bypass Cloudflare → get cf_clearance cookie
2. Copy cf_clearance + FAP cookies into requests.Session()
3. requests.Session GET FAP → trigger FeID redirect → follow to FeID login
4. Parse CSRF token from FeID page
5. POST credentials with same session (cookies + CSRF match)
6. Follow redirects back to FAP authenticated
7. Save cookies for aiohttp
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, List, Dict
from urllib.parse import urlencode, urlparse, parse_qs, urljoin

import requests as http_requests

logger = logging.getLogger(__name__)

# FlareSolverr API client
import requests as _requests


class FlareSolverrLogin:
    FAP_LOGIN_URL = "https://fap.fpt.edu.vn/Default.aspx"
    FAP_SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
    FEID_LOGIN_URL = "https://feid.fpt.edu.vn/Account/Login"
    SESSION_ID = "fap_session"

    def __init__(self, flaresolverr_url: str = None, data_dir: str = "data"):
        self.flaresolverr_url = flaresolverr_url or os.getenv(
            "FLARESOLVERR_URL", "http://localhost:8191/v1"
        )
        self.session_id = self.SESSION_ID
        self.data_dir = Path(data_dir)
        self.cookies_file = self.data_dir / "fap_cookies.json"
        self.request_timeout = int(
            os.getenv("FLARESOLVERR_REQUEST_TIMEOUT_SECONDS", "240")
        )
        self.proxy_url = os.getenv("PROXY_URL")

    # ── FlareSolverr helpers ──────────────────────────────────────

    def _fs_request(self, payload: dict) -> dict:
        """Send request to FlareSolverr API."""
        resp = _requests.post(
            self.flaresolverr_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _ensure_fs_session(self) -> bool:
        """Create FlareSolverr browser session if not exists."""
        result = self._fs_request({"cmd": "sessions.list"})
        if self.session_id in result.get("sessions", []):
            return True
        result = self._fs_request(
            {"cmd": "sessions.create", "session": self.session_id}
        )
        return result.get("status") == "ok"

    def _get_cf_cookies(self) -> Optional[List[Dict]]:
        """Use FlareSolverr to bypass Cloudflare and get cf_clearance."""
        if not self._ensure_fs_session():
            logger.error("Failed to create FlareSolverr session")
            return None

        logger.info("FlareSolverr: fetching FAP to get cf_clearance...")
        result = self._fs_request({
            "cmd": "request.get",
            "url": self.FAP_LOGIN_URL,
            "session": self.session_id,
            "maxTimeout": 60000,
        })

        if result.get("status") != "ok":
            logger.error(f"FlareSolverr failed: {result.get('message')}")
            return None

        solution = result.get("solution", {})
        cookies = solution.get("cookies", [])
        cf = any(c.get("name") == "cf_clearance" for c in cookies)
        logger.info(f"Got {len(cookies)} cookies from FlareSolverr, cf_clearance={cf}")
        return cookies

    # ── requests.Session helpers ──────────────────────────────────

    def _build_http_session(self, fs_cookies: List[Dict]) -> http_requests.Session:
        """Build a requests.Session with FlareSolverr cookies + proxy."""
        session = http_requests.Session()

        # Set proxy if available
        if self.proxy_url:
            session.proxies = {"http": self.proxy_url, "https": self.proxy_url}

        # Copy cookies from FlareSolverr into the requests session
        for c in fs_cookies:
            session.cookies.set(
                c["name"],
                c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
            )

        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

        return session

    # ── HTML parsing helpers ───────────────────────────────────────

    def _is_authenticated(self, html: str) -> bool:
        return "ctl00_mainContent_drpSelectWeek" in html

    def _extract_aspnet_fields(self, html: str) -> dict:
        """Extract __VIEWSTATE, __EVENTVALIDATION etc. from ASP.NET page."""
        fields = {}
        for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
            m = re.search(rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]*)"', html)
            if not m:
                m = re.search(rf'<input[^>]+id="{re.escape(name)}"[^>]+value="([^"]*)"', html)
            if m:
                fields[name] = m.group(1)
        return fields

    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """Extract __RequestVerificationToken from FeID page."""
        m = re.search(
            r'<input[^>]+name="__RequestVerificationToken"[^>]+value="([^"]*)"', html
        )
        if m:
            return m.group(1)
        return None

    def _extract_feid_hidden_fields(self, html: str) -> dict:
        """Extract hidden fields from FeID form."""
        fields = {}
        for m in re.finditer(r'<input[^>]+type="hidden"[^>]*>', html, re.IGNORECASE):
            tag = m.group(0)
            name_m = re.search(r'name="([^"]*)"', tag)
            val_m = re.search(r'value="([^"]*)"', tag)
            if name_m:
                fields[name_m.group(1)] = val_m.group(1) if val_m else ""
        return fields

    # ── Main login flow ────────────────────────────────────────────

    def login(self, feid: str, password: str, campus: str = "4") -> bool:
        """
        Full automated login:
        1. FlareSolverr → cf_clearance cookie
        2. requests.Session → FAP → FeID redirect → parse CSRF → POST credentials
        3. Save authenticated cookies
        """
        logger.info("Starting auto-login: FlareSolverr bypass + HTTP login...")

        # Step 1: Get cf_clearance from FlareSolverr
        fs_cookies = self._get_cf_cookies()
        if not fs_cookies:
            logger.error("Failed to get Cloudflare cookies from FlareSolverr")
            return False

        # Check if already authenticated via FlareSolverr
        # (FlareSolverr page might already show schedule if session is valid)
        result = self._fs_request({
            "cmd": "request.get",
            "url": self.FAP_SCHEDULE_URL,
            "session": self.session_id,
            "maxTimeout": 60000,
        })
        sol = result.get("solution", {})
        if self._is_authenticated(sol.get("response", "")):
            logger.info("FlareSolverr session already authenticated!")
            return self._save_cookies_flare(sol.get("cookies", []))

        # Step 2: Build HTTP session with FlareSolverr cookies
        http = self._build_http_session(fs_cookies)
        logger.info(f"HTTP session ready with {len(http.cookies)} cookies")

        # Step 3: GET FAP login page → extract ASP.NET fields → POST to trigger FeID
        logger.info("Step 3: GET FAP login page...")
        resp = http.get(self.FAP_LOGIN_URL, timeout=30, allow_redirects=True)
        logger.info(f"FAP response: {resp.status_code}, URL: {resp.url}")

        if self._is_authenticated(resp.text):
            logger.info("Already authenticated on FAP!")
            return self._save_cookies_http(http)

        aspnet = self._extract_aspnet_fields(resp.text)
        if not aspnet.get("__VIEWSTATE"):
            logger.error("Could not parse ASP.NET fields from FAP page")
            logger.debug(f"First 500: {resp.text[:500]}")
            return False

        # Step 4: POST to FAP to trigger FeID login
        logger.info(f"Step 4: POST FAP to trigger FeID login (campus={campus})...")
        form_data = {
            "__EVENTTARGET": "ctl00$mainContent$btnloginFeId",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": aspnet.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": aspnet.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": aspnet.get("__EVENTVALIDATION", ""),
            "ctl00$mainContent$ddlCampus": campus,
            "ctl00$mainContent$message": "",
        }

        resp = http.post(
            self.FAP_LOGIN_URL,
            data=form_data,
            timeout=30,
            allow_redirects=True,
            headers={"Referer": self.FAP_LOGIN_URL, "Content-Type": "application/x-www-form-urlencoded"},
        )

        logger.info(f"After FeID trigger: {resp.status_code}, URL: {resp.url}")

        if self._is_authenticated(resp.text):
            logger.info("Authenticated after FeID trigger!")
            return self._save_cookies_http(http)

        if "feid.fpt.edu.vn" not in resp.url:
            logger.error(f"Not redirected to FeID. URL: {resp.url}")
            logger.debug(f"First 500: {resp.text[:500]}")
            return False

        # Step 5: Parse FeID login form → extract CSRF → POST credentials
        logger.info("Step 5: Parsing FeID login form...")
        csrf = self._extract_csrf_token(resp.text)
        feid_hidden = self._extract_feid_hidden_fields(resp.text)

        if not csrf:
            logger.error("Could not find CSRF token on FeID page")
            logger.debug(f"First 1000: {resp.text[:1000]}")
            return False

        logger.info(f"FeID CSRF token found, hidden fields: {list(feid_hidden.keys())}")

        # Build FeID login form data
        feid_form = dict(feid_hidden)  # includes ReturnUrl, ProjectId, etc.
        feid_form["__RequestVerificationToken"] = csrf
        feid_form["Username"] = feid
        feid_form["Password"] = password

        # POST to the current FeID URL (includes ReturnUrl in query string)
        feid_post_url = resp.url

        logger.info(f"POSTing credentials to {feid_post_url[:80]}...")
        resp = http.post(
            feid_post_url,
            data=feid_form,
            timeout=30,
            allow_redirects=True,
            headers={"Referer": feid_post_url, "Content-Type": "application/x-www-form-urlencoded"},
        )

        logger.info(f"After FeID login: {resp.status_code}, URL: {resp.url}")

        if self._is_authenticated(resp.text):
            logger.info("Login successful! Schedule page accessible.")
            return self._save_cookies_http(http)

        # Might need one more redirect
        if "fap.fpt.edu.vn" in resp.url:
            logger.info("Redirected to FAP, checking schedule page...")
            resp = http.get(self.FAP_SCHEDULE_URL, timeout=30)
            if self._is_authenticated(resp.text):
                logger.info("Login successful!")
                return self._save_cookies_http(http)

        # Check if still on FeID (wrong credentials)
        if "feid.fpt.edu.vn" in resp.url:
            # Look for error messages
            errors = re.findall(r'class="[^"]*field-validation-error[^"]*"[^>]*>([^<]+)', resp.text)
            errors += re.findall(r'class="[^"]*validation-summary-errors[^"]*"[^>]*>\s*<[^>]*>\s*([^<]+)', resp.text)
            if errors:
                logger.error(f"FeID login error: {errors}")
            else:
                logger.error(f"FeID login failed (no error message). URL: {resp.url}")
        else:
            logger.error(f"Login failed. Final URL: {resp.url}")

        logger.debug(f"Final page (first 500): {resp.text[:500]}")
        self._save_cookies_http(http)
        return False

    # ── Cookie saving ──────────────────────────────────────────────

    def _save_cookies_flare(self, cookies: List[Dict]) -> bool:
        """Save FlareSolverr-format cookies."""
        if not cookies:
            return False
        self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cookies_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
        fap = [c for c in cookies if "fpt.edu.vn" in c.get("domain", "")]
        logger.info(f"Saved {len(cookies)} cookies ({len(fap)} FAP)")
        self._log_important(cookies)
        return True

    def _save_cookies_http(self, session: http_requests.Session) -> bool:
        """Convert requests.Session cookies to FlareSolverr format and save."""
        cookies = []
        for c in session.cookies:
            cookies.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "secure": c.secure,
            })

        if not cookies:
            logger.warning("No cookies to save")
            return False

        self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cookies_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        fap = [c for c in cookies if "fpt.edu.vn" in c.get("domain", "")]
        logger.info(f"Saved {len(cookies)} cookies ({len(fap)} FAP)")
        self._log_important(cookies)
        return True

    def _log_important(self, cookies: list):
        for name in ["cf_clearance", "ASP.NET_SessionId", "__AntiXsrfToken"]:
            for c in cookies:
                if c.get("name") == name:
                    v = c.get("value", "")
                    logger.info(f"  {name}: {v[:30]}{'...' if len(v) > 30 else ''}")

    def check_and_refresh(self, feid: str = None, password: str = None, campus: str = "4") -> bool:
        """Check session, attempt auto-login if not authenticated."""
        feid = feid or os.getenv("FAP_USERNAME") or os.getenv("FAP_FEID")
        password = password or os.getenv("FAP_PASSWORD")

        if not feid or not password:
            logger.error("No FEID credentials for auto-login")
            return False

        return self.login(feid=feid, password=password, campus=campus)
