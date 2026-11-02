param(
    [string]$Verzija = '',
    [string]$Opis = '',
    [switch]$Publish
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# PowerShell 5.1 can promote native-program stderr to a terminating error.
# Execute native commands with a temporary non-terminating preference and check exit codes.
function Invoke-Native {
    param([Parameter(Mandatory=$true)][string]$Program, [string[]]$Arguments = @(), [switch]$Quiet)
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($Quiet) {
            $output = @(& $Program @Arguments 2>$null)
        } else {
            $output = @(& $Program @Arguments 2>&1)
        }
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $old
    }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = ($output -join "`n") }
}

$source = Join-Path $PSScriptRoot 'mister_muscle_qt.py'
$iss = Join-Path $PSScriptRoot 'MisterMuscle_Setup.iss'
$notesFile = Join-Path $PSScriptRoot 'CHANGELOG.md'
if (-not (Test-Path -LiteralPath $notesFile -PathType Leaf)) {
    throw 'CHANGELOG.md missing. Add a version heading like ## v5.3.0 before publishing.'
}
$changelog = [IO.File]::ReadAllText($notesFile)
$headingPattern = '(?m)^\s{0,3}#{1,3}\s*\[?v?(?<version>\d+\.\d+(?:\.\d+)?)\]?\b[^\r\n]*$'
$headings = [regex]::Matches($changelog, $headingPattern)
if ($headings.Count -eq 0) { throw 'No version heading found in CHANGELOG.md (example: ## v5.2.12).' }
$latestHeading = $headings[0]
$detectedVersion = $latestHeading.Groups['version'].Value
if ([string]::IsNullOrWhiteSpace($Verzija)) { $Verzija = $detectedVersion }
elseif ($Verzija -ne $detectedVersion) {
    throw "Requested version $Verzija does not match first CHANGELOG.md version $detectedVersion."
}
$notesStart = $latestHeading.Index
$notesEnd = if ($headings.Count -gt 1) { $headings[1].Index } else { $changelog.Length }
$releaseNotes = $changelog.Substring($notesStart, $notesEnd - $notesStart).Trim()
if ($releaseNotes -notmatch '(?m)^\s*[-*]\s+\S') {
    throw "Changelog v$Verzija has no bullet-point release notes."
}
if ($Verzija -notmatch '^\d+\.\d+(\.\d+)?$') { throw 'Invalid changelog version' }
if ([string]::IsNullOrWhiteSpace($Opis)) { $Opis = "Release v$Verzija from CHANGELOG.md" }
$releaseNotesPath = Join-Path $PSScriptRoot '.release-notes-current.md'
[IO.File]::WriteAllText($releaseNotesPath, $releaseNotes + "`r`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Detected v$Verzija from CHANGELOG.md" -ForegroundColor Cyan
Write-Host $releaseNotes -ForegroundColor DarkGray
$setup = Join-Path $PSScriptRoot 'Output\MisterMuscle_Setup.exe'
$repo = 'wilsoncro/mister-muscle-downloader'
$portableZip = Join-Path $PSScriptRoot ("Output\MisterMuscle_Portable_v$Verzija.zip")

foreach ($file in @($source, $iss, (Join-Path $PSScriptRoot 'build_qt.py'))) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing project file: $file" }
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher (py) missing' }

if ($Publish) {
    if (-not (Test-Path -LiteralPath $notesFile -PathType Leaf)) { throw 'CHANGELOG.md missing.' }
    foreach ($program in @('git','gh')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) { throw "$program is missing" }
    }
    $inside = Invoke-Native git @('rev-parse','--is-inside-work-tree') -Quiet
    if ($inside.ExitCode -ne 0 -or $inside.Output.Trim() -ne 'true') {
        throw "This folder is NOT a Git repository: $PSScriptRoot. Open the existing cloned repository and copy your project files there; do not run git init in an unrelated folder."
    }
    $branch = Invoke-Native git @('branch','--show-current') -Quiet
    if ($branch.ExitCode -ne 0 -or $branch.Output.Trim() -ne 'main') { throw 'Publishing requires the main branch of the cloned repository.' }
    $origin = Invoke-Native git @('remote','get-url','origin') -Quiet
    if ($origin.ExitCode -ne 0 -or $origin.Output -notmatch '(^|[/:])wilsoncro/mister-muscle-downloader(\.git)?\s*$') {
        throw "Git origin does not point to $repo. Check: git remote -v"
    }
    $auth = Invoke-Native gh @('auth','status') -Quiet
    if ($auth.ExitCode -ne 0) { throw 'GitHub login required: gh auth login' }
    $releases = Invoke-Native gh @('release','list','--repo',$repo,'--limit','100','--json','tagName') -Quiet
    if ($releases.ExitCode -ne 0) { throw "Could not check GitHub releases: $($releases.Output)" }
    $tags = @($releases.Output | ConvertFrom-Json)
    if ($tags | Where-Object { $_.tagName -eq "v$Verzija" }) { throw "Release v$Verzija already exists; refusing to overwrite" }
}

