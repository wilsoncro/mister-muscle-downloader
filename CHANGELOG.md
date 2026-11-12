## v5.3.10 - In-App Hotstar Authentication and Host-Specific Login

- Added a service-aware login popup for account-restricted Inspect, Preview and Download requests.
- Instagram reuses the existing in-app Instagram login window; successful login enables a retry with the user-authorized Instagram cookies.
- Hotstar offers a new embedded login dialog loading the original official Hotstar URL in its own isolated Qt WebEngine profile, with the current page address visible.
- After user confirmation, store only Hotstar/JioHotstar session cookies locally and use them for authorized Inspect, Preview and Download requests via yt-dlp. No passwords are collected by Mister Muscle, and cookies are not passed to other platforms or included in bug reports.
- Added a Settings section to open the Hotstar in-app login proactively, view local session status, and clear Hotstar session cookies/cache on logout.
- Reuse the exact failed download job after successful Hotstar login without automatically retrying indefinitely; offer opening the official page in an external browser as a fallback.
- Preserve warnings rather than false crash reports for ordinary registration requirements, while retaining genuine per-user error reporting.
- This feature does NOT circumvent DRM, subscriptions, regional restrictions or other provider access controls. Some media will remain unavailable even with a valid account.
- Preserve previous Car Multimedia MP4 mode, independent A1/V1 cutting and Windows hotfixes.

## v5.3.9 - Hotstar Account Required and Inspect/Preview Error Handling

- Handle videos restricted to registered users (including the Hotstar "only available for registered users" message) as an access requirement rather than an internal application crash. The user sees a clear sign-in notice in Inspect and Preview.
- Preserve the original media provider's access restrictions: this update does not bypass login, subscriptions, DRM, or geographic availability.
- Prevent multiple automatic crash reports for a single Inspect or Preview operation: record yt-dlp diagnostics as warnings while the process runs, then issue one error if it ends with an unexpected failure.
- Inspect/Preview still report genuine exceptions for each affected user independently; there is no cross-user deduplication or suppression of unrelated errors.
- Preserve diagnostic output even when Qt consumed stderr/stdout before the finished callback, avoiding misleading "Metadata inspect exited with code 1" messages.
- Only accept a preview when yt-dlp finishes successfully and a playable file exists; partial output from failed runs no longer counts as success.
- Keep the Car Multimedia MP4 mode, independent A1/V1 cutting and previous Windows hotfixes intact.

## v5.3.8 - Car Multimedia MP4 Compatibility

- Fixed a common car multimedia playback issue: selecting Video + Audio / MP4 / Best available could produce an MP4 container containing AV1, VP9, Opus, 4K or 60 FPS streams unsupported by many USB players.
- Added Car Multimedia (MP4) as a fifth choice in the File type dropdown. No separate checkbox: existing best-quality downloads remain unchanged.
- Car mode downloads the source normally, then transcodes video to H.264 Baseline Level 3.1 with yuv420p, max 1280x720 and constant 30 FPS, plus AAC-LC stereo 44.1 kHz audio; MP4 has faststart enabled.
- Limit peak video bitrate to 3.5 Mbps, use predictable CPU libx264 rather than unknown GPU profiles, and never upscale lower-resolution source videos.
- Car mode is a separate File type choice; it forces MP4 output and the best available source up to 720p. The mode persists in the queued task for pause/resume and crash recovery.
- Validate final video profile, frame rate, dimensions, codec and audio streams with ffprobe before treating the download as successful.
- Preserve the original source if conversion or validation fails. Warn that some car models still need a different resolution, filesystem or USB format.

## v5.3.7 - Windows Player HTTP and Temporary File Cleanup Hotfix

- Treat browser-initiated HTTP stream disconnects (WinError 10054, 10053, 10058 and broken pipes) as normal player events, not errors or automatic crash reports. Keep unexpected server failures visible in the Status Log.
- Stop Qt media playback and WebEngine navigation before closing the local player HTTP server; join the listener thread before removing temporary playback files.
- Make preview, original-player and source-cut temporary folders resilient to WinError 32 when Windows is still holding a media file, with bounded cleanup retries and non-fatal warnings.
- Clean only app-owned abandoned media scratch folders older than seven days on startup; never delete original downloaded video/audio files.
- Make remote A1 audio and V1 thumbnail preview scratch cleanup tolerate Windows file-lock races.
- Normalize setup and installed-app version labels to exactly one v prefix; keep the actual version number numeric in the program and installer.
- Preserve the independent A1/V1 audio/video cut markers, full waveform and all existing download features.

