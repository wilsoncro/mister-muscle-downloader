Mister Muscle Downloader v5.3.8 - Car Multimedia Dropdown Mode

Some car USB players skip MP4 files if the contained AV1/VP9/Opus codecs, 4K or
high frame rates are unsupported. MP4 is a container, not a codec guarantee.

New File type option: Car Multimedia (MP4)

Select this directly in the File type dropdown and start the download.
No checkbox or extra panel. MP4 output and best source up to 720p are automatic.

Verified output target:
- H.264 Baseline Level 3.1, yuv420p, max 1280x720, 30 FPS constant
- Video maxrate 3.5 Mbit/s, VBV buffer 7 Mbit
- AAC-LC stereo, 44.1 kHz
- MP4 with faststart for seeking
- No upscaling of lower-resolution source video

The existing Video + audio / Best available path is unchanged. Car mode is
stored as a separate queue mode (also preserved on pause/resume/relaunch).
If a conversion fails, the original source is retained.

Some cars still need smaller files, FAT32 USB or 480p; the exact head unit
model is necessary to guarantee playback.

Regression: test_car_multimedia_538.py includes real FFmpeg profile checks,
1080p/60fps downconversion, small-video non-upscaling, previous audio A1/V1
and Windows reliability tests.
