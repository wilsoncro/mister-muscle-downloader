MISTER MUSCLE DOWNLOADER v5.3.1 - CRITICAL HOTFIX
==============================================

This is a source/package hotfix for the already published v5.3.0.
The v5.3.0 Windows app could open extra windows when loading online audio
and video previews from one pasted link. PyInstaller places pro_timeline.py
under _internal, but standalone yt-dlp.exe is copied into the outer tools/
directory. The old fallback launched MisterMuscle.exe itself twice.

Fixed:
- Both online timeline workers always resolve external tools relative
  to the frozen app executable location.
- If yt-dlp.exe is missing, workers fail safely and report the error.
- Version and What's New / CHANGELOG updated to 5.3.1.

Publish steps (Windows):
1. Replace corresponding source files in YOUR EXISTING cloned GitHub repo.
   Keep your existing repo's .git folder, tools/, assets/, icon, etc.
2. Before publishing, build a local copy (optional):
   powershell -ExecutionPolicy Bypass -File .\release.ps1
3. Install/test: paste one YouTube URL, and verify there is only ONE
   MisterMuscle.exe GUI process/window in Task Manager; timeline previews
   should still work (test Smart mode, not Light mode).
4. Publish v5.3.1 with objavi.bat. It will build, commit, push and create
   the new GitHub release including installer and portable ZIP.

Note: This package cannot be built as a Windows EXE inside this Linux
workspace, so the real Windows installation / runtime test is essential.
No change was made to existing automatic error report behavior.
