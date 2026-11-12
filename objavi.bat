@echo off
setlocal
cd /d "%~dp0"
if not exist "release.ps1" (
  echo ERROR: release.ps1 not found next to objavi.bat
  pause
  exit /b 1
)
rem Verify v5.3.9 source before any build, git commit, or GitHub upload.
if exist "test_restricted_media_539.py" (
  set "PATH=%~dp0tools;%PATH%"
  echo Checking v5.3.9 Inspect, Preview and media compatibility...
  py -3 "test_full_waveform_and_cuts_535.py"
  if errorlevel 1 (
    echo.
    echo ERROR: v5.3.9 checks failed. Nothing published.
    pause
    exit /b 1
  )
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1" -Publish %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo.
  echo Publishing failed with code %RESULT%.
  pause
)
exit /b %RESULT%
