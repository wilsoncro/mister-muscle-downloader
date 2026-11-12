"""v5.3.9: Inspect/Preview expected access limits vs genuine application failures.

Four independent fake users exercise the same real Hotstar response. Their
events are not merged; access restrictions are shown locally as warnings.
Genuine extractor problems still produce one error per operation.
"""
import ast
import json
import re
import tempfile
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=(ROOT/'mister_muscle_qt.py').read_text(encoding='utf-8')
SETUP=(ROOT/'MisterMuscle_Setup.iss').read_text(encoding='utf-8')
version=re.search(r"(?m)^APP_VERSION = '(\d+\.\d+\.\d+)'", SOURCE)
assert version is not None
assert tuple(map(int,version.group(1).split('.'))) >= (5,3,9)
assert '#define MyAppVersion "'+version.group(1)+'"' in SETUP
TREE=ast.parse(SOURCE)

def extract(function_name,class_name=None,globals_=None):
    if class_name:
        klass=next(x for x in TREE.body
                   if isinstance(x,ast.ClassDef) and x.name==class_name)
        items=klass.body
    else: items=TREE.body
    fn=next(x for x in items
            if isinstance(x,ast.FunctionDef) and x.name==function_name)
    tree=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
    scope={} if globals_ is None else dict(globals_)
    exec(compile(tree,'<isolated regression>', 'exec'),scope)
    return scope[function_name]

scrub=extract('scrub_bug_log',globals_={'re':re})
notice=extract('_restricted_media_notice')
env={'re':re,'json':json,'Path':Path,'scrub_bug_log':scrub,
     '_restricted_media_notice':notice,'QProcess':types.SimpleNamespace(NormalExit=0)}
capture=extract('_capture_process_output','Main',env)
metadata=extract('metadata_finished','Main',env)
preview=extract('preview_finished','Main',env)

class Label:
    def __init__(self):self.text=''
    def setText(self,msg):self.text=str(msg)

class Stream:
    def __init__(self,stderr=b'',stdout=b''):
        self.stderr=stderr;self.stdout=stdout
    def readAllStandardError(self):
        b=self.stderr;self.stderr=b'';return b
    def readAllStandardOutput(self):
        b=self.stdout;self.stdout=b'';return b

class Page:
    def __init__(self):
        self.link_info=Label()
        self.original_player_note=Label()
        self.reports=[]
        self._inspect_diagnostics=[]
        self._preview_diagnostics=[]
        self.meta_proc=None
        self.preview_proc=None
    def log(self,level,source,message):
        self.reports.append((level,source,str(message)))

HOTSTAR=(b'ERROR: [hotstar] 1000066865: '
         b'This video is only available for registered users. '
         b'Use --cookies-from-browser to supply valid authentication.\n')
UNEXPECTED=b'ERROR: [generic] Extractor crashed while parsing metadata.\n'


def test_access_classification():
    for msg in (HOTSTAR,'Please sign in to watch this video',
                'This video is private', 'authentication required',
                'sign in to confirm you are not a bot'):
        response=notice(msg)
        assert response and ('sign in' in response.lower()
                             or 'signed-in' in response.lower()), msg
    for msg in ('Video HTTP timeout', 'PermissionError: local file locked',
                'ERROR: invalid format information','ffmpeg decode failed'):
        assert notice(msg) is None, msg
    assert notice(HOTSTAR).startswith('Hotstar')
    print('PASS protected service sign-in notices are classified without bypassing access')


def test_four_independent_users():
    for n in range(4):
        page=Page()
        if n%2==0:  # Inspect on user #1 / #3
            page.meta_proc=Stream(stderr=HOTSTAR)
            capture(page,page.meta_proc,'INSPECT',True)
            metadata(page,1,0)
            assert 'Hotstar requires' in page.link_info.text
            assert page.meta_proc is None
        else:       # Preview on user #2 / #4
            page.preview_proc=Stream(stdout=HOTSTAR)
            with tempfile.TemporaryDirectory() as tmp:
                page.preview_file=str(Path(tmp)/'not-created.mp4')
                capture(page,page.preview_proc,'PREVIEW',False)
                preview(page,1,0)
            assert 'Hotstar requires' in page.link_info.text
            assert 'Hotstar requires' in page.original_player_note.text
            assert page.preview_proc is None
        assert page.reports
        assert all(level != 'ERROR' for level,src,msg in page.reports),page.reports
        assert not any('https://' in msg for _,_,msg in page.reports)
    print('PASS four separate users each get an informative warning, not a crash report')


def test_unknown_error_still_reported_once():
    for name in ('INSPECT','PREVIEW'):
        page=Page()
        if name=='INSPECT':
            page.meta_proc=Stream(stderr=UNEXPECTED)
            capture(page,page.meta_proc,name,True)
            metadata(page,1,0)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                # A partial MP4 must not be treated as valid when yt-dlp fails.
                p=Path(tmp)/'partial.mp4'
                p.write_bytes(b'partial-media'*200)
                page.preview_file=str(p)
                page.preview_proc=Stream(stdout=UNEXPECTED)
                capture(page,page.preview_proc,name,False)
                preview(page,1,0)
        failures=[msg for level,src,msg in page.reports
                  if level=='ERROR' and src==name]
        assert len(failures)==1,(name,page.reports)
        assert 'Extractor crashed' in failures[0]
    print('PASS genuine Inspect and Preview failures still report once each')


if __name__=='__main__':
    test_access_classification()
    test_four_independent_users()
    test_unknown_error_still_reported_once()
    from test_car_multimedia_538 import test_compatibility
    test_compatibility()
    from test_windows_cleanup_537 import test_temporary_locks,test_http_disconnect
    test_temporary_locks()
    test_http_disconnect()
    from test_separate_audio_markers_536 import markers_test,ffmpeg_test
    markers_test()
    ffmpeg_test()
    from test_full_waveform_and_cuts_535 import _check_waveform
    _check_waveform()
    print('PASS v5.3.9 and all previously required FFmpeg/Windows regressions')
