MISTER MUSCLE DOWNLOADER v5.3.3 — AUDIO PREVIEW PERMISSION FIX
================================================================

WHAT THIS VERSION INCLUDES
- Prevents Permission denied errors from yt-dlp temporary files inside
  C:\Program Files\Mister Muscle Downloader by using writable user temp paths.
- Applies the same protection to audio waveform and video thumbnail previews.
- Includes existing v5.3.2 improvements: hidden CMD windows, faster preview
  loading and cache reuse for Light / Smart / Full.
- Retains the v5.3.1 fix for multiple app windows after pasting a link.
- Does not change downloaded video/audio quality or clip exports.

HOW TO TEST AND PUBLISH ON WINDOWS
1. Unpack this package into your EXISTING cloned GitHub repo containing .git.
   Replace project files, keeping your existing tools/, assets/, icons and .git.
2. Build without publishing:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\release.ps1
3. Install locally. Paste a video URL, confirm a single app window, load the
   AUDIO waveform and thumbnails, switch Light / Smart / Full without CMD windows,
   and verify export and download behavior.
4. If all works, run objavi.bat to publish v5.3.3.

Note: source-level tests run here; Windows app behavior must be tested locally.
