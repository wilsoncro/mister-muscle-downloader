"""Native compact two-track editing timeline for the existing Mister Muscle GUI.
Waveform is derived from local audio using ffmpeg; remote sources show an unloaded track.
"""
import array, json, shutil, subprocess, sys, tempfile, os, threading
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QThread, QSettings
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QImage
from PySide6.QtWidgets import QWidget, QSizePolicy

# Keep bundled Windows command-line tools invisible while preserving stderr and
# exit codes for existing timeline error handling. On macOS/Linux do not alter
# subprocess behavior.
_NO_CONSOLE = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


def _preview_temp_root():
    """Use a user-writable directory, never Program Files, for online previews."""
    if sys.platform == 'win32':
        # Frozen installers normally start in C:\Program Files. Child processes
        # must not use that protected folder for their scratch files.
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
        root = base / 'MisterMuscleQt' / 'preview_temp'
        root.mkdir(parents=True, exist_ok=True)
        return str(root)
    return tempfile.gettempdir()


def _preview_process_env(directory):
    """Use a persistent writable scratch folder for external helper processes.

    TEMP/TMP must NOT point into the per-download directory: yt-dlp may spawn
    additional helpers that still need scratch files after a preview task ends.
    The persistent root survives cancellation and rapid Light/Smart/Full changes.
    The *output* directory stays unique for each worker (its cwd/--paths).
    """
    root = _preview_temp_root()
    env = os.environ.copy()
    env.update({'TEMP': root, 'TMP': root, 'TMPDIR': root})
    return env


def _tools_dir():
    """Locate external tools next to the real executable in PyInstaller builds.

    In --onedir packages __file__ points into _internal, while build_qt.py
    installs yt-dlp.exe/FFmpeg in <install folder>/tools.
    """
    root = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    return root / 'tools'


def _yt_dlp_command():
    """Never re-launch the frozen GUI executable to run yt-dlp.

    Previously two timeline preview workers fell back to
    [sys.executable, '-m', 'yt_dlp'], opening two extra GUI windows.
    """
    executable = _tools_dir() / ('yt-dlp.exe' if sys.platform == 'win32' else 'yt-dlp')
    if executable.is_file():
        return [str(executable)]
    if getattr(sys, 'frozen', False):
        raise FileNotFoundError('Bundled yt-dlp executable not found: ' + str(executable))
    return [sys.executable, '-m', 'yt_dlp']

