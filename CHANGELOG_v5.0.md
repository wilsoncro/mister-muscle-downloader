# Mister Muscle Downloader v5.0

A major update to Mister Muscle Downloader, bringing a redesigned Windows interface, more flexible download options, integrated media tools, and a simpler installation experience.

## Highlights

- **New desktop interface:** A redesigned dark-themed interface built with **PySide6 / Qt**, with a dedicated navigation sidebar and a more organized download workspace.
- **Three download modes:** Choose **Video + Audio**, **Video Only**, or **Audio Only**, each with its own format selection.
- **Integrated Media Studio:** Preview videos, work with a timeline, mark clip boundaries, and export clips without leaving the main workspace.
- **Download management:** Track active, pending, completed, and failed downloads from the Download Center.
- **Automatic tool updates:** Checks for updates to yt-dlp and FFmpeg/FFprobe and can apply them from trusted upstream sources.
- **English and Croatian:** Choose your interface language, with English as the default.
- **What’s New:** A short in-app summary of major changes on first launch after updating.
- **Windows installer:** The release build is designed to bundle the app and its required download tools into one installer.

## Download formats and quality

- **Video + Audio:** MP4, MKV, WEBM.
- **Video Only:** MP4, MKV, WEBM, without an audio track.
- **Audio Only:** MP3, M4A, WAV, FLAC, OPUS, OGG, AAC.
- Format choices update automatically when switching download modes.
- The interface remembers the selected format for each mode while the app is running.
- Choose video quality from **Best available**, **2160p**, **1440p**, **1080p**, **720p**, **480p**, or **360p**.
- Each queued download keeps its own mode, resolution, and output-format settings.
- Audio extraction and format conversion use yt-dlp and FFmpeg where required.

> Note: Available source streams and successful conversion depend on the source website, the video, and codec/container compatibility. A requested format or resolution is not guaranteed for every URL.

## New Download workspace

- Paste one or multiple video URLs, with one link per line.
- Quickly paste, clear, inspect, or preview a link.
- Display available video information, including title and duration when metadata is available.
- Choose the download destination from the interface.
- Monitor progress and download status.
- Pause, resume, or cancel an active download.
- Open the destination folder directly from the app.

## Download Center, Queue, and History

- A dedicated **Download Center** shows completed, downloading, pending, and failed tasks.
- Filter the Download Center by task status and search downloads.
- See video thumbnails and metadata when available.
- Retry failed downloads.
- Queue multiple URLs and start or resume pending downloads.
- Reorder queued tasks, remove selected entries, or clear the pending queue.
- Save the pending queue and restore it after restarting the app.
- Resume downloads using yt-dlp's partial-download support where available.
- Keep a download history with actions to open or play downloaded files.

## Media Studio and clipping

- Integrated video preview and timeline controls in the **New Download** screen.
- Load a video link or open a local video file.
- Mark clip start and end points from the timeline.
- Export a marked clip using FFmpeg.
- Support multiple timeline selections for clip exports.
- Clip aspect-ratio options include **Original**, **16:9**, **9:16**, **1:1**, **4:5**, **3:4**, **21:9**, and **4:3**.
- Full-video downloads retain their original framing; aspect-ratio choices apply to clip exports.
- Embedded playback uses Qt WebEngine when available, with a local-preview fallback for sources that block embedding.

## Language and release highlights

- **English** is the default language for new users.
- Switch to **Hrvatski** in Settings; the language choice is remembered.
- Localized player and timeline controls, clip actions, and key interface messages.
- A concise **What’s New** dialog highlights important changes after updating, with an option to revisit it.

## Automatic updates and component management

- Automatically check for component updates when the application starts.
- **yt-dlp:** Download and install available updates from the official yt-dlp release channel.
- **FFmpeg and FFprobe:** Check and update both executables together using the Gyan.dev Windows Full Build, linked from the official FFmpeg download page.
- Store updated tools in a user-writable location so standard Windows installations do not require modifying protected Program Files files.
- **PySide6:** Check its official PyPI release information; packaged Windows builds receive Qt/PySide6 upgrades through a new application installer instead of replacing loaded libraries.
- **Mister Muscle Downloader:** Check GitHub Releases for a newer installer and offer an update/restart flow where needed.
- Show update progress and status, including when a download is ready but not yet applied.
- Improve update worker lifecycle handling to avoid crashes during repeated update checks.

## Reliability and diagnostics

- Added a **Status Log** screen for application, download, FFmpeg, and player messages.
- Filter logs to errors or warnings, copy them, or save them to a file.
- Optional subtle error notification sound.
- Persist application session data and download history in the user profile.
- Improved update status messages and distinguished installed versions from newer upstream releases.
- Running application files and loaded Qt libraries are not overwritten in place.

## Packaging and installation

- Windows desktop packaging using **PyInstaller** and **Inno Setup**.
- Release build copies **yt-dlp**, **FFmpeg**, and **FFprobe** into the packaged application.
- Qt WebEngine, multimedia, and supporting components are included in the build configuration.
- Installer creates Start Menu shortcuts, offers an optional desktop shortcut, and supports Windows uninstallation.
- The installed app is intended to run without separately installing Python or the bundled command-line tools.

## Notes

- This is a substantial interface and packaging update; some workflows may look different from earlier versions.
- Certain sites may restrict downloads or embedded previews, and availability can change independently of the app.
- Before public distribution, verify the installer and all three download modes on Windows.

**Thank you for using Mister Muscle Downloader!**
