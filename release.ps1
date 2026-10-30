param(
    [Parameter(Mandatory=$true)][string]$Verzija,
    [string]$Opis = '',
    [switch]$Publish
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$repo = 'wilsoncro/mister-muscle-downloader'
if ($Verzija -notmatch '^\d+\.\d+(\.\d+)?$') { throw 'Verzija mora biti npr. 5.0 ili 5.0.1.' }
foreach ($command in @('py','git','gh')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Nedostaje alat: $command" }
}

# Git repo must be checked BEFORE building. Never create an unrelated history.
$gitRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $gitRoot) {
    throw "Ova mapa nije Git repozitorij: $PSScriptRoot`nKloniraj postojeći repo: git clone https://github.com/$repo.git`nZatim prebaci izvorne datoteke u kloniranu mapu (bez dist/build/Output/tools) i pokreni skriptu tamo."
}
$origin = (& git remote get-url origin 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $origin) { throw 'Git remote origin nije postavljen.' }
if ($origin -notmatch '(^|[:/])wilsoncro/mister-muscle-downloader(\.git)?$') {
    throw "Git origin nije očekivani repozitorij: $origin"
}

$source = Join-Path $PSScriptRoot 'mister_muscle_qt.py'
$iss = Join-Path $PSScriptRoot 'MisterMuscle_Setup.iss'
$notesFile = Join-Path $PSScriptRoot 'CHANGELOG_v5.0.md'
foreach ($required in @($source,$iss,$notesFile,(Join-Path $PSScriptRoot 'build_qt.py'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Nedostaje: $required" }
}
$code = [IO.File]::ReadAllText($source)
if ($code -notmatch "APP_VERSION\s*=\s*'[^']*'") { throw 'APP_VERSION nije pronađen u mister_muscle_qt.py' }
$code = [regex]::Replace($code,"APP_VERSION\s*=\s*'[^']*'","APP_VERSION = '$Verzija'",1)
[IO.File]::WriteAllText($source,$code,(New-Object System.Text.UTF8Encoding($false)))
$setupText = [IO.File]::ReadAllText($iss)
if ($setupText -notmatch '#define MyAppVersion "[^"]*"') { throw 'MyAppVersion nije pronađen u .iss datoteci' }
$setupText = [regex]::Replace($setupText,'#define MyAppVersion "[^"]*"',"#define MyAppVersion `"$Verzija`"",1)
[IO.File]::WriteAllText($iss,$setupText,(New-Object System.Text.UTF8Encoding($false)))

Write-Host "Building Mister Muscle v$Verzija..." -ForegroundColor Cyan
& py -3 (Join-Path $PSScriptRoot 'build_qt.py')
if ($LASTEXITCODE -ne 0) { throw 'Build failed. Nothing published.' }
$setup = Join-Path $PSScriptRoot 'Output\MisterMuscle_Setup.exe'
if (-not (Test-Path -LiteralPath $setup)) { throw "Installer nije pronađen: $setup" }
Write-Host "Installer ready: $setup" -ForegroundColor Green
if (-not $Publish) {
    Write-Host 'Test build complete; no GitHub changes. Add -Publish to publish.' -ForegroundColor Yellow
    exit 0
}

& gh auth status 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Prijavi se: gh auth login' }
$releaseJson = & gh release list --repo $repo --limit 100 --json tagName
if ($LASTEXITCODE -ne 0) { throw 'GitHub release check failed.' }
$existing = @($releaseJson | ConvertFrom-Json)
if ($existing | Where-Object { $_.tagName -eq "v$Verzija" }) {
    throw "Release v$Verzija već postoji. Za novu objavu koristi novu verziju."
}

# Only stage source files. Ignore generated files and dependencies.
$paths = @('mister_muscle_qt.py','mister_muscle_original_player.py','build_qt.py',
    'release.ps1','objavi.bat','MisterMuscle_Setup.iss','README_RELEASE.txt',
    'CHANGELOG_v5.0.md','assets','ikona.ico')
foreach ($path in $paths) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $path))) { continue }
    # git warnings on stderr must not become terminating PowerShell errors.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & git -c core.quotepath=false add -- $path 2>$null | Out-Null; $exitCode = $LASTEXITCODE }
    finally { $ErrorActionPreference = $previous }
    if ($exitCode -ne 0) { Write-Warning "Preskačem Git staging: $path (exit $exitCode)" }
}
$staged = @(& git diff --cached --name-only)
if ($LASTEXITCODE -ne 0) { throw 'git diff --cached failed.' }
# Prevent accidentally publishing dependencies that were already staged earlier.
$bad = @($staged | Where-Object { $_ -match '^(dist|build|Output|tools|node_modules|bgutil-ytdlp-pot-provider)/' })
if ($bad.Count -gt 0) {
    throw "U Git stagingu su generirane datoteke ($($bad.Count)). Očisti staging naredbom 'git restore --staged .' pa pokušaj ponovno."
}
if ($staged.Count -gt 0) {
    if (-not $Opis) { $Opis = "Mister Muscle Downloader v$Verzija" }
    & git commit -m "v$Verzija - $Opis"
    if ($LASTEXITCODE -ne 0) { throw 'git commit failed.' }
    & git push
    if ($LASTEXITCODE -ne 0) { throw 'git push failed. Release not created.' }
} else {
    Write-Host 'No new source changes to commit.' -ForegroundColor Yellow
}
& gh release create "v$Verzija" "$setup" --repo $repo --title "Mister Muscle Downloader v$Verzija" --notes-file "$notesFile" --latest
if ($LASTEXITCODE -ne 0) { throw 'GitHub release failed.' }
Write-Host "PUBLISHED v$Verzija" -ForegroundColor Green
