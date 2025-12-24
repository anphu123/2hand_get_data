@echo off
echo ============================================
echo   DEPLOY TO GOOGLE CLOUD RUN
echo ============================================
echo.

REM Check if gcloud is installed
gcloud --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Google Cloud SDK not installed!
    echo Download from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Get project ID
for /f "tokens=*" %%a in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%a
if "%PROJECT_ID%"=="" (
    echo [ERROR] No project set. Run: gcloud init
    pause
    exit /b 1
)

echo Project: %PROJECT_ID%
echo.

echo [1/4] Building Docker image...
call gcloud builds submit --tag gcr.io/%PROJECT_ID%/aihuishou-scraper

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [2/4] Deploying to Cloud Run...
call gcloud run deploy aihuishou-scraper ^
    --image gcr.io/%PROJECT_ID%/aihuishou-scraper ^
    --platform managed ^
    --region asia-southeast1 ^
    --allow-unauthenticated ^
    --memory 2Gi ^
    --cpu 2 ^
    --timeout 300 ^
    --port 5000

if errorlevel 1 (
    echo [ERROR] Deploy failed!
    pause
    exit /b 1
)

echo.
echo [3/4] Getting URL...
for /f "tokens=*" %%a in ('gcloud run services describe aihuishou-scraper --region asia-southeast1 --format "value(status.url)"') do set SERVICE_URL=%%a

echo.
echo ============================================
echo   DEPLOYED SUCCESSFULLY!
echo   URL: %SERVICE_URL%
echo ============================================
echo.
pause
