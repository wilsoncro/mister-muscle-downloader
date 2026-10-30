@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Mister Muscle - Objavi Update

echo ==========================================
echo        MISTER MUSCLE - OBJAVI UPDATE
echo ==========================================
echo.
if not exist "release.ps1" (
    echo GRESKA: release.ps1 nije pronadjen u ovoj mapi.
    goto :end
)
set "MM_VERSION="
set "MM_DESC="
set /p "MM_VERSION=Upisi verziju (npr. 5.1.7): "
if not defined MM_VERSION (
    echo GRESKA: Verzija ne moze biti prazna.
    goto :end
)
set /p "MM_DESC=Upisi update log: "
if not defined MM_DESC (
    echo GRESKA: Update log ne moze biti prazan.
    goto :end
)
echo.
echo Verzija: %MM_VERSION%
echo Opis: %MM_DESC%
choice /C DN /M "Zelis li buildati i objaviti update"
if errorlevel 2 goto :cancel

echo.
echo Pokrecem release.ps1...
rem Pass inputs via environment variables so spaces and quotes stay intact.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& { & '.\release.ps1' -Verzija $env:MM_VERSION -Opis $env:MM_DESC -Publish; if (-not $?) { exit 1 } }"
if errorlevel 1 (
    echo.
    echo GRESKA: Objavljivanje nije uspjelo. Pogledaj poruke iznad.
) else (
    echo.
    echo Release skripta je zavrsila bez prijavljene greske.
)
goto :end
:cancel
echo Objavljivanje otkazano.
:end
echo.
pause
endlocal
