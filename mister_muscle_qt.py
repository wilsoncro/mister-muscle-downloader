# -*- coding: utf-8 -*-
"""Mister Muscle Qt — native UI migration, phase 1.
Requires: pip install PySide6 yt-dlp
Optional: ffmpeg on PATH for merging and cutting.
"""
import os, sys, re, json, subprocess, shutil, tempfile, threading, functools, http.server, traceback, logging, urllib.request, urllib.parse, importlib.metadata, base64, platform, io
import shiboken6
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, QProcess, QUrl, QSize, QTimer, QObject, Slot, QElapsedTimer, QFile, QIODevice, QThread, Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QTextEdit,QLineEdit,QComboBox,QStackedWidget,QFrame,QScrollArea,QProgressBar,QFileDialog,
    QMessageBox,QListWidget,QListWidgetItem,QSlider,QCheckBox,QSizePolicy,QButtonGroup,QGraphicsDropShadowEffect,QPlainTextEdit,QDialog)
from PySide6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QDesktopServices, QTextCursor, QTextCharFormat, QShortcut, QKeySequence
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput,QSoundEffect
from PySide6.QtMultimediaWidgets import QVideoWidget
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
    from PySide6.QtWebChannel import QWebChannel
    WEB_ENGINE_AVAILABLE=True
except ImportError:
    WEB_ENGINE_AVAILABLE=False
from mister_muscle_original_player import _player_html
APP_VERSION = '5.2.0'
APP_REPOSITORY = 'wilsoncro/mister-muscle-downloader'
DONATE_URL = 'https://paypal.me/MrMuscle1995'  # Preserved from the original application


BASE=Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
APP_DIR=Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else BASE
TOOLS_DIR=APP_DIR/'tools'
if getattr(sys, 'frozen', False):
    os.environ['PATH']=str(TOOLS_DIR)+os.pathsep+os.environ.get('PATH','')
YTDLP_EXE=str(TOOLS_DIR/'yt-dlp.exe') if getattr(sys, 'frozen', False) else sys.executable
def ytdlp_args(args):
    return args[2:] if getattr(sys, 'frozen', False) and args[:2]==['-m','yt_dlp'] else args
DATA=Path(os.environ.get('APPDATA',str(Path.home()))) / 'MisterMuscleQt'
DATA.mkdir(parents=True,exist_ok=True)
HISTORY=DATA/'history.json'
SESSION=DATA/'session.json'
LOG_FILE=DATA/'status.log'
WHATS_NEW_MARKER=DATA/'last_whats_new_version.txt'
LANGUAGE_FILE=DATA/'language.json'
try:
    APP_LANGUAGE=json.loads(LANGUAGE_FILE.read_text(encoding='utf-8')).get('language','en')
except (OSError,ValueError,AttributeError):
    APP_LANGUAGE='en'
if APP_LANGUAGE not in ('en','hr'): APP_LANGUAGE='en'
UI_HR={'New Download': 'Novo preuzimanje', 'Download Center': 'Centar preuzimanja', 'Queue': 'Red čekanja', 'History': 'Povijest', 'Settings': 'Postavke', 'Status Log': 'Dnevnik događaja', 'Player & Cutting': 'Player i rezanje', 'File type': 'Vrsta datoteke', 'Resolution': 'Rezolucija', 'Video container': 'Videoformat', 'Clip aspect ratio': 'Omjer slike isječka', 'Save to': 'Spremi u', 'Change folder': 'Promijeni mapu', 'Video links': 'Poveznice na videozapise', 'Paste': 'Zalijepi', 'Clear': 'Očisti', 'Inspect': 'Provjeri', 'Cancel': 'Odustani', 'Open folder': 'Otvori mapu', 'Open log folder': 'Otvori mapu dnevnika', 'Copy log': 'Kopiraj dnevnik', 'Save log as…': 'Spremi dnevnik kao…', 'Clear log': 'Očisti dnevnik', 'All events': 'Svi događaji', 'Errors only': 'Samo pogreške', 'Warnings + errors': 'Upozorenja i pogreške', 'Ready for a new download': 'Spremno za novo preuzimanje', 'Everything ready? Start your download.': 'Sve je spremno? Pokrenite preuzimanje.', 'Start / Resume': 'Pokreni / Nastavi', 'Remove selected': 'Ukloni odabrano', 'Move up': 'Pomakni gore', 'Move down': 'Pomakni dolje', 'Clear pending': 'Očisti čekanje', 'Play selected': 'Reproduciraj odabrano', 'Open selected folder': 'Otvori odabranu mapu', 'Download folder': 'Mapa za preuzimanja', 'Change download folder': 'Promijeni mapu preuzimanja', 'Check for updates now': 'Provjeri ažuriranja', 'Update check will start shortly…': 'Provjera ažuriranja uskoro će započeti…', 'Ready to cut': 'Spremno za rezanje', 'From': 'Od', 'To': 'Do', 'Open local video': 'Otvori lokalni video', 'Open video': 'Otvori video', 'Open last download': 'Otvori posljednje preuzimanje', 'Open original advanced player / tools': 'Otvori izvorni napredni player / alate', 'Completed': 'Dovršeno', 'Downloading': 'Preuzimanje', 'Pending': 'Na čekanju', 'Failed': 'Neuspješno', 'All': 'Sve', 'Retry': 'Pokušaj ponovno', 'Remove': 'Ukloni', 'Play': 'Reproduciraj', 'Copy link': 'Kopiraj poveznicu', 'Pause': 'Pauziraj', 'Resume': 'Nastavi', 'Start queue': 'Pokreni red čekanja', 'Clear failed': 'Očisti neuspjele', 'Search downloads...': 'Pretraži preuzimanja...', 'Video + audio': 'Video + zvuk', 'Video only': 'Samo video', 'Audio only': 'Samo zvuk', 'Best available': 'Najbolja dostupna', 'Original': 'Izvorno', 'Clip export active': 'Izvoz isječka u tijeku', 'Preview active': 'Pregled je aktivan', 'Remote cut active': 'Udaljeno rezanje u tijeku', 'Missing links': 'Nedostaju poveznice', 'Paste at least one link first.': 'Najprije zalijepite barem jednu poveznicu.', 'Invalid range': 'Neispravan raspon', 'FFmpeg missing': 'Nedostaje FFmpeg', 'No local video': 'Nema lokalnog videa', 'Open a local video in Media Studio first.': 'Najprije otvorite lokalni video u Media Studiju.', 'Invalid time': 'Neispravno vrijeme', 'Save clip': 'Spremi isječak', 'Export local clip': 'Izvezi lokalni isječak', 'Exporting local clip…': 'Izvoz lokalnog isječka…', 'No video': 'Nema videa', 'Open a local video first.': 'Najprije otvorite lokalni video.', 'Video required': 'Potreban je video', 'Select Video + audio or Video only.': 'Odaberite Video + zvuk ili Samo video.', 'Save failed': 'Spremanje nije uspjelo', 'Unexpected error': 'Neočekivana pogreška', 'Download failed': 'Preuzimanje nije uspjelo', 'Session recovery': 'Oporavak sesije', 'Queue completed.': 'Red čekanja je dovršen.', 'Ready to capture diagnostics': 'Spremno za bilježenje dijagnostike', 'Subtle error sound': 'Tihi zvuk pogreške', 'Paste a link to inspect its title and duration.': 'Zalijepite poveznicu za provjeru naslova i trajanja.', 'Aspect ratio is applied to clip exports. Full-video downloads retain their original framing.': 'Omjer slike primjenjuje se pri izvozu isječaka. Cijeli videozapisi zadržavaju izvorni kadar.', 'Original timeline • precise clipping • multi-selection': 'Izvorna vremenska crta • precizno rezanje • višestruki odabir', 'Paste a link or open a local video to use the original timeline.': 'Zalijepite poveznicu ili otvorite lokalni video za korištenje vremenske crte.', 'Paste a video link above or choose Open Local Video to activate the timeline.': 'Zalijepite poveznicu iznad ili odaberite Otvori lokalni video.', 'Original timeline loaded automatically • drag to select your clip': 'Izvorna vremenska crta učitana je automatski • povucite za odabir isječka', 'Downloader tools and configuration.': 'Alati za preuzimanje i postavke.', 'All cutting controls are now in New Download → Media Studio.': 'Sve kontrole rezanja nalaze se u Novo preuzimanje → Media Studio.', 'Successfully downloaded files in this Qt version.': 'Uspješno preuzete datoteke u ovoj Qt verziji.', 'Pending links waiting to be downloaded.': 'Poveznice koje čekaju preuzimanje.', 'Preview downloaded videos and cut clips with FFmpeg.': 'Pregledajte preuzete videozapise i režite isječke uz FFmpeg.', 'A major update with a new interface, more download control, and built-in media tools.': 'Veliko ažuriranje s novim sučeljem, naprednijim preuzimanjima i ugrađenim medijskim alatima.', 'Redesigned interface': 'Redizajnirano sučelje', 'Flexible formats': 'Fleksibilni formati', 'Better download management': 'Bolje upravljanje preuzimanjima', 'Reliability & diagnostics': 'Pouzdanost i dijagnostika', 'Easier Windows installation': 'Jednostavnija instalacija na Windowsu', 'A modern Qt workspace with faster navigation and a dedicated Download Center.': 'Moderno Qt sučelje s bržom navigacijom i zasebnim centrom preuzimanja.', 'Video + Audio, Video Only, and Audio Only now have separate format choices and quality controls.': 'Video sa zvukom, samo video i samo zvuk sada imaju zasebne formate i kontrole kvalitete.', 'Preview videos, mark timeline selections, and export clips with multiple aspect ratios.': 'Pregledajte videozapise, označite dijelove vremenske crte i izvezite isječke u različitim omjerima slike.', 'Pause and resume, manage your queue, retry failed downloads, and browse history.': 'Pauzirajte i nastavite preuzimanja, upravljajte redom čekanja, ponovite neuspjele zadatke i pregledajte povijest.', 'Session recovery, detailed Status Log, and built-in update checks.': 'Oporavak sesije, detaljan dnevnik događaja i ugrađena provjera ažuriranja.', 'A single installer bundles the app and required download tools.': 'Jedan instalater uključuje aplikaciju i potrebne alate za preuzimanje.', 'Let’s go!': 'Krenimo!'}

def ui_translate(value):
    if APP_LANGUAGE!='hr':return value
    if value in UI_HR:return UI_HR[value]
    # Preserve icons, prefixes and suffixes while translating the UI caption.
    for english,croatian in UI_HR.items():
        if value.endswith(english) and len(value)-len(english)<8:
            return value[:-len(english)]+croatian
    return value

SUPPORTED_MEDIA_HOSTS = {'youtube.com','youtu.be','m.youtube.com','www.youtube.com','music.youtube.com','instagram.com','www.instagram.com','tiktok.com','www.tiktok.com','vm.tiktok.com','vt.tiktok.com','facebook.com','www.facebook.com','fb.watch','twitter.com','x.com','www.x.com','vimeo.com','www.vimeo.com','reddit.com','www.reddit.com'}

def valid_media_url(raw):
    try:
        parsed=urllib.parse.urlsplit(raw.strip())
        host=(parsed.hostname or '').lower().rstrip('.')
        return parsed.scheme in ('http','https') and host in SUPPORTED_MEDIA_HOSTS and bool(parsed.path.strip('/') or parsed.query)
    except (ValueError,TypeError):
        return False

def extract_media_links(text):
    candidates=re.findall(r'https?://[^\s<>\"\']+',text or '',flags=re.I)
    seen=set();result=[]
    for candidate in candidates:
        url=candidate.rstrip('.,;!)]}')
        if valid_media_url(url) and url not in seen:
            seen.add(url);result.append(url)
    return result

DEFAULT_FOLDER=Path.home()/'Downloads'
STYLE='''
* {font-family:'Segoe UI';font-size:13px;color:#dce0f5}
QMainWindow,QWidget#root {background:#090c19}
QWidget {background:transparent}
QFrame#sidebar {background:#0d1021;border-right:1px solid #242945}
QFrame#topbar {background:#101428;border-bottom:1px solid #252b48}
QFrame#card {background:#151a31;border:1px solid #2b3153;border-radius:19px}
QFrame#task {background:#151a31;border:1px solid #2d3458;border-radius:17px}
QFrame#stat {background:#151a31;border:1px solid #2c3153;border-radius:15px}\nQFrame#summary {background:#12172b;border:1px solid #2a3150;border-radius:13px}
QFrame#empty {background:#12172d;border:1px dashed #3a4265;border-radius:22px}
QLabel#heading {font-size:30px;font-weight:800;color:#f7f8ff}
QLabel#sub {font-size:12px;color:#949dbb}
QLabel#section {font-size:15px;font-weight:700;color:#eef0ff}
QLabel#eyebrow {font-size:11px;font-weight:700;color:#a48eff;letter-spacing:1px}
QPushButton {background:#242945;border:1px solid #333a5e;border-radius:11px;padding:11px 17px;font-weight:600;color:#dce1fa}
QPushButton:hover {background:#343c63;border-color:#6458a9}
QPushButton#primary {background:#7659ef;border:1px solid #8e73ff;color:white}
QPushButton#primary:hover {background:#8c70ff}
QPushButton#nav {background:transparent;border:0;border-radius:12px;text-align:left;padding:15px 17px;color:#a6acc9;font-size:13px}
QPushButton#nav:hover {background:#1b2140}
QPushButton#nav:checked {background:#28234f;color:#e4d9ff;border-left:3px solid #967cff}
QPushButton#chip {background:#181e37;border:1px solid #303756;border-radius:17px;padding:9px 18px;color:#aeb6d3}
QPushButton#chip:checked {background:#7659ef;color:white;border-color:#7659ef}\nQComboBox::drop-down {border:0;width:25px}\nQComboBox QAbstractItemView {background:#141a32;color:#eff0ff;selection-background-color:#7659ef}
QLineEdit,QTextEdit,QComboBox,QListWidget {background:#0c1125;border:1px solid #323a5d;border-radius:12px;padding:12px;selection-background-color:#7659ef;color:#eef0ff}
QLineEdit:focus,QTextEdit:focus {border-color:#8e78f5}
QProgressBar {background:#2c3352;border:0;border-radius:5px;height:9px;text-align:center}
QProgressBar::chunk {background:#8b6dff;border-radius:5px}
QSlider::groove:horizontal {height:6px;background:#353a57;border-radius:3px}
QSlider::handle:horizontal {background:#9176ff;width:15px;margin:-5px 0;border-radius:7px}
QScrollArea {border:0;background:transparent}
QScrollBar:vertical {background:#101428;width:9px;border:0}
QScrollBar::handle:vertical {background:#3b4264;border-radius:4px;min-height:25px}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0}
QLabel#success {color:#55dcb1;font-weight:700}
QLabel#active {color:#b7a3ff;font-weight:700}
QLabel#error {color:#ff9b9b;font-weight:700}
QLabel#pending {color:#efc77d;font-weight:700}
QPushButton#small {padding:7px 12px;border-radius:9px;font-size:11px}
QFrame#task {min-height:105px}

QListWidget {background:#12172d;border:1px solid #2b3356;border-radius:15px;padding:10px;outline:0}
QListWidget::item {background:#1a203a;border:1px solid #31395d;border-radius:10px;padding:15px;margin:5px;color:#dce1fa}
QListWidget::item:selected {background:#302653;border-color:#8e73ff}
QFrame#task:hover {border-color:#6555a5}
QPlainTextEdit#log {background:#090e20;border:1px solid #323a5d;border-radius:12px;
 color:#c6d5f4;font-family:'Consolas';font-size:12px;padding:12px}


'''

def button(label, fn, primary=False):
    b=QPushButton(label); b.clicked.connect(fn)
    if primary:b.setObjectName('primary')
    return b

def heading(title,subtitle):
    w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,10)
    h=QLabel(title);h.setObjectName('heading');l.addWidget(h)
    s=QLabel(subtitle);s.setObjectName('sub');l.addWidget(s)
    return w

def card():
    f=QFrame();f.setObjectName('card');v=QVBoxLayout(f);v.setContentsMargins(22,20,22,20);v.setSpacing(14)
    return f,v

class OriginalPlayerBridge(QObject):
    """Translate callbacks from the original pywebview timeline to Qt."""
    def __init__(self, app):
        super().__init__(app)
        self.app=app

    @Slot(float)
    def oznaci_pocetak(self, seconds):
        self.app.cut_from.setText(self.app.format_seconds(seconds))

    @Slot(float)
    def oznaci_kraj(self, seconds):
        self.app.cut_to.setText(self.app.format_seconds(seconds))

    @Slot(float, float)
    def skini_shorts_iz_player(self, start, end):
        self.oznaci_pocetak(start)
        self.oznaci_kraj(end)
        self.app.remote_cut()

    @Slot('QVariantList')
    def skini_visestruke_isjecke(self, selections):
        self.app.export_multiple_selections(selections)

    @Slot()
    def zatrazi_lokalni_pregled(self):
        self.app.original_player_note.setText(
            'YouTube blocked embedded playback. Preparing a local preview…')
        self.app.preview_link()


