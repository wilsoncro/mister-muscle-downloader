## v5.2.15 - Enhanced Automatic Error Diagnostics

- Added redacted Preview process error details to automatic reports, including relevant yt-dlp/FFmpeg failure messages.
- Added recent event categories and an error occurrence count for better troubleshooting.
- Included application environment and a short sanitized diagnostic summary.
- Preserved automatic reporting preferences, offline retry, duplicate protection, and the option to disable reporting.
- No automatic screenshots, full logs, download links, or local filenames are attached.

## v5.2.14 - Automatic Error Reporting

- Enabled automatic error reporting by default for new installations, with an option to turn it off in Settings.
- Preserved existing users' automatic reporting preference.
- Automatically submits sanitized error reports to Mister Muscle Bug Center.
- Added duplicate-report protection and retry queue for temporary network failures.
- Does not automatically attach screenshots or full diagnostic logs.
