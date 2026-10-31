@echo off
setlocal
cd /d "%~dp0"
if not exist "release.ps1" (
  echo ERROR: release.ps1 not found next to objavi.bat
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1" -Publish %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo.
  echo Publishing failed with code %RESULT%.
  pause
)
exit /b %RESULT%
