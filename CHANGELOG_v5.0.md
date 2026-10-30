# Mister Muscle Downloader v5.1.6

## New in v5.1.6
- Report a Bug page below Settings: category, description, up to three screenshots (including clipboard image paste), optional redacted diagnostics, review and confirmation before sending.
- Reports sent to private Supabase bug_reports table and screenshot storage through submit-bug-report Edge Function; no user login required.
- Administrator can view reports in Supabase Table Editor.
- Auto-paste supported media links immediately after copying, while Mister Muscle is running, including when the window is in the background. Toggle it off in New Download.
- Updated the in-app What's New screen to summarize changes and fixes from v5.1.1 to v5.1.6.

## Features and fixes since v5.1.0
- Instagram Photos download mode for image posts and carousels using gallery-dl; supports cookies from a logged-in browser or a user-selected cookies.txt file. Instagram access and downloads depend on the account, source and platform restrictions.
- Clipboard validation accepts supported media URLs, ignores unrelated clipboard content and avoids duplicate URLs.
- Embedded YouTube player controls enabled where the source permits playback.
- Media Studio: local HTTP server resilience in frozen builds, better 404 diagnostics, local-video routing, and Qt WebEngine load-status logging fixes.
- Update Center: improved version detection for bundled yt-dlp and PySide6; version-specific installer downloads and installation flow.
- Build: faster repeated PyInstaller builds without unconditional --clean. Use a clean build if stale build artifacts are suspected.
- Qt desktop interface, download center, queue, history, format and quality options, Media Studio timeline and clip export, and English/Croatian language support.

## Testing note
Source syntax and package structure checked; Windows installer and end-to-end Instagram downloads have not been tested in this environment.
