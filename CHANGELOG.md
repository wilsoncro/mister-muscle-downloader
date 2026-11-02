## v5.3.1 - Critical Windows Startup Hotfix

- Fixed a critical issue where pasting one video link could open the app three times in the packaged Windows release.
- Corrected the Media Studio audio preview and thumbnail workers to find bundled `yt-dlp.exe` in the installed application's `tools` folder.
- Added a fail-safe: if `yt-dlp.exe` is missing in a packaged build, preview workers show an error instead of re-launching `MisterMuscle.exe`.
- Preserved all v5.3.0 download formats, timeline features, queues, reports and updater behavior.

## v5.3.0 - Redesigned Downloads and Media Studio

- Redesigned New Download with File type, Output format and Resolution immediately visible; advanced settings stay separate.
- Added mode-specific output formats for Video + audio, Video only and Audio only, plus an Instagram Photos workflow.
- Kept MP4/MKV/WEBM choices for video and MP3/M4A/WAV/FLAC/OPUS/OGG/AAC choices for audio where supported.
- Integrated the original media player with V1 thumbnail previews, A1 audio waveform and precise timeline clip selection.
- Added multiple clip ranges, Remove Last / Clear All controls and batch clip export from the player.
- Added timeline loading modes and zoom/frame-step controls, with improved preservation of selected clips.
- Added local Media Studio tools for aspect-ratio exports, local media preview, scenes, waveform and file management.
- Preserved the download queue, retry, pause/resume, progress display, Download Center and session recovery.
- Improved cancellation of preview/audio processing when switching sources and reduced unnecessary background jobs.
- Added bounded preview caches and fixed temporary-file timing issues during audio waveform generation.
- Fixed Remove Last clip ordering and corrected the display of partial waveforms for long videos.
- Improved FFmpeg/FFprobe detection for exports, conversions and packaged installations.
- Kept the update center, format settings, status logging and existing error reporting behavior.
- Prepared a stable Windows installer and a portable ZIP with required tools; the installer retains the existing application identity.

## v5.2.16 - What's New Display Fix

- Fixed the What's New window to show the latest two versions.
- Updated embedded release notes for packaged Windows installations.
- Preserved enhanced automatic error diagnostics from v5.2.15.

## v5.2.15 - Enhanced Automatic Error Diagnostics

- Added redacted Preview process error details to automatic reports, including relevant yt-dlp/FFmpeg failure messages.
- Added recent event categories and an error occurrence count for better troubleshooting.
- Included application environment and a short sanitized diagnostic summary.
- Preserved automatic reporting preferences, offline retry, duplicate protection, and the option to disable reporting.
- No automatic screenshots, full logs, download links, or local filenames are attached.

## v5.2.14 - Automatic Error Reporting

- Enabled automatic error reporting by default for new installations, with an option to turn it off in Settings.
- Preserved existing users' automatic error reporting preference.
- Automatically submits sanitized error reports to Mister Muscle Bug Center.
- Added duplicate-report protection and retry queue for temporary network failures.
- Does not automatically attach screenshots or full diagnostic logs.
