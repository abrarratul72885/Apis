@echo off
cd /d "%~dp0"
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\APIS.lnk"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LINK%'); $s.TargetPath='wscript.exe'; $s.Arguments='\"%~dp0Start APIS in the background.vbs\"'; $s.WorkingDirectory='%~dp0'; $s.Save()"
if exist "%LINK%" (
  echo Done. APIS will now start by itself when you sign in to Windows.
  echo Open it any time at http://localhost:8501
) else (
  echo Something went wrong. Please start APIS with "Start APIS" instead.
)
pause
