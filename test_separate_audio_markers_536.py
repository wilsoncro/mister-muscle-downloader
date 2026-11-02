"""Regression tests for separate V1 video and A1 audio markers (v5.3.6)."""
import ast
import subprocess
import sys
import tempfile
import shutil
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=(ROOT/'mister_muscle_qt.py').read_text(encoding='utf-8')
TIMELINE=(ROOT/'pro_timeline.py').read_text(encoding='utf-8')
assert "APP_VERSION = '5.3.6'" in SOURCE
assert '#define MyAppVersion "5.3.6"' in (ROOT/'MisterMuscle_Setup.iss').read_text(encoding='utf-8')

def method_from_ast(text, cls, name):
    tree=ast.parse(text)
    c=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==cls)
    node=next(x for x in c.body if isinstance(x,ast.FunctionDef) and x.name==name)
    module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    scope={}
    exec(compile(module,'<regression>', 'exec'),scope)
    return scope[name]

class Signal:
    def __init__(self):self.events=[]
    def emit(self,*a):self.events.append(a)

class TimelineFake:
    _video_changed=method_from_ast(TIMELINE,'ProTimeline','_video_changed')
    set_tracks_linked=method_from_ast(TIMELINE,'ProTimeline','set_tracks_linked')
    set_audio_range=method_from_ast(TIMELINE,'ProTimeline','set_audio_range')
    add_audio_selection=method_from_ast(TIMELINE,'ProTimeline','add_audio_selection')
    split_audio_at_playhead=method_from_ast(TIMELINE,'ProTimeline','split_audio_at_playhead')
    _apply=method_from_ast(TIMELINE,'ProTimeline','_apply')
    def __init__(self):
        self.duration=120.;self.start=5.;self.end=45.
        self.audio_start=5.;self.audio_end=45.;self.audio_linked=True
        self.audio_selections=[];self.selections=[(5.,45.)]
        self.playhead=28.;self._drag='audio_start';self._audio_drag_anchor=None
        self.audioRangeChanged=Signal();self.audioSelectionsChanged=Signal()
        self.trackLinkChanged=Signal();self.rangeChanged=Signal();self.seekRequested=Signal()
    def update(self):pass
    def _time(self,x):return x

def markers_test():
    t=TimelineFake()
    t._video_changed(8.,48.)
    assert (t.audio_start,t.audio_end)==(8.,48.)
    t._apply(12.)
    assert (t.audio_start,t.audio_end)==(12.,48.)
    assert (t.start,t.end)==(5.,45.)
    assert t.audio_linked is False
    assert t.trackLinkChanged.events[-1]==(False,)
    t.add_audio_selection()
    assert t.audio_selections==[(12.,48.)] and t.selections==[(5.,45.)]
    t.playhead=23.
    t.split_audio_at_playhead()
    assert t.audio_selections==[(12.,48.),(12.,23.),(23.,48.)]
    assert t.audio_end==23. and t.end==45.
    t.set_tracks_linked(True)
    assert t.audio_linked is True and (t.audio_start,t.audio_end)==(5.,45.)
    print('PASS independently draggable A1 range, A1 clip split, A/V relinking')

def ffmpeg_test():
    build=method_from_ast(SOURCE,'Main','clip_ffmpeg_args')
    def make(mode):
        return types.SimpleNamespace(_clip_job_media_mode=mode,
            _clip_job_audio_range=None,
            aspect=types.SimpleNamespace(currentText=lambda:'Original'))
    av=make('Video + Audio')
    args=build(av,'input.mp4','output.mp4',0.25,2.75,audio_range=(1.0,2.0))
    assert args.count('-i')==2 and args.count('-ss')==2, args
    assert ['-map','1:a:0','-af','apad']==args[args.index('-map',args.index('-map')+1):][:4]
    assert '-t' in args and '-c:a' in args
    assert build(make('Video Only'),'src.mp4','out.mp4',.1,2.,audio_range=(1.,2.)).count('-i')==1
    assert build(make('Audio Only'),'src.mp4','out.m4a',.1,2.,audio_range=(1.,2.)).count('-i')==1
    assert '-vn' in build(make('Audio Only'),'src.mp4','out.m4a',.1,2.)
    print('PASS separate FFmpeg source inputs, silent video and audio-only modes')
    if not all(shutil.which(x) for x in ('ffmpeg','ffprobe')):
        print('SKIP actual FFmpeg media export (binaries unavailable)')
        return
    with tempfile.TemporaryDirectory() as tmp:
        inp=Path(tmp)/'source.mp4';out=Path(tmp)/'out.mp4'
        make_src=subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
             'color=c=black:s=320x180:r=15','-f','lavfi','-i',
             'sine=frequency=500:sample_rate=16000','-t','4',
             '-c:v','mpeg4','-c:a','aac','-shortest',str(inp)],capture_output=True,timeout=60)
        assert make_src.returncode==0,make_src.stderr.decode(errors='replace')[-800:]
        p=subprocess.run(['ffmpeg',*build(av,str(inp),str(out),0.25,2.75,audio_range=(1.0,2.0))],
                 capture_output=True,timeout=80)
        assert p.returncode==0,p.stderr.decode(errors='replace')[-1000:]
        streams=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_type',
            '-of','csv=p=0',str(out)],capture_output=True,text=True,timeout=20)
        assert set(streams.stdout.split())=={'audio','video'},streams.stdout
        dur=subprocess.run(['ffprobe','-v','error','-show_entries',
            'format=duration','-of','default=noprint_wrappers=1:nokey=1',
            str(out)],capture_output=True,text=True,timeout=20)
        seconds=float(dur.stdout.strip())
        assert 2.25 < seconds < 2.95,seconds
        print('PASS actual FFmpeg independently trimmed A1/V1 export, duration',seconds)

if __name__=='__main__':
    assert 'self.audio_marker_status' in SOURCE and 'self.link_av_markers' in SOURCE
    assert "audio_selections if audio_mode else self.pro_timeline.selections" in SOURCE
    assert 'self.pro_timeline.audio_start,self.pro_timeline.audio_end' in SOURCE
    markers_test()
    ffmpeg_test()
    from test_full_waveform_and_cuts_535 import _check_waveform
    _check_waveform()
    print('PASS full-length waveform regression')
