@echo off
chcp 65001 >nul 2>&1
title Video Daily

echo ========================================
echo   Video Daily Launcher
echo ========================================
echo.

:: Start backend
echo [Backend] Starting FastAPI on port 8000...
start "VideoDaily-Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

:: Start frontend
echo [Frontend] Starting React dev server on port 5173...
start "VideoDaily-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   URLs:
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo ========================================
echo.
echo Press any key to exit this launcher...
pause >nul