class WaveformWorker(QThread):
    ready = Signal(float, object, object)
    error = Signal(str)
    def __init__(self, source):
        super().__init__(); self.source=str(source)
        self._stop_requested=threading.Event()
        self.process=None
    def stop(self):
        self._stop_requested.set()
        process=self.process
        if process and process.poll() is None:
            try: process.terminate()
            except OSError: pass
    def run(self):
        tool_dir=Path(sys.executable).resolve().parent/'tools'
        local_dir=Path(__file__).resolve().parent/'tools'
        def find_tool(name):
            for folder in (local_dir,tool_dir):
                candidate=folder/(name+'.exe' if sys.platform=='win32' else name)
                if candidate.is_file():return str(candidate)
            return shutil.which(name)
        ffmpeg=find_tool('ffmpeg'); ffprobe=find_tool('ffprobe')
        if not ffmpeg:
            self.error.emit('FFmpeg not found. Put ffmpeg.exe in the app tools folder or add FFmpeg to PATH.')
            return
        try:
            duration=0.0
            if ffprobe:
                p=subprocess.run([ffprobe,'-v','error','-show_entries','format=duration','-of','json',self.source],capture_output=True,timeout=20,**_NO_CONSOLE)
                if p.returncode == 0:
                    duration=float(json.loads(p.stdout)['format']['duration'])
            if not 0<duration<86400:
                self.error.emit('Cannot read video duration. Check that the file is playable and ffprobe is installed.')
                return
            # Decode the COMPLETE soundtrack, including recordings longer than
            # 15 minutes. Adaptive sampling keeps the buffer bounded while the
            # resulting 800 envelope points cover 0..duration without gaps.
            # For long media, fewer audio samples per second are sufficient for
            # a visual overview; this does not alter any exported audio.
            rate=max(80,min(2000,round(180000.0/duration)))
            # Keep the decoding process cancellable when a new source is pasted.
            command=[ffmpeg,'-v','error','-nostdin','-i',self.source,
                     '-vn','-ac','1','-ar',str(rate),'-f','s16le','pipe:1']
            if self._stop_requested.is_set():return
            self.process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**_NO_CONSOLE)
            try:
                audio_data,err=self.process.communicate(timeout=360)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.communicate()
                raise
            returncode=self.process.returncode
            self.process=None
            if self._stop_requested.is_set():return
            if returncode:
                self.error.emit('FFmpeg audio extraction failed: '+err.decode('utf-8','replace')[-350:])
                return
            samples=array.array('h');samples.frombytes(audio_data[:len(audio_data)//2*2])
            if not samples:
                self.error.emit('No decoded audio samples. This video may have no audio track.')
                return
            step=max(1,len(samples)//700)
            peaks=[min(1.,max(abs(v) for v in samples[i:i+step])/32768.) for i in range(0,len(samples),step)]
            # Extract only a small bounded set of thumbnail frames. Each frame is
            # generated independently, avoiding an entire-video decode buffer.
            thumbs=[]
            audio_extensions={'.mp3','.m4a','.wav','.flac','.opus','.ogg','.aac','.wma'}
            audio_only=(Path(self.source).parent.name.startswith('mm_wave_')
                        or Path(self.source).suffix.lower() in audio_extensions)
            for i in range(0 if audio_only else 10):
                if self._stop_requested.is_set():return
                at=max(0.,(i+.5)*duration/10)
                try:
                    frame=subprocess.run([ffmpeg,'-v','error','-nostdin','-ss',str(at),'-i',self.source,
                        '-frames:v','1','-vf','scale=128:72:force_original_aspect_ratio=decrease',
                        '-f','image2pipe','-vcodec','mjpeg','pipe:1'],capture_output=True,timeout=8,**_NO_CONSOLE)
                    thumbs.append(frame.stdout if frame.returncode==0 else b'')
                except (OSError,subprocess.TimeoutExpired):thumbs.append(b'')
            if not self._stop_requested.is_set():
                self.ready.emit(duration,peaks[:800],thumbs)
        except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as exc:
            if not self._stop_requested.is_set():
                self.error.emit('Waveform analysis error: '+str(exc))

class RemoteAudioWorker(QThread):
    """Fetch audio-only media into a temporary directory; never the full video stream."""
    ready = Signal(str)
    error = Signal(str)
    def __init__(self, url, mode="Smart"):
        super().__init__(); self.url=url; self.mode=mode; self.temp=None; self.process=None; self._handed_off=False
        self._stop_requested=threading.Event()
    def run(self):
        # Retry once on a transient missing-file error. A new job directory
        # avoids reusing a partially written output after a failed transfer.
        for attempt in range(2):
            if self._stop_requested.is_set(): return
            try:
                self.temp=tempfile.TemporaryDirectory(prefix='mm_wave_', dir=_preview_temp_root(), ignore_cleanup_errors=True)
                folder=Path(self.temp.name)
                folder.mkdir(parents=True,exist_ok=True)
                tools=_tools_dir()
                cmd=_yt_dlp_command()
                ffmpeg=tools/'ffmpeg.exe'
                if ffmpeg.is_file(): cmd+=['--ffmpeg-location',str(tools)]
                # Put the output and yt-dlp's own temporary media files in
                # explicit writable folders, never the installation directory.
                # Use a relative template rather than a Windows absolute path.
                cmd+=['--no-playlist','--no-part','--no-overwrites','--no-progress',
                      '--socket-timeout','15','--retries','2','--max-filesize','500M',
                      '-N',('4' if attempt==0 else '1'), '-f','worstaudio/bestaudio/best',
                      '-P',str(folder), '-P','temp:'+str(folder),
                      '-o','audio.%(ext)s', '--',self.url]
                if self._stop_requested.is_set():return
                self.process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                                              cwd=str(folder),env=_preview_process_env(str(folder)),**_NO_CONSOLE)
                if self._stop_requested.is_set():self.stop()
                try: _,err=self.process.communicate(timeout=600)
                except subprocess.TimeoutExpired:
                    self.process.kill();self.process.communicate()
                    raise RuntimeError('Audio preview timed out while loading the complete soundtrack')
                if self._stop_requested.is_set():return
                if self.process.returncode:
                    detail=err.decode('utf-8','replace')[-600:].strip()
                    if attempt==0 and ('[Errno 2]' in detail or 'No such file or directory' in detail):
                        self.process=None
                        try:self.temp.cleanup()
                        except PermissionError:pass  # Windows may still hold a yt-dlp fragment briefly.
                        self.temp=None
                        continue
                    raise RuntimeError('Audio preview unavailable: '+detail)
                paths=[f for f in folder.iterdir() if f.is_file() and f.stat().st_size>0]
                if not paths:raise RuntimeError('Audio stream was not downloaded')
                self.ready.emit(str(max(paths,key=lambda f:f.stat().st_size)))
                return
            except Exception as exc:
                if not self._stop_requested.is_set():self.error.emit(str(exc))
                return
            finally:
                # On success the GUI owns cleanup until waveform extraction ends.
                # On failure _remote_finished() will clean the last directory.
                self.process=None
    def stop(self):
        self._stop_requested.set()
        if self.process and self.process.poll() is None:
            try:self.process.terminate()
            except OSError:pass
    def cleanup(self):
        if self.temp:
            try:self.temp.cleanup()
            except PermissionError:pass  # Never treat a locked scratch file as a playback error.
            self.temp=None

class RemoteThumbnailWorker(QThread):
    """Fetch a small low-resolution video representation, then extract a few frames.
    Optional and bounded; does not block the main GUI or the audio worker.
    """
    ready = Signal(object)
    error = Signal(str)
    def __init__(self, url, mode='Smart'):
        super().__init__(); self.url=url; self.mode=mode; self.process=None
        self._stop_requested=threading.Event()
    def stop(self):
        self._stop_requested.set()
        if self.process and self.process.poll() is None:
            try:self.process.terminate()
            except OSError:pass
    def run(self):
        with tempfile.TemporaryDirectory(prefix='mm_v1_', dir=_preview_temp_root(), ignore_cleanup_errors=True) as directory:
            try:
                tools=_tools_dir()
                cmd=_yt_dlp_command()
                # Avoid high-quality full video; cap total transfer and bandwidth.
                # YouTube's current signature challenge can require yt-dlp's EJS
                # component. Opt in explicitly; without it some video formats
                # are not exposed even though audio-only extraction succeeds.
                cmd+=['--remote-components','ejs:github']
                deno=next((str(x) for x in (tools/'deno.exe',Path(sys.executable).resolve().parent/'tools'/'deno.exe') if x.is_file()),None) or shutil.which('deno')
                if deno:
                    cmd+=['--js-runtimes',f'deno:{deno}']
                # Thumbnail previews do not need an audio stream or HD video.
                # Prefer low-resolution video-only; fall back to muxed sources
                # when sites expose no separate video stream. The final user
                # download format/quality is unaffected by this preview choice.
                preview_format = (
                    'bestvideo[height<=240]/best[height<=240]/worst[height<=360]/best'
                    if self.mode == 'Smart' else
                    'bestvideo[height<=360]/best[height<=360]/worst[height<=360]/best'
                )
                cmd+=['--no-playlist','--no-part','--no-progress','--socket-timeout','12',
                      '--retries','2','--max-filesize',('100M' if self.mode=='Smart' else '200M'),
                      '-N','4','-f',preview_format,
                      '-P',directory, '-P','temp:'+directory,
                      '-o','video.%(ext)s','--',self.url]
                if self._stop_requested.is_set():return
                self.process=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,
                                              cwd=directory, env=_preview_process_env(directory),**_NO_CONSOLE)
                if self._stop_requested.is_set():self.stop()
                try:_,err=self.process.communicate(timeout=300 if self.mode=='Smart' else 360)
                except subprocess.TimeoutExpired:
                    self.stop();self.process.kill();self.process.communicate();self.error.emit('Video preview timed out');return
                if self._stop_requested.is_set():return
                if self.process.returncode:
                    detail=err.decode('utf-8','replace')[-850:].strip()
                    if 'remote-components' in detail or 'ejs:github' in detail:
                        detail += ' | Check yt-dlp update, Deno runtime and network access to GitHub.'
                    self.error.emit('Video preview unavailable: '+detail);return
                files=[f for f in Path(directory).iterdir() if f.is_file() and f.stat().st_size>0]
                if not files:self.error.emit('No preview video file received');return
                path=str(max(files,key=lambda f:f.stat().st_size))
                ffmpeg=next((str(x) for x in (tools/'ffmpeg.exe',Path(sys.executable).resolve().parent/'tools'/'ffmpeg.exe') if x.is_file()),None) or shutil.which('ffmpeg')
                ffprobe=next((str(x) for x in (tools/'ffprobe.exe',Path(sys.executable).resolve().parent/'tools'/'ffprobe.exe') if x.is_file()),None) or shutil.which('ffprobe')
                if not ffmpeg or not ffprobe:self.error.emit('FFmpeg/FFprobe not found for video frames');return
                probe=subprocess.run([ffprobe,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',path],capture_output=True,timeout=15,**_NO_CONSOLE)
                duration=float(probe.stdout.strip())
                if duration<=0:self.error.emit('Could not determine preview video duration');return
                count=6 if self.mode=='Smart' else 12
                frames=[]
                for i in range(count):
                    if self._stop_requested.is_set():return
                    at=(i+.5)*duration/count
                    proc=subprocess.run([ffmpeg,'-v','error','-nostdin','-ss',str(at),'-i',path,'-frames:v','1','-vf','scale=128:72:force_original_aspect_ratio=decrease','-f','image2pipe','-vcodec','mjpeg','pipe:1'],capture_output=True,timeout=10,**_NO_CONSOLE)
                    frames.append(proc.stdout if proc.returncode==0 else b'')
                if not self._stop_requested.is_set():self.ready.emit(frames)
            except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
                if not self._stop_requested.is_set():self.error.emit(str(exc))

class ProTimeline(QWidget):
    rangeChanged=Signal(float,float)
    seekRequested=Signal(float)
    togglePlaybackRequested=Signal()
    selectionsChanged=Signal(object)
    audioRangeChanged=Signal(float,float)
    audioSelectionsChanged=Signal(object)
    trackLinkChanged=Signal(bool)
    def __init__(self,parent=None):
        super().__init__(parent);self.setMinimumHeight(192);self.setMaximumHeight(230)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.duration=60.;self.start=0.;self.end=10.;self.audio_start=0.;self.audio_end=10.;self.audio_linked=True;self.playhead=0.;self.zoom=1.
        self.wave=[];self.thumbs=[];self.wave_status='Waveform requires decoded audio; online YouTube playback alone does not provide audio samples';self.source_label='No source loaded';self.worker=None;self._workers=[];self._remote_workers=[];self._remote_active=None;self._drag=None;self.offset=0.
        self._clipboard_range=None;self._undo=[];self._redo=[]
        self.selections=[];self.audio_selections=[];self._select_anchor=None;self._audio_drag_anchor=None
        self.mode=QSettings('MisterMuscle','Downloader').value('timeline_mode','Smart');self._thumbnail_workers=[];self._thumbnail_active=None;self.video_status='Video thumbnails not loaded';self._remote_duration=None
        if self.mode not in ('Light','Smart','Full'):self.mode='Smart'
        self._current_remote_url=None
        self.wave_duration=0.0
        self._wave_cache={};self._thumb_cache={}
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip('V1 purple markers = video • A1 turquoise markers = audio • Drag A1 independently • Shift+drag to save clips')
        self.rangeChanged.connect(self._video_changed)
    def set_mode(self, mode):
        if mode not in ('Light','Smart','Full') or mode==self.mode:return
        self.mode=mode
        QSettings('MisterMuscle','Downloader').setValue('timeline_mode',mode)
        # Apply a changed loading profile immediately, not only to the next URL.
        if self._current_remote_url:
            # Keep both track ranges and audio clip marks on preview-mode changes.
            audio_state=(self.audio_start,self.audio_end,self.audio_linked,list(self.audio_selections))
            # Keep all user clip marks when only the preview quality changes.
            state=(self.duration,self.start,self.end,self.playhead,self.zoom,
                   self.offset,list(self.selections))
            self.set_remote_source(self._current_remote_url)
            self.duration,self.start,self.end,self.playhead,self.zoom,self.offset,_=state
            self.selections=state[-1]
            self.selectionsChanged.emit(list(self.selections))
            self.audio_start,self.audio_end,self.audio_linked,self.audio_selections=audio_state
            self.audioRangeChanged.emit(self.audio_start,self.audio_end)
            self.audioSelectionsChanged.emit(list(self.audio_selections))
            self.trackLinkChanged.emit(self.audio_linked)
            self.update()

    @staticmethod
    def _cache_set(cache, key, value):
        if key in cache:cache.pop(key)
        cache[key]=value
        while len(cache)>5:cache.pop(next(iter(cache)))

    def stop_background_tasks(self, wait_ms=0):
        """Signal cancellation; keep QThread references until finished callbacks run."""
        for worker in [*self._workers,*self._remote_workers,*self._thumbnail_workers]:
            if worker.isRunning() and hasattr(worker,'stop'):
                worker.stop()
        if wait_ms:
            # At shutdown only: avoid QThread: Destroyed while thread is still running.
            for worker in [*self._workers,*self._remote_workers,*self._thumbnail_workers]:
                if worker.isRunning():worker.wait(wait_ms)
        return not any(w.isRunning() for w in [*self._workers,*self._remote_workers,*self._thumbnail_workers])

    def set_remote_source(self, url):
        self.set_source('Online audio preview')
        self._current_remote_url=url
        cached_wave=self._wave_cache.get(url)
        cached_thumbs=self._thumb_cache.get((url,self.mode))
        if self.mode == 'Smart' and cached_thumbs is None:
            # Full has 12 evenly spaced frames. Every other frame gives a
            # sufficient 6-frame Smart preview, with zero additional traffic.
            full_frames=self._thumb_cache.get((url,'Full'))
            if full_frames and len(full_frames)>=12:
                cached_thumbs=full_frames[1::2]
                self._cache_set(self._thumb_cache,(url,'Smart'),cached_thumbs)
        self.wave_status='Loading audio preview…' if cached_wave is None else ''
        self.video_status=('Video thumbnails disabled in Light mode' if self.mode=='Light'
                           else 'Loading video frames…' if cached_thumbs is None else 'Video thumbnails ready')
        if cached_wave is not None:
            self.duration,self.wave=cached_wave
            self.wave_duration=self.duration
            self.wave_status=''
            # A cached waveform has the same full-length selection semantics.
            if self.start==0. and self.end==10. and not self.selections:
                self.end=self.duration
                self.rangeChanged.emit(self.start,self.end)
            else:
                self.end=min(self.end,self.duration)
            self._video_changed(self.start,self.end)
        if cached_thumbs is not None:
            self.thumbs=[QImage.fromData(frame) for frame in cached_thumbs]
        self.update()
        if self.mode!='Light' and cached_thumbs is None:
            thumbs=RemoteThumbnailWorker(url,self.mode);self._thumbnail_active=thumbs
            self._thumbnail_workers.append(thumbs)
            thumbs.ready.connect(lambda frames,w=thumbs:self._remote_thumbnails_ready(w,frames))
            thumbs.error.connect(lambda message,w=thumbs:self._remote_thumbnails_error(w,message))
            thumbs.finished.connect(lambda w=thumbs:self._thumbnail_workers.remove(w) if w in self._thumbnail_workers else None)
            thumbs.start()
        if cached_wave is None:
            remote=RemoteAudioWorker(url,self.mode);self._remote_active=remote
            self._remote_workers.append(remote)
            remote.ready.connect(lambda path,w=remote:self._remote_ready(w,path))
            remote.error.connect(lambda message,w=remote:self._remote_error(w,message))
            remote.finished.connect(lambda w=remote:self._remote_finished(w))
            remote.start()

    def _remote_thumbnails_error(self,worker,message):
        if worker is self._thumbnail_active:
            self.video_status='V1: '+message[:160];self.update()

    def _remote_thumbnails_ready(self,worker,frames):
        if worker is not self._thumbnail_active:return
        self.thumbs=[QImage.fromData(b) for b in frames]
        if any(not im.isNull() for im in self.thumbs):
            self._cache_set(self._thumb_cache,(worker.url,worker.mode),frames)
        self.video_status='Video thumbnails ready' if any(not im.isNull() for im in self.thumbs) else 'Video frames could not be decoded'
        self.update()

    def _remote_ready(self,remote,path):
        if remote is not self._remote_active:return
        remote._handed_off=True
        self.wave_status='Generating waveform from online audio…';self.update()
        worker=WaveformWorker(path);self.worker=worker;self._workers.append(worker)
        worker.ready.connect(lambda duration,peaks,thumbs,w=worker:self._wave_ready(w,duration,peaks,thumbs))
        worker.error.connect(lambda message,w=worker:self._wave_error(w,message))
        worker.finished.connect(lambda w=worker,r=remote:self._wave_finished(w,r))
        worker.start()

    def _wave_finished(self,worker,remote):
        if worker in self._workers:self._workers.remove(worker)
        remote.cleanup()

    def _remote_error(self,remote,message):
        if remote is self._remote_active:
            self.wave_status=message;self.update()

    def _remote_finished(self,remote):
        if remote in self._remote_workers:self._remote_workers.remove(remote)
        # On error, no waveform worker owns the temporary directory.
        if not remote._handed_off:
            remote.cleanup()

    def set_source(self,label,local_path=None):
        self.stop_background_tasks()
        self.selections=[];self.selectionsChanged.emit([])
        self.audio_selections=[];self.audioSelectionsChanged.emit([])
        self.audio_linked=True;self.trackLinkChanged.emit(True)
        self.audio_start=0.;self.audio_end=10.;self.audioRangeChanged.emit(0.,10.)
        self._current_remote_url=None
        self._remote_active=None;self._thumbnail_active=None
        self.worker=None;self.source_label=label;self.wave=[];self.wave_duration=0.;self.thumbs=[];self.video_status='Analyzing video frames…' if local_path else 'No video frames';self.wave_status='Waveform requires decoded audio; online YouTube playback alone does not provide audio samples';self.offset=0.;self.duration=60.;self.start=0.;self.end=10.;self.playhead=0.;self.update()
        if local_path and Path(local_path).is_file():
            self.wave_status='Analyzing audio…';worker=WaveformWorker(local_path);self.worker=worker
            self._workers.append(worker)
            worker.finished.connect(lambda w=worker:self._workers.remove(w) if w in self._workers else None)
            worker.ready.connect(lambda duration,peaks,thumbs,w=worker:self._wave_ready(w,duration,peaks,thumbs))
            worker.error.connect(lambda message,w=worker:self._wave_error(w,message))
            worker.start()
    def _wave_error(self,worker,message):
        if worker is not self.worker:return
        self.wave_status=message;self.update()
    def _wave_ready(self,worker,duration,peaks,thumbs):
        if worker is not self.worker:return
        self.duration=duration;self.wave=peaks;self.wave_duration=duration
        self.wave_status='No audio samples detected' if not peaks else ''
        if self._remote_active is not None and peaks:
            self._cache_set(self._wave_cache,self._remote_active.url,(duration,peaks))
        # Audio-only online previews must never overwrite independently loaded V1 frames.
        if thumbs and any(thumbs) and self._remote_active is None:
            self.thumbs=[QImage.fromData(b) for b in thumbs]
        # For a newly loaded source the initial 00:00:10 is just a placeholder.
        # Make the full media range selectable once duration is known, unless
        # the user has already changed the markers or saved selections.
        if self.start==0. and self.end==10. and not self.selections:
            self.end=duration
            self.rangeChanged.emit(self.start,self.end)
        else:
            self.end=min(self.end,duration)
        self._video_changed(self.start,self.end)
        self.update()
    def _video_changed(self,start,end):
        if self.audio_linked:
            self.audio_start=float(start)
            self.audio_end=float(end)
            self.audioRangeChanged.emit(self.audio_start,self.audio_end)
            self.update()
    def set_tracks_linked(self,linked):
        linked=bool(linked)
        if self.audio_linked==linked:return
        self.audio_linked=linked
        if linked:self._video_changed(self.start,self.end)
        self.trackLinkChanged.emit(linked)
        self.update()
    def set_audio_range(self,start,end,unlink=True):
        if unlink and self.audio_linked:self.set_tracks_linked(False)
        self.audio_start=max(0.,min(float(start),self.duration))
        self.audio_end=max(self.audio_start,min(float(end),self.duration))
        self.audioRangeChanged.emit(self.audio_start,self.audio_end)
        self.update()
    def set_range(self,start,end):
        self.start=max(0.,min(float(start),self.duration))
        self.end=max(self.start,min(float(end),self.duration))
        self._video_changed(self.start,self.end)
        self.update()
    def set_zoom(self,zoom):
        self.zoom=max(1.,min(16.,float(zoom)))
        self.offset=min(self.offset,max(0.,self.duration-self.duration/self.zoom))
        self.update()
    def set_playhead(self,seconds):
        self.playhead=max(0.,min(self.duration,float(seconds)))
        self.update()
    def scroll_time(self,seconds):
        self.offset=max(0.,min(float(seconds),max(0.,self.duration-self.duration/self.zoom)))
        self.update()
    def step_frames(self, count, fps=30):
        """Frame-sized timeline seek; actual precision depends on the source/player."""
        self.set_playhead(self.playhead + count / fps)
        self.seekRequested.emit(self.playhead)

    def _remember(self):
        self._undo.append((self.start,self.end));self._undo=self._undo[-50:];self._redo.clear()
    def split_at_playhead(self):
        # Preserve BOTH halves as saved clips; the original media is untouched.
        # The left half remains selected, and Export all clips writes both halves.
        if self.start + .03 < self.playhead < self.end - .03:
            self._remember()
            a,t,b=self.start,self.playhead,self.end
            for item in ((a,t),(t,b)):
                if not any(abs(item[0]-x)<.03 and abs(item[1]-y)<.03 for x,y in self.selections):
                    self.selections.append(item)
            self.end=t
            self.selectionsChanged.emit(list(self.selections))
            self.rangeChanged.emit(self.start,self.end)
            self.update()
    def split_audio_at_playhead(self):
        if self.audio_start+.03<self.playhead<self.audio_end-.03:
            a,t,b=self.audio_start,self.playhead,self.audio_end
            for item in ((a,t),(t,b)):
                if not any(abs(item[0]-x)<.03 and abs(item[1]-y)<.03 for x,y in self.audio_selections):
                    self.audio_selections.append(item)
            self.set_audio_range(a,t)
            self.audioSelectionsChanged.emit(list(self.audio_selections))
            self.update()
    def add_audio_selection(self):
        a,b=self.audio_start,self.audio_end
        if b-a<.03:return
        if not any(abs(a-x)<.03 and abs(b-y)<.03 for x,y in self.audio_selections):
            self.audio_selections.append((a,b))
            self.audioSelectionsChanged.emit(list(self.audio_selections))
            self.update()
    def remove_last_audio_selection(self):
        if self.audio_selections:
            self.audio_selections.pop()
            self.audioSelectionsChanged.emit(list(self.audio_selections))
            self.update()
    def clear_audio_selections(self):
        self.audio_selections.clear()
        self.audioSelectionsChanged.emit([])
        self.update()

    def copy_range(self):
        self._clipboard_range=(self.start,self.end)
    def paste_range(self):
        if self._clipboard_range:
            self._remember();self.set_range(*self._clipboard_range)
            self.rangeChanged.emit(self.start,self.end)
    def undo_range(self):
        if self._undo:
            self._redo.append((self.start,self.end));self.set_range(*self._undo.pop())
            self.rangeChanged.emit(self.start,self.end)
    def redo_range(self):
        if self._redo:
            self._undo.append((self.start,self.end));self.set_range(*self._redo.pop())
            self.rangeChanged.emit(self.start,self.end)

    def add_selection(self):
        """Save current IN/OUT as an independent non-destructive clip selection."""
        a,b=sorted((self.start,self.end))
        if b-a<0.03:return
        if not any(abs(a-x)<.03 and abs(b-y)<.03 for x,y in self.selections):
            # Preserve insertion order: Remove last must remove the most recently added clip.
            self.selections.append((a,b))
            self.selectionsChanged.emit(list(self.selections));self.update()

    def remove_last_selection(self):
        if self.selections:
            self.selections.pop();self.selectionsChanged.emit(list(self.selections));self.update()

    def clear_selections(self):
        self.selections.clear();self.selectionsChanged.emit([]);self.update()

    def keyPressEvent(self,event):
        mods=event.modifiers()
        ctrl=bool(mods & Qt.ControlModifier)
        if ctrl and event.key()==Qt.Key_Return:self.add_selection();event.accept();return
        if ctrl and event.key()==Qt.Key_Backspace:self.clear_selections();event.accept();return
        if event.key()==Qt.Key_M:self.add_selection();event.accept();return
        if event.key()==Qt.Key_Delete:self.remove_last_selection();event.accept();return
        if ctrl and event.key()==Qt.Key_X:self.split_at_playhead();event.accept();return
        if ctrl and event.key()==Qt.Key_C:self.copy_range();event.accept();return
        if ctrl and event.key()==Qt.Key_V:self.paste_range();event.accept();return
        if ctrl and event.key()==Qt.Key_Z:self.undo_range();event.accept();return
        if ctrl and event.key()==Qt.Key_Y:self.redo_range();event.accept();return
        if event.key()==Qt.Key_Space:self.togglePlaybackRequested.emit();event.accept();return
        if event.key()==Qt.Key_Left:
            self.step_frames(-1);event.accept();return
        if event.key()==Qt.Key_Right:
            self.step_frames(1);event.accept();return
        if event.key()==Qt.Key_I:
            self._remember();self.start=min(self.playhead,self.end);self.rangeChanged.emit(self.start,self.end);self.update();return
        if event.key()==Qt.Key_O:
            self._remember();self.end=max(self.playhead,self.start);self.rangeChanged.emit(self.start,self.end);self.update();return
        super().keyPressEvent(event)

    def wheelEvent(self,event):
        if event.modifiers() & Qt.ControlModifier:
            self.set_zoom(self.zoom*(1.2 if event.angleDelta().y()>0 else 1/1.2))
        else:
            self.scroll_time(self.offset-(event.angleDelta().y()/120)*self.duration/self.zoom/8)
        event.accept()
    def _rect(self):return QRectF(78,31,max(1,self.width()-92),142)
    def _time(self,x):
        r=self._rect();return max(0.,min(self.duration,self.offset+(x-r.left())/r.width()*self.duration/self.zoom))
    def _x(self,t):
        r=self._rect();return r.left()+(t-self.offset)/max(.01,self.duration/self.zoom)*r.width()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),QColor('#181d2e'))
        r=self._rect();p.setPen(QColor('#8c98b5'))
        for i in range(7):
            t=self.offset+i*self.duration/self.zoom/6;x=self._x(t)
            p.drawText(QPointF(x-11,20),f'{int(t//60):02}:{int(t%60):02}')
            p.setPen(QPen(QColor('#303951'),1));p.drawLine(QPointF(x,28),QPointF(x,175));p.setPen(QColor('#8c98b5'))
        for top,h,label,color in [(34,61,'V1  VIDEO','#51438b'),(103,65,'A1  AUDIO','#155e62')]:
            p.fillRect(QRectF(4,top,68,h),QColor('#252c41'))
            p.setPen(QColor('#dce4f5'));p.drawText(QRectF(9,top+5,62,20),Qt.AlignLeft,label)
            p.fillRect(QRectF(r.left(),top,r.width(),h),QColor(color))
        # Real extracted thumbnails, if a local source has been indexed.
        if self.thumbs:
            p.save();p.setClipRect(QRectF(r.left(),35,r.width(),59))
            for i,img in enumerate(self.thumbs):
                if img.isNull():continue
                center=(i+.5)*self.duration/max(1,len(self.thumbs))
                x=self._x(center);width=max(28.,self.duration/max(1,len(self.thumbs)) / (self.duration/self.zoom)*r.width())
                p.drawImage(QRectF(x-width/2,36,width,57),img)
            p.restore()
        p.setPen(QColor('#c4b5fd'))
        if not any(not im.isNull() for im in self.thumbs):
            p.drawText(QRectF(r.left()+8,65,r.width()-12,22),Qt.AlignLeft,self.video_status[:85])
        p.drawText(QRectF(r.left()+8,40,r.width()-12,20),Qt.AlignLeft,self.source_label[:65])
        if self.wave:
            # Map envelope samples evenly over the complete soundtrack.
            # The entire A1 track stays populated even for multi-hour sources.
            p.save();p.setClipRect(QRectF(r.left(),104,r.width(),62))
            p.setPen(QPen(QColor('#6ce2d1'),1.5))
            count=len(self.wave)
            span=self.wave_duration or self.duration
            for i,peak in enumerate(self.wave):
                t=(i+.5)*span/count
                x=self._x(t)
                if x<r.left()-1 or x>r.right()+1:continue
                amp=peak*24
                p.drawLine(QPointF(x,134-amp),QPointF(x,134+amp))
            p.restore()
        else:
            p.setPen(QColor('#9abbbf'));p.drawText(QRectF(r.left()+8,118,r.width()-12,28),Qt.AlignLeft,self.wave_status)
        # Each track has independent highlighted selections and IN/OUT handles.
        p.save()
        p.setClipRect(QRectF(r.left(),34,r.width(),61))
        for i,(a,b) in enumerate(self.selections):
            xa,xb=self._x(a),self._x(b)
            if xb<r.left() or xa>r.right():continue
            p.fillRect(QRectF(xa,34,max(1,xb-xa),61),QColor(170,139,250,70))
            p.setPen(QColor('#ebddff'))
            p.drawText(QRectF(xa+3,73,max(15,xb-xa-5),18),Qt.AlignLeft,str(i+1))
        p.restore()
        p.save()
        p.setClipRect(QRectF(r.left(),103,r.width(),65))
        for i,(a,b) in enumerate(self.audio_selections):
            xa,xb=self._x(a),self._x(b)
            if xb<r.left() or xa>r.right():continue
            p.fillRect(QRectF(xa,103,max(1,xb-xa),65),QColor(55,235,215,66))
            p.setPen(QColor('#e0fff9'))
            p.drawText(QRectF(xa+3,145,max(15,xb-xa-5),18),Qt.AlignLeft,str(i+1))
        p.restore()
        vx1,vx2=self._x(self.start),self._x(self.end)
        ax1,ax2=self._x(self.audio_start),self._x(self.audio_end)
        p.save();p.setClipRect(QRectF(r.left(),34,r.width(),61))
        p.fillRect(QRectF(vx1,34,max(1,vx2-vx1),61),QColor(170,139,250,35))
        for x,label in ((vx1,'IN'),(vx2,'OUT')):
            if not r.left()<=x<=r.right():continue
            p.setPen(QPen(QColor('#ba9bff'),2));p.drawLine(QPointF(x,34),QPointF(x,95))
            p.setBrush(QColor('#ba9bff'));p.drawRoundedRect(QRectF(x-5,34,10,12),2,2)
            p.drawText(QRectF(x+6,47,40,16),Qt.AlignLeft,label)
        p.restore()
        p.save();p.setClipRect(QRectF(r.left(),103,r.width(),65))
        p.fillRect(QRectF(ax1,103,max(1,ax2-ax1),65),QColor(55,235,215,34))
        for x,label in ((ax1,'A IN'),(ax2,'A OUT')):
            if not r.left()<=x<=r.right():continue
            p.setPen(QPen(QColor('#4beddc'),2));p.drawLine(QPointF(x,103),QPointF(x,168))
            p.setBrush(QColor('#4beddc'));p.drawRoundedRect(QRectF(x-5,103,10,12),2,2)
            p.drawText(QRectF(x+6,111,48,17),Qt.AlignLeft,label)
        p.restore()
        p.setPen(QPen(QColor('#f5c66b'),2));px=self._x(self.playhead)
        if r.left()<=px<=r.right():
            p.drawLine(QPointF(px,28),QPointF(px,173))
            p.setBrush(QColor('#f5c66b'));p.drawRoundedRect(QRectF(px-5,24,10,9),2,2)
        p.end()
    def mousePressEvent(self,event):
        if event.button()!=Qt.LeftButton:return
        x=event.position().x();y=event.position().y()
        if 103<=y<=168:
            # A1 edits are independent even when the Link A/V toggle was on.
            self.set_tracks_linked(False)
            self._audio_drag_anchor=self._time(x)
            if event.modifiers() & Qt.ShiftModifier:
                self._drag='audio_multi'
            elif abs(x-self._x(self.audio_start))<11:
                self._drag='audio_start'
            elif abs(x-self._x(self.audio_end))<11:
                self._drag='audio_end'
            else:
                self._drag='audio_span'
            if self._drag in ('audio_start','audio_end'):self._apply(x)
            return
        if event.modifiers() & Qt.ShiftModifier:
            self._select_anchor=self._time(x);self._drag='multi';return
        self._drag='start' if abs(x-self._x(self.start))<11 else 'end' if abs(x-self._x(self.end))<11 else 'seek'
        self._apply(x)
    def mouseMoveEvent(self,event):
        if self._drag:self._apply(event.position().x())
    def mouseReleaseEvent(self,event):
        if self._drag=='multi' and self._select_anchor is not None:
            a,b=sorted((self._select_anchor,self._time(event.position().x())))
            if b-a>=.03:
                self.set_range(a,b);self.add_selection();self.rangeChanged.emit(self.start,self.end)
        elif self._drag=='audio_multi' and self._audio_drag_anchor is not None:
            a,b=sorted((self._audio_drag_anchor,self._time(event.position().x())))
            if b-a>=.03:
                self.set_audio_range(a,b)
                self.add_audio_selection()
        self._select_anchor=None;self._audio_drag_anchor=None;self._drag=None
    def _apply(self,x):
        t=self._time(x)
        if self._drag=='multi':
            self.set_range(min(self._select_anchor,t),max(self._select_anchor,t));self.rangeChanged.emit(self.start,self.end)
        elif self._drag=='start':self.start=min(t,self.end);self.rangeChanged.emit(self.start,self.end)
        elif self._drag=='end':self.end=max(t,self.start);self.rangeChanged.emit(self.start,self.end)
        elif self._drag=='audio_start':self.set_audio_range(min(t,self.audio_end),self.audio_end)
        elif self._drag=='audio_end':self.set_audio_range(self.audio_start,max(t,self.audio_start))
        elif self._drag in ('audio_span','audio_multi'):
            if self._audio_drag_anchor is not None:
                self.set_audio_range(*sorted((self._audio_drag_anchor,t)))
        else:self.playhead=t;self.seekRequested.emit(t)
        self.update()
