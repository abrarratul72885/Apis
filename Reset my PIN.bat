@echo off
cd /d "%~dp0"
echo This changes your PIN only. Your records are not touched.
echo Close APIS first if it is running.
echo.
py -3 server\apis_server.py --reset-pin 2>nul || python server\apis_server.py --reset-pin
pause