if WEB_ENGINE_AVAILABLE:
    class LoggedWebPage(QWebEnginePage):
        def __init__(self, profile, parent, logger):
            super().__init__(profile,parent)
            self._logger=logger
        def javaScriptConsoleMessage(self, level, message, line, source):
            # PySide6 / QtWebEngine exposes JavaScriptConsoleMessageLevel as an
            # enum object; int(level) raises TypeError in recent PySide6 builds.
            # Match symbolic names first to remain compatible with Qt versions.
            level_key=getattr(level,'name',str(level)).lower()
            if 'error' in level_key:
                level_name='ERROR'
            elif 'warning' in level_key or 'warn' in level_key:
                level_name='WARN'
            elif 'info' in level_key:
                level_name='INFO'
            else:
                numeric=getattr(level,'value',level)
                level_name={0:'INFO',1:'WARN',2:'ERROR'}.get(numeric,'INFO')
            if level_name=='WARN' and ('Failed to create WebGPU Context Provider' in message
                                        or "Unrecognized feature: 'web-share'" in message):
                level_name='DEBUG'
            # YouTube/DoubleClick conversion tracking CORS failures do not affect playback.
            if ('doubleclick.net/pagead/' in message or 'youtube.com/pagead/viewthroughconversion/' in message) and ('CORS' in message or 'Access to fetch' in message):
                return
            self._logger(level_name,'PLAYER JS',f'{message} ({source}:{line})')


