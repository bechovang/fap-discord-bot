@echo off
REM FlareSolverr Quick Start Script for Windows
REM This script checks if Docker is available and starts FlareSolverr

echo ============================================================
echo FlareSolverr Quick Start
echo ============================================================
echo.

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Docker not found!
    echo.
    echo Please install Docker Desktop first:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    echo OR download FlareSolverr Windows binary:
    echo https://github.com/FlareSolverr/FlareSolverr/releases
    pause
    exit /b 1
)

echo [+] Docker found!
echo.

REM Check if FlareSolverr container exists
docker ps -a | findstr flaresolverr >nul 2>&1
if %errorlevel% equ 0 (
    echo [.] FlareSolverr container exists
    echo.

    REM Check if running
    docker ps | findstr flaresolverr >nul 2>&1
    if %errorlevel% equ 0 (
        echo [+] FlareSolverr is already running!
        echo [+] API available at: http://localhost:8191
        echo.
        echo Test connection:
        echo   python scraper/flaresolverr_auth.py test
    ) else (
        echo [.] Starting FlareSolverr container...
        docker start flaresolverr
        echo [+] FlareSolverr started!
        echo [+] API available at: http://localhost:8191
        echo.
        echo Test connection:
        echo   python scraper/flaresolverr_auth.py test
    )
) else (
    echo [.] Creating new FlareSolverr container...
    echo.

    docker run -d ^
      --name=flaresolverr ^
      -p 8191:8191 ^
      -e LOG_LEVEL=info ^
      --restart unless-stopped ^
      ghcr.io/flaresolverr/flaresolverr:latest

    if %errorlevel% equ 0 (
        echo [+] FlareSolverr started successfully!
        echo [+] API available at: http://localhost:8191
        echo.
        echo Waiting for FlareSolverr to be ready...
        timeout /t 5 /nobreak >nul
        echo.
        echo Test connection:
        echo   python scraper/flaresolverr_auth.py test
    ) else (
        echo [!] Failed to start FlareSolverr
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo Useful Commands:
echo ============================================================
echo.
echo View logs:
echo   docker logs -f flaresolverr
echo.
echo Restart:
echo   docker restart flaresolverr
echo.
echo Stop:
echo   docker stop flaresolverr
echo.
echo Remove and recreate:
echo   docker rm -f flaresolverr
echo   start_flaresolverr.bat
echo.

pause
