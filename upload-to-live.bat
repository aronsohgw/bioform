@echo off
REM Safely test, commit, and push BioForm changes to the live site.
REM Usage:  upload-to-live.bat "short message about what you changed"
REM Double-clicking also works — it will prompt for the message.

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "MSG=%~1"
if "%MSG%"=="" (
    set /p MSG="What did you change? (short sentence): "
)
if "%MSG%"=="" (
    echo ERROR: Commit message cannot be empty.
    pause
    exit /b 1
)

echo.
echo ===== 1/5  Showing what changed =====
git status --short
for /f %%i in ('git status --short ^| find /c /v ""') do set CHANGED=%%i
if "%CHANGED%"=="0" (
    echo.
    echo Nothing to upload - no files changed since last push.
    pause
    exit /b 0
)

echo.
echo ===== 2/5  Secret safety check =====
git status --short | findstr /i /c:".env" >nul
if not errorlevel 1 (
    echo.
    echo STOP: .env file is in your changes. I will NOT push - it would leak your API keys.
    echo Check your .gitignore before continuing.
    pause
    exit /b 1
)
echo OK - no secrets staged.

echo.
echo ===== 3/5  Running backend tests =====
pushd backend
call venv\Scripts\python.exe -m pytest -q
set PYTEST_EXIT=!errorlevel!
popd
if not "%PYTEST_EXIT%"=="0" (
    echo.
    echo STOP: Backend tests failed. Pushing this would likely break the live site.
    echo Fix the failing test first, then run this script again.
    pause
    exit /b 1
)
echo OK - backend tests pass.

echo.
echo ===== 4/5  Building frontend =====
pushd frontend
call npm run build
set VITE_EXIT=!errorlevel!
popd
if not "%VITE_EXIT%"=="0" (
    echo.
    echo STOP: Frontend build failed. Vercel would fail with the same error.
    echo Fix it first, then run this script again.
    pause
    exit /b 1
)
echo OK - frontend builds cleanly.

echo.
echo ===== 5/5  Committing and pushing =====
git add .
git commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo Commit failed. Nothing pushed.
    pause
    exit /b 1
)
git push
if errorlevel 1 (
    echo.
    echo Push failed. Check your internet connection or GitHub auth.
    pause
    exit /b 1
)

echo.
echo =================================================
echo  Pushed successfully!
echo  Frontend redeploys in ~2 min  (vercel.com/dashboard)
echo  Backend  redeploys in ~5-10 min (dashboard.render.com)
echo  First visitor may wait ~40s for Render cold start.
echo =================================================
pause
