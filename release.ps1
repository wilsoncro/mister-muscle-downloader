# ============================================================================
#  release.ps1
#  Automatizira CIJELI proces objavljivanja nove verzije - jednom komandom:
#    1) upise novi broj verzije na oba mjesta (skini_klip_gui.py i .iss)
#    2) pokrene build_exe.py (napravi .exe i Setup.exe)
#    3) git add + commit + push
#    4) napravi GitHub Release i na njega prikaci Setup.exe
#
#  PRIPREMA (jednom, prije prve upotrebe):
#    1) Instaliraj GitHub CLI (besplatno): https://cli.github.com/
#    2) U terminalu pokreni:  gh auth login   (jednom se prijavis, pamti te)
#    3) Svaki put kad zatreba novi build/release, u ovom folderu pokreni:
#         .\release.ps1 -Verzija "1.2" -Opis "Kratak opis izmjena"
#
#  Ako izostavis -Opis, skripta ce zatraziti da ga upises interaktivno.
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$Verzija,

    [string]$Opis = ""
)

$ErrorActionPreference = "Stop"
$Ovdje = $PSScriptRoot
Set-Location $Ovdje

function Korak($tekst) {
    Write-Host ""
    Write-Host "=== $tekst ===" -ForegroundColor Cyan
}

function Provjeri($naredba, $poruka) {
    if (-not (Get-Command $naredba -ErrorAction SilentlyContinue)) {
        Write-Host "GRESKA: '$naredba' nije pronadjen. $poruka" -ForegroundColor Red
        exit 1
    }
}

# ---- 0) provjera alata ----
Provjeri "git" "Instaliraj Git: https://git-scm.com/download/win"
Provjeri "python" "Instaliraj Python: https://python.org"
Provjeri "gh" "Instaliraj GitHub CLI: https://cli.github.com/"

$ghStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "GRESKA: nisi prijavljen u GitHub CLI. Pokreni jednom: gh auth login" -ForegroundColor Red
    exit 1
}

if (-not $Opis) {
    $Opis = Read-Host "Kratak opis ove verzije (za Release napomene)"
}

# ---- 1) upisi novi broj verzije na oba mjesta ----
Korak "Postavljam verziju na $Verzija"

$guiPath = Join-Path $Ovdje "skini_klip_gui.py"
$issPath = Join-Path $Ovdje "MisterMuscle_Setup.iss"

(Get-Content $guiPath -Raw) -replace 'APP_VERZIJA = "[^"]*"', "APP_VERZIJA = `"$Verzija`"" |
    Set-Content $guiPath -NoNewline -Encoding UTF8

(Get-Content $issPath -Raw) -replace '#define MyAppVersion "[^"]*"', "#define MyAppVersion `"$Verzija`"" |
    Set-Content $issPath -NoNewline -Encoding UTF8

Write-Host "Verzija postavljena u skini_klip_gui.py i MisterMuscle_Setup.iss" -ForegroundColor Green

# ---- 2) build (exe + setup) ----
Korak "Gradim .exe i instalater"
# MM_BEZ_PAUZE govori build_exe.py da PRESKOCI svoj "Pritisni Enter za izlaz"
# na kraju - inace bi ovaj skript tiho zapeo tu i cekao Enter koji nitko ne
# zna da treba pritisnuti (build_exe.py se inace pokrece samostalno, gdje ta
# pauza ima smisla - drzi cmd prozor otvoren da se ispis stigne procitati).
$env:MM_BEZ_PAUZE = "1"
python build_exe.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "GRESKA: build_exe.py nije uspio." -ForegroundColor Red
    exit 1
}

$setupExe = Join-Path $Ovdje "Output\MisterMuscle_Setup.exe"
if (-not (Test-Path $setupExe)) {
    Write-Host "GRESKA: $setupExe nije pronadjen nakon builda - je li Inno Setup instaliran?" -ForegroundColor Red
    exit 1
}

# ---- 3) git commit + push ----
Korak "Saljem izmjene na GitHub"
git add .
git commit -m "v$Verzija - $Opis"
git push

# ---- 4) GitHub Release s Setup.exe ----
Korak "Pravim GitHub Release v$Verzija"
gh release create "v$Verzija" $setupExe --title "v$Verzija" --notes "$Opis"

Write-Host ""
Write-Host "GOTOVO! v$Verzija je objavljena." -ForegroundColor Green
Write-Host "Pogledaj: gh repo view --web" -ForegroundColor Green
