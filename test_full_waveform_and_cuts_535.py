"""Offline v5.3.5 regression checks: full waveform and three export modes."""
import ast
import subprocess
import sys
import tempfile
import types
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
QT = HERE / 'mister_muscle_qt.py'
TIMELINE = HERE / 'pro_timeline.py'


def _clip_method():
    module = ast.parse(QT.read_text(encoding='utf-8'))
    main = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'Main')
    node = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == 'clip_ffmpeg_args')
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(QT), 'exec'), namespace)
    return namespace['clip_ffmpeg_args']


def _check_exports():
    source = QT.read_text(encoding='utf-8')
    assert "APP_VERSION = '5.3.5'" in source
    assert "addItems(['Video + Audio','Video Only','Audio Only'])" in source
    assert "fmt='bestaudio/best'" in source
    assert "NoWheelComboBox" in source
    assert 'MyAppVersion "5.3.5"' in (HERE / 'MisterMuscle_Setup.iss').read_text(encoding='utf-8')
    build = _clip_method()
    def fake_self(mode):
        return types.SimpleNamespace(
            _clip_job_media_mode=mode,
            aspect=types.SimpleNamespace(currentText=lambda: '16:9 (YouTube)'))
    for mode, expected in (('Video + Audio', {'audio', 'video'}), ('Video Only', {'video'}), ('Audio Only', {'audio'})):
        dest = 'out.m4a' if mode == 'Audio Only' else 'out.mp4'
        args = build(fake_self(mode), 'source.mp4', dest, 0.4, 2.7)
        if mode == 'Audio Only':
            assert '-vn' in args and '0:a:0' in args and '-vf' not in args
        elif mode == 'Video Only':
            assert '-an' in args and '-c:a' not in args
        else:
            assert '0:a?' in args and '-c:a' in args
        if not all(shutil.which(x) for x in ('ffmpeg', 'ffprobe')):
            continue
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'source.mp4'
            out = Path(d) / dest
            p = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                'color=c=black:s=320x180:r=15', '-f', 'lavfi', '-i',
                'sine=frequency=440:sample_rate=16000', '-t', '3',
                '-c:v', 'mpeg4', '-c:a', 'aac', '-shortest', str(src)], capture_output=True, timeout=45)
            assert p.returncode == 0, p.stderr.decode()[-500:]
            p = subprocess.run(['ffmpeg', *build(fake_self(mode), src, out, 0.4, 2.7)],
                               capture_output=True, timeout=45)
            assert p.returncode == 0, (mode, p.stderr.decode()[-500:])
            p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                'stream=codec_type', '-of', 'csv=p=0', str(out)], capture_output=True, text=True)
            assert set(p.stdout.split()) == expected, (mode, p.stdout)


def _check_waveform():
    code = TIMELINE.read_text(encoding='utf-8')
    assert 'seconds=min(duration,900)' not in code
    assert 'self.wave_duration=duration' in code
    if not all(shutil.which(x) for x in ('ffmpeg','ffprobe')):
        return
    class Recorder:
        def __init__(self): self.events = []
        def emit(self, *args): self.events.append(args)
    class Thread:
        def __init__(self, *args, **kwargs): pass
    core = types.ModuleType('PySide6.QtCore')
    core.Qt = types.SimpleNamespace()
    core.QRectF = core.QPointF = core.QSettings = object
    core.QThread = Thread
    core.Signal = lambda *args: Recorder()
    gui = types.ModuleType('PySide6.QtGui')
    for name in ('QColor','QPainter','QPen','QBrush','QImage'):
        setattr(gui, name, object)
    widgets = types.ModuleType('PySide6.QtWidgets')
    widgets.QWidget = widgets.QSizePolicy = object
    py = types.ModuleType('PySide6')
    sys.modules.update({'PySide6': py, 'PySide6.QtCore': core,
        'PySide6.QtGui': gui, 'PySide6.QtWidgets': widgets})
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('mm535_timeline', str(TIMELINE))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            media = Path(d) / 'over_15_minutes.m4a'
            p = subprocess.run(['ffmpeg', '-v','error','-y','-f','lavfi','-i',
                'sine=frequency=220:sample_rate=8000','-t','1000','-c:a','aac',
                '-b:a','18k',str(media)],capture_output=True,timeout=120)
            assert p.returncode == 0, p.stderr.decode()[-500:]
            module.WaveformWorker.ready.events.clear()
            module.WaveformWorker.error.events.clear()
            module.WaveformWorker(media).run()
            assert not module.WaveformWorker.error.events, module.WaveformWorker.error.events
            duration, peaks, frames = module.WaveformWorker.ready.events[-1]
            assert duration > 999 and 100 < len(peaks) <= 800 and not frames
    finally:
        for key in ('PySide6','PySide6.QtCore','PySide6.QtGui','PySide6.QtWidgets'):
            sys.modules.pop(key, None)


if __name__ == '__main__':
    _check_exports()
    print('PASS three clip export modes')
    _check_waveform()
    print('PASS full waveform over 15 minutes')
