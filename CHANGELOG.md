# Changelog

## v5.2.13 — Animated What’s New and release presentation
- Show animated dark-theme What’s New cards for the newest and previous releases (v5.2.13 and v5.2.12).
- Improve Croatian and English release descriptions and automatic first-launch display after updating.
- Keep automatic Download Center navigation, original video titles, duplicate protection, 4K downloads, and GPU Premiere conversion.
- Keep automatic publishing through objavi.bat using version and notes from CHANGELOG.md.

## v5.2.12 — Download Center and original titles
- Redesigned What’s New with dark release cards, animated fade-in, and localized latest/previous release notes.
- Automatically return to New Download 3.5 seconds after the final successful download; do not interrupt queued downloads.
- Open Download Center immediately after Start Download.
- Fetch the source title asynchronously without delaying the download.
- Save video with the original source title; do not append a video ID or other text.
- Keep duplicate download/conversion guards and Premiere GPU encoder preflight.
- Preserve 4K quality, NVENC/AMF/QSV and CPU fallback.

## v5.2.11 — Legacy Fast Premiere and GPU support
- Restore fast processing for already-compatible videos.
- Retain 4K and hardware encoding support.
