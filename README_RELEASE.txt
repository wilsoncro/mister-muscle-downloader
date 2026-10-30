MISTER MUSCLE DOWNLOADER — Windows v5.0 RELEASE KIT
=====================================================

IMPORTANT: This is BUILD SOURCE, not a finished Windows installer.
Build must run on Windows. Nothing is published without -Publish.

1. Copy this kit into a local clone of your GitHub repository
   (or copy your existing .git folder into the kit; do not delete .git).
2. Install on YOUR BUILD PC (end users need none of these):
   - Python 3.12 or 3.13 64-bit, with 'py' launcher
   - py -m pip install -U PySide6 PyInstaller
   - Inno Setup 6 (ISCC.exe)
   - Git, GitHub CLI (gh auth login) for publishing
3. Put OFFICIAL Windows binaries in tools/:
      yt-dlp.exe   from github.com/yt-dlp/yt-dlp/releases
      ffmpeg.exe   from a trusted Windows FFmpeg build
      ffprobe.exe  from the same FFmpeg build
   The build intentionally FAILS if any is missing; no network dependency
   on a user's first launch. Do not use unknown third-party mirrors.
4. DRY RUN: open PowerShell in the kit/repository folder:
      .\objavi.bat -Verzija "5.0" -Opis "Mister Muscle 5.0 Stable"
   This builds Output\MisterMuscle_Setup.exe WITHOUT publishing.
5. Install and test the EXE on a clean Windows VM. Check player,
   WebChannel, preview, downloads, cutting, sound and auto-update.
   Also install over a previous v4.x version to test in-place upgrade.
6. ONLY AFTER TESTS, publish:
      .\objavi.bat -Verzija "5.0" -Opis "Mister Muscle 5.0 Stable" -Publish
   It pushes selected source files and creates a GitHub Release with
   MisterMuscle_Setup.exe on wilsoncro/mister-muscle-downloader.

IMPORTANT COMPATIBILITY:
- Original Inno Setup AppId is preserved for upgrades.
- Old installed clients will detect v5.0 only if their old updater
  checks GitHub latest release and can launch this installer.
- The new app's beta version number 7.14 is changed to 5.0 at build time.
- Qt app settings live under %APPDATA%\MisterMuscleQt; old Tkinter
  settings may use another location and are NOT migrated automatically.
- The bundled yt-dlp.exe/ffmpeg.exe/ffprobe.exe are used for download
  and cutting. Their updates require a new installer build.
- The in-app updater currently DOWNLOADS future setup packages but does
  NOT silently install them. No automatic self-install is promised.
- A separate legacy Tkinter tool requires Python and is not supported
  inside the frozen app. The main Qt functions do not require Python.
- Unsigned installer may trigger Windows SmartScreen; code signing is
  recommended before broad public distribution.

NO GitHub release has been created by this kit.