## v5.3.6 - Independent A1 Audio Markers and Track Cutting

- Added separate turquoise A1 IN/OUT drag handles beneath the purple V1 handles in Media Studio.
- The Link A/V toggle preserves synchronized cutting by default; moving an A1 handle automatically unlinks audio without disturbing the video range.
- A IN / A OUT buttons mark independent audio times at the playhead.
- Audio Only exports use A1 markers, Video Only exports use V1 markers. Video + Audio can export differing A1 and V1 ranges within one MP4.
- When A1 is shorter than V1, the combined export pads the remaining picture with silence. Longer A1 selections are capped to the selected video duration.
- Added dedicated A1 clip selections: save, split, remove last, clear, and export all audio clips to M4A.
- Retained original source files, full-length waveform, silent background processes and existing Windows hotfixes.

## v5.3.5 - Complete Audio Waveform and Direct Audio / Video Cutting

- Removed the 15-minute audio waveform limit: the A1 audio track now shows the entire soundtrack, including longer recordings.
- Adaptively downsampled waveform analysis to keep memory bounded for multi-hour videos; full audio is still decoded for correct coverage. This changes the preview only, never the downloaded or exported quality.
- Made the initial IN/OUT range cover the full media duration when duration becomes available (if the user has not already moved the handles).
- Added a visible Export Selection control below the Media Studio timeline with Video + Audio (MP4), Video Only (silent MP4), and Audio Only (M4A).
- Export marked ranges and multiple saved selections with the chosen track option, for both local media and online links.
- Allow local audio sources (MP3, M4A, WAV, FLAC, OGG, OPUS, AAC) in the Media Studio; skip unnecessary thumbnail extraction for audio-only inputs.
- Remote audio-only cutting fetches an audio stream rather than the full video. Original input files remain unchanged.
- Preserved v5.3.4 scroll behavior, writable preview scratch directory, hidden CMD windows, cache and previous hotfixes.

## v5.3.4 - Reliable Audio Preview and Scroll Fix

- Fixed missing-file (`[Errno 2]`) errors when generating the online audio waveform after the v5.3.3 permission fix.
- Kept the preview process temporary directory stable in a writable user-local folder, separate from per-job media outputs that are deleted after processing.
- Set yt-dlp output and temporary-media paths explicitly; added a one-time retry in a fresh output directory for transient missing-file errors, using sequential fragments on retry.
- Disabled mouse-wheel changes on format, resolution, Light/Smart/Full and other dropdown menus so normal page scrolling cannot change options accidentally. Mouse and keyboard selection still work.
- Retained the silent background processes, preview speed improvements, cache optimization, and the v5.3.1 multiple-window fix.

## v5.3.3 - Audio Preview Permission Fix

- Fixed audio waveform preview errors (`Permission denied`) when the app is installed in `C:\Program Files`.
- Audio and video preview workers now use a user-writable directory and explicit `TMP`, `TEMP` and `TMPDIR` paths instead of creating temporary files in the protected installation folder.
- Preserved the previous CMD-window fix, faster preview transfers, cache behavior, and existing downloads and exports.

## v5.3.2 - Silent Tools and Faster Media Studio Previews

- Fixed command prompt windows flashing during Light / Smart / Full mode changes in packaged Windows builds.
- Launches all timeline background yt-dlp, FFmpeg and FFprobe processes with CREATE_NO_WINDOW on Windows, preserving logs, exit codes and cancellation.
- Removed artificial speed limits for online waveform audio and video thumbnail preview downloads; actual speed still depends on the source and network.
- Preferred smaller audio and low-resolution video-only streams for previews, with fallback formats to preserve source compatibility.
- Enabled up to four concurrent yt-dlp fragment transfers where supported; no effect on sources that do not use fragments.
- Reused Full-mode video preview frames when returning to Smart mode, avoiding repeat downloads when cached frames are available.
- Preserved the v5.3.1 fix preventing extra app launches when pasting a link, plus existing exports, download quality, Light / Smart / Full behavior and error diagnostics.

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
