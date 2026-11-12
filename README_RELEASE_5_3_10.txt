Mister Muscle Downloader v5.3.10 — In-App Hotstar Login and Host-Specific Authentication

What's new
- When Inspect, Preview, or Download reports that Instagram needs an account,
  Mister Muscle offers its existing Instagram in-app sign-in window.
- When a Hotstar or JioHotstar source requires sign-in, Mister Muscle offers
  a new official-site login window inside the app.
- Users sign in on Hotstar's real website, then explicitly select "Use this
  session". This stores service cookies under their own Windows AppData.
- Authorized cookies are made available to yt-dlp only for Hotstar/JioHotstar
  requests. On successful login the original Inspect, Preview, or Download
  operation may be tried again.
- A Settings section has in-app Hotstar login, local session status and an
  option to clear locally saved credentials (cookies and browser cache).
- Provider error notices remain warnings instead of duplicate crash reports,
  but genuine errors are still reported independently per user.
- Existing Car Multimedia MP4 and A1/V1 editing functionality is unchanged.

Security and restrictions
- Passwords are never read or stored by Mister Muscle. The official login
  is rendered by Qt WebEngine in a separate profile.
- A local file may contain Hotstar authentication cookies after user consent.
  Keep your Windows user account secure, do not share the cookie file, and
  clear the session in Settings when finished.
- This does not bypass DRM, geo-restrictions, paid subscriptions or service
  access policies. Some videos cannot be downloaded even with valid login.
- Website sign-in could be restricted inside embedded browsers by the provider.

Verification
- test_hoster_login_5310.py checks provider isolation, user-initiated login
  prompt and retry, cancellation, and saved session cookie domain filtering,
  then runs earlier Hotstar, Windows and FFmpeg compatibility regressions.
- The release is published only after the GitHub Windows installer and
  portable ZIP are built and verified.
