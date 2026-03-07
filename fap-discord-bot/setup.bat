@echo off
REM Quick setup script for persistent Chromium profile
echo ============================================================
echo FAP Persistent Profile Setup
echo ============================================================
echo.
echo 1. A Chrome window will open
echo 2. Login with your Google account
echo 3. Wait for the schedule page to load
echo 4. Come back here and press a key
echo.
pause

cd /d "%~dp0"
python scraper\persistent_chromium.py setup

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo Setup Complete!
    echo ============================================================
    echo Now test: python scraper\persistent_chromium.py test
    echo.
)
