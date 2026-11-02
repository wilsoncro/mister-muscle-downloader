Mister Muscle Downloader v5.3.5 - Full Waveform and Direct Audio / Video Cutting

Changes since v5.3.4:
- Complete audio waveform instead of a 15-minute preview limit.
- Full-length IN/OUT selection and split-at-playhead markers.
- Video + Audio, Video Only and Audio Only exports from Media Studio.
- Local audio files supported, with AAC/M4A clip export.
- Several previously released Windows permission, scrolling and preview fixes retained.

GitHub Actions:
- Each push to main runs a Windows test build without public release.
- To publish after a successful test: Actions > Build Mister Muscle on Windows > Run workflow, branch main, check "Also publish a GitHub Release".
- A matching v5.3.5 tag can also trigger a release build.
- Release publication is blocked if version strings differ or compilation fails.
- If you prefer the local Windows build, objavi.bat is still available.

Do not publish before reviewing the Windows build test result.