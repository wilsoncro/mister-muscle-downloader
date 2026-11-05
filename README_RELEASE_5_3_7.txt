Mister Muscle Downloader v5.3.7 - Windows Player and Temporary Files Hotfix

Fixes:
- WinError 10054/10053/10058 from Chromium closing a localhost media request are
  treated as normal player disconnects instead of sent as automatic crash reports.
- Genuine local-server exceptions still go to Status Log.
- Stop WebEngine navigation and Qt media playback before shutting down the HTTP
  server; wait for the listener thread before attempting temp-file cleanup.
- WinError 32 from files still held by Windows is non-fatal. Cleanup retries
  briefly and leaves locked scratch files in the system Temp folder if needed.
- On the next launch, app-owned abandoned scratch directories older than 7 days
  are removed on a best-effort basis. Original downloads are never affected.
- Setup title and installed-app label now contain exactly one 'v' before 5.3.7.
- Independent A1 audio / V1 video trims and the full-duration waveform remain.

Automated verification:
- v5.3.7 tests include simulated temp lock, HTTP disconnect filtering, and
  the existing FFmpeg video/audio and full-waveform regression tests.
- Windows GitHub Actions publishes only after an entirely successful build.
