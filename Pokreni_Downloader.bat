@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Mister Muscle Downloader
echo Pokrecem aplikaciju...
python skini_klip_gui.py
if errorlevel 1 (
    echo.
    echo Dogodila se greska. Instaliraj potrebne pakete:
    echo     pip install pywebview psutil pywin32
    echo.
    echo ^(pywin32 je potreban da se player za oznacavanje isjecka UGRADI u glavni
    echo  prozor - bez njega otvara se u zasebnom prozoru. yt-dlp i ffmpeg se skidaju
    echo  automatski pri prvom pokretanju - za njih NE treba nikakav pip install^)
    pause
)
