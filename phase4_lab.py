"""Experimental opt-in queue lab. Never starts downloads automatically."""
import json, os, sys, subprocess, re, urllib.parse, time, threading
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QPlainTextEdit)
from phase3_engine import Job, QueueEngine, load_jobs, save_jobs

ROOT = Path.home() / 'AppData' / 'Local' / 'MisterMuscleDownloader' / 'local_beta_phase4'
STATE = ROOT / 'queue.json'

def parse_progress_line(line):
    """Read yt-dlp's progress template; missing speed/ETA stay unknown."""
    if not line.startswith('download:'):
        return None
    parts=line[len('download:'):].strip().split('|', 2)
    match=re.search(r'(\d+(?:\.\d+)?)%',parts[0])
    if not match:
        return None
    percent=f'{min(100.0, float(match.group(1))):.1f}%'
    def clean(value):
        value=re.sub(r'\x1b\[[0-9;]*m','',value).strip()
        return value[:32] if value and value.lower() not in ('na','n/a','none','unknown') else '—'
    speed=clean(parts[1]) if len(parts)>1 else '—'
    eta=clean(parts[2]) if len(parts)>2 else '—'
    return percent,speed,eta

class Worker(QThread):
    finished_result = Signal(dict)
    failed = Signal(str)
    progress = Signal(str, str, str, str)
    def __init__(self, jobs, folder, concurrency):
        super().__init__(); self.jobs=jobs; self.folder=folder; self.concurrency=concurrency
        self._lock=threading.RLock()
        self._processes={}
        self._requested={}

    def request_action(self, url, action):
        """Mark the job before terminating the child; partial files remain resumable."""
        with self._lock:
            job=next((j for j in self.jobs if j.url==url),None)
            if job is None or job.status not in ('pending','running'):
                return False
            job.status='paused' if action=='pause' else 'canceled'
            self._requested[url]=action
            process=self._processes.get(url)
            if process and process.poll() is None:
                process.terminate()
            return True
    def run(self):
        def runner(job, selector):
            # yt-dlp's default title-based naming, made explicit for predictability.
            # Do not use --restrict-filenames or a numeric-ID output template.
            args=[sys.executable,'-m','yt_dlp','--continue','--no-playlist','--no-overwrites',
                  '--newline','--progress-template','download:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s',
                  '-o','%(title)s.%(ext)s',
                  '-P',str(self.folder),'-f',selector,'--',job.url]
            started=time.monotonic()
            with self._lock:
                if job.status != 'running':
                    return
            with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, encoding='utf-8', errors='replace',
                                  bufsize=1, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as process:
                with self._lock:
                    self._processes[job.url]=process
                    if self._requested.get(job.url):
                        process.terminate()
                try:
                    for line in process.stdout:
                        if time.monotonic()-started>3600:
                            process.kill()
                            raise RuntimeError('DownloadTimeout')
                        if line.startswith('download:'):
                            metrics=parse_progress_line(line)
                            if metrics:
                                self.progress.emit(job.url, *metrics)
                        elif '[Merger]' in line or '[ExtractAudio]' in line or '[Fixup' in line:
                            self.progress.emit(job.url, 'Processing', '—', '—')
                    result=process.wait()
                finally:
                    with self._lock:
                        self._processes.pop(job.url,None)
            with self._lock:
                if self._requested.get(job.url):
                    raise RuntimeError('UserStopped')
            if result: raise RuntimeError('DownloadFailed')
            self.progress.emit(job.url, '100%', '—', '00:00')
        try:
            engine=QueueEngine(self.jobs, STATE, concurrency=self.concurrency, retries=1,
                               delay=1, runner=runner)
            self.finished_result.emit(engine.run())
        except Exception as exc:
            self.failed.emit(type(exc).__name__)

