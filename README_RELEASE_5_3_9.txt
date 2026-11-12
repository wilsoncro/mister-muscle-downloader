Mister Muscle Downloader v5.3.9 — Inspect and Preview Access Notices

Situation:
Four separate Windows 10 users submitted Hotstar Inspect and Preview reports.
Hotstar returned "This video is only available for registered users".
This is an access restriction from the provider, not a downloader crash.
The app previously logged each yt-dlp ERROR line and its process exit code as
separate crash reports, making one denied request look like multiple failures.

Fixed:
- Inspect and Preview show "Hotstar requires a signed-in, authorized account"
  when the provider denies access to registered-only media.
- The app does not attempt to bypass sign-in, payment, DRM or geo restrictions.
- Expected access notices are WARN events, not automatic crash reports.
- Unexpected extractor/process failures still report ERROR, independently for
  each user, exactly once per Inspect/Preview operation.
- Collect the text from the process stream before it gets drained by Qt;
  avoid meaningless "Metadata inspect exited with code 1" reports.
- A partial MP4 file from a failed preview is never treated as a successful
  preview.
- All previous downloads, Car Multimedia MP4, full timeline and A1/V1
  audio/video markers remain available.

Test:
test_restricted_media_539.py simulates 4 independent users, protected Hotstar
responses, unanticipated extractor failures, preview partial files, previous
FFmpeg transcoding and Windows regressions.

Publication:
GitHub Actions builds and releases only after all tests and Windows installer
packaging succeed.
