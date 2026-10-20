@echo off
title APIS
cd /d "%~dp0"
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto nopython
echo Starting APIS. Keep this window open while you use the app.
echo (Close this window to stop APIS.)
echo.
%PY% server\apis_server.py
echo.
echo APIS has stopped.
pause
goto :eof
:nopython
echo Python is not installed yet.
echo.
echo 1. A web page will open. Download Python and run the installer.
echo 2. IMPORTANT: tick "Add python.exe to PATH" at the bottom of the first screen.
echo 3. Then double-click "Start APIS" again.
start https://www.python.org/downloads/
pause