class Lab(QWidget):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Mister Muscle — Phase 4 Experimental Queue Lab')
        self.resize(1080,560); ROOT.mkdir(parents=True,exist_ok=True)
        self.jobs=load_jobs(STATE) if STATE.exists() else []
        self.worker=None; self.folder=Path.home()/'Downloads'; self.live_progress={}; self.live_speed={}; self.live_eta={}
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Experimental local queue • Separate from main queue • Video+audio only • Pause / resume / cancel per selected job'))
        layout.addWidget(QLabel('Paste one or more video URLs (one per line):'))
        self.url_input=QPlainTextEdit();self.url_input.setPlaceholderText('https://www.youtube.com/watch?v=...\nhttps://...')
        self.url_input.setFixedHeight(85);layout.addWidget(self.url_input)
        add_controls=QHBoxLayout();layout.addLayout(add_controls)
        self.add_button=QPushButton('Add to Queue');self.add_button.clicked.connect(self.add_links);add_controls.addWidget(self.add_button)
        self.import_button=QPushButton('Import .txt');self.import_button.clicked.connect(self.import_links);add_controls.addWidget(self.import_button)
        self.remove_button=QPushButton('Remove selected');self.remove_button.clicked.connect(self.remove_selected);add_controls.addWidget(self.remove_button)
        self.pause_button=QPushButton('Pause selected');self.pause_button.clicked.connect(self.pause_selected);add_controls.addWidget(self.pause_button)
        self.resume_button=QPushButton('Resume selected');self.resume_button.clicked.connect(self.resume_selected);add_controls.addWidget(self.resume_button)
        self.cancel_button=QPushButton('Cancel selected');self.cancel_button.clicked.connect(self.cancel_selected);add_controls.addWidget(self.cancel_button)
        add_controls.addStretch()
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['URL','Format','Status','Progress','Speed','ETA','Attempts']);layout.addWidget(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        controls=QHBoxLayout();layout.addLayout(controls)
        controls.addWidget(QLabel('Parallel:'))
        self.parallel=QSpinBox();self.parallel.setRange(1,3);self.parallel.setValue(2);controls.addWidget(self.parallel)
        choose=QPushButton('Choose output folder');choose.clicked.connect(self.choose_folder);controls.addWidget(choose)
        self.start=QPushButton('Start experimental queue');self.start.clicked.connect(self.begin);controls.addWidget(self.start)
        self.retry=QPushButton('Retry failed');self.retry.clicked.connect(self.retry_failed);controls.addWidget(self.retry)
        # Editing tools are integrated in the main New Download page.
        self.info=QLabel('Downloads: '+str(self.folder));layout.addWidget(self.info)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(700)
        self.refresh()
    @staticmethod
    def parse_links(text):
        allowed={'youtube.com','youtu.be','instagram.com','tiktok.com','facebook.com',
                 'fb.watch','twitter.com','x.com','vimeo.com','reddit.com'}
        links=[]; seen=set()
        for raw in re.findall(r'https?://[^\s<>"\']+', text or '', flags=re.I):
            url=raw.rstrip('.,;!)]}')
            try:
                parsed=urllib.parse.urlsplit(url)
                host=(parsed.hostname or '').lower().rstrip('.')
                supported=any(host==h or host.endswith('.'+h) for h in allowed)
                if parsed.scheme not in ('http','https') or not supported or not (parsed.path.strip('/') or parsed.query):
                    continue
            except ValueError:
                continue
            if url not in seen:
                seen.add(url);links.append(url)
        return links

    def add_links(self):
        if self.worker and self.worker.isRunning():return
        links=self.parse_links(self.url_input.toPlainText())
        if not links:
            QMessageBox.warning(self,'No valid URLs','Paste supported video links first.');return
        existing={j.url for j in self.jobs}
        new=[url for url in links if url not in existing]
        if len(self.jobs)+len(new)>1000:
            QMessageBox.warning(self,'Queue limit','Maximum 1000 jobs in the local queue.');return
        for url in new:self.jobs.append(Job(url=url,mode='video',format_id='bv*+ba/b'))
        save_jobs(STATE,self.jobs)
        self.url_input.clear();self.refresh()
        self.info.setText(f'Added {len(new)} job(s), skipped {len(links)-len(new)} duplicate(s). Downloads: {self.folder}')

    def import_links(self):
        if self.worker and self.worker.isRunning():return
        filename,_=QFileDialog.getOpenFileName(self,'Import video links',str(Path.home()),'Text files (*.txt)')
        if not filename:return
        try:
            path=Path(filename)
            if path.stat().st_size>1024*1024:raise ValueError('Text file is larger than 1 MB')
            content=path.read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError,ValueError) as exc:
            QMessageBox.warning(self,'Import failed',str(exc));return
        self.url_input.setPlainText(content)
        self.add_links()

    def remove_selected(self):
        if self.worker and self.worker.isRunning():return
        rows=sorted({index.row() for index in self.table.selectedIndexes()},reverse=True)
        if not rows:return
        for row in rows:
            if 0<=row<len(self.jobs):self.jobs.pop(row)
        save_jobs(STATE,self.jobs);self.refresh()

    def selected_jobs(self):
        return [self.jobs[i] for i in sorted({x.row() for x in self.table.selectedIndexes()})
                if 0 <= i < len(self.jobs)]

    def pause_selected(self):
        self._stop_selected('pause')

    def cancel_selected(self):
        self._stop_selected('cancel')

    def _stop_selected(self, action):
        changed=False
        for job in self.selected_jobs():
            if job.status not in ('pending','running'):
                continue
            if self.worker and self.worker.isRunning():
                changed=self.worker.request_action(job.url,action) or changed
            else:
                job.status='paused' if action=='pause' else 'canceled'
                changed=True
        if changed and not (self.worker and self.worker.isRunning()):
            save_jobs(STATE,self.jobs)
        self.refresh()

    def resume_selected(self):
        # Resume means requeue from the existing yt-dlp .part file on next Start.
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self,'Wait for current batch',
                'Wait for active downloads to finish, then resume and click Start.')
            return
        changed=False
        for job in self.selected_jobs():
            if job.status in ('paused','canceled'):
                job.status='pending';job.error='';changed=True
                self.live_progress.pop(job.url,None);self.live_speed.pop(job.url,None);self.live_eta.pop(job.url,None)
        if changed:save_jobs(STATE,self.jobs)
        self.refresh()

    def open_studio(self):
        from beta_studio import BetaStudio
        if not hasattr(self,'studio_window') or not self.studio_window.isVisible():
            self.studio_window=BetaStudio(self.folder)
        self.studio_window.show();self.studio_window.raise_()

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Output folder',str(self.folder))
        if folder:self.folder=Path(folder);self.info.setText('Downloads: '+folder)
    def refresh(self):
        if not self.worker or not self.worker.isRunning():
            if STATE.exists():
                try:self.jobs=load_jobs(STATE)
                except (OSError,ValueError,KeyError,TypeError):pass
        self.table.setRowCount(len(self.jobs))
        for i,j in enumerate(self.jobs):
            for col,value in enumerate((j.url,j.format_id,j.status,
                '100%' if j.status=='completed' else ('—' if j.status in ('paused','canceled') else self.live_progress.get(j.url,'—')),self.live_speed.get(j.url,'—') if j.status=='running' else '—',self.live_eta.get(j.url,'—') if j.status=='running' else '—',str(j.attempts))):
                self.table.setItem(i,col,QTableWidgetItem(value))
    def begin(self):
        if self.worker and self.worker.isRunning():return
        if not any(j.status=='pending' for j in self.jobs):
            QMessageBox.information(self,'No pending jobs','No pending jobs.');return
        if QMessageBox.question(self,'Experimental downloads',
            'Start actual downloads in the selected folder? Existing main app queue is unaffected.')!=QMessageBox.Yes:return
        self.start.setEnabled(False);self.retry.setEnabled(False)
        self.add_button.setEnabled(False);self.import_button.setEnabled(False);self.remove_button.setEnabled(False)
        self.live_progress={}; self.live_speed={}; self.live_eta={}
        self.worker=Worker(self.jobs,self.folder,self.parallel.value())
        self.worker.progress.connect(self.on_progress)
        self.worker.finished_result.connect(lambda result:self.done(str(result)))
        self.worker.failed.connect(lambda msg:self.done('Error: '+msg))
        self.worker.start()
    def on_progress(self,url,value,speed,eta):
        if any(j.url==url and j.status=='running' for j in self.jobs):
            self.live_progress[url]=value
            self.live_speed[url]=speed
            self.live_eta[url]=eta
        self.refresh()

    def done(self,msg):
        self.start.setEnabled(True);self.retry.setEnabled(True)
        self.add_button.setEnabled(True);self.import_button.setEnabled(True);self.remove_button.setEnabled(True)
        self.refresh()
        QMessageBox.information(self,'Queue result',msg)
    def retry_failed(self):
        if self.worker and self.worker.isRunning():return
        for job in self.jobs:
            if job.status=='failed':job.status='pending';job.error=''
        save_jobs(STATE,self.jobs);self.refresh()
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self,'Active downloads','Wait for active downloads to finish before closing.')
            event.ignore();return
        super().closeEvent(event)

if __name__=='__main__':
    app=QApplication(sys.argv)
    win=Lab();win.show();sys.exit(app.exec())
