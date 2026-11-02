"""Local-only opt-in media tools. FFmpeg operations never overwrite input files."""
import json, re, shutil, subprocess, sys, threading, time
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QComboBox, QLineEdit, QPlainTextEdit, QMessageBox,
    QTabWidget, QCheckBox, QSpinBox, QProgressBar)

ROOT=Path.home()/'AppData'/'Local'/'MisterMuscleDownloader'/'local_beta_tools'
ROOT.mkdir(parents=True,exist_ok=True)
PREFS=ROOT/'preferences.json'
PRESETS={'Original':'copy','MP4 H.264':'libx264','MP4 H.265':'libx265','WebM VP9':'libvpx-vp9'}

def timecode(value):
    if not re.fullmatch(r'(?:\d+:)?[0-5]?\d:[0-5]\d(?:\.\d{1,3})?',value.strip()):
        raise ValueError('Use HH:MM:SS or MM:SS')
    bits=[float(x) for x in value.split(':')]
    return sum(x*60**i for i,x in enumerate(reversed(bits)))

def parse_cuts(value):
    cuts=[]
    for line in value.splitlines():
        if not line.strip(): continue
        pieces=line.split('-',1)
        if len(pieces)!=2:raise ValueError('One range per line: 00:10-00:20')
        start,end=(timecode(x.strip()) for x in pieces)
        if end<=start:raise ValueError('End must be after start')
        cuts.append((start,end))
    if not cuts:raise ValueError('Add at least one cut range')
    if len(cuts)>100:raise ValueError('Maximum 100 cuts')
    return cuts

def aspect_filter(ratio):
    if ratio=='Original':return []
    width,height={'16:9':(16,9),'9:16':(9,16),'1:1':(1,1),'4:5':(4,5)}[ratio]
    return ['-vf',f'crop=if(gte(iw/ih\\,{width}/{height})\\,ih*{width}/{height}\\,iw):if(gte(iw/ih\\,{width}/{height})\\,ih\\,iw*{height}/{width})']

def safe_output(folder,stem,ext):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',stem).strip(' .')[:140] or 'video'
    for i in range(10000):
        candidate=folder/(stem+(f'_{i}' if i else '')+ext)
        if not candidate.exists():return candidate
    raise RuntimeError('Too many matching filenames')

def health_report():
    results={}
    for tool in ('ffmpeg','ffprobe'):
        executable=shutil.which(tool)
        if executable:
            try:
                result=subprocess.run([executable,'-version'],capture_output=True,text=True,timeout=8)
                results[tool]='OK' if result.returncode==0 else 'ERROR'
            except (OSError,subprocess.TimeoutExpired):results[tool]='ERROR'
        else:results[tool]='MISSING'
    try:
        import yt_dlp
        results['yt-dlp']='OK'
    except ImportError:results['yt-dlp']='MISSING'
    try:
        import PySide6
        results['PySide6']='OK'
    except ImportError:results['PySide6']='MISSING'
    return results

