@echo off
title WQ-Brain Launcher

:menu
cls
echo =======================================
echo          WQ-Brain Launcher
echo =======================================
echo 1. Start Web UI (server.py)
echo 2. Run Simulation Directly (main.py)
echo 3. Exit
echo =======================================
choice /c 123 /n /m "Please select an option (1-3): "

if errorlevel 3 goto end
if errorlevel 2 goto main
if errorlevel 1 goto server

goto menu

:server
echo.
echo Starting WQ-Brain Web UI...
echo The browser will open automatically...
timeout /t 2 >nul
start http://127.0.0.1:8000
python server.py
pause
goto menu

:main
echo.
echo Running main.py directly...
python -u main.py
pause
goto menu

:end
exit
