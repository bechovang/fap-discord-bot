"""
Automated FeID Login via FlareSolverr API

Uses FlareSolverr's request.get / request.post to automate the full login flow:
1. GET FAP Default.aspx (Cloudflare bypassed by FlareSolverr)
2. Extract ASP.NET hidden fields (__VIEWSTATE, __EVENTVALIDATION, etc.)
3. POST to trigger FeID login (__doPostBack for btnloginFeId)
4. Extract FeID login form fields
5. POST FeID credentials
6. Follow redirects back to FAP authenticated
7. Save cookies for aiohttp
"""
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional, List, Dict
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


class FlareSolverrLogin:
    FAP_LOGIN_URL = "https://fap.fpt.edu.vn/Default.aspx"
    FAP_SCHEDULE_URL = "https://fap.fpt.edu.vn/Report/ScheduleOfWeek.aspx"
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

    def _request(self, payload: dict) -> dict:
        """Send request to FlareSolverr API."""
        resp = requests.post(
            self.flaresolverr_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _ensure_session(self) -> bool:
        """Create FlareSolverr browser session if not exists."""
        result = self._request({"cmd": "sessions.list"})
        sessions = result.get("sessions", [])
        if self.session_id in sessions:
            return True
        result = self._request(
            {"cmd": "sessions.create", "session": self.session_id}
        )
        return result.get("status") == "ok"

    def _extract_hidden_fields(self, html: str) -> dict:
        """Extract ASP.NET hidden fields from HTML."""
        fields = {}
        for name in [
            "__VIEWSTATE",
            "__VIEWSTATEGENERATOR",
            "__EVENTVALIDATION",
            "__EVENTTARGET",
            "__EVENTARGUMENT",
        ]:
            match = re.search(
                rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]*)"', html
            )
            if match:
                fields[name] = match.group(1)
            else:
                match2 = re.search(
                    rf'<input[^>]+id="{re.escape(name)}"[^>]+value="([^"]*)"', html
                )
                if match2:
                    fields[name] = match2.group(1)
        return fields

    def _is_authenticated(self, html: str) -> bool:
        """Check if the page shows authenticated content (schedule page)."""
        return "ctl00_mainContent_drpSelectWeek" in html

    def _has_feid_button(self, html: str) -> bool:
        """Check if the FeID login button is present."""
        return "btnloginFeId" in html

    def login(self, feid: str, password: str, campus: str = "4") -> bool:
        """
        Full automated login flow via FlareSolverr.

        Args:
            feid: FEID username/email
            password: FEID password
            campus: Campus ID (3=HL, 4=HCM, 5=DN, 6=CT, 7=QN)

        Returns:
            True if login succeeded and cookies saved
        """
        logger.info("Starting automated FeID login via FlareSolverr...")

        if not self._ensure_session():
            logger.error("Failed to create FlareSolverr session")
            return False

        # Step 1: Load FAP login page
        logger.info("Step 1: Loading FAP login page...")
        result = self._request({
            "cmd": "request.get",
            "url": self.FAP_LOGIN_URL,
            "session": self.session_id,
            "maxTimeout": 60000,
        })

        if result.get("status") != "ok":
            logger.error(f"Failed to load FAP: {result.get('message')}")
            return False

        solution = result.get("solution", {})
        html = solution.get("response", "")
        url = solution.get("url", "")

        logger.info(f"FAP page loaded, URL: {url}")

        if self._is_authenticated(html):
            logger.info("Already authenticated! Saving cookies...")
            return self._save_cookies(solution.get("cookies", []))

        if not self._has_feid_button(html):
            logger.error("FeID login button not found on page")
            logger.debug(f"Page content (first 500): {html[:500]}")
            return False

        # Step 2: Select campus and trigger FeID login via POST
        logger.info(f"Step 2: Selecting campus {campus} and triggering FeID login...")
        hidden = self._extract_hidden_fields(html)
        logger.info(f"Extracted {len(hidden)} hidden fields from FAP page")

        form_data = {
            "__EVENTTARGET": "ctl00$mainContent$btnloginFeId",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
            "__VIEWSTATEGENERATOR": hidden.get("__VIEWSTATEGENERATOR", ""),
            "__EVENTVALIDATION": hidden.get("__EVENTVALIDATION", ""),
            "ctl00$mainContent$ddlCampus": campus,
            "ctl00$mainContent$message": "",
        }

        result = self._request({
            "cmd": "request.post",
            "url": self.FAP_LOGIN_URL,
            "session": self.session_id,
            "postData": urlencode(form_data),
            "maxTimeout": 60000,
        })

        if result.get("status") != "ok":
            logger.error(f"FeID trigger POST failed: {result.get('message')}")
            return False

        solution = result.get("solution", {})
        html = solution.get("response", "")
        url = solution.get("url", "")

        logger.info(f"After FeID trigger, URL: {url}")

        # Check if we somehow got authenticated already
        if self._is_authenticated(html):
            logger.info("Authenticated after FeID trigger!")
            return self._save_cookies(solution.get("cookies", []))

        # Step 3: Handle FeID login page
        if "feid.fpt.edu.vn" not in url and "identity" not in url.lower():
            # Maybe still on FAP page, try to navigate
            logger.warning(f"Not on FeID page, URL: {url}")

            # Check if there's a redirect we need to follow
            if "Login" in html and "Password" in html:
                logger.info("Found login form on current page, attempting fill...")
            else:
                logger.error(f"Unexpected page after FeID trigger. URL: {url}")
                logger.debug(f"Page content (first 1000): {html[:1000]}")
                return False

        # Step 3: Extract FeID form fields and submit credentials
        logger.info("Step 3: Submitting FeID credentials...")

        # Try to find username/password inputs on FeID page
        feid_fields = self._extract_feid_form_fields(html)

        if feid_fields:
            logger.info(f"Found FeID form fields: {list(feid_fields.keys())}")

            # Build form data with FeID credentials
            feid_form = {}
            feid_form.update(feid_fields.get("hidden", {}))
            feid_form[feid_fields["username_field"]] = feid
            feid_form[feid_fields["password_field"]] = password

            feid_action_url = feid_fields.get("action_url", url)

            logger.info(f"POSTing credentials to {feid_action_url}")

            result = self._request({
                "cmd": "request.post",
                "url": feid_action_url,
                "session": self.session_id,
                "postData": urlencode(feid_form),
                "maxTimeout": 120000,
            })

            if result.get("status") != "ok":
                logger.error(f"FeID login POST failed: {result.get('message')}")
                return False

            solution = result.get("solution", {})
            html = solution.get("response", "")
            url = solution.get("url", "")
            logger.info(f"After FeID login, URL: {url}")
        else:
            logger.warning("Could not parse FeID form fields from page")
            logger.debug(f"FeID page content (first 2000): {html[:2000]}")
            return False

        # Step 4: Check if login succeeded
        # The FeID login should redirect back to FAP
        # We may need to follow additional redirects

        if self._is_authenticated(html):
            logger.info("Login successful! Schedule page accessible.")
            return self._save_cookies(solution.get("cookies", []))

        # If not on schedule page yet, try navigating there
        if "fap.fpt.edu.vn" in url:
            logger.info("Redirected back to FAP, checking schedule page...")
            result = self._request({
                "cmd": "request.get",
                "url": self.FAP_SCHEDULE_URL,
                "session": self.session_id,
                "maxTimeout": 60000,
            })

            solution = result.get("solution", {})
            html = solution.get("response", "")

            if self._is_authenticated(html):
                logger.info("Login successful! Schedule page accessible.")
                return self._save_cookies(solution.get("cookies", []))

        logger.error(f"Login may have failed. Final URL: {url}")
        logger.debug(f"Final page content (first 500): {html[:500]}")

        # Save cookies anyway - might be partially authenticated
        self._save_cookies(solution.get("cookies", []))
        return False

    def _extract_feid_form_fields(self, html: str) -> Optional[dict]:
        """Extract form fields from the FeID login page."""
        # Find the form
        form_match = re.search(
            r'<form[^>]*action="([^"]*)"[^>]*>(.*?)</form>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if not form_match:
            # Try finding any form
            form_match = re.search(
                r'<form[^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE
            )

        form_html = form_match.group(0) if form_match else html
        action_url = form_match.group(1) if form_match else ""

        # Find username input
        username_field = None
        for selector in [
            r'<input[^>]*name="Username"[^>]*>',
            r'<input[^>]*name="username"[^>]*>',
            r'<input[^>]*name="email"[^>]*>',
            r'<input[^>]*id="Input_Email"[^>]*>',
            r'<input[^>]*id="Email"[^>]*>',
            r'<input[^>]*type="email"[^>]*>',
        ]:
            match = re.search(selector, form_html, re.IGNORECASE)
            if match:
                name_match = re.search(r'name="([^"]*)"', match.group(0))
                if name_match:
                    username_field = name_match.group(1)
                    break

        # Find password input
        password_field = None
        for selector in [
            r'<input[^>]*name="Password"[^>]*>',
            r'<input[^>]*name="password"[^>]*>',
            r'<input[^>]*id="Input_Password"[^>]*>',
            r'<input[^>]*id="Password"[^>]*>',
            r'<input[^>]*type="password"[^>]*>',
        ]:
            match = re.search(selector, form_html, re.IGNORECASE)
            if match:
                name_match = re.search(r'name="([^"]*)"', match.group(0))
                if name_match:
                    password_field = name_match.group(1)
                    break

        if not username_field or not password_field:
            logger.warning(
                f"Could not find login fields: username={username_field}, password={password_field}"
            )
            return None

        # Extract all hidden inputs from the form
        hidden_fields = {}
        for match in re.finditer(
            r'<input[^>]*type="hidden"[^>]*>', form_html, re.IGNORECASE
        ):
            input_tag = match.group(0)
            name_match = re.search(r'name="([^"]*)"', input_tag)
            value_match = re.search(r'value="([^"]*)"', input_tag)
            if name_match:
                hidden_fields[name_match.group(1)] = (
                    value_match.group(1) if value_match else ""
                )

        return {
            "username_field": username_field,
            "password_field": password_field,
            "hidden": hidden_fields,
            "action_url": action_url,
        }

    def _save_cookies(self, cookies: List[Dict]) -> bool:
        """Save cookies to file for aiohttp to use."""
        if not cookies:
            logger.warning("No cookies to save")
            return False

        self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cookies_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        fap_cookies = [
            c for c in cookies if "fpt.edu.vn" in c.get("domain", "")
        ]
        logger.info(
            f"Saved {len(cookies)} cookies ({len(fap_cookies)} FAP) to {self.cookies_file}"
        )

        important = ["cf_clearance", "ASP.NET_SessionId", "__AntiXsrfToken"]
        for cookie in cookies:
            if cookie.get("name") in important:
                val = cookie.get("value", "")
                preview = val[:30] + "..." if len(val) > 30 else val
                logger.info(f"  {cookie['name']}: {preview}")

        return True

    def check_and_refresh(self, feid: str = None, password: str = None, campus: str = "4") -> bool:
        """
        Check if session is authenticated. If not, attempt auto-login.

        Returns:
            True if session is authenticated (either already or after login)
        """
        if not self._ensure_session():
            logger.error("Failed to create FlareSolverr session")
            return False

        # Try fetching schedule page first
        result = self._request({
            "cmd": "request.get",
            "url": self.FAP_SCHEDULE_URL,
            "session": self.session_id,
            "maxTimeout": 60000,
        })

        solution = result.get("solution", {})
        html = solution.get("response", "")
        cookies = solution.get("cookies", [])

        if self._is_authenticated(html):
            logger.info("Session is authenticated, saving cookies")
            return self._save_cookies(cookies)

        logger.info("Session not authenticated, attempting auto-login...")

        # Save whatever cookies we have (Cloudflare cookies)
        self._save_cookies(cookies)

        if not feid or not password:
            feid = os.getenv("FAP_USERNAME") or os.getenv("FAP_FEID")
            password = os.getenv("FAP_PASSWORD")

        if not feid or not password:
            logger.error("No FEID credentials available for auto-login")
            return False

        return self.login(feid=feid, password=password, campus=campus)