class Task(QThread):
    done=Signal(bool,str)
    def __init__(self,args,timeout=7200):
        super().__init__();self.args=args;self.timeout=timeout
    def run(self):
        try:
            result=subprocess.run(self.args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=self.timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode:raise RuntimeError('FFmpeg returned error code '+str(result.returncode))
            self.done.emit(True,'Operation completed successfully')
        except Exception as exc:self.done.emit(False,str(exc)[:200])

class BetaStudio(QWidget):
    def __init__(self,folder):
        super().__init__();self.setWindowTitle('Mister Muscle Downloader — Media Studio');self.resize(840,700)
        self.folder=Path(folder);self.source=None;self.task=None
        outer=QVBoxLayout(self)
        self.tabs=QTabWidget();outer.addWidget(self.tabs)
        self.media=QWidget();v=QVBoxLayout(self.media);self.tabs.addTab(self.media,'Cut / Export')
        row=QHBoxLayout();v.addLayout(row)
        self.file_label=QLabel('No local video selected');row.addWidget(self.file_label,1)
        b=QPushButton('Open video');b.clicked.connect(self.open_file);row.addWidget(b)
        v.addWidget(QLabel('Cut ranges, one per line (MM:SS-MM:SS). Each range creates a separate file:'))
        self.ranges=QPlainTextEdit('00:00:05-00:00:15');v.addWidget(self.ranges)
        row=QHBoxLayout();v.addLayout(row)
        row.addWidget(QLabel('Export preset:'));self.preset=QComboBox();self.preset.addItems(PRESETS);row.addWidget(self.preset)
        row.addWidget(QLabel('Aspect ratio:'));self.aspect=QComboBox();self.aspect.addItems(['Original','16:9','9:16','1:1','4:5']);row.addWidget(self.aspect)
        self.export=QPushButton('Export selected cuts');self.export.clicked.connect(self.export_cuts);v.addWidget(self.export)
        self.wave=QPushButton('Generate audio waveform image');self.wave.clicked.connect(self.waveform);v.addWidget(self.wave)
        self.scene=QPushButton('Detect scene changes');self.scene.clicked.connect(self.detect_scenes);v.addWidget(self.scene)
        self.scene_threshold=QLineEdit('0.35');self.scene_threshold.setPlaceholderText('Scene threshold 0.1–0.9');v.addWidget(self.scene_threshold)
        self.output=QPlainTextEdit();self.output.setReadOnly(True);v.addWidget(self.output)
        self.library=QWidget();lv=QVBoxLayout(self.library);self.tabs.addTab(self.library,'Download Library')
        self.search=QLineEdit();self.search.setPlaceholderText('Search local downloaded files');self.search.textChanged.connect(self.refresh_library);lv.addWidget(self.search)
        self.files=QListWidget();lv.addWidget(self.files)
        br=QHBoxLayout();lv.addLayout(br)
        b=QPushButton('Choose library folder');b.clicked.connect(self.choose_folder);br.addWidget(b)
        b=QPushButton('Refresh');b.clicked.connect(self.refresh_library);br.addWidget(b)
        b=QPushButton('Open selected');b.clicked.connect(self.open_selected);br.addWidget(b)
        self.tools=QWidget();tv=QVBoxLayout(self.tools);self.tabs.addTab(self.tools,'Health / Settings')
        b=QPushButton('Run health check');b.clicked.connect(self.check_health);tv.addWidget(b)
        b=QPushButton('One-click repair: validate and create local folders');b.clicked.connect(self.repair);tv.addWidget(b)
        self.health=QPlainTextEdit();self.health.setReadOnly(True);tv.addWidget(self.health)
        self.theme=QComboBox();self.theme.addItems(['Dark','Light']);self.theme.currentTextChanged.connect(self.apply_theme);tv.addWidget(self.theme)
        self.mini=QCheckBox('Mini mode (compact window)');self.mini.toggled.connect(self.set_mini);tv.addWidget(self.mini)
        self.status=QLabel('Ready');outer.addWidget(self.status)
        self.setAcceptDrops(True);self.refresh_library()
    def open_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Open video',str(self.folder),'Media (*.mp4 *.mkv *.mov *.webm *.avi *.m4v *.mp3 *.wav)')
        if path:self.source=Path(path);self.file_label.setText(self.source.name)
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(x.isLocalFile() for x in event.mimeData().urls()):event.acceptProposedAction()
    def dropEvent(self,event):
        for url in event.mimeData().urls():
            p=Path(url.toLocalFile())
            if p.is_file() and p.suffix.lower() in ('.mp4','.mkv','.mov','.webm','.avi','.m4v','.mp3','.wav'):
                self.source=p;self.file_label.setText(p.name);event.acceptProposedAction();return
    def require_source(self):
        if not self.source or not self.source.is_file():raise ValueError('Choose a local media file first')
        if not shutil.which('ffmpeg'):raise ValueError('FFmpeg is missing from PATH')
    def execute(self,args,after=None):
        if self.task and self.task.isRunning():raise ValueError('Wait for the current operation')
        self.task=Task(args)
        self.status.setText('Working…')
        def finished(ok,msg):
            self.status.setText(msg)
            self.output.appendPlainText(msg)
            if ok and after:after()
        self.task.done.connect(finished);self.task.start()
    def export_cuts(self):
        try:
            self.require_source();cuts=parse_cuts(self.ranges.toPlainText());preset=self.preset.currentText();ratio=self.aspect.currentText()
            if preset=='Original' and ratio!='Original':raise ValueError('Cropping requires a re-encoding preset')
            self._cut_queue=[]
            for i,(start,end) in enumerate(cuts,1):
                ext=self.source.suffix if preset=='Original' else ('.webm' if preset=='WebM VP9' else '.mp4')
                output=safe_output(self.folder,self.source.stem+f'_clip_{i}',ext)
                args=[shutil.which('ffmpeg'),'-nostdin','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(self.source),'-t',str(end-start)]
                if preset=='Original':args+=['-c','copy']
                else:args+=aspect_filter(ratio)+['-c:v',PRESETS[preset],'-c:a','aac' if ext=='.mp4' else 'libopus']
                args+=['-n',str(output)]
                self._cut_queue.append((args,output))
            self._next_cut()
        except (ValueError,OSError) as exc:QMessageBox.warning(self,'Export',str(exc))
    def _next_cut(self):
        if not self._cut_queue:return
        args,output=self._cut_queue.pop(0)
        self.output.appendPlainText('Exporting: '+output.name)
        self.execute(args,after=self._next_cut)
    def waveform(self):
        try:
            self.require_source();out=safe_output(self.folder,self.source.stem+'_waveform','.png')
            args=[shutil.which('ffmpeg'),'-nostdin','-hide_banner','-loglevel','error','-i',str(self.source),'-filter_complex','aformat=channel_layouts=mono,showwavespic=s=1280x240:colors=white','-frames:v','1','-n',str(out)]
            self.execute(args)
            self.output.appendPlainText('Waveform output: '+str(out))
        except ValueError as exc:QMessageBox.warning(self,'Waveform',str(exc))
    def detect_scenes(self):
        try:
            self.require_source();threshold=float(self.scene_threshold.text())
            if not 0.1<=threshold<=0.9:raise ValueError('Threshold must be between 0.1 and 0.9')
            out=safe_output(self.folder,self.source.stem+'_scenes','.txt')
            # A worker runs ffmpeg; write only its sanitized scene timestamps.
            if self.task and self.task.isRunning():raise ValueError('Wait for the current operation')
            self.task=SceneTask(str(self.source),threshold,str(out));self.task.done.connect(lambda ok,msg:self.output.appendPlainText(msg));self.task.start()
            self.status.setText('Detecting scenes…')
        except ValueError as exc:QMessageBox.warning(self,'Scenes',str(exc))
    def refresh_library(self):
        self.files.clear();needle=self.search.text().lower()
        if not self.folder.exists():return
        for p in sorted(self.folder.iterdir(),key=lambda p:p.name.lower()):
            if p.is_file() and p.suffix.lower() in ('.mp4','.mkv','.webm','.mov','.avi','.mp3','.m4a','.wav') and needle in p.name.lower():
                self.files.addItem(p.name)
    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Library folder',str(self.folder))
        if folder:self.folder=Path(folder);self.refresh_library()
    def open_selected(self):
        item=self.files.currentItem()
        if item:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder/item.text())))
    def check_health(self):
        self.health.setPlainText('\n'.join(f'{k}: {v}' for k,v in health_report().items()))
    def repair(self):
        ROOT.mkdir(parents=True,exist_ok=True);self.folder.mkdir(parents=True,exist_ok=True)
        self.check_health();self.health.appendPlainText('Local folders verified. Missing programs are not installed automatically.')
    def apply_theme(self,theme):
        self.setStyleSheet('QWidget {background:#161a2c;color:#edf0ff} QLineEdit,QPlainTextEdit,QListWidget {background:#242b42;color:white}' if theme=='Dark' else 'QWidget {background:#f3f5f8;color:#172033} QLineEdit,QPlainTextEdit,QListWidget {background:white;color:#172033}')
    def set_mini(self,checked):self.resize(600,400) if checked else self.resize(840,700)
    def closeEvent(self,event):
        if self.task and self.task.isRunning():
            QMessageBox.warning(self,'Task active','Wait for the current media operation to finish.');event.ignore();return
        super().closeEvent(event)

class SceneTask(QThread):
    done=Signal(bool,str)
    def __init__(self,source,threshold,out):
        super().__init__();self.source=source;self.threshold=threshold;self.out=out
    def run(self):
        try:
            args=[shutil.which('ffmpeg'),'-nostdin','-hide_banner','-i',self.source,'-vf',f"select='gt(scene,{self.threshold})',showinfo",'-an','-f','null','-']
            p=subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=3600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if p.returncode:raise RuntimeError('FFmpeg scene analysis failed')
            times=re.findall(rb'pts_time:([0-9.]+)',p.stderr)
            Path(self.out).write_text('\n'.join(x.decode('ascii') for x in times)+'\n',encoding='utf-8')
            self.done.emit(True,f'Detected {len(times)} scenes. Saved: {self.out}')
        except Exception as exc:self.done.emit(False,str(exc)[:200])
