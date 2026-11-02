MISTER MUSCLE DOWNLOADER v5.3.2 — COMBINED HOTFIX + FAST PREVIEW
================================================================

All fixes in this ONE release:
- Fixed audio waveform permission-denied errors when running from Program Files.
- Preview workers now use writable per-user scratch folders and child-process temp paths.
- Hidden Windows CMD windows for timeline background tools in Light/Smart/Full.
- Faster remote audio waveform and video thumbnail downloads: no artificial
  bandwidth caps, leaner preview formats, up to four fragments where supported.
- Reuse Full thumbnails on return to Smart, without re-downloading them.
- Includes v5.3.1 critical fix: pasting a video URL cannot spawn the packaged
  main app instead of yt-dlp.exe; missing bundled yt-dlp reports an error.
- Main video/audio download and clip export quality remain unchanged.

STEPS ON YOUR WINDOWS PC
1. Unzip the contents of MisterMuscle_v5.3.2_COMBINED into your EXISTING
   local GitHub repository folder (must contain .git). Overwrite project files.
   Keep your existing tools/, assets/, icons and .git folder.
2. Build without publishing to test locally:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\release.ps1
3. Open the built app; paste a URL; confirm exactly one GUI app window,
   successful audio and video tracks, no CMD flash, working Light/Smart/Full,
   smooth transition Full -> Smart, working exports and diagnostics.
4. When it all passes, run objavi.bat to publish GitHub release v5.3.2.

Note: source-level checks performed here; real network throughput and Windows
GUI/installer behavior require testing on your Windows computer.
