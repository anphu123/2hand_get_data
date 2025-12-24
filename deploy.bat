@echo off
echo ============================================
echo   AIHUISHOU SCRAPER - LOCAL DEPLOY
echo ============================================
echo.

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not installed!
    echo Please install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

echo [1/4] Building Docker image...
docker build -t aihuishou-scraper .

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [2/4] Stopping old container...
docker stop aihuishou-scraper 2>nul
docker rm aihuishou-scraper 2>nul

echo.
echo [3/4] Starting new container...
docker run -d --name aihuishou-scraper -p 5000:5000 --restart unless-stopped aihuishou-scraper

if errorlevel 1 (
    echo [ERROR] Run failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Done!
echo ============================================
echo   DEPLOYED SUCCESSFULLY!
echo   Access: http://localhost:5000
echo   Access: http://192.168.1.49:5000
echo ============================================
echo.
echo Press any key to exit...
pause >nul
