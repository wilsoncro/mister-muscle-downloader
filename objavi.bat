@echo off
REM ============================================================================
REM  objavi.bat
REM  Wrapper oko release.ps1 koji RIJESAVA "not digitally signed" bugicu
REM  jednom zauvijek - svaki put kad se release.ps1 ponovno skine (nova verzija
REM  s chata), Windows ga automatski oznaci kao "sa interneta" (Mark of the
REM  Web) i blokira. Ovaj .bat sam otkljuca file i pokrene ga s Bypass
REM  policy - vise NIKAD nece trebati rucno "Unblock-File".
REM
REM  Koristenje (identicno kao release.ps1, samo umjesto ".\release.ps1" pises
REM  ".\objavi.bat"):
REM      .\objavi.bat -Verzija "1.3" -Opis "Kratak opis izmjena"
REM ============================================================================

cd /d "%~dp0"

powershell -NoProfile -Command "Unblock-File -Path '.\release.ps1'" >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -File ".\release.ps1" %*
