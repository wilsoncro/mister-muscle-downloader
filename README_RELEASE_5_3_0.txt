MISTER MUSCLE DOWNLOADER v5.3.0 - GITHUB RELEASE PACKAGE
=======================================================

PACKAGE CONTENTS:
Stable v5.3.0 application sources, required Qt timeline / Media Studio modules,
Windows build script, stable Inno Setup script, and one-click objavi.bat / release.ps1.

IMPORTANT: THIS ZIP DOES NOT CONTAIN THE WINDOWS INSTALLER OR EXTERNAL EXECUTABLE TOOLS.
The installer and portable ZIP are generated on your Windows computer.

HOW TO PUBLISH (on your Windows machine):
1. Use your EXISTING local clone of https://github.com/wilsoncro/mister-muscle-downloader
   (folder containing a .git directory; branch must be main). Back up local changes.
2. Extract the files from this ZIP directly INTO that existing clone, replacing files.
   Do not extract into an unrelated folder and run objavi.bat there.
3. Ensure you have: py (Python 64-bit with PySide6/PyInstaller installed), Inno Setup 6/7,
   git, and gh already logged in with `gh auth login`.
4. Required executables: yt-dlp.exe, ffmpeg.exe, ffprobe.exe, either in tools/,
   at repository root, or accessible through PATH. The build script copies them to tools/.
   Optional deno.exe is included if present in tools/, root, or PATH.
   gallery-dl.exe is downloaded by the build script if needed.
5. Run objavi.bat from the existing clone. It builds and publishes v5.3.0.
   It stops with a clear error if prerequisites, git remote, or release checks fail.

OUTPUT:
  Output\MisterMuscle_Setup.exe
  Output\MisterMuscle_Portable_v5.3.0.zip
GitHub Release v5.3.0 contains both files and uses the v5.3.0 CHANGELOG section.

NOTES:
- A successful Windows build and a short launch/smoke test on Windows are still necessary.
- GitHub push / release publication cannot be tested from this package alone.
- Existing bug reporting logic was not modified by this release preparation.
- The application settings folder returns to the stable MisterMuscleQt location.
- The installer uses the same stable AppId as earlier public releases to allow an upgrade.