class UpdateCheckWorker(QThread):
    completed = Signal(object)

    def run(self):
        results = []
        def fetch_json(url):
            request = urllib.request.Request(url, headers={
                'User-Agent': 'MisterMuscleDownloader/7.14',
                'Accept': 'application/json'})
            with urllib.request.urlopen(request, timeout=7) as response:
                return json.load(response)

        def newer(remote, local):
            try:
                from packaging.version import Version
                return Version(str(remote).lstrip('vV')) > Version(str(local).lstrip('vV'))
            except Exception:
                def parts(v):
                    return tuple(int(x) for x in re.findall(r'\d+', str(v))[:4])
                return parts(remote) > parts(local)

        try:
            data = fetch_json('https://api.github.com/repos/' + APP_REPOSITORY + '/releases/latest')
            tag = str(data.get('tag_name', '')).strip()
            url = str(data.get('html_url', '')).strip()
            if tag:
                assets = data.get('assets', [])
                installer = next((a for a in assets if str(a.get('name','')).lower().endswith('.exe')
                                  and str(a.get('browser_download_url','')).startswith('https://github.com/')), None)
                asset_url = installer.get('browser_download_url', '') if installer else ''
                results.append(('Mister Muscle Downloader', APP_VERSION, tag, newer(tag, APP_VERSION), asset_url))
            else:
                results.append(('Mister Muscle Downloader', APP_VERSION, 'Unknown', False, ''))
        except Exception as exc:
            results.append(('Mister Muscle Downloader', APP_VERSION, 'Check unavailable: ' + str(exc), False, ''))

        # Bundled Windows releases have no pip dist-info for these components.
        # Query the actual executable and the imported PySide6 module instead.
        current = 'Unknown'
        try:
            if getattr(sys, 'frozen', False):
                executable = str(TOOLS_DIR / 'yt-dlp.exe')
                if not Path(executable).is_file():
                    raise FileNotFoundError(executable)
                process = subprocess.run([executable, '--version'], capture_output=True,
                                         text=True, timeout=8,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if process.returncode:
                    raise RuntimeError((process.stderr or process.stdout).strip()[:160])
                current = process.stdout.strip().splitlines()[0]
            else:
                try:
                    current = importlib.metadata.version('yt-dlp')
                except importlib.metadata.PackageNotFoundError:
                    from yt_dlp.version import __version__ as current
            latest = fetch_json('https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest')['tag_name'].lstrip('v')
            results.append(('yt-dlp', current, latest, newer(latest, current),
                            'https://github.com/yt-dlp/yt-dlp/releases/latest'))
        except Exception as exc:
            results.append(('yt-dlp', current,
                            'Check unavailable: ' + str(exc), False, ''))

        try:
            import PySide6
            current = PySide6.__version__
            try:
                latest = fetch_json('https://pypi.org/pypi/PySide6/json')['info']['version']
                results.append(('PySide6', current, latest, newer(latest, current),
                                'https://pypi.org/project/PySide6/'))
            except Exception as exc:
                results.append(('PySide6', current, 'Check unavailable: ' + str(exc), False, ''))
        except Exception as exc:
            results.append(('PySide6', 'Unknown', 'Check unavailable: ' + str(exc), False, ''))

        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            try:
                run = subprocess.run([ffmpeg, '-version'], capture_output=True, text=True, timeout=5,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                first = (run.stdout or run.stderr).splitlines()[0]
                results.append(('FFmpeg', first[:85], 'Installed (manual update check)', False, 'https://ffmpeg.org/download.html'))
            except Exception as exc:
                results.append(('FFmpeg', 'Found', 'Version check unavailable: ' + str(exc), False, ''))
        else:
            results.append(('FFmpeg', 'Not found', 'Install for cutting', False, 'https://ffmpeg.org/download.html'))
        self.completed.emit(results)


class UpdateDownloadWorker(QThread):
    progress = Signal(str)
    completed = Signal(object)

    def __init__(self, updates, parent=None):
        super().__init__(parent)
        self.updates = updates

    def run(self):
        output = []
        target = DATA / 'updates'
        target.mkdir(parents=True, exist_ok=True)
        for name, version, url in self.updates:
            try:
                if name == 'Mister Muscle Downloader':
                    # Only trusted GitHub Release EXE assets from this repository.
                    prefix = 'https://github.com/' + APP_REPOSITORY + '/releases/download/'
                    if not url.startswith(prefix) or not url.lower().endswith('.exe'):
                        output.append((name, 'No compatible Windows installer in GitHub Release; skipped'))
                        continue
                    filename = Path(urllib.parse.urlsplit(url).path).name
                    safe_version = re.sub(r'[^A-Za-z0-9._-]', '_', str(version))[:60]
                    dest = target / (Path(filename).stem + '_v' + safe_version + '.exe')
                    if dest.exists() and dest.stat().st_size > 1024:
                        output.append((name, 'Installer ready: ' + str(dest), str(dest)))
                        continue
                    self.progress.emit('Downloading ' + name + ' ' + version)
                    request = urllib.request.Request(url, headers={'User-Agent':'MisterMuscleDownloader/7.14'})
                    temp = dest.with_suffix(dest.suffix + '.part')
                    try:
                        with urllib.request.urlopen(request, timeout=30) as response, temp.open('wb') as out:
                            downloaded = 0
                            while True:
                                block = response.read(256 * 1024)
                                if not block: break
                                downloaded += len(block)
                                if downloaded > 750 * 1024 * 1024:
                                    raise ValueError('Installer exceeds size limit')
                                out.write(block)
                        if downloaded < 1024:
                            raise ValueError('Downloaded file is too small')
                        temp.replace(dest)
                    finally:
                        temp.unlink(missing_ok=True)
                    output.append((name, 'Installer ready: ' + str(dest), str(dest)))
                elif name in ('yt-dlp', 'PySide6'):
                    if getattr(sys, 'frozen', False):
                        output.append((name, 'Bundled component: update via next Mister Muscle installer'))
                        continue
                    self.progress.emit('Downloading package ' + name + ' ' + version)
                    package_dir = target / 'python_packages' / name
                    package_dir.mkdir(parents=True, exist_ok=True)
                    # Download only; do not modify the running Python environment.
                    run = subprocess.run([sys.executable, '-m', 'pip', 'download', '--only-binary=:all:',
                                          '--disable-pip-version-check', '--dest', str(package_dir),
                                          name + '==' + version], capture_output=True, text=True,
                                         timeout=180, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                    if run.returncode:
                        output.append((name, 'Download failed: ' + (run.stderr or run.stdout)[-280:]))
                    else:
                        output.append((name, 'Downloaded to ' + str(package_dir) + ' (not installed)'))
            except Exception as exc:
                output.append((name, 'Download failed: ' + str(exc)))
        self.completed.emit(output)


BUG_REPORT_ENDPOINT = 'https://fjxxavinkqhjeqiolwsk.supabase.co/functions/v1/submit-bug-report'


def scrub_bug_log(value):
    """Conservative log redaction: no URLs, paths, email addresses or credentials."""
    lines = []
    for line in str(value).splitlines()[-150:]:
        line = re.sub(r'https?://\S+', '[URL REDACTED]', line, flags=re.I)
        line = re.sub(r'(?i)(authorization|cookie|token|password|secret|api[_-]?key)\s*[:=]\s*\S+', r'\1=[REDACTED]', line)
        line = re.sub(r'(?i)\b[A-Z]:\\[^\s]+', '[PATH REDACTED]', line)
        line = re.sub(r'(?i)\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b', '[EMAIL REDACTED]', line)
        lines.append(line[:400])
    return '\n'.join(lines)[-15000:]


class BugReportWorker(QThread):
    completed = Signal(bool, str)

    def __init__(self, payload, parent=None):
        super().__init__(parent)
        self.payload = payload

    def run(self):
        try:
            body = json.dumps(self.payload, ensure_ascii=False).encode('utf-8')
            if len(body) > 11_000_000:
                raise ValueError('Report exceeds maximum upload size (11 MB).')
            request = urllib.request.Request(BUG_REPORT_ENDPOINT, data=body,
                headers={'Content-Type':'application/json', 'User-Agent':'MisterMuscleDownloader/' + APP_VERSION}, method='POST')
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read(8192).decode('utf-8'))
                if not result.get('ok') or not result.get('report_id'):
                    raise ValueError(result.get('error', 'Server did not confirm report'))
                self.completed.emit(True, str(result['report_id']))
        except Exception as exc:
            self.completed.emit(False, str(exc)[:400])


class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('Mister Muscle Downloader — v' + APP_VERSION)
        self.resize(1360,850);self.setMinimumSize(990,640)
        self._log_count=0
        self._log_lines=[]
        self._log_max_lines=2500
        self._log_pending=[]
        self._log_path=LOG_FILE
        self._log_file_error=False
        self._error_sound_cooldown=QElapsedTimer()
        self._error_sound=QSoundEffect(self)
        self._error_sound.setSource(QUrl.fromLocalFile(str(BASE/'assets'/'soft_error.wav')))
        self._error_sound.setVolume(0.60)
        self._error_sound.statusChanged.connect(self._on_alarm_status)
        self._log_flush_timer=QTimer(self)
        self._log_flush_timer.setInterval(180)
        self._log_flush_timer.timeout.connect(self.flush_log_view)
        self._log_flush_timer.start()
        self.folder=str(DEFAULT_FOLDER);self.history=self.load_history();self.proc=None;self.queue=[]
        self.current_url='';self.current_title='';self.finished_count=0;self.current_mode=None;self.last_file='';self.canceled=False;self.cut_proc=None;self.meta_proc=None;self.preview_proc=None;self.preview_dir=None;self.preview_file=None;self.remote_proc=None;self.remote_tmp=None;self.remote_output=None;self.remote_source=None;self.remote_url=None;self.remote_format=None;self.remote_stage=None;self.clip_percent=0;self.clip_detail='';self._clip_last_log=-1;self._clip_last_activity=0;self._clip_started=0;self._clip_ffmpeg_buffer='';self.download_percent=0;self.download_detail='';self.failed_items=[];self.center_filter='All';self.current_download_record=None;self.output_buffer='';self.last_ui_percent=-1;self.pause_requested=False;self.paused=False;self.session_loading=False;self.last_saved_state=None;self.current_quality='Best available'
        self.media_info={r.get('url'):r.get('metadata',{}) for r in self.history if r.get('url') and isinstance(r.get('metadata'),dict)};self.thumb_cache={};self.thumb_pending=set();self.net=QNetworkAccessManager(self)
        self.player=QMediaPlayer();self.audio=QAudioOutput();self.player.setAudioOutput(self.audio)
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root)
        outer=QHBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        side=QFrame();side.setObjectName('sidebar');side.setFixedWidth(240);outer.addWidget(side)
        sv=QVBoxLayout(side);sv.setContentsMargins(16,27,16,23);sv.setSpacing(6)
        # Original Mister Muscle branding: shared icon for the window and sidebar.
        logo_file=str(Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent)) / 'assets' / 'logo.png')
        if Path(logo_file).is_file():
            self.setWindowIcon(QIcon(logo_file))
            logo_label=QLabel()
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet('background:transparent; padding:0;')
            logo_label.setPixmap(QPixmap(logo_file).scaled(112,112,Qt.KeepAspectRatio,Qt.SmoothTransformation))
            sv.addWidget(logo_label)
        brand=QLabel('MISTER MUSCLE')
        brand.setStyleSheet('font-size:17px;font-weight:800;color:#f8f6ff;padding:12px 8px 2px')
        sv.addWidget(brand)
        tag=QLabel('     VIDEO DOWNLOADER')
        tag.setStyleSheet('font-size:10px;letter-spacing:2px;color:#8e91b8;padding-bottom:30px')
        sv.addWidget(tag)
        shell=QWidget();outer.addWidget(shell,1)
        shell_layout=QVBoxLayout(shell);shell_layout.setContentsMargins(0,0,0,0);shell_layout.setSpacing(0)
        top=QFrame();top.setObjectName('topbar');top.setFixedHeight(65)
        tr=QHBoxLayout(top);tr.setContentsMargins(31,0,30,0)
        self.top_section=QLabel('DOWNLOAD TASKS')
        self.top_section.setStyleSheet('font-size:12px;font-weight:800;letter-spacing:1px;color:#e3e1fb')
        tr.addWidget(self.top_section)
        tr.addSpacing(26)
        top_hint=QLabel('Your media workspace')
        top_hint.setObjectName('sub');tr.addWidget(top_hint);tr.addStretch()
        top_new=button('＋  New Download',lambda:self.switch(0),True)
        tr.addWidget(button('♥  Donate',lambda:QDesktopServices.openUrl(QUrl(DONATE_URL))))
        tr.addWidget(top_new)
        shell_layout.addWidget(top)
        self.stack=QStackedWidget();shell_layout.addWidget(self.stack,1)
        self.nav=[]
        pages=[('⊕   New Download',self.make_download),('▣   Download Center',self.make_center),
               ('☷   Queue',self.make_queue),('◷   History',self.make_history),
               ('▶   Player & Cutting',self.make_player),('⚙   Settings',self.make_settings),
               ('⚑   Report a Bug',self.make_bug_report),('☰   Status Log',self.make_log)]
        group_label=QLabel('   WORKSPACE');group_label.setObjectName('eyebrow')
        sv.addWidget(group_label)
        for i,(name,factory) in enumerate(pages):
            b=button(name,lambda checked=False,n=i:self.switch(n))
            b.setObjectName('nav');b.setCheckable(True)
            sv.addWidget(b);self.nav.append(b);self.stack.addWidget(self.page(factory()))
            if i==4:b.hide()  # Legacy cutting backend retained, redundant page hidden
        sv.addStretch()
        footer=QLabel('●  READY TO DOWNLOAD')
        footer.setStyleSheet('color:#5bd5b5;font-size:10px;font-weight:700;padding:9px')
        sv.addWidget(footer)
        sv.addWidget(QLabel('MISTER MUSCLE  /  v' + APP_VERSION))
        self.restore_session()
        self._language_timer=QTimer(self)
        self._language_timer.timeout.connect(self.refresh_language)
        self._language_timer.start(450)
        self.refresh_language()
        self._original_preview_url=''
        self._auto_player_timer=QTimer(self)
        self._auto_player_timer.setSingleShot(True)
        self._auto_player_timer.setInterval(850)
        self._auto_player_timer.timeout.connect(self.auto_load_original_player)
        self.urls.textChanged.connect(self.on_studio_source_changed)
        self.switch(0)
        QApplication.clipboard().dataChanged.connect(self.auto_paste_clipboard)
        self.log('INFO','APP','Mister Muscle Downloader v' + APP_VERSION + ' started')
        self.log('INFO','APP',f'Python {sys.version.split()[0]} | Qt WebEngine: {WEB_ENGINE_AVAILABLE}')
        self.log('INFO','APP',f'Log file: {self._log_path}')
        self.log('INFO','APP',f'FFmpeg: {shutil.which("ffmpeg") or "not found in PATH"}')
        if self.urls.toPlainText().strip():
            self._auto_player_timer.start()
        QTimer.singleShot(1200, self.check_updates)
        QTimer.singleShot(350, self.show_whats_new_if_needed)

    def refresh_language(self):
        # UI text can change while downloading; refresh visible captions without
        # modifying machine-readable formats, queue entries, or URLs.
        for widget in (self.findChildren(QLabel) + self.findChildren(QPushButton) + self.findChildren(QCheckBox)):
            if widget is self.language_label: continue
            current=widget.text()
            previous=widget.property('_mm_localized_value')
            original=widget.property('_mm_english_value')
            if original is None or (previous is not None and current!=previous):
                original=current
            translated=ui_translate(original)
            widget.setProperty('_mm_english_value',original)
            widget.setProperty('_mm_localized_value',translated)
            if current!=translated: widget.setText(translated)

    def change_language(self,index):
        global APP_LANGUAGE
        new_language=self.language_select.itemData(index)
        if new_language not in ('en','hr'):return
        APP_LANGUAGE=new_language
        try: LANGUAGE_FILE.write_text(json.dumps({'language':APP_LANGUAGE}),encoding='utf-8')
        except OSError as exc:self.log('WARN','LANGUAGE',str(exc))
        self.refresh_language()
        # Embedded player HTML is generated in the selected language on next load.
        self._original_preview_url=''
        if getattr(self,'_studio_local',None):self.open_local_path_in_studio(self._studio_local)
        elif self.urls.toPlainText().strip():self.auto_load_original_player()

    def on_studio_source_changed(self):
        """Keep the embedded browser hidden until a usable source is loaded."""
        if not self.urls.toPlainText().strip():
            self._auto_player_timer.stop()
            self._original_preview_url = ''
            self._studio_local = None
            self.hide_studio_player()
        else:
            self._auto_player_timer.start()

    def hide_studio_player(self):
        if hasattr(self, 'original_web'):
            self.original_web.hide()
            self.original_web.setUrl(QUrl('about:blank'))
        if hasattr(self, 'original_player_note'):
            self.original_player_note.setText('Paste a video link above or choose Open Local Video to activate the timeline.')

    def show_studio_player(self):
        if hasattr(self, 'original_web'):
            self.original_web.show()
            QTimer.singleShot(0, self.adjust_original_player_height)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'original_web'):
            QTimer.singleShot(0,self.adjust_original_player_height)

    def adjust_original_player_height(self):
        """Keep a true 16:9 video with timeline controls below it."""
        if getattr(self, '_fullscreen_host', None) is not None:return
        if not hasattr(self,'original_web') or not self.original_web.isVisible():return
        width=self.original_web.width()
        if width<200:return
        # 16:9 video plus timeline, toolbar and multi-cut selection area.
        # The parent QScrollArea handles the extra vertical space.
        desired=max(680,min(1800,round(width*9/16)+340))
        if abs(self.original_web.height()-desired)>4:
            self.original_web.setFixedHeight(desired)

    def page(self,inner):
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        container=QWidget();layout=QVBoxLayout(container);layout.setContentsMargins(35,30,35,30)
        layout.addWidget(inner);layout.addStretch();scroll.setWidget(container);return scroll
    def column(self):
        w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(0,0,0,0);v.setSpacing(18);return w,v
    def switch(self,i):
        self.stack.setCurrentIndex(i)
        self.top_section.setText('STATUS LOG' if i==7 else 'REPORT A BUG' if i==6 else 'SETTINGS' if i==5 else 'DOWNLOAD TASKS' if i in (0,1,2,3) else 'MEDIA STUDIO')
        for n,b in enumerate(self.nav):b.setChecked(n==i)
        if i==1:self.refresh_center()
        if i==2:self.refresh_queue()
        if i==3:self.refresh_history()

    def log(self,level,source,message):
        """Timestamped diagnostics to the new tab and persistent status.log."""
        level=str(level).upper()
        message=str(message).replace('\r','\n')
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        for line in message.splitlines() or ['']:
            if not line.strip():continue
            entry=f'[{timestamp}] [{level}] [{source}] {line[:5000]}'
            self._log_lines.append((level,entry))
            self._log_pending.append((level,entry))
            self._log_count+=1
            if len(self._log_lines)>self._log_max_lines:
                self._log_lines=self._log_lines[-self._log_max_lines:]
            try:
                if self._log_path.exists() and self._log_path.stat().st_size>5_000_000:
                    old=self._log_path.with_suffix('.previous.log')
                    self._log_path.replace(old)
                with self._log_path.open('a',encoding='utf-8') as f:f.write(entry+'\n')
            except OSError:
                self._log_file_error=True
        if level=='ERROR' and hasattr(self,'log_sound_enabled') and self.log_sound_enabled.isChecked():
            if not self._error_sound_cooldown.isValid() or self._error_sound_cooldown.elapsed()>=8000:
                self._error_sound_cooldown.start()
                if self._error_sound.status()==QSoundEffect.Status.Ready:
                    self._error_sound.play()
        if hasattr(self,'log_count_label'):
            self.log_count_label.setText(f'{self._log_count} events  •  {self._log_path}')

    def _on_alarm_status(self):
        if self._error_sound.status()==QSoundEffect.Status.Error:
            self.log('WARN','ALARM','Audio file failed to load: '+str(BASE/'assets'/'soft_error.wav'))

    def test_alarm(self):
        if self._error_sound.status()==QSoundEffect.Status.Ready:
            self._error_sound.stop()
            self._error_sound.play()
            self.log('INFO','ALARM','Test alarm playback requested')
        else:
            self.log('WARN','ALARM','Sound not ready; checking Windows system sound fallback')
            if sys.platform=='win32':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception as exc:
                    self.log('WARN','ALARM','Windows sound fallback failed: '+str(exc))

    def _on_web_fullscreen_request(self, request):
        """Handle HTML5 video fullscreen without rebuilding/reloading the player."""
        if request.toggleOn():
            if getattr(self, '_fullscreen_host', None) is not None:
                request.accept()
                return
            request.accept()
            self._fullscreen_host = QDialog(self)
            self._fullscreen_host.setWindowTitle('Mister Muscle - Player fullscreen')
            self._fullscreen_host.setWindowFlags(Qt.WindowType.Window)
            self._fullscreen_host.setStyleSheet('background: black;')
            layout = QVBoxLayout(self._fullscreen_host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.original_web.setMinimumHeight(0)
            self.original_web.setMaximumHeight(16777215)
            self.original_web.setParent(self._fullscreen_host)
            self.original_web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(self.original_web)
            self._fullscreen_host.finished.connect(self._restore_web_player)
            # A Qt shortcut catches Esc even when the embedded page has focus.
            self._fullscreen_escape = QShortcut(QKeySequence('Esc'), self._fullscreen_host)
            self._fullscreen_escape.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self._fullscreen_escape.activated.connect(self._fullscreen_host.close)
            self._fullscreen_host.showFullScreen()
            self.original_web.show()
            self.original_web.setFocus()
        else:
            request.accept()
            host = getattr(self, '_fullscreen_host', None)
            if host is not None:
                host.close()

    def _restore_web_player(self):
        host = getattr(self, '_fullscreen_host', None)
        if host is None:
            return
        self._fullscreen_host = None
        self._fullscreen_escape = None
        self.original_web.setParent(self._player_web_parent)
        self._player_web_layout.insertWidget(self._player_web_index, self.original_web)
        self.original_web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.original_web.show()
        QTimer.singleShot(0, self.adjust_original_player_height)

    def make_log(self):
        w,v=self.column()
        v.addWidget(heading('Status Log','Live yt-dlp, FFmpeg, player and application diagnostics.'))
        toolbar=QHBoxLayout()
        self.log_filter=QComboBox()
        self.log_filter.addItems(['All events','Errors only','Warnings + errors'])
        self.log_filter.currentIndexChanged.connect(self.refresh_log_view)
        toolbar.addWidget(self.log_filter)
        self.log_sound_enabled=QCheckBox('Subtle error sound')
        self.log_sound_enabled.setChecked(True)
        self.log_sound_enabled.setToolTip('Play a quiet notification at most once every 8 seconds when a new ERROR is logged.')
        toolbar.addWidget(self.log_sound_enabled)
        toolbar.addWidget(button('Test Alarm',self.test_alarm))
        toolbar.addWidget(button('Copy log',self.copy_log))
        toolbar.addWidget(button('Save log as…',self.save_log_as))
        toolbar.addWidget(button('Open log folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA)))))
        toolbar.addWidget(button('Clear log',self.clear_log))
        toolbar.addStretch()
        v.addLayout(toolbar)
        self.log_count_label=QLabel('Ready to capture diagnostics')
        self.log_count_label.setObjectName('sub')
        v.addWidget(self.log_count_label)
        self.log_view=QPlainTextEdit()
        self.log_view.setObjectName('log')
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setMaximumBlockCount(self._log_max_lines)
        self.log_view.setMinimumHeight(430)
        v.addWidget(self.log_view,1)
        hint=QLabel('Tip: reproduce the error, open Status Log, then click Copy log. Links may appear in logs; review before sharing.')
        hint.setObjectName('sub');hint.setWordWrap(True)
        v.addWidget(hint)
        return w

    def _visible_log(self,level):
        index=self.log_filter.currentIndex()
        return index==0 or (index==1 and level=='ERROR') or (index==2 and level in ('WARN','ERROR'))

    @staticmethod
    def _log_format(level):
        fmt=QTextCharFormat()
        colors={'ERROR':'#ff6d80','WARN':'#f2c56f','INFO':'#c6d5f4','DEBUG':'#8292b5'}
        fmt.setForeground(QColor(colors.get(level,'#c6d5f4')))
        if level=='ERROR':
            fmt.setFontWeight(QFont.Weight.DemiBold)
        return fmt

    def _append_colored_logs(self,records):
        if not records:return
        cursor=self.log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        for level,entry in records:
            # Preserve one entry per line without introducing an extra blank line.
            if not self.log_view.document().isEmpty():
                cursor.insertBlock()
            cursor.insertText(entry,self._log_format(level))
        self.log_view.setTextCursor(cursor)

    def flush_log_view(self):
        if not hasattr(self,'log_view'):return
        pending=self._log_pending
        self._log_pending=[]
        if not pending:return
        bar=self.log_view.verticalScrollBar()
        follow=bar.value()>=bar.maximum()-25
        self._append_colored_logs([(level,entry) for level,entry in pending if self._visible_log(level)])
        if follow:bar.setValue(bar.maximum())

    def refresh_log_view(self):
        if not hasattr(self,'log_view'):return
        self._log_pending=[]
        self.log_view.clear()
        self._append_colored_logs([(level,entry) for level,entry in self._log_lines if self._visible_log(level)])
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def copy_log(self):
        QApplication.clipboard().setText('\n'.join(line for _,line in self._log_lines))
        self.log('INFO','LOG','Log copied to clipboard')

    def save_log_as(self):
        filename,_=QFileDialog.getSaveFileName(self,'Save diagnostics',str(Path.home()/'Desktop'/'mister_muscle_status.log'),'Log files (*.log);;Text files (*.txt)')
        if not filename:return
        try:
            Path(filename).write_text('\n'.join(line for _,line in self._log_lines)+'\n',encoding='utf-8')
            self.log('INFO','LOG',f'Log saved: {filename}')
        except OSError as exc:
            self.log('ERROR','LOG',f'Cannot save log: {exc}')
            QMessageBox.warning(self,'Save failed',str(exc))

    def clear_log(self):
        if QMessageBox.question(self,'Clear status log','Clear the current log and saved status.log?')!=QMessageBox.Yes:return
        self._log_lines=[];self._log_pending=[];self._log_count=0
        self.log_view.clear()
        try:self._log_path.write_text('',encoding='utf-8')
        except OSError as exc:QMessageBox.warning(self,'Clear failed',str(exc))
        self.log_count_label.setText('0 events')
        self.log('INFO','LOG','Status log cleared')

    def watch_process(self,proc,name,stderr=True,stdout=False):
        """Non-blocking process output capture; works with merged and split channels."""
        if stdout:
            proc.readyReadStandardOutput.connect(
                lambda p=proc,n=name:self._capture_process_output(p,n,False))
        if stderr:
            proc.readyReadStandardError.connect(
                lambda p=proc,n=name:self._capture_process_output(p,n,True))
        proc.errorOccurred.connect(
            lambda error,p=proc,n=name:self.log('ERROR',n,f'Process error {error}: {p.errorString()}'))
        proc.started.connect(lambda p=proc,n=name:self.log('INFO',n,f'Process started: {p.program()} {" ".join(p.arguments()[:5])} …'))

    def _capture_process_output(self,proc,name,is_stderr):
        raw=bytes(proc.readAllStandardError() if is_stderr else proc.readAllStandardOutput())
        if raw:
            text=raw.decode('utf-8',errors='replace')
            for line in re.split(r'[\r\n]+',text):
                if line.strip():
                    self.log('ERROR' if 'ERROR:' in line or 'Error:' in line else 'WARN' if 'WARNING:' in line else 'INFO',name,line)

    def make_download(self):
        w,v=self.column()
        v.setSpacing(13)
        v.addWidget(heading('New Download','Paste a link, choose your format and start — all in one workspace.'))
        row=QHBoxLayout();row.setSpacing(14)
        left=QVBoxLayout();left.setSpacing(14)
        right=QVBoxLayout();right.setSpacing(14)

        source,sl=card()
        eyebrow=QLabel('01  SOURCE');eyebrow.setObjectName('eyebrow');sl.addWidget(eyebrow)
        sl.addWidget(QLabel('Video links'))
        self.urls=QTextEdit()
        self.urls.setPlaceholderText('Paste a YouTube, TikTok or Instagram URL here…\nOne link per line')
        self.urls.setFixedHeight(62)
        sl.addWidget(self.urls)
        actions=QHBoxLayout();actions.setSpacing(7)
        for label,fn in [('Paste',self.paste),('Clear',self.urls.clear),
                         ('Inspect',self.inspect_link),('▶ Preview',self.preview_link)]:
            b=button(label,fn);actions.addWidget(b)
        sl.addLayout(actions)
        self.link_info=QLabel('Paste a link to inspect its title and duration.')
        self.link_info.setObjectName('sub');self.link_info.setWordWrap(True)
        sl.addWidget(self.link_info)
        left.addWidget(source)

        options,ol=card()
        eyebrow=QLabel('02  FORMAT & QUALITY');eyebrow.setObjectName('eyebrow');ol.addWidget(eyebrow)
        choices=QHBoxLayout();choices.setSpacing(12)
        modebox=QVBoxLayout();modebox.addWidget(QLabel('File type'))
        self.mode=QComboBox();self.mode.addItems(['Video + audio','Video only','Audio only','Instagram Photos'])
        modebox.addWidget(self.mode)
        qualitybox=QVBoxLayout();qualitybox.addWidget(QLabel('Resolution'))
        self.quality=QComboBox();self.quality.addItems(['Best available','2160p','1440p','1080p','720p','480p','360p'])
        qualitybox.addWidget(self.quality)
        choices.addLayout(modebox,1);choices.addLayout(qualitybox,1)
        ol.addLayout(choices)
        exportrow=QHBoxLayout();exportrow.setSpacing(12)
        vc=QVBoxLayout()
        self.format_label=QLabel('Output format');vc.addWidget(self.format_label)
        self.video_container=QComboBox();vc.addWidget(self.video_container)
        self._mode_formats={0:['MP4','MKV','WEBM'],1:['MP4','MKV','WEBM'],2:['MP3','M4A','WAV','FLAC','OPUS','OGG','AAC'],3:['Original']}
        self._saved_formats={0:'MP4',1:'MP4',2:'MP3',3:'Original'}
        self._previous_mode=0
        self.mode.currentIndexChanged.connect(self.update_mode_formats)
        self.update_mode_formats(0)
        exportrow.addLayout(vc,1)
        ac2=QVBoxLayout();ac2.addWidget(QLabel('Clip aspect ratio'))
        self.aspect=QComboBox();self.aspect.addItems(['Original','16:9 (YouTube)','9:16 (TikTok / Reels / Shorts)','1:1 (Square)','4:5 (Instagram)','3:4 (Portrait)','21:9 (Ultrawide)','4:3 (Classic)'])
        ac2.addWidget(self.aspect);exportrow.addLayout(ac2,1)
        ol.addLayout(exportrow)
        aspect_note=QLabel('Aspect ratio is applied to clip exports. Full-video downloads retain their original framing.')
        aspect_note.setObjectName('sub');aspect_note.setWordWrap(True);ol.addWidget(aspect_note)
        folderrow=QHBoxLayout()
        foldercol=QVBoxLayout()
        foldercol.addWidget(QLabel('Save to'))
        self.folder_label=QLabel(self.folder);self.folder_label.setObjectName('sub')
        self.folder_label.setWordWrap(True);foldercol.addWidget(self.folder_label)
        folderrow.addLayout(foldercol,1)
        folderrow.addWidget(button('Change folder',self.choose_folder))
        ol.addLayout(folderrow)
        self.instagram_options=QFrame()
        ig_layout=QVBoxLayout(self.instagram_options)
        ig_layout.addWidget(QLabel('Instagram login / Cookies (from old downloader)'))
        self.ig_cookie_source=QComboBox()
        self.ig_cookie_source.addItems(['Logged-in browser','cookies.txt file'])
        ig_layout.addWidget(self.ig_cookie_source)
        self.ig_browser=QComboBox()
        self.ig_browser.addItems(['Chrome','Edge','Firefox','Brave','Opera','Vivaldi'])
        ig_layout.addWidget(self.ig_browser)
        self.ig_cookie_path=QLineEdit()
        self.ig_cookie_path.setPlaceholderText('Path to cookies.txt')
        ig_layout.addWidget(self.ig_cookie_path)
        ig_layout.addWidget(button('Choose cookies.txt',self.choose_instagram_cookies))
        self.ig_cookie_source.currentIndexChanged.connect(self.update_instagram_cookie_controls)
        self.update_instagram_cookie_controls()
        self.instagram_options.hide()
        ol.addWidget(self.instagram_options)
        self.autopaste_checkbox=QCheckBox('Auto-paste supported links while app is running')
        self.autopaste_checkbox.setChecked(True)
        sl.addWidget(self.autopaste_checkbox)
        right.addWidget(options)

        actioncard,ac=card()
        eyebrow=QLabel('03  DOWNLOAD');eyebrow.setObjectName('eyebrow');ac.addWidget(eyebrow)
        intro=QLabel('Everything ready? Start your download.')
        intro.setWordWrap(True);ac.addWidget(intro)
        self.start_btn=button('⬇  START DOWNLOAD',self.start_download,True)
        self.start_btn.setMinimumHeight(52);ac.addWidget(self.start_btn)
        self.pause_btn=button('Ⅱ  Pause active download',self.pause_download);ac.addWidget(self.pause_btn)
        self.progress=QProgressBar();self.progress.setValue(0)
        self.progress.setTextVisible(True);ac.addWidget(self.progress)
        self.status=QLabel('Ready for a new download')
        self.status.setObjectName('sub');self.status.setWordWrap(True)
        ac.addWidget(self.status)
        buttons=QHBoxLayout()
        buttons.addWidget(button('Cancel',self.cancel))
        buttons.addWidget(button('Open folder',self.open_folder))
        ac.addLayout(buttons)
        left.addWidget(actioncard)
        right.addStretch(1)

        playercard,pc=card()
        eyebrow=QLabel('04  MEDIA STUDIO');eyebrow.setObjectName('eyebrow');pc.addWidget(eyebrow)
        pc.addWidget(QLabel('Original timeline • precise clipping • multi-selection'))
        description=QLabel('Drag the timeline handles, mark Start / End, or add multiple selections — your original editing workflow.')
        description.setWordWrap(True);description.setObjectName('sub')
        pc.addWidget(description)
        localrow=QHBoxLayout();localrow.setSpacing(8)
        localrow.addWidget(button('📂  Open Local Video',self.open_local_in_studio))
        localrow.addWidget(button('✂  Export local clip',self.export_local_clip))
        pc.addLayout(localrow)
        self.original_player_note=QLabel('Paste a link or open a local video to use the original timeline.')
        self.original_player_note.setObjectName('sub')
        self.original_player_note.setWordWrap(True)
        pc.addWidget(self.original_player_note)
        pc.addWidget(button('✂  Export marked clip in original quality',self.export_studio_clip,True))
        if WEB_ENGINE_AVAILABLE:
            self.original_web=QWebEngineView()
            self.original_page=LoggedWebPage(self.original_web.page().profile(),self.original_web,self.log)
            self.original_web.setPage(self.original_page)
            # Chromium disables HTML5 fullscreen by default unless explicitly enabled.
            self.original_web.settings().setAttribute(
                self.original_web.settings().WebAttribute.FullScreenSupportEnabled, True)
            self.original_page.fullScreenRequested.connect(self._on_web_fullscreen_request)
            self.original_web.loadFinished.connect(self._on_player_load_finished)
            self.original_web.page().loadingChanged.connect(self._on_player_loading_changed)
            self.original_web.setMinimumHeight(0)
            self.original_web.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
            QTimer.singleShot(0,self.adjust_original_player_height)
            pc.addWidget(self.original_web)
            self._player_web_parent=self.original_web.parentWidget()
            self._player_web_layout=pc
            self._player_web_index=pc.indexOf(self.original_web)
            self.original_web.hide()  # No blank white WebEngine canvas before a source is loaded
            self.original_bridge=OriginalPlayerBridge(self)
            self.original_channel=QWebChannel(self.original_web.page())
            self.original_channel.registerObject('bridge',self.original_bridge)
            self.original_web.page().setWebChannel(self.original_channel)
            self.original_web.settings().setAttribute(
                self.original_web.settings().WebAttribute.PlaybackRequiresUserGesture,False)
        else:
            pc.addWidget(QLabel('Install PySide6 QtWebEngine to use the original embedded player.'))
        # Source and download options stay compact at the top. The original
        # timeline player spans the entire content area below both columns.
        # Stack Source and Download on the left; Format & Quality on the right.
        # This removes the large blank area beneath Source.
        row.addLayout(left,7)
        row.addLayout(right,5)
        v.addLayout(row)
        v.addWidget(playercard,1)
        return w

    def update_mode_formats(self, mode):
        """Keep a separate output-format choice for each download mode."""
        if mode not in self._mode_formats:return
        previous=self.video_container.currentText()
        if previous:self._saved_formats[self._previous_mode]=previous
        self.video_container.blockSignals(True)
        self.video_container.clear()
        self.video_container.addItems(self._mode_formats[mode])
        self.video_container.setCurrentText(self._saved_formats.get(mode,self._mode_formats[mode][0]))
        self.video_container.blockSignals(False)
        self._previous_mode=mode
        self.quality.setEnabled(mode in (0,1))
        self.instagram_options.setVisible(mode==3) if hasattr(self,'instagram_options') else None

    def selected_download_format(self):
        return self.video_container.currentText().lower()

    @staticmethod
    def normalize_task(item):
        """Support saved queues from earlier releases (3-item tasks)."""
        if not isinstance(item,(tuple,list)) or len(item) not in (3,4):return None
        url,mode,quality=item[:3]
        if not isinstance(url,str) or not isinstance(mode,int) or not isinstance(quality,str):return None
        if quality not in ('Best available','2160p','1440p','1080p','720p','480p','360p'):return None
        if len(item)==4:
            fmt=str(item[3]).lower()
            if mode not in (0,1,2,3) or fmt not in ({0:('mp4','mkv','webm'),1:('mp4','mkv','webm'),2:('mp3','m4a','wav','flac','opus','ogg','aac'),3:('original',)}[mode]):return None
        else:
            if mode not in range(9):return None
            old_audio={2:'mp3',3:'m4a',4:'wav',5:'flac',6:'opus',7:'aac',8:'ogg'}
            fmt=old_audio.get(mode,'mp4')
            mode=2 if mode>=2 else mode
        return (url,mode,quality,fmt)

    @staticmethod
    def format_seconds(seconds):
        seconds=max(0,float(seconds))
        hours=int(seconds//3600)
        minutes=int(seconds//60)%60
        secs=seconds%60
        return f'{hours:02d}:{minutes:02d}:{secs:06.3f}'

    def open_local_in_studio(self):
        path,_=QFileDialog.getOpenFileName(self,'Open local video',self.folder,
            'Videos (*.mp4 *.mkv *.mov *.webm *.avi *.m4v);;All files (*)')
        if path:self.open_local_path_in_studio(path)

    def open_local_path_in_studio(self,path):
        self.local_path=path
        self._studio_local=path
        self._original_preview_url=''  # permit a later URL to replace local source
        self.player.setSource(QUrl.fromLocalFile(path))
        if WEB_ENGINE_AVAILABLE:
            # Serve the actual local file from the same origin as player.html.
            html=_player_html('generic',video_src='/local-video',jezik=APP_LANGUAGE)
            self.serve_original_player_html(html)
        self.original_player_note.setText('Local video: '+Path(path).name)
        self.log('INFO','PLAYER','Local file loaded: '+path)

    def export_studio_clip(self):
        if getattr(self,'_studio_local',None):self.export_local_clip()
        else:self.remote_cut()

    def export_local_clip(self):
        if not getattr(self,'_studio_local',None):
            QMessageBox.information(self,'No local video','Open a local video in Media Studio first.');return
        if self.remote_proc and self.remote_proc.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Busy','Wait for the current export.');return
        try:self.remote_start,self.remote_end=self.parse_cut_times()
        except ValueError:
            QMessageBox.warning(self,'Invalid range','Mark a valid start and end in the timeline.');return
        output,_=QFileDialog.getSaveFileName(self,'Export local clip',
            str(Path(self._studio_local).with_name(Path(self._studio_local).stem+'_cut.mp4')),'MP4 (*.mp4)')
        if not output:return
        if Path(output).resolve()==Path(self._studio_local).resolve():
            QMessageBox.warning(self,'Unsafe output','Do not overwrite the source video.');return
        if Path(output).exists() and QMessageBox.question(self,'Overwrite?','Replace existing output?')!=QMessageBox.Yes:return
        ffmpeg=shutil.which('ffmpeg') or str(BASE/'ffmpeg.exe')
        if not Path(ffmpeg).is_file() and not shutil.which('ffmpeg'):
            QMessageBox.warning(self,'FFmpeg missing','FFmpeg is required for exporting.');return
        self._multi_active=False
        self.remote_source=Path(self._studio_local)
        self.remote_output=output
        self.remote_proc=QProcess(self)
        self.remote_proc.setProgram(ffmpeg)
        self.remote_proc.setArguments(self.clip_ffmpeg_args(self.remote_source,output,self.remote_start,self.remote_end))
        self.cut_status.setText('Exporting local clip…')
        self.remote_proc.finished.connect(self.remote_export_finished)
        self.remote_proc.readyReadStandardOutput.connect(self.clip_ffmpeg_progress)
        self.watch_process(self.remote_proc,'FFMPEG',stderr=True,stdout=False)
        self.remote_proc.start()

    def clip_ffmpeg_args(self,source,output,start,end):
        ratios={'16:9 (YouTube)':(16,9),'9:16 (TikTok / Reels / Shorts)':(9,16),
                '1:1 (Square)':(1,1),'4:5 (Instagram)':(4,5),'3:4 (Portrait)':(3,4),
                '21:9 (Ultrawide)':(21,9),'4:3 (Classic)':(4,3)}
        args=['-hide_banner','-loglevel','warning','-nostats','-progress','pipe:1','-y','-ss',str(start),'-i',str(source),
              '-t',str(end-start),'-map','0:v:0','-map','0:a?']
        ratio=ratios.get(self.aspect.currentText())
        if ratio:
            w,h=ratio
            # Center crop with even dimensions for H.264 compatibility.
            args+=['-vf',rf'crop=trunc(min(iw\,ih*{w}/{h})/2)*2:trunc(min(ih\,iw*{h}/{w})/2)*2']
        return args+['-c:v','libx264','-preset','medium','-crf','19',
                     '-c:a','aac','-movflags','+faststart',str(output)]

    def auto_load_original_player(self):
        """Debounced auto-load, following the original Tkinter app's behavior."""
        links=extract_media_links(self.urls.toPlainText())
        if self.urls.toPlainText().strip() and not links:
            QMessageBox.warning(self,'Invalid links','Only supported media URLs are accepted.');return
        if self.mode.currentIndex()==3 and any(urllib.parse.urlsplit(u).hostname not in ('instagram.com','www.instagram.com') for u in links):
            QMessageBox.warning(self,'Instagram Photos','Use Instagram post links in this mode.');return
        if not links:return
        url=links[0]
        if not re.match(r'^https?://',url,re.I):return
        if url==self._original_preview_url:return
        self._studio_local=None
        self._original_preview_url=url
        self.log('INFO','PLAYER',f'Auto-load requested for {url}')
        if not WEB_ENGINE_AVAILABLE:
            self.original_player_note.setText('QtWebEngine is unavailable; use Preview Link instead.')
            return
        match=re.search(r'(?:v=|youtu\\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})',url)
        if match and ('youtube.com' in url.lower() or 'youtu.be' in url.lower()):
            self.original_player_note.setText('Original timeline loaded automatically • drag to select your clip')
            html=_player_html('youtube',video_id=match.group(1),jezik=APP_LANGUAGE)
            self.serve_original_player_html(html)
        else:
            self.original_player_note.setText('Preparing a local preview for this video source…')
            self.preview_link()

    def _on_player_loading_changed(self, info):
        # Qt reports the actual Chromium network error, unlike loadFinished(False).
        try:
            if info.status() == info.LoadStatus.LoadFailedStatus:
                self.log('ERROR', 'PLAYER',
                    f'WebEngine navigation failed: {info.url().toString()} | '
                    f'code={info.errorCode()} | {info.errorString()}')
        except Exception as exc:
            self.log('WARN', 'PLAYER', f'Could not inspect navigation status: {exc}')

    def _on_player_load_finished(self, ok):
        url = self.original_web.url().toString()
        if url == 'about:blank':
            return  # Intentional navigation when clearing the source.
        self.log('INFO' if ok else 'ERROR', 'PLAYER',
                 f'Player page loaded: {ok} | {url}')
        if not ok and hasattr(self, 'original_player_note'):
            self.original_player_note.setText(
                'Media Studio page could not load. Open Status Log for the network error.')

    def serve_original_player_html(self,html,video_directory=None):
        directory=Path(video_directory) if video_directory else None
        if not hasattr(self,'_original_player_dir'):
            self._original_player_dir=tempfile.TemporaryDirectory(prefix='mm_original_player_')
        root=directory or Path(self._original_player_dir.name)
        if getattr(self,'_original_server_root',None)!=str(root):
            if hasattr(self,'_original_server'):
                self._original_server.shutdown()
                self._original_server.server_close()
            # PyInstaller --windowed sets sys.stderr to None. The default
            # SimpleHTTPRequestHandler writes every request to stderr, which
            # can raise inside the HTTP request handler before headers are sent.
            # Keep HTTP diagnostics in the application's persistent status log.
            app_logger = self.log
            class PlayerHTTPHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(root), **kwargs)
                def translate_path(self, path):
                    requested = urllib.parse.urlsplit(path).path
                    if requested == '/local-video':
                        local = getattr(self.server, 'local_video_path', None)
                        if local and Path(local).is_file():
                            return str(Path(local).resolve())
                    return super().translate_path(path)
                def log_message(self, fmt, *args):
                    try:
                        app_logger('DEBUG', 'PLAYER HTTP', fmt % args)
                    except Exception:
                        pass
                def log_error(self, fmt, *args):
                    try:
                        severity = 'DEBUG' if self.path.startswith('/favicon.ico') else 'ERROR'
                        app_logger(severity, 'PLAYER HTTP', f'{self.path} | root={root} | ' + (fmt % args))
                    except Exception:
                        pass
            class PlayerHTTPServer(http.server.ThreadingHTTPServer):
                daemon_threads = True
                allow_reuse_address = True
                def handle_error(self, request, client_address):
                    try:
                        app_logger('ERROR', 'PLAYER HTTP',
                                   'Request handler crashed: ' + traceback.format_exc())
                    except Exception:
                        pass
            self._original_server=PlayerHTTPServer(('127.0.0.1',0),PlayerHTTPHandler)
            self._original_server.local_video_path = None
            self._original_server_thread=threading.Thread(
                target=self._original_server.serve_forever,daemon=True)
            self._original_server_thread.start()
            self._original_server_root=str(root)
        self._original_server.local_video_path = getattr(self, '_studio_local', None)
        # The player page is served over HTTP. Chromium blocks qrc:/// URLs
        # from HTTP origins, so expose Qt's bundled WebChannel JavaScript
        # through the SAME localhost server as the player HTML.
        webchannel_file=root/'qwebchannel.js'
        resource=QFile(':/qtwebchannel/qwebchannel.js')
        if not resource.open(QIODevice.OpenModeFlag.ReadOnly):
            self.log('ERROR','PLAYER',
                'Qt resource :/qtwebchannel/qwebchannel.js unavailable; cutting bridge cannot initialize.')
        else:
            try:
                js=bytes(resource.readAll())
                if not js or b'QWebChannel' not in js:
                    self.log('ERROR','PLAYER','Qt WebChannel JavaScript resource is empty or invalid.')
                else:
                    webchannel_file.write_bytes(js)
                    self.log('INFO','PLAYER',f'WebChannel bridge script served locally ({len(js)} bytes)')
            finally:
                resource.close()
        root.mkdir(parents=True, exist_ok=True)
        html_path=root/'player.html'
        html=html.replace('</head>', '''
        <script src="/qwebchannel.js"></script>
        <script>
        // Preserve the original pywebview API while using Qt WebChannel.
        // Queue early timeline callbacks until the asynchronous bridge is ready.
        (function(){
          const pending=[];
          let bridge=null;
          function invoke(name,args){
            if (bridge && typeof bridge[name]==='function') bridge[name].apply(bridge,args);
            else pending.push([name,args]);
          }
          window.pywebview={api:{
            oznaci_pocetak:function(t){invoke('oznaci_pocetak',[Number(t)]);},
            oznaci_kraj:function(t){invoke('oznaci_kraj',[Number(t)]);},
            skini_visestruke_isjecke:function(items){invoke('skini_visestruke_isjecke',[items]);},
            zatrazi_lokalni_pregled:function(){invoke('zatrazi_lokalni_pregled',[]);}
          }};
          if (typeof QWebChannel==='undefined') {
            console.error('Mister Muscle: local qwebchannel.js did not load.');
            return;
          }
          if (!window.qt || !qt.webChannelTransport) {
            console.error('Mister Muscle: Qt WebChannel transport unavailable.');
            return;
          }
          new QWebChannel(qt.webChannelTransport,function(channel){
            bridge=channel.objects.bridge;
            if (!bridge) { console.error('Mister Muscle: Python bridge object missing.'); return; }
            window.__mmBridge=bridge;
            while (pending.length) {
              const call=pending.shift();
              try { invoke(call[0],call[1]); }
              catch(e) { console.error('Mister Muscle bridge callback failed: '+e); }
            }
            console.info('Mister Muscle: Qt cutting bridge connected.');
          });
        })();
        </script>
        <style>
          body{background:#12172c!important;padding:10px!important;overflow-y:auto!important;height:auto!important;min-height:100%!important;}
          #omot{min-height:0!important;height:auto!important;flex:none!important;}
          #player-wrap{width:100%!important;aspect-ratio:16 / 9!important;height:auto!important;min-height:0!important;flex:0 0 auto!important;border-radius:13px!important;border-color:#333c60!important;}
          #player-wrap iframe,#player-wrap video,#player{width:100%!important;height:100%!important;object-fit:contain!important;}
          #timeline-container{background:#202744!important;border-color:#3a436b!important;}
          .shorts-panel,.selekcija-red{background:#1b223d!important;border-color:#343d63!important;backdrop-filter:none!important;}
          .kontrole button{border-radius:10px!important;box-shadow:none!important;}
          .shorts-panel input,.selekcija-polje input{background:#10162b!important;border-color:#41496c!important;}
          #status-bar{color:#7de0bc!important;}
        </style></head>''')
        html_path.write_text(html,encoding='utf-8')
        self.log('INFO','PLAYER',f'Player HTML written to {html_path}')
        url=f'http://127.0.0.1:{self._original_server.server_port}/player.html'
        # Confirm the local HTTP endpoint works before asking Chromium to load it.
        try:
            # Explicitly bypass system proxies for 127.0.0.1.
            local_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with local_opener.open(urllib.request.Request(url, headers={
                    'User-Agent': 'MisterMuscleDownloader/5.1'}), timeout=3) as response:
                sample=response.read(512)
                if response.status != 200 or not sample:
                    raise RuntimeError(f'HTTP {response.status}: empty player page')
            self.log('INFO','PLAYER',f'Local player server OK: {url}')
        except Exception as exc:
            self.log('ERROR','PLAYER',f'Local player server failed: {url} | {exc}')
            self.original_player_note.setText('Local player server unavailable. See Status Log.')
            return
        self.show_studio_player()
        self.original_web.setUrl(QUrl(url))

    def make_center(self):
        w,v=self.column()
        v.addWidget(heading('Download Center','Your videos, progress and completed files in one place.'))
        stats_frame=QFrame();stats_frame.setObjectName('summary')
        stats=QHBoxLayout(stats_frame);stats.setContentsMargins(20,12,20,12);stats.setSpacing(20)
        self.center_stats_cards={}
        for key,symbol in [('Completed','✓'),('Downloading','↓'),('Pending','◷'),('Failed','!')]:
            block=QWidget()
            inner=QHBoxLayout(block);inner.setContentsMargins(0,0,0,0);inner.setSpacing(8)
            caption=QLabel(symbol+'  '+key);caption.setObjectName('sub');inner.addWidget(caption)
            val=QLabel('0');val.setStyleSheet('font-size:14px;font-weight:800;color:#f4f0ff')
            inner.addWidget(val)
            self.center_stats_cards[key]=val
            stats.addWidget(block)
        stats.addStretch()
        v.addWidget(stats_frame)
        tools=QHBoxLayout()
        self.center_filters={}
        for name in ('All','Downloading','Completed','Failed'):
            b=QPushButton(name);b.setObjectName('chip');b.setCheckable(True)
            b.clicked.connect(lambda checked=False,n=name:self.set_center_filter(n))
            tools.addWidget(b);self.center_filters[name]=b
        tools.addStretch()
        tools.addWidget(button('Clear failed',self.clear_failed))
        self.center_search=QLineEdit();self.center_search.setPlaceholderText('Search downloads...')
        self.center_search.setMaximumWidth(310)
        self.center_search.textChanged.connect(self.refresh_center)
        tools.addWidget(self.center_search)
        v.addLayout(tools)
        self.center_scroll=QScrollArea();self.center_scroll.setWidgetResizable(True)
        self.center_scroll.setMinimumHeight(300)
        self.center_container=QWidget()
        self.center_layout=QVBoxLayout(self.center_container)
        self.center_layout.setSpacing(13);self.center_layout.setContentsMargins(0,4,8,12)
        self.center_scroll.setWidget(self.center_container);v.addWidget(self.center_scroll)
        self.set_center_filter('All')
        return w

    def set_center_filter(self,name):
        self.center_filter=name
        for key,b in self.center_filters.items():b.setChecked(key==name)
        self.refresh_center()

    def fetch_thumbnail(self, url):
        """Optional image retrieval from the inspected video's thumbnail URL."""
        meta=self.media_info.get(url,{})
        thumb=meta.get('thumbnail','')
        if not thumb.startswith('https://') or thumb in self.thumb_cache or thumb in self.thumb_pending:
            return
        self.thumb_pending.add(thumb)
        request=QNetworkRequest(QUrl(thumb))
        request.setRawHeader(b'User-Agent',b'Mozilla/5.0 MisterMuscleDownloader/7.0')
        reply=self.net.get(request)
        def finished():
            self.thumb_pending.discard(thumb)
            if reply.error()==reply.NetworkError.NoError:
                raw=bytes(reply.readAll())
                if len(raw)<4_000_000:
                    image=QPixmap()
                    if image.loadFromData(raw):
                        self.thumb_cache[thumb]=image
                        if self.stack.currentIndex()==1:self.refresh_center()
            reply.deleteLater()
        reply.finished.connect(finished)

    def thumbnail_widget(self,url):
        """Real thumbnail if metadata was inspected; neutral placeholder otherwise."""
        image=QLabel()
        image.setFixedSize(132,76)
        image.setAlignment(Qt.AlignCenter)
        image.setStyleSheet('background:#202744;border:1px solid #333a61;border-radius:11px;color:#a78dff;font-size:25px')
        meta=self.media_info.get(url,{})
        thumb=meta.get('thumbnail','')
        pixmap=self.thumb_cache.get(thumb)
        if pixmap:
            image.setPixmap(pixmap.scaled(132,76,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation))
        else:
            image.setText('▶')
            self.fetch_thumbnail(url)
        return image

    def center_task(self,title,subtitle,state,percent=None,detail='',filepath='',url='',active=False):
        frame=QFrame();frame.setObjectName('task')
        layout=QHBoxLayout(frame);layout.setContentsMargins(21,17,21,17);layout.setSpacing(17)
        badge=self.thumbnail_widget(url)
        layout.addWidget(badge)
        main=QVBoxLayout();main.setSpacing(7)
        meta=self.media_info.get(url,{})
        display_title=meta.get('title') or title or 'Untitled video'
        label=QLabel(display_title)
        label.setWordWrap(True);label.setStyleSheet('font-size:15px;font-weight:700')
        main.addWidget(label)
        extra=[]
        if meta.get('uploader'):extra.append(meta['uploader'])
        if isinstance(meta.get('duration'),(float,int)):
            d=int(meta['duration']);extra.append(f'{d//60}:{d%60:02d}')
        if meta.get('height'):extra.append(f"{meta['height']}p")
        info=QLabel('  •  '.join(extra+[subtitle]));info.setObjectName('sub');info.setWordWrap(True);main.addWidget(info)
        if percent is not None:
            progress=QProgressBar();progress.setValue(int(percent));progress.setTextVisible(False)
            main.addWidget(progress)
            if detail:
                d=QLabel(detail);d.setObjectName('sub');main.addWidget(d)
        layout.addLayout(main,1)
        actions=QVBoxLayout();actions.setSpacing(8)
        status=QLabel(state);status.setAlignment(Qt.AlignRight)
        status.setObjectName('active' if active else 'success' if state=='Completed' else 'error' if state=='Failed' else 'pending' if state=='Pending' else 'sub')
        actions.addWidget(status)
        if active:
            actions.addWidget(button('Ⅱ  Pause',self.pause_download))
            actions.addWidget(button('Cancel',self.cancel))
        elif state=='Pending':
            actions.addWidget(button('▶  Resume' if self.paused else 'Start queue',self.start_pending))
            actions.addWidget(button('Remove',lambda checked=False,u=url:self.remove_pending_url(u)))
        elif state=='Failed' and url:
            actions.addWidget(button('↻  Retry',lambda checked=False,u=url:self.retry_download(u)))
        elif filepath and Path(filepath).is_file():
            if Path(filepath).suffix.lower() in ('.mp4','.mkv','.mov','.webm','.avi'):
                actions.addWidget(button('▶  Play',lambda checked=False,p=filepath:self.play_file(p)))
            actions.addWidget(button('Open folder',lambda checked=False,p=filepath:self.reveal_file(p)))
        elif url:
            actions.addWidget(button('Copy link',lambda checked=False,u=url:QApplication.clipboard().setText(u)))
        actions.addStretch()
        layout.addLayout(actions)
        return frame

    def play_file(self,path):
        if Path(path).is_file():
            self.local_path=path
            self.player.setSource(QUrl.fromLocalFile(path))
            self.switch(4)
            self.player.play()

    def reveal_file(self,path):
        if not Path(path).exists():return
        if sys.platform=='win32':
            subprocess.Popen(['explorer','/select,',str(Path(path).resolve())])
        else:
            subprocess.Popen(['xdg-open',str(Path(path).resolve().parent)])

    def make_queue(self):
        w,v=self.column();v.addWidget(heading('Queue','Pending links waiting to be downloaded.'))
        self.queue_list=QListWidget();self.queue_list.setSelectionMode(QListWidget.ExtendedSelection);self.queue_list.setMinimumHeight(330);v.addWidget(self.queue_list)
        r=QHBoxLayout();r.addWidget(button('Start / Resume',self.start_pending,True));r.addWidget(button('Remove selected',self.remove_selected_queue));r.addWidget(button('Move up',lambda:self.move_queue(-1)));r.addWidget(button('Move down',lambda:self.move_queue(1)));r.addWidget(button('Clear pending',self.clear_queue));v.addLayout(r);return w
    def make_history(self):
        w,v=self.column();v.addWidget(heading('History','Successfully downloaded files in this Qt version.'))
        self.history_list=QListWidget();self.history_list.setSelectionMode(QListWidget.ExtendedSelection);self.history_list.setMinimumHeight(400);v.addWidget(self.history_list)
        r=QHBoxLayout()
        r.addWidget(button('▶  Play selected',self.play_selected_history))
        r.addWidget(button('Open selected folder',self.reveal_selected_history))
        r.addWidget(button('Remove selected',self.remove_history))
        v.addLayout(r);return w
    def make_player(self):
        w,v=self.column();v.addWidget(heading('Player & Cutting','Preview downloaded videos and cut clips with FFmpeg.'))
        c,cl=card();self.video=QVideoWidget();self.video.setMinimumHeight(310);self.player.setVideoOutput(self.video);cl.addWidget(self.video)
        r=QHBoxLayout();r.addWidget(button('Open local video',self.open_video));r.addWidget(button('Open last download',self.open_last_download));r.addWidget(button('▶ / ❚❚',self.toggle_play));cl.addLayout(r)
        self.seek=QSlider(Qt.Horizontal);self.seek.setRange(0,1000);self.seek.sliderMoved.connect(self.seek_video);cl.addWidget(self.seek)
        self.player.positionChanged.connect(self.update_position);self.player.durationChanged.connect(self.update_duration)
        self.local_path=None
        r=QHBoxLayout();self.cut_from=QLineEdit('00:00:00');self.cut_to=QLineEdit('00:00:10')
        r.addWidget(QLabel('From'));r.addWidget(self.cut_from);r.addWidget(QLabel('To'));r.addWidget(self.cut_to);cl.addLayout(r)
        r=QHBoxLayout();r.addWidget(button('Mark start at playhead',lambda:self.mark_cut(self.cut_from)));r.addWidget(button('Mark end at playhead',lambda:self.mark_cut(self.cut_to)));cl.addLayout(r)
        self.cut_button=button('✂  Export selected clip (accurate)',self.cut_clip,True);cl.addWidget(self.cut_button)
        self.remote_cut_button=button('✂  Cut from original link (selected quality)',self.remote_cut,True);cl.addWidget(self.remote_cut_button)
        self.cut_status=QLabel('Ready to cut');self.cut_status.setObjectName('sub');cl.addWidget(self.cut_status)
        info=QLabel('Local cutting uses the opened file. Cut from original link downloads the selected quality first, then exports the selected time range. It can take longer and use significant disk space. Some streams may be unavailable.')
        info.setWordWrap(True);info.setObjectName('sub');cl.addWidget(info);v.addWidget(c)
        v.addWidget(button('Open original advanced player / tools',self.open_legacy));return w
    def show_whats_new_if_needed(self):
        """Display release highlights once per app version, including after upgrades."""
        try:
            last_seen=WHATS_NEW_MARKER.read_text(encoding='utf-8').strip() if WHATS_NEW_MARKER.exists() else ''
        except OSError:
            last_seen=''
        if last_seen != APP_VERSION:
            self.show_whats_new()

    def show_whats_new(self):
        dialog=QDialog(self)
        dialog.setWindowTitle('What’s New — Mister Muscle Downloader v' + APP_VERSION)
        dialog.setMinimumWidth(540)
        dialog.resize(630, 520)
        layout=QVBoxLayout(dialog)
        layout.setContentsMargins(26,24,26,22)
        layout.setSpacing(14)
        title=QLabel('🚀  What’s New in v' + APP_VERSION)
        title.setStyleSheet('font-size:23px;font-weight:800;color:#f7f8ff')
        layout.addWidget(title)
        intro=QLabel('Latest features and fixes through v5.1.7.')
        intro.setWordWrap(True)
        intro.setObjectName('sub')
        layout.addWidget(intro)
        highlights=[
            ('🔔  Alarm sound repair', 'Bundled notification sound, improved error sound volume, a Test Alarm button in Status Log, and sound-load diagnostics.'),
            ('⛶  Player fullscreen', 'Embedded player fullscreen requests now open a fullscreen Qt window; Esc returns to the app.'),
            ('🧹  Cleaner player log', 'Ignore harmless YouTube/DoubleClick conversion tracking CORS console errors without disabling browser security.'),
            ('🐞  Report a Bug', 'Send a report with up to 3 screenshots and optional redacted diagnostics directly to the developer without an account.'),
            ('📋  Instant auto-paste', 'Supported YouTube, Instagram and TikTok links are added as soon as they are copied, even when the app is in the background. Disable with the checkbox in New Download.'),
            ('🔎  Clipboard filtering', 'Only supported media links are accepted; ordinary text and duplicate links are ignored.'),
            ('📸  Instagram Photos', 'Download photo posts and carousels with gallery-dl using browser cookies or a cookies.txt file where required.'),
            ('▶  YouTube controls', 'Show native YouTube playback controls when the embedded player allows them.'),
            ('🛠  Media Studio stability', 'Improved packaged-app local HTTP handling, 404 diagnostics, video routes and Qt WebEngine loading-status reporting.'),
            ('🔄  Update Center', 'Improved bundled component version checks and installer update download/launch flow.'),
            ('⚡  Faster release builds', 'Removed unconditional PyInstaller --clean for quicker repeat builds.'),
            ('🎨  Desktop workspace', 'Qt interface, Download Center, queue, history, clipping, format choices, and English/Croatian support.'),
        ]
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        inner=QWidget()
        content=QVBoxLayout(inner)
        content.setSpacing(12)
        for heading_text, description in highlights:
            heading_label=QLabel(heading_text)
            heading_label.setStyleSheet('font-size:14px;font-weight:700;color:#e8e0ff')
            content.addWidget(heading_label)
            detail=QLabel(description)
            detail.setObjectName('sub')
            detail.setWordWrap(True)
            content.addWidget(detail)
        content.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll,1)
        close_button=button('Let’s go!',dialog.accept,True)
        layout.addWidget(close_button)
        if APP_LANGUAGE=='hr':
            for label in dialog.findChildren(QLabel):
                label.setText(ui_translate(label.text()))
            for control in dialog.findChildren(QPushButton):
                control.setText(ui_translate(control.text()))
            dialog.setWindowTitle('Što je novo — Mister Muscle Downloader v'+APP_VERSION)
        dialog.exec()
        try:
            WHATS_NEW_MARKER.write_text(APP_VERSION,encoding='utf-8')
        except OSError as exc:
            self.log('WARN','UPDATE',f'Could not save What’s New state: {exc}')

    def _clear_finished_worker(self, name, worker):
        if getattr(self, name, None) is worker:
            setattr(self, name, None)

    def check_updates(self):
        if (getattr(self, '_update_worker', None) is not None
                and shiboken6.isValid(self._update_worker)
                and self._update_worker.isRunning()):
            return
        self.update_status.setText('Checking for updates in the background…')
        self.update_button.setEnabled(False)
        self.log('INFO', 'UPDATE', 'Checking GitHub releases, yt-dlp, PySide6 and local FFmpeg')
        worker = UpdateCheckWorker(self)
        self._update_worker = worker
        worker.completed.connect(self.show_update_results)
        worker.finished.connect(lambda w=worker: self._clear_finished_worker('_update_worker', w))
        worker.finished.connect(lambda: self.update_button.setEnabled(True))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def show_update_results(self, results):
        updates = []
        lines = []
        for name, current, latest, is_newer, url in results:
            if is_newer:
                lines.append(f'UPDATE AVAILABLE: {name} — {current} → {latest}')
                self.log('WARN', 'UPDATE', f'{name}: {current} -> {latest}')
                if name == 'Mister Muscle Downloader' and url:
                    updates.append((name, latest, url))
                elif name in ('yt-dlp', 'PySide6') and getattr(sys, 'frozen', False):
                    lines.append('Bundled component: update with the next Mister Muscle installer.')
                elif name in ('yt-dlp', 'PySide6'):
                    updates.append((name, latest, url))
                elif name == 'Mister Muscle Downloader':
                    lines.append('GitHub Release has no compatible EXE installer yet.')
                elif getattr(sys, 'frozen', False):
                    lines.append(f'{name} is bundled; update through a future Mister Muscle installer.')
            else:
                lines.append(f'{name}: {current} | {latest}')
                self.log('WARN' if latest.startswith('Check unavailable') else 'INFO', 'UPDATE', f'{name}: {latest}')
        self.update_status.setText('\n'.join(lines))
        if updates:
            if (getattr(self, '_download_worker', None) is not None
                and shiboken6.isValid(self._download_worker)
                and self._download_worker.isRunning()):
                return
            worker = UpdateDownloadWorker(updates, self)
            self._download_worker = worker
            worker.progress.connect(lambda msg: self.log('INFO', 'UPDATE', msg))
            worker.completed.connect(self.show_download_results)
            worker.finished.connect(lambda w=worker: self._clear_finished_worker('_download_worker', w))
            worker.finished.connect(worker.deleteLater)
            worker.start()
        else:
            self.log('INFO', 'UPDATE', 'No downloadable updates found')

    def show_download_results(self, results):
        installers = []
        lines = []
        for entry in results:
            name, result = entry[:2]
            self.log('ERROR' if 'failed' in result.lower() else 'INFO', 'UPDATE', name + ': ' + result)
            lines.append(f'{name}: {result}')
            if name == 'Mister Muscle Downloader' and len(entry) > 2:
                installer = Path(entry[2])
                if installer.is_file() and installer.stat().st_size > 1024:
                    installers.append(installer)
        self.update_status.setText(self.update_status.text() + '\n\n' + '\n'.join(lines))
        if installers:
            self._pending_installer = str(installers[-1])
            self.install_update_button.setEnabled(True)
            answer = QMessageBox.question(
                self, 'Install Mister Muscle update',
                'The new Mister Muscle installer is ready.\n\n'
                'Install it now? The application will close and Windows may request permission.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            if answer == QMessageBox.StandardButton.Yes:
                self.install_downloaded_update()

    def install_downloaded_update(self):
        path = Path(getattr(self, '_pending_installer', ''))
        expected = (DATA / 'updates').resolve()
        if not path.is_file() or path.suffix.lower() != '.exe' or path.resolve().parent != expected:
            QMessageBox.warning(self, 'Installer unavailable', 'The downloaded installer could not be verified locally.')
            return
        if not getattr(sys, 'frozen', False):
            QMessageBox.information(self, 'Developer mode', 'Automatic installation is only available in the installed Windows app.')
            return
        self.log('INFO', 'UPDATE', 'Launching installer: ' + str(path))
        try:
            # Windows launches the installer as a separate process; UAC remains under user control.
            os.startfile(str(path))
        except OSError as exc:
            self.log('ERROR', 'UPDATE', 'Could not start installer: ' + str(exc))
            QMessageBox.warning(self, 'Update failed', str(exc))
            return
        self.close()

    def make_bug_report(self):
        w,v=self.column()
        v.addWidget(heading('Report a Bug','Send a problem report directly to the developer. No account needed.'))
        c,cl=card()
        cl.addWidget(QLabel('Problem category'))
        self.bug_category=QComboBox()
        self.bug_category.addItems(['Player / Media Studio','Downloads','Instagram Photos','Auto-Paste','Updates','Other'])
        cl.addWidget(self.bug_category)
        cl.addWidget(QLabel('Describe the problem (at least 10 characters)'))
        self.bug_description=QTextEdit()
        self.bug_description.setPlaceholderText('What happened? What did you expect? How can we reproduce it?')
        self.bug_description.setMinimumHeight(115)
        cl.addWidget(self.bug_description)
        cl.addWidget(QLabel('Screenshots (up to 3 PNG/JPG/WEBP, max 5 MB each)'))
        self.bug_images=[]
        self.bug_image_list=QListWidget()
        self.bug_image_list.setMaximumHeight(135)
        cl.addWidget(self.bug_image_list)
        row=QHBoxLayout()
        row.addWidget(button('Add images',self.bug_add_images))
        row.addWidget(button('Paste screenshot',self.bug_paste_screenshot))
        row.addWidget(button('Remove selected',self.bug_remove_image))
        cl.addLayout(row)
        self.bug_include_log=QCheckBox('Include recent Status Log (sensitive content redacted)')
        self.bug_include_log.setChecked(False)
        cl.addWidget(self.bug_include_log)
        note=QLabel('Before sending, review the description, images and optional log preview. Screenshots may contain personal information. Reports are stored privately.')
        note.setWordWrap(True);note.setObjectName('sub');cl.addWidget(note)
        cl.addWidget(button('Preview report',self.bug_preview))
        self.bug_send_button=button('Send Bug Report',self.bug_send,True)
        cl.addWidget(self.bug_send_button)
        self.bug_status=QLabel('Ready to report')
        self.bug_status.setWordWrap(True);self.bug_status.setObjectName('sub')
        cl.addWidget(self.bug_status)
        v.addWidget(c)
        return w

    def bug_add_images(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Select screenshots',str(Path.home()),'Images (*.png *.jpg *.jpeg *.webp)')
        for path in paths:
            if len(self.bug_images)>=3:break
            if path not in self.bug_images and Path(path).is_file() and Path(path).stat().st_size<=5*1024*1024:
                self.bug_images.append(path)
        self.bug_refresh_images()

    def bug_paste_screenshot(self):
        image=QApplication.clipboard().image()
        if image.isNull():
            QMessageBox.information(self,'Screenshot','Clipboard does not contain an image.');return
        if len(self.bug_images)>=3:
            QMessageBox.warning(self,'Screenshots','Maximum 3 screenshots.');return
        path=DATA / ('bug_clipboard_' + str(datetime.now().timestamp()).replace('.','_') + '.png')
        if not image.save(str(path),'PNG') or path.stat().st_size>5*1024*1024:
            path.unlink(missing_ok=True)
            QMessageBox.warning(self,'Screenshot','Screenshot could not be saved or exceeds 5 MB.');return
        self.bug_images.append(str(path));self.bug_refresh_images()

    def bug_remove_image(self):
        index=self.bug_image_list.currentRow()
        if 0<=index<len(self.bug_images):self.bug_images.pop(index)
        self.bug_refresh_images()

    def bug_refresh_images(self):
        self.bug_image_list.clear()
        for path in self.bug_images:
            self.bug_image_list.addItem(Path(path).name + '  (' + str(round(Path(path).stat().st_size/1024)) + ' KB)')

    def bug_payload(self):
        description=self.bug_description.toPlainText().strip()
        if not 10<=len(description)<=10000:
            raise ValueError('Description must contain 10–10000 characters.')
        images=[]
        for path in self.bug_images:
            file=Path(path)
            data=file.read_bytes()
            if len(data)>5*1024*1024:raise ValueError('Each screenshot must be smaller than 5 MB.')
            ext=file.suffix.lower()
            mime={' .png':'image/png','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}.get(ext)
            if not mime:raise ValueError('Only PNG, JPG and WEBP screenshots are supported.')
            images.append({'mime':mime,'data':base64.b64encode(data).decode('ascii')})
        return {'category':self.bug_category.currentText(), 'description':description,
                'app_version':APP_VERSION, 'system_info':platform.system()+' '+platform.release(),
                'diagnostic_log':scrub_bug_log('\n'.join(line for _,line in self._log_lines)) if self.bug_include_log.isChecked() else '',
                'images':images}

    def bug_preview(self):
        try:payload=self.bug_payload()
        except Exception as exc:QMessageBox.warning(self,'Invalid report',str(exc));return
        dialog=QDialog(self);dialog.setWindowTitle('Review Bug Report');dialog.resize(650,480)
        layout=QVBoxLayout(dialog)
        preview=QPlainTextEdit();preview.setReadOnly(True)
        preview.setPlainText('Category: '+payload['category']+'\nVersion: '+payload['app_version']+
            '\nSystem: '+payload['system_info']+'\nScreenshots: '+', '.join(Path(x).name for x in self.bug_images)+
            '\n\nDescription:\n'+payload['description']+'\n\nDiagnostic log:\n'+(payload['diagnostic_log'] or '(not included)'))
        layout.addWidget(preview)
        layout.addWidget(button('Close preview',dialog.accept))
        dialog.exec()

    def bug_send(self):
        try:payload=self.bug_payload()
        except Exception as exc:QMessageBox.warning(self,'Invalid report',str(exc));return
        if QMessageBox.question(self,'Send Bug Report',
            'Send the description, '+str(len(payload['images']))+' screenshot(s) and '+
            ('redacted diagnostics' if payload['diagnostic_log'] else 'no diagnostics')+
            ' to the developer? Review screenshots for personal information before continuing.')!=QMessageBox.Yes:return
        self.bug_send_button.setEnabled(False)
        self.bug_status.setText('Sending report…')
        self.bug_worker=BugReportWorker(payload,self)
        self.bug_worker.completed.connect(self.bug_sent)
        self.bug_worker.start()

    def bug_sent(self,ok,message):
        self.bug_send_button.setEnabled(True)
        if ok:
            self.bug_status.setText('Report sent successfully. ID: '+message)
            self.bug_description.clear();self.bug_images=[];self.bug_refresh_images()
            self.log('INFO','BUG REPORT','Report submitted: '+message)
        else:
            self.bug_status.setText('Could not send report: '+message)
            self.log('WARN','BUG REPORT',message)

    def make_settings(self):
        w,v=self.column();v.addWidget(heading('Settings','Downloader tools and configuration.'))
        c,cl=card();cl.addWidget(QLabel('MISTER MUSCLE • v' + APP_VERSION))
        info=QLabel('PySide6 interface • yt-dlp downloads • FFmpeg local cutting\nQueue recovery • Resume with yt-dlp partial files • FFmpeg cutting.\nOriginal advanced tools remain available.')
        info.setWordWrap(True);info.setObjectName('sub');cl.addWidget(info)
        language_row=QHBoxLayout()
        self.language_label=QLabel('Language / Jezik')
        self.language_select=QComboBox()
        self.language_select.addItem('English','en')
        self.language_select.addItem('Hrvatski','hr')
        self.language_select.setCurrentIndex(0 if APP_LANGUAGE=='en' else 1)
        self.language_select.currentIndexChanged.connect(self.change_language)
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_select,1)
        cl.addLayout(language_row)
        cl.addWidget(button('View What’s New in v' + APP_VERSION,self.show_whats_new))
        cl.addWidget(button('Change download folder',self.choose_folder))
        cl.addWidget(QLabel('UPDATE CENTER  •  Automatically checks on startup'))
        self.update_status=QLabel('Update check will start shortly…')
        self.update_status.setWordWrap(True)
        self.update_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cl.addWidget(self.update_status)
        self.update_button=button('Check for updates now',self.check_updates)
        cl.addWidget(self.update_button)
        self.install_update_button=button('Install downloaded update',self.install_downloaded_update,True)
        self.install_update_button.setEnabled(False)
        cl.addWidget(self.install_update_button)
        update_note=QLabel('Updates download to AppData/MisterMuscleQt/updates. When a new installer is ready, you can approve installation and restart. FFmpeg is checked locally only.')
        update_note.setObjectName('sub');update_note.setWordWrap(True);cl.addWidget(update_note)
        cl.addWidget(QLabel('All cutting controls are now in New Download → Media Studio.'));v.addWidget(c);return w
    def choose_instagram_cookies(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose cookies.txt',str(Path.home()),'Text files (*.txt);;All files (*)')
        if path:self.ig_cookie_path.setText(path)

    def update_instagram_cookie_controls(self,*_):
        file_mode=self.ig_cookie_source.currentIndex()==1
        self.ig_browser.setVisible(not file_mode)
        self.ig_cookie_path.setVisible(file_mode)

    def auto_paste_clipboard(self):
        if not hasattr(self,'autopaste_checkbox') or not self.autopaste_checkbox.isChecked():return
        # React to clipboard changes even when another window has focus.
        self.paste()

    def paste(self):
        links=extract_media_links(QApplication.clipboard().text())
        existing=set(x.strip() for x in self.urls.toPlainText().splitlines())
        new=[u for u in links if u not in existing]
        if new:self.urls.insertPlainText(('\n' if self.urls.toPlainText().strip() else '')+'\n'.join(new))
    def choose_folder(self):
        p=QFileDialog.getExistingDirectory(self,'Download folder',self.folder)
        if p:self.folder=p;self.folder_label.setText(p);self.persist_session()
    def open_folder(self):
        import webbrowser
        if sys.platform=='win32':os.startfile(self.folder)
        else:subprocess.Popen(['xdg-open',self.folder])
    def start_download(self):
        links=extract_media_links(self.urls.toPlainText())
        if self.urls.toPlainText().strip() and not links:
            QMessageBox.warning(self,'Invalid links','Only supported media URLs are accepted.');return
        if self.mode.currentIndex()==3 and any(urllib.parse.urlsplit(u).hostname not in ('instagram.com','www.instagram.com') for u in links):
            QMessageBox.warning(self,'Instagram Photos','Use Instagram post links in this mode.');return
        if not links:QMessageBox.information(self,'Missing links','Paste at least one link first.');return
        self.queue.extend((u,self.mode.currentIndex(),self.quality.currentText(),self.selected_download_format()) for u in links)
        self.urls.clear();self.paused=False;self.persist_session();self.run_next()
    def start_pending(self):
        self.paused=False
        self.pause_btn.setText('Ⅱ  Pause active download')
        self.persist_session()
        self.run_next()
    def remove_selected_queue(self):
        rows=sorted({i.row() for i in self.queue_list.selectedIndexes()},reverse=True)
        for row in rows:
            if 0<=row<len(self.queue):self.queue.pop(row)
        self.refresh_queue()

    def move_queue(self,direction):
        rows=sorted({i.row() for i in self.queue_list.selectedIndexes()})
        if not rows:return
        if direction>0:rows.reverse()
        next_selection=[]
        for row in rows:
            target=row+direction
            if 0<=target<len(self.queue):
                self.queue[row],self.queue[target]=self.queue[target],self.queue[row]
                next_selection.append(target)
            else:next_selection.append(row)
        self.refresh_queue()
        for row in next_selection:
            self.queue_list.item(row).setSelected(True)

    def remove_pending_url(self,url):
        for i,(candidate,mode,quality,fmt) in enumerate(self.queue):
            if candidate==url:
                self.queue.pop(i)
                self.refresh_queue()
                break

    def clear_failed(self):
        if not self.failed_items:return
        if QMessageBox.question(self,'Clear failed tasks','Remove all failed task entries from this session?')!=QMessageBox.Yes:return
        self.failed_items.clear()
        self.refresh_center();self.persist_session()

    def clear_queue(self):
        self.queue.clear();self.refresh_queue()
    def run_next(self):
        if self.paused:return
        if self.proc and self.proc.state()!=QProcess.NotRunning:return
        if not self.queue:
            self.status.setText('Queue completed.');self.refresh_center();return
        self.current_url,mode,quality,output_format=self.queue.pop(0);self.current_output_format=output_format;self.current_title=self.media_info.get(self.current_url,{}).get('title') or self.current_url;self.current_mode=mode;self.current_quality=quality;self.last_file='';self.canceled=False;self.pause_requested=False;self.output_buffer='';self.last_ui_percent=-1
        self.proc=QProcess(self);self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.on_output)
        self.watch_process(self.proc,'DOWNLOAD',stderr=False,stdout=False)
        self.proc.finished.connect(self.on_finished)
        if mode==3:
            gallery=str(TOOLS_DIR/'gallery-dl.exe') if getattr(sys,'frozen',False) else (shutil.which('gallery-dl') or str(TOOLS_DIR/'gallery-dl.exe'))
            if not Path(gallery).is_file():
                self.log('ERROR','INSTAGRAM','gallery-dl.exe missing from tools folder')
                QMessageBox.warning(self,'Instagram Photos','gallery-dl.exe is missing. Rebuild with gallery-dl bundled.')
                self.proc=None;self.start_btn.setEnabled(True);self.queue.insert(0,(self.current_url,mode,quality,output_format));return
            if self.ig_cookie_source.currentIndex()==1:
                cookie_path=self.ig_cookie_path.text().strip()
                if not Path(cookie_path).is_file():
                    QMessageBox.warning(self,'Instagram Photos','Choose an existing cookies.txt file.')
                    self.proc=None;self.start_btn.setEnabled(True);self.queue.insert(0,(self.current_url,mode,quality,output_format));return
                cookie_args=['--cookies',cookie_path]
            else:
                cookie_args=['--cookies-from-browser',self.ig_browser.currentText().lower()]
            self.log('INFO','INSTAGRAM','Starting gallery-dl with selected cookie source')
            self.proc.start(gallery,[*cookie_args,'--directory',self.folder,self.current_url])
            self.start_btn.setEnabled(False)
            self.persist_session();self.refresh_queue();self.refresh_center()
            return
        fmt={'Best available':None,'2160p':2160,'1440p':1440,'1080p':1080,'720p':720,'480p':480,'360p':360}[quality]
        args=['-m','yt_dlp','--newline','--continue','--no-playlist','--print','after_move:filepath','-P',self.folder,'-o','%(title).180B [%(id)s].%(ext)s']
        if mode==2:args+=['-x','--audio-format',('vorbis' if output_format=='ogg' else output_format),'--audio-quality','0']
        elif mode==1:
            height=f'[height<={fmt}]' if fmt else ''
            preferred=f'bestvideo[ext={output_format}]{height}/bestvideo{height}' if output_format in ('mp4','webm') else f'bestvideo{height}'
            args+=['-f',preferred,'--remux-video',output_format]
        else:args+=['-f',f'bestvideo[height<={fmt}]+bestaudio/best[height<={fmt}]' if fmt else 'bestvideo+bestaudio/best','--merge-output-format',output_format,'--remux-video',output_format]
        args.append(self.current_url)
        self.download_percent=0;self.download_detail='Preparing download...';self.progress.setValue(0);self.status.setText('Starting: '+self.current_url)
        self.proc.start(YTDLP_EXE,ytdlp_args(args));self.start_btn.setEnabled(False)
        self.pause_btn.setText('Ⅱ  Pause active download')
        self.persist_session()
        self.refresh_queue();self.refresh_center()
    def on_output(self,flush=False):
        if not self.proc:return
        self.output_buffer+=bytes(self.proc.readAllStandardOutput()).decode('utf-8',errors='replace')
        chunks=self.output_buffer.replace('\r','\n').split('\n')
        if flush:
            lines=chunks
            self.output_buffer=''
        else:
            lines=chunks[:-1]
            self.output_buffer=chunks[-1][-2048:]
        changed=False
        for line in lines:
            m=re.search(r'\[download\]\s+(\d+(?:\.\d+)?)%',line)
            if line.strip():
                self.log('ERROR' if 'ERROR:' in line else 'WARN' if 'WARNING:' in line else 'INFO','DOWNLOAD',line.strip())
            if m:
                pct=min(100,int(float(m.group(1))))
                if pct!=self.download_percent or self.download_detail!=line.strip()[:160]:
                    self.download_percent=pct
                    self.download_detail=line.strip()[:160]
                    self.progress.setValue(pct)
                    changed=True
            if '[download] Destination:' in line and not self.media_info.get(self.current_url,{}).get('title'):
                self.current_title=Path(line.split('Destination:',1)[1].strip()).name
            path=line.strip()
            if path and (path.startswith(str(Path(self.folder))) or Path(path).is_absolute()):
                if Path(path).is_file():self.last_file=path
            if '[Merger]' in line:self.status.setText('Merging video and audio...')
            elif m:self.status.setText(line.strip()[:190])
            elif 'ERROR:' in line:self.status.setText(line.strip()[:190])
        if changed and self.stack.currentIndex()==1:self.refresh_center()

    def pause_download(self):
        """Stop yt-dlp without deleting .part files; retry with --continue on Resume."""
        if not self.proc or self.proc.state()==QProcess.NotRunning:
            QMessageBox.information(self,'Nothing to pause','No active download is running.')
            return
        if self.pause_requested:return
        self.pause_requested=True
        self.paused=True
        self.status.setText('Pausing download; partial files will be kept…')
        self.pause_btn.setEnabled(False)
        self.proc.kill()

    def persist_session(self):
        if self.session_loading:return
        current=None
        if self.proc and self.proc.state()!=QProcess.NotRunning:
            current=[self.current_url,self.current_mode,self.current_quality,self.current_output_format]
        data={'version':2,'folder':self.folder,'queue':[list(x) for x in self.queue],
              'failed':self.failed_items,'paused':self.paused,'active':current}
        try:
            temp=SESSION.with_suffix('.tmp')
            temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            temp.replace(SESSION)
        except OSError as e:
            self.status.setText('Warning: Could not save queue: '+str(e)) if hasattr(self,'status') else None

    def restore_session(self):
        if not SESSION.exists():return
        try:
            data=json.loads(SESSION.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version') not in (1,2):return
            self.session_loading=True
            folder=data.get('folder')
            if isinstance(folder,str) and Path(folder).is_dir():
                self.folder=folder;self.folder_label.setText(folder)
            queue=[task for x in data.get('queue',[])[:1000] if (task:=self.normalize_task(x)) is not None]
            active=self.normalize_task(data.get('active'))
            if active:queue.insert(0,active)
            self.queue=queue
            failed=data.get('failed',[])
            self.failed_items=[x for x in failed[:1000] if isinstance(x,dict) and isinstance(x.get('url'),str)]
            self.paused=bool(self.queue)
            self.status.setText('Restored pending downloads. Press Start / Resume to continue.' if self.queue else 'Ready for a new download')
            self.session_loading=False
            self.refresh_queue()
            self.persist_session()
        except (OSError,ValueError,TypeError,KeyError) as e:
            self.session_loading=False
            QMessageBox.warning(self,'Session recovery','Could not restore saved queue: '+str(e))

    def on_finished(self,exitcode,status):
        self.on_output(flush=True)
        self.log('INFO' if exitcode==0 else 'ERROR','DOWNLOAD',f'Process finished: exit={exitcode}, status={status}')
        if self.pause_requested:
            self.queue.insert(0,(self.current_url,self.current_mode,self.current_quality,self.current_output_format))
            self.pause_requested=False
            self.proc=None
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText('▶  Resume via Queue')
            self.status.setText('Paused — partial download kept. Use Queue > Start / Resume.')
            self.refresh_queue()
            self.persist_session()
            return
        ok=(exitcode==0 and status==QProcess.NormalExit)
        if ok:
            self.progress.setValue(100);self.finished_count+=1
            self.history.insert(0,{'url':self.current_url,'title':self.current_title,'date':datetime.now().strftime('%Y-%m-%d %H:%M'),'mode':self.current_mode,'file':self.last_file,'metadata':self.media_info.get(self.current_url,{})})
            HISTORY.write_text(json.dumps(self.history,ensure_ascii=False,indent=2),encoding='utf-8')
            self.status.setText('✓ Download completed')
        else:
            self.status.setText(('Canceled: ' if self.canceled else '✕ Download failed: ')+self.current_url)
            if not self.canceled:self.failed_items.append({'url':self.current_url,'date':datetime.now().strftime('%Y-%m-%d %H:%M'),'mode':self.current_mode,'quality':getattr(self,'current_quality',self.quality.currentText()),'format':getattr(self,'current_output_format','mp4')})
        self.start_btn.setEnabled(True);self.proc=None
        self.refresh_center();self.refresh_history();self.persist_session();self.run_next()
    def cancel(self):
        if self.proc and self.proc.state()!=QProcess.NotRunning:
            self.canceled=True;self.paused=False;self.queue.clear();self.proc.kill();self.status.setText('Canceled')
            self.persist_session()
    def refresh_queue(self):
        self.queue_list.clear()
        for u,mode,q,fmt in self.queue:self.queue_list.addItem(f'{u}  •  {q}  •  {fmt.upper()}')
        self.refresh_center()
        self.persist_session()
    def clip_center_update(self, detail=None, percent=None):
        if detail is not None:self.clip_detail=str(detail)
        if percent is not None:self.clip_percent=max(0,min(100,int(percent)))
        if hasattr(self,'center_layout'):
            self.refresh_center()

    def clip_diagnostic_tick(self):
        if not self.remote_proc or self.remote_proc.state()==QProcess.NotRunning:return
        import time
        now=time.monotonic()
        if now-self._clip_last_activity>=15:
            elapsed=int(now-self._clip_started)
            silent=int(now-self._clip_last_activity)
            self.log('WARN' if silent>=60 else 'INFO','CLIP DIAGNOSTICS',
                     f'Stage={self.remote_stage}; elapsed={elapsed}s; no output for {silent}s; '
                     f'process state={self.remote_proc.state()}; output={self.remote_output}; '
                     f'progress={self.clip_percent}%. FFmpeg may still be encoding.')
            self._clip_last_activity=now  # repeat diagnostic every 15s, not every timer tick

    def clip_begin_stage(self,stage,detail):
        import time
        self.remote_stage=stage
        self.clip_percent=0 if stage=='download' else 50
        self.clip_detail=detail
        self._clip_started=time.monotonic()
        self._clip_last_activity=self._clip_started
        self._clip_last_log=-1
        self._clip_ffmpeg_buffer=''
        if not hasattr(self,'_clip_diagnostic_timer'):
            self._clip_diagnostic_timer=QTimer(self)
            self._clip_diagnostic_timer.setInterval(15000)
            self._clip_diagnostic_timer.timeout.connect(self.clip_diagnostic_tick)
        self._clip_diagnostic_timer.start()
        self.log('INFO','CLIP DIAGNOSTICS',f'Starting {stage}: {detail}; output={self.remote_output}')
        self.clip_center_update()

    def clip_ffmpeg_progress(self):
        if not self.remote_proc:return
        import time
        data=bytes(self.remote_proc.readAllStandardOutput()).decode('utf-8',errors='replace')
        self._clip_ffmpeg_buffer+=data
        while '\n' in self._clip_ffmpeg_buffer:
            line,self._clip_ffmpeg_buffer=self._clip_ffmpeg_buffer.split('\n',1)
            line=line.strip()
            if not line or '=' not in line:continue
            key,value=line.split('=',1)
            if key in ('out_time_us','out_time_ms','out_time'):
                try:
                    if key=='out_time':
                        parts=value.split(':');seconds=float(parts[-1])+60*float(parts[-2])+3600*float(parts[-3])
                    else:seconds=int(value)/1000000
                    duration=max(0.001,self.remote_end-self.remote_start)
                    pct=min(99,max(0,int(seconds/duration*100)))
                    self._clip_last_activity=time.monotonic()
                    if pct!=self._clip_last_log and (pct//5!=self._clip_last_log//5 or pct>=99):
                        self._clip_last_log=pct
                        self.log('INFO','CLIP PROGRESS',f'FFmpeg encoding {pct}% ({seconds:.1f}s / {duration:.1f}s)')
                    self.clip_center_update(f'FFmpeg encoding: {pct}% • {seconds:.1f}s / {duration:.1f}s',50+pct//2)
                    self.cut_status.setText(self.clip_detail)
                except (ValueError,IndexError,OverflowError):pass
            elif key=='speed':
                self.log('DEBUG','CLIP DIAGNOSTICS',f'FFmpeg speed={value}')
            elif key=='progress' and value=='end':
                self.log('INFO','CLIP DIAGNOSTICS','FFmpeg reported progress=end')

    def refresh_center(self):
        if not hasattr(self,'center_layout'):return
        active=bool(self.proc and self.proc.state()!=QProcess.NotRunning)
        clip_active=bool(self.remote_proc and self.remote_proc.state()!=QProcess.NotRunning)
        for key,count in [('Completed',len(self.history)),('Downloading',int(active)+int(clip_active)),
                          ('Pending',len(self.queue)),('Failed',len(self.failed_items))]:
            self.center_stats_cards[key].setText(str(count))
        while self.center_layout.count():
            item=self.center_layout.takeAt(0)
            widget=item.widget()
            if widget:widget.deleteLater()
        search=self.center_search.text().strip().casefold()
        shown=0
        def matches(title,other=''):
            return not search or search in (str(title)+' '+str(other)).casefold()
        if self.center_filter in ('All','Downloading') and clip_active and matches('Clip export',self.remote_url or self.remote_output or ''):
            self.center_layout.addWidget(self.center_task(
                '✂ Clip: '+Path(self.remote_output or 'clip.mp4').name,
                self.clip_detail or 'Preparing clip', 'Downloading',
                self.clip_percent,self.clip_detail,url=self.remote_url or '',active=True))
            shown+=1
        if self.center_filter in ('All','Downloading') and active and matches(self.current_title,self.current_url):
            self.center_layout.addWidget(self.center_task(
                self.current_title,self.current_url,'Downloading',
                self.download_percent,self.download_detail,url=self.current_url,active=True))
            shown+=1
        if self.center_filter in ('All','Downloading'):
            for url,mode,quality,fmt in self.queue[:100]:
                if not matches(url,quality):continue
                self.center_layout.addWidget(self.center_task(
                    url,quality,'Pending',None,url=url))
                shown+=1
        if self.center_filter in ('All','Completed'):
            for record in self.history[:200]:
                title=record.get('title') or record.get('url') or 'Untitled'
                if not matches(title,record.get('url','')):continue
                self.center_layout.addWidget(self.center_task(
                    title,record.get('date','')+'  •  '+str(record.get('mode','')),
                    'Completed',100,filepath=record.get('file',''),url=record.get('url','')))
                shown+=1
        if self.center_filter in ('All','Failed'):
            for record in reversed(self.failed_items[-100:]):
                if not matches(record.get('url','')):continue
                self.center_layout.addWidget(self.center_task(
                    record.get('url',''),record.get('date',''),'Failed',
                    url=record.get('url','')))
                shown+=1
        if not shown:
            empty=QFrame();empty.setObjectName('empty')
            ev=QVBoxLayout(empty);ev.setContentsMargins(24,28,24,28);ev.setSpacing(13)
            art=QLabel('↓');art.setAlignment(Qt.AlignCenter)
            art.setStyleSheet('font-size:40px;color:#a08bff')
            ev.addWidget(art)
            title=QLabel('Everything you download, in one place' if self.center_filter=='All'
                         else 'Nothing in '+self.center_filter.lower()+' yet')
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet('font-size:20px;font-weight:750;color:#f1efff')
            ev.addWidget(title)
            desc=QLabel('Paste a video link to start downloading. Your tasks will appear here with live progress.' if self.center_filter=='All'
                        else 'Try another filter or start a new download.')
            desc.setWordWrap(True);desc.setAlignment(Qt.AlignCenter);desc.setObjectName('sub')
            ev.addWidget(desc)
            action=button('＋  Create new download',lambda:self.switch(0),True)
            action.setMaximumWidth(240)
            row=QHBoxLayout();row.addStretch();row.addWidget(action);row.addStretch();ev.addLayout(row)
            self.center_layout.addWidget(empty)
        self.center_layout.addStretch()

    def refresh_history(self):
        self.history_list.clear()
        for r in self.history:self.history_list.addItem(f"{r.get('date','')}   •   {r.get('title',r.get('url',''))}")
    def remove_history(self):
        rows=sorted((self.history_list.row(i) for i in self.history_list.selectedItems()),reverse=True)
        for n in rows:self.history.pop(n)
        HISTORY.write_text(json.dumps(self.history,ensure_ascii=False,indent=2),encoding='utf-8');self.refresh_history()
    def play_selected_history(self):
        row=self.history_list.currentRow()
        if row<0 or row>=len(self.history):return
        path=self.history[row].get('file','')
        if path and Path(path).is_file():
            self.play_file(path)
        else:
            QMessageBox.information(self,'File not found','The downloaded file is no longer at its saved location.')

    def reveal_selected_history(self):
        row=self.history_list.currentRow()
        if row<0 or row>=len(self.history):return
        path=self.history[row].get('file','')
        if path and Path(path).is_file():
            self.reveal_file(path)
        else:
            QMessageBox.information(self,'File not found','The downloaded file is no longer at its saved location.')

    def retry_download(self,url):
        """Retry a failed URL with the currently selected format and quality."""
        if not url:return
        failed=next((item for item in reversed(self.failed_items) if item.get('url')==url),{})
        self.failed_items=[item for item in self.failed_items if item.get('url')!=url]
        self.queue.append(self.normalize_task((url,failed.get('mode',self.mode.currentIndex()),failed.get('quality',self.quality.currentText()),failed.get('format',self.selected_download_format()))) or (url,self.mode.currentIndex(),self.quality.currentText(),self.selected_download_format()))
        self.refresh_queue()
        self.run_next()

    def load_history(self):
        try:
            data=json.loads(HISTORY.read_text(encoding='utf-8'));return data if isinstance(data,list) else []
        except (OSError,ValueError):return []
    def open_video(self):
        p,_=QFileDialog.getOpenFileName(self,'Open video',self.folder,'Video files (*.mp4 *.mkv *.mov *.webm *.avi);;All files (*)')
        if p:self.local_path=p;self.player.setSource(QUrl.fromLocalFile(p));self.player.play()
    def toggle_play(self):
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.pause()
        else:self.player.play()
    def seek_video(self,v):
        if self.player.duration():self.player.setPosition(int(v*self.player.duration()/1000))
    def update_position(self,p):
        if self.player.duration() and not self.seek.isSliderDown():self.seek.setValue(int(p*1000/self.player.duration()))
    def update_duration(self,d):pass
    def mark_cut(self, field):
        ms=self.player.position()
        seconds=ms//1000
        field.setText(f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}.{ms%1000:03d}')

    def open_last_download(self):
        for record in self.history:
            p=record.get('file','')
            if p and Path(p).is_file():
                self.local_path=p
                self.player.setSource(QUrl.fromLocalFile(p))
                self.player.play()
                return
        QMessageBox.information(self,'No file found','No completed video file with a known location was found.')

    def inspect_link(self):
        links=[line.strip() for line in self.urls.toPlainText().splitlines() if line.strip()]
        if not links:
            QMessageBox.information(self,'Missing link','Paste a video link first.');return
        if self.meta_proc and self.meta_proc.state()!=QProcess.NotRunning:return
        self.link_info.setText('Inspecting video metadata…')
        self.meta_proc=QProcess(self)
        self.meta_proc.setProgram(YTDLP_EXE)
        self.meta_proc.setArguments(ytdlp_args(['-m','yt_dlp','--dump-single-json','--skip-download','--no-playlist',links[0]]))
        self.meta_proc.finished.connect(self.metadata_finished)
        self.watch_process(self.meta_proc,'INSPECT',stderr=False,stdout=False)
        self.meta_proc.readyReadStandardError.connect(lambda:self._capture_process_output(self.meta_proc,'INSPECT',True))
        self.meta_proc.start()

    def metadata_finished(self,code,status):
        output=bytes(self.meta_proc.readAllStandardOutput()).decode('utf-8',errors='replace')
        errors=bytes(self.meta_proc.readAllStandardError()).decode('utf-8',errors='replace')
        if code!=0:
            self.log('ERROR','INSPECT',errors or f'Metadata inspect exited with code {code}')
            self.link_info.setText('Could not inspect link: '+errors[-250:]);return
        try:
            data=json.loads(output)
            links=[x.strip() for x in self.urls.toPlainText().splitlines() if x.strip()]
            if links:
                self.media_info[links[0]]={
                    'title':str(data.get('title') or ''),
                    'uploader':str(data.get('uploader') or ''),
                    'duration':data.get('duration'),
                    'thumbnail':str(data.get('thumbnail') or ''),
                    'width':data.get('width'),
                    'height':data.get('height'),
                }
            duration=data.get('duration')
            time=f'{int(duration)//60}:{int(duration)%60:02d}' if isinstance(duration,(float,int)) else 'unknown'
            self.link_info.setText(f"{data.get('title','Untitled')}  •  {data.get('uploader','Unknown creator')}  •  {time}  •  {data.get('extractor_key','')}")
            self.refresh_center()
        except (ValueError,TypeError):
            self.link_info.setText('Metadata unavailable for this link.')

    def preview_link(self):
        """Download a temporary low-resolution preview without blocking the Qt event loop."""
        links=[line.strip() for line in self.urls.toPlainText().splitlines() if line.strip()]
        if not links:
            QMessageBox.information(self,'Missing link','Paste a video link first.');return
        if self.remote_proc and self.remote_proc.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Remote cut active','Wait for the source download / clip export to finish.')
            return
        if self.preview_proc and self.preview_proc.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Preview busy','A preview is already being prepared.');return
        ffmpeg=shutil.which('ffmpeg') or str(BASE/'ffmpeg.exe')
        if not (shutil.which('ffmpeg') or Path(ffmpeg).is_file()):
            QMessageBox.warning(self,'FFmpeg missing','A working FFmpeg installation is required for preview conversion.');return
        # Keep previous preview files alive while the player might still reference them.
        if not hasattr(self,'_preview_dirs'):self._preview_dirs=[]
        self.preview_dir=tempfile.TemporaryDirectory(prefix='mm_preview_')
        self._preview_dirs.append(self.preview_dir)
        self.preview_file=str(Path(self.preview_dir.name)/'preview.mp4')
        self.preview_proc=QProcess(self)
        self.preview_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.preview_proc.setProgram(YTDLP_EXE)
        self.preview_proc.setArguments(ytdlp_args([
            '-m','yt_dlp','--no-playlist','--no-progress','--no-part',
            '-f','bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            '--merge-output-format','mp4','--recode-video','mp4',
            '-o',self.preview_file,links[0]]))
        self.preview_proc.finished.connect(self.preview_finished)
        self.watch_process(self.preview_proc,'PREVIEW',stderr=False,stdout=False)
        self.preview_proc.readyReadStandardOutput.connect(lambda:self._capture_process_output(self.preview_proc,'PREVIEW',False))
        self.link_info.setText('Preparing temporary preview (up to 480p). This may take a moment…')
        self.preview_proc.start()

    def preview_finished(self,code,status):
        output=bytes(self.preview_proc.readAllStandardOutput()).decode('utf-8',errors='replace')
        if code==0 and status==QProcess.NormalExit and Path(self.preview_file).is_file():
            self.local_path=self.preview_file
            self.player.setSource(QUrl.fromLocalFile(self.preview_file))
            if WEB_ENGINE_AVAILABLE:
                html=_player_html('generic',video_src='/preview.mp4',jezik=APP_LANGUAGE)
                self.serve_original_player_html(html,video_directory=self.preview_dir.name)
                self.original_player_note.setText('Original Mister Muscle timeline • local preview loaded automatically')
                self.switch(0)
            else:
                self.switch(4)
                self.player.play()
            self.cut_status.setText('Preview opened. Local cutting uses the temporary preview; remote cutting downloads the original quality.')
        else:
            self.link_info.setText('Preview unavailable: '+output[-400:])
        self.log('INFO' if code==0 else 'ERROR','PREVIEW',f'Preview process finished: exit={code}, file={self.preview_file}')
        self.preview_proc=None

    def parse_cut_times(self):
        def secs(t):
            parts=[float(x) for x in t.strip().split(':')]
            if not 1<=len(parts)<=3 or any(x<0 for x in parts):
                raise ValueError()
            total=0.0
            for x in parts:total=total*60+x
            return total
        start=secs(self.cut_from.text())
        end=secs(self.cut_to.text())
        if end<=start:raise ValueError()
        return start,end

    def export_multiple_selections(self,selections):
        """Export the original player's selected ranges from one source download."""
        if self.remote_proc and self.remote_proc.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Busy','Wait for the current cutting job.');return
        def seconds(value):
            values=[float(x) for x in str(value).strip().split(':')]
            if not 1<=len(values)<=3 or any(x<0 for x in values):raise ValueError()
            n=0.0
            for v in values:n=n*60+v
            return n
        try:
            ranges=[(seconds(start),seconds(end)) for start,end in selections]
            if not ranges or any(end<=start for start,end in ranges):raise ValueError()
        except (ValueError,TypeError):
            QMessageBox.warning(self,'Invalid clips','Check that every selection has valid Start / End times.');return
        folder=QFileDialog.getExistingDirectory(self,'Choose folder for all exported clips',self.folder)
        if not folder:return
        self._multi_ranges=ranges
        self._multi_folder=folder
        self._multi_index=0
        self.cut_from.setText(self.format_seconds(ranges[0][0]))
        self.cut_to.setText(self.format_seconds(ranges[0][1]))
        self.remote_cut(batch=True)

    @staticmethod
    def available_clip_filename(filename):
        """Suggest a new output name instead of overwriting an earlier clip."""
        path=Path(filename)
        if not path.exists():
            return str(path)
        for index in range(2, 10000):
            candidate=path.with_name(f'{path.stem}_{index}{path.suffix}')
            if not candidate.exists():
                return str(candidate)
        raise OSError('No available clip filename in the selected folder')

    def remote_cut(self,batch=False):
        """Fetch the original source at the requested quality, then perform accurate local cutting."""
        if self.remote_proc and self.remote_proc.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Busy','A remote cut is already in progress.');return
        if self.cut_proc and self.cut_proc.state()!=QProcess.NotRunning:
            QMessageBox.information(self,'Busy','Wait for the current export to finish.');return
        links=[line.strip() for line in self.urls.toPlainText().splitlines() if line.strip()]
        if not links:
            QMessageBox.information(self,'Missing link','Paste the source link in New Download first.');return
        try:
            self.remote_start,self.remote_end=self.parse_cut_times()
        except ValueError:
            QMessageBox.warning(self,'Invalid time','Enter valid start and end times, with end after start.');return
        ffmpeg=shutil.which('ffmpeg') or str(BASE/'ffmpeg.exe')
        if not (shutil.which('ffmpeg') or Path(ffmpeg).is_file()):
            QMessageBox.warning(self,'FFmpeg missing','Install FFmpeg before cutting.');return
        if batch:
            output=str(Path(self._multi_folder)/'MisterMuscle_clip_001.mp4')
        else:
            output,_=QFileDialog.getSaveFileName(self,'Save original-quality clip',
                        self.available_clip_filename(Path(self.folder)/'MisterMuscle_original_cut.mp4'),'MP4 video (*.mp4)')
            if not output:return
        # Resolve output conflicts before downloading the entire source.
        if Path(output).exists():
            if batch:
                output=self.available_clip_filename(output)
            elif QMessageBox.question(self,'Overwrite existing clip?',
                    'This file already exists. Replace it?')!=QMessageBox.Yes:
                self.cut_status.setText('Export canceled before source download.')
                return
        self._remote_overwrite_approved=not batch
        self._multi_active=bool(batch)
        self.remote_output=output
        self.remote_url=links[0]
        self.remote_format=self.quality.currentText()
        mode=self.mode.currentIndex()
        if mode>=2:
            QMessageBox.warning(self,'Video required','Select Video + audio or Video only.');return
        self.remote_tmp=tempfile.TemporaryDirectory(prefix='mm_source_cut_')
        source_dir=Path(self.remote_tmp.name)
        max_height={'Best available':None,'2160p':2160,'1440p':1440,'1080p':1080,
                    '720p':720,'480p':480,'360p':360}[self.remote_format]
        height=f'[height<={max_height}]' if max_height else ''
        fmt=f'bestvideo{height}+bestaudio/best{height}' if mode==0 else f'bestvideo{height}/best{height}'
        args=['-m','yt_dlp','--no-playlist','--newline','-f',fmt,
              '--merge-output-format','mkv','-P',str(source_dir),
              '-o','source.%(ext)s',self.remote_url]
        self.remote_proc=QProcess(self)
        self.remote_proc.setProcessChannelMode(QProcess.MergedChannels)
        self.remote_proc.setProgram(YTDLP_EXE)
        self.remote_proc.setArguments(ytdlp_args(args))
        self.remote_proc.readyReadStandardOutput.connect(self.remote_progress)
        self.watch_process(self.remote_proc,'REMOTE CUT',stderr=False,stdout=False)
        self.remote_proc.finished.connect(self.remote_download_finished)
        self.remote_cut_button.setEnabled(False)
        self.cut_status.setText('Downloading source at '+self.remote_format+' for accurate cutting…')
        self.clip_begin_stage('download','Downloading source for clip')
        self.remote_proc.start()

    def remote_progress(self):
        if self.remote_proc:
            lines=bytes(self.remote_proc.readAllStandardOutput()).decode('utf-8',errors='replace')
            for line in lines.splitlines():
                self.log('ERROR' if 'ERROR:' in line else 'WARN' if 'WARNING:' in line else 'INFO','REMOTE CUT',line)
                if '[download]' in line and '%' in line:
                    self.cut_status.setText('Source download: '+line.strip()[:120])
                    m=re.search(r'(\d+(?:\.\d+)?)%',line)
                    if m:
                        self.clip_center_update('Downloading source: '+m.group(1)+'%',int(float(m.group(1))*0.5))
                elif 'ERROR:' in line:
                    self.cut_status.setText(line.strip()[-250:])

    def remote_download_finished(self,code,status):
        self.remote_progress()
        self.remote_proc=None
        if code!=0 or status!=QProcess.NormalExit:
            self.remote_fail('Source download failed or was canceled.')
            return
        files=[f for f in Path(self.remote_tmp.name).iterdir()
               if f.is_file() and f.suffix.lower() in ('.mkv','.mp4','.webm','.mov')]
        if not files:
            self.remote_fail('Source video was not found after download.')
            return
        self.remote_source=max(files,key=lambda f:f.stat().st_size)
        if Path(self.remote_output).resolve()==self.remote_source.resolve():
            self.remote_fail('Output cannot overwrite source.');return
        # The initial output was checked before downloading; never ask again
        # after an expensive source fetch. For batch output, avoid collisions.
        if getattr(self,'_multi_active',False) and Path(self.remote_output).exists():
            self.remote_output=self.available_clip_filename(self.remote_output)
        ffmpeg=shutil.which('ffmpeg') or str(BASE/'ffmpeg.exe')
        self.remote_proc=QProcess(self)
        self.remote_proc.setProgram(ffmpeg)
        self.remote_proc.setArguments(self.clip_ffmpeg_args(self.remote_source,self.remote_output,self.remote_start,self.remote_end))
        self.clip_begin_stage('export','Source downloaded. FFmpeg encoding clip…')
        self.cut_status.setText('Source downloaded. Exporting accurate clip…')
        self.remote_proc.finished.connect(self.remote_export_finished)
        self.remote_proc.readyReadStandardOutput.connect(self.clip_ffmpeg_progress)
        self.watch_process(self.remote_proc,'FFMPEG',stderr=True,stdout=False)
        self.remote_proc.start()

    def _start_next_batch_export(self):
        ffmpeg=shutil.which('ffmpeg') or str(BASE/'ffmpeg.exe')
        self.remote_proc=QProcess(self)
        self.remote_proc.setProgram(ffmpeg)
        self.remote_proc.setArguments(self.clip_ffmpeg_args(self.remote_source,self.remote_output,self.remote_start,self.remote_end))
        self.clip_begin_stage('export',f'Exporting clip {self._multi_index+1}/{len(self._multi_ranges)}')
        self.cut_status.setText(f'Exporting clip {self._multi_index+1}/{len(self._multi_ranges)}…')
        self.remote_proc.finished.connect(self.remote_export_finished)
        self.remote_proc.readyReadStandardOutput.connect(self.clip_ffmpeg_progress)
        self.watch_process(self.remote_proc,'FFMPEG',stderr=True,stdout=False)
        self.remote_proc.start()

    def remote_export_finished(self,code,status):
        self.clip_ffmpeg_progress()
        errors=bytes(self.remote_proc.readAllStandardError()).decode('utf-8',errors='replace')
        self.log('INFO','CLIP DIAGNOSTICS',f'FFmpeg finished: exit_code={code}; exit_status={status}; stderr_tail={errors[-700:]}')
        success=(code==0 and status==QProcess.NormalExit and Path(self.remote_output).is_file())
        self.remote_proc=None
        if success:
            if getattr(self,'_multi_active',False):
                self._multi_index+=1
                if self._multi_index<len(self._multi_ranges):
                    self.remote_start,self.remote_end=self._multi_ranges[self._multi_index]
                    self.remote_output=str(Path(self._multi_folder)/f'MisterMuscle_clip_{self._multi_index+1:03d}.mp4')
                    self.remote_output=self.available_clip_filename(self.remote_output)
                    self._start_next_batch_export()
                    return
                self.cut_status.setText(f'✓ Exported {self._multi_index} clips to {self._multi_folder}')
                self.original_player_note.setText(f'Exported {self._multi_index} clips successfully.')
            else:
                self.cut_status.setText('✓ Original-quality clip exported: '+self.remote_output)
            self.clip_center_update('Clip completed',100)
            self.remote_cleanup()
        else:
            self.remote_fail('Clip export failed: '+errors[-250:])

    def remote_cleanup(self):
        self.remote_proc=None
        self.remote_cut_button.setEnabled(True)
        if self.remote_tmp:
            self.remote_tmp.cleanup()
            self.remote_tmp=None
        self.remote_stage=None
        if hasattr(self,'_clip_diagnostic_timer'):self._clip_diagnostic_timer.stop()
        self.clip_center_update()
        self._multi_active=False

    def remote_fail(self,message):
        self.log('ERROR','REMOTE CUT',message)
        self.cut_status.setText('✕ '+message)
        self.remote_cleanup()

    def cut_clip(self):
        if not self.local_path or not Path(self.local_path).is_file():
            QMessageBox.information(self,'No video','Open a local video first.');return
        if self.cut_proc and self.cut_proc.state()!=QProcess.NotRunning:return
        ffmpeg=shutil.which('ffmpeg') or str(BASE/'ffmpeg.exe')
        if not (shutil.which('ffmpeg') or Path(ffmpeg).is_file()):
            QMessageBox.warning(self,'FFmpeg missing','Install FFmpeg or place ffmpeg.exe next to this app.');return
        try:
            def secs(t):
                parts=[float(x) for x in t.strip().split(':')]
                if len(parts)>3 or any(x<0 for x in parts):raise ValueError()
                total=0
                for x in parts:total=total*60+x
                return total
            start=secs(self.cut_from.text());end=secs(self.cut_to.text())
            if end<=start:raise ValueError()
            if self.player.duration() and end>self.player.duration()/1000+0.2:raise ValueError()
        except ValueError:
            QMessageBox.warning(self,'Invalid time','Use HH:MM:SS.mmm, with end later than start and within the video.');return
        out,_=QFileDialog.getSaveFileName(self,'Save clip',str(Path(self.local_path).with_name(Path(self.local_path).stem+'_cut.mp4')),'MP4 video (*.mp4)')
        if not out:return
        if Path(out).resolve()==Path(self.local_path).resolve():
            QMessageBox.warning(self,'Unsafe output','Output must be different from the source video.');return
        if Path(out).exists() and QMessageBox.question(self,'Overwrite?','Replace existing output file?')!=QMessageBox.Yes:return
        self.cut_proc=QProcess(self)
        self.cut_proc.setProgram(ffmpeg)
        self.cut_proc.setArguments(['-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',self.local_path,
                                   '-t',str(end-start),'-map','0:v:0','-map','0:a?','-c:v','libx264','-preset','medium',
                                   '-crf','19','-c:a','aac','-movflags','+faststart',out])
        self.cut_button.setEnabled(False)
        self.cut_status.setText('Exporting clip…')
        self.cut_proc.finished.connect(lambda code,status:self.cut_finished(code,status,out))
        self.watch_process(self.cut_proc,'FFMPEG',stderr=True,stdout=False)
        self.cut_proc.start()

    def cut_finished(self,code,status,out):
        self.cut_button.setEnabled(True)
        self.log('INFO' if code==0 else 'ERROR','FFMPEG',f'Clip export exit={code}, output={out}')
        if code==0 and status==QProcess.NormalExit and Path(out).is_file():
            self.cut_status.setText('✓ Export complete: '+out)
        else:
            error=bytes(self.cut_proc.readAllStandardError()).decode('utf-8',errors='replace')
            self.cut_status.setText('✕ Export failed: '+error[-250:])

    def open_legacy(self):
        legacy=BASE/'legacy_downloader.py'
        if not legacy.exists():QMessageBox.warning(self,'Missing legacy tools','legacy_downloader.py is missing from this folder.');return
        QMessageBox.information(self,'Legacy tools','Legacy Python tools are available only when running from source.') if getattr(sys, 'frozen', False) else subprocess.Popen([sys.executable,str(legacy)],cwd=str(BASE))
    def closeEvent(self,event):
        if self.proc and self.proc.state()!=QProcess.NotRunning:
            if QMessageBox.question(self,'Active download','A download is active. Quit and keep it queued for resume?')!=QMessageBox.Yes:
                event.ignore();return
            self.paused=True
            self.queue.insert(0,(self.current_url,self.current_mode,self.current_quality,self.current_output_format))
            self.proc.blockSignals(True)
            self.proc.kill();self.proc.waitForFinished(3000)
        if self.remote_proc and self.remote_proc.state()!=QProcess.NotRunning:
            if QMessageBox.question(self,'Remote cut active','Cancel the source download / clip export and quit?')!=QMessageBox.Yes:
                event.ignore();return
            self.remote_proc.kill();self.remote_proc.waitForFinished(3000)
        if self.preview_proc and self.preview_proc.state()!=QProcess.NotRunning:
            if QMessageBox.question(self,'Preview active','Cancel preview preparation and quit?')!=QMessageBox.Yes:
                event.ignore();return
            self.preview_proc.kill();self.preview_proc.waitForFinished(3000)
        if self.cut_proc and self.cut_proc.state()!=QProcess.NotRunning:
            if QMessageBox.question(self,'Clip export active','Cancel the clip export and quit?')!=QMessageBox.Yes:
                event.ignore();return
            self.cut_proc.kill();self.cut_proc.waitForFinished(3000)
        if self.remote_tmp:self.remote_tmp.cleanup()
        self.persist_session()
        self.log('INFO','APP','Application closing')
        if hasattr(self,'_original_server'):
            self._original_server.shutdown()
            self._original_server.server_close()
            self._original_player_dir.cleanup()
        super().closeEvent(event)

if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    win=Main()
    def report_exception(exc_type,exc_value,exc_tb):
        detail=''.join(traceback.format_exception(exc_type,exc_value,exc_tb))
        win.log('ERROR','PYTHON',detail)
        try:QMessageBox.critical(win,'Unexpected error','An error occurred. Open Status Log for details.\n\n'+str(exc_value))
        except Exception:pass
    sys.excepthook=report_exception
    win.show();sys.exit(app.exec())