$code = [IO.File]::ReadAllText($source)
if ($code -notmatch "APP_VERSION\s*=\s*'[^']*'") { throw 'APP_VERSION not found' }
if ($code -notmatch '(?m)^APP_IS_BETA\s*=\s*False\s*$') { throw 'Refusing to publish a BETA build as stable.' }
$code = [regex]::Replace($code, "APP_VERSION\s*=\s*'[^']*'", "APP_VERSION = '$Verzija'", 1)
[IO.File]::WriteAllText($source, $code, (New-Object System.Text.UTF8Encoding($false)))
$setupText = [IO.File]::ReadAllText($iss)
if ($setupText -notmatch '#define MyAppVersion "[^"]*"') { throw 'MyAppVersion not found in .iss' }
$setupText = [regex]::Replace($setupText, '#define MyAppVersion "[^"]*"', "#define MyAppVersion `"$Verzija`"", 1)
[IO.File]::WriteAllText($iss, $setupText, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "Building Mister Muscle v$Verzija..." -ForegroundColor Cyan
$build = Invoke-Native py @('-3','build_qt.py')
if ($build.Output) { Write-Host $build.Output }
if ($build.ExitCode -ne 0) { throw 'Build failed; nothing published.' }
if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) { throw 'Setup EXE missing; nothing published.' }
Write-Host "Installer ready: $setup" -ForegroundColor Green
$portableDir = Join-Path $PSScriptRoot 'dist\MisterMuscle'
if (-not (Test-Path -LiteralPath (Join-Path $portableDir 'MisterMuscle.exe') -PathType Leaf)) {
    throw 'Portable application EXE missing; nothing published.'
}
if (Test-Path -LiteralPath $portableZip) { Remove-Item -LiteralPath $portableZip -Force }
Compress-Archive -LiteralPath $portableDir -DestinationPath $portableZip -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $portableZip -PathType Leaf)) { throw 'Portable ZIP missing; nothing published.' }
Write-Host "Portable ZIP ready: $portableZip" -ForegroundColor Green
if (-not $Publish) { Write-Host 'DRY RUN: no GitHub changes. Use -Publish after testing.' -ForegroundColor Yellow; exit 0 }


Write-Host 'Publishing release...' -ForegroundColor Cyan
# Commit only release source files. Never stage the entire repository.
# Thousands of deleted node_modules/build files can be left unstaged safely.
$paths = @('mister_muscle_qt.py','mister_muscle_original_player.py','pro_timeline.py','phase3_engine.py','phase4_lab.py','beta_studio.py','legacy_downloader.py','build_qt.py','release.ps1','objavi.bat','MisterMuscle_Setup.iss','README_RELEASE.txt','README_RELEASE_5_3_0.txt','CHANGELOG.md','assets','ikona.ico')
$existing = @($paths | Where-Object { Test-Path -LiteralPath (Join-Path $PSScriptRoot $_) })
# Do not accidentally include changes that were staged before this script ran.
$preStaged = Invoke-Native git @('diff','--cached','--name-only') -Quiet
if ($preStaged.ExitCode -ne 0) { throw "Cannot inspect Git index: $($preStaged.Output)" }
$unrelated = @($preStaged.Output -split "`n" | Where-Object {
    $item = $_.Trim()
    if (-not $item) { return $false }
    foreach ($allowed in $paths) {
        if ($item -eq $allowed -or $item.StartsWith("$allowed/")) { return $false }
    }
    return $true
})
if ($unrelated.Count -gt 0) {
    throw "Unrelated files already staged; not safe to commit. Unstage them using 'git restore --staged .' (does not delete files), then retry. First: $($unrelated[0])"
}
foreach ($path in $existing) {
    $result = Invoke-Native git @('add','--',$path) -Quiet
    if ($result.ExitCode -ne 0) { throw "git add failed for '$path': $($result.Output)" }
}
$staged = Invoke-Native git @('diff','--cached','--name-only') -Quiet
if ($staged.ExitCode -ne 0) { throw "Cannot inspect staged files: $($staged.Output)" }
if (-not [string]::IsNullOrWhiteSpace($staged.Output)) {
    $identity = Invoke-Native git @('var','GIT_AUTHOR_IDENT') -Quiet
    if ($identity.ExitCode -ne 0) { throw "Git author identity missing. Set git config user.name and git config user.email. $($identity.Output)" }
    $commit = Invoke-Native git @('commit','-m',"Release v$Verzija")
    if ($commit.Output) { Write-Host $commit.Output }
    if ($commit.ExitCode -ne 0) {
        $status = Invoke-Native git @('status','--short','--untracked-files=no')
        throw "git commit failed (exit $($commit.ExitCode)). $($commit.Output)`nGit status: $($status.Output)"
    }
} else {
    Write-Host 'No release-source changes to commit; skipping git commit.' -ForegroundColor Yellow
}
# Always push, including when the release version was already committed locally.
$push = Invoke-Native git @('push')
if ($push.Output) { Write-Host $push.Output }
if ($push.ExitCode -ne 0) { throw "git push failed (exit $($push.ExitCode)): $($push.Output)" }
$release = Invoke-Native gh @('release','create',"v$Verzija",$setup,$portableZip,'--repo',$repo,'--title',"Mister Muscle Downloader v$Verzija",'--notes-file',$releaseNotesPath,'--latest') -Quiet
if ($release.ExitCode -ne 0) { throw "GitHub release failed: $($release.Output)" }
Write-Host "PUBLISHED v$Verzija" -ForegroundColor Green
Write-Host $release.Output

Remove-Item -LiteralPath $releaseNotesPath -ErrorAction SilentlyContinue
