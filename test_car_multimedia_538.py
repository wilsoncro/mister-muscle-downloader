"""Mister Muscle v5.3.8: car USB multimedia H.264/AAC regression tests."""
import ast
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / 'mister_muscle_qt.py').read_text(encoding='utf-8')
INSTALLER = (HERE / 'MisterMuscle_Setup.iss').read_text(encoding='utf-8')


def get_helper(name):
    tree = ast.parse(SOURCE)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    namespace = {}
    exec(compile(module, '<car codec helper>', 'exec'), namespace)
    return namespace[name]


def run_cmd(args, timeout=65):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    assert p.returncode == 0, (p.stderr or p.stdout)[-1800:]
    return p


def test_compatibility():
    version=re.search(r"(?m)^APP_VERSION = '(\d+\.\d+\.\d+)'", SOURCE)
    assert version is not None
    assert tuple(map(int,version.group(1).split('.'))) >= (5,3,8)
    assert '#define MyAppVersion "'+version.group(1)+'"' in INSTALLER
    assert "Car Multimedia (MP4)" in SOURCE
    assert "self.mode=NoWheelComboBox();self.mode.addItems(" in SOURCE
    assert "self.car_compatible" not in SOURCE, 'Car mode must be in dropdown, not checkbox'
    assert "self._mode_formats={0:" in SOURCE and "4:['MP4']" in SOURCE
    assert "self._car_for_download=(mode==4)" in SOURCE
    assert "self.current_mode in (0,1,4)" in SOURCE
    assert "self.current_mode in (0,4):self._premiere_args_base" in SOURCE
    assert "fmt=(720 if mode==4" in SOURCE
    assert "if mode not in (0,1,2,3,4)" in SOURCE
    assert "self._premiere_encoders=(['libx264'] if car_mode else" in SOURCE
    assert "self._premiere_stream_copy=(not car_mode" in SOURCE
    assert "self._premiere_audio_copy=(not car_mode" in SOURCE
    assert "if getattr(self,'_car_for_download',False):" in SOURCE

    filters = get_helper('car_multimedia_video_filter')()
    vcodec_args = get_helper('car_multimedia_video_args')()
    assert 'scale=' in filters and 'fps=30' in filters and 'format=yuv420p' in filters
    assert ['-profile:v', 'baseline'] == vcodec_args[
        vcodec_args.index('-profile:v'):vcodec_args.index('-profile:v')+2]
    assert vcodec_args[vcodec_args.index('-level:v')+1] == '3.1'
    assert vcodec_args[vcodec_args.index('-maxrate')+1] == '3500k'
    if not (shutil.which('ffmpeg') and shutil.which('ffprobe')):
        raise AssertionError('Real FFmpeg/ffprobe binaries are required for car profile verification')

    for size in ('1920x1080', '640x360'):
        with tempfile.TemporaryDirectory(prefix='mm_car_test_') as directory:
            source = Path(directory)/'incompatible.mkv'
            output = Path(directory)/'car-compatible.mp4'
            # MPEG-4 Part 2 + Opus inside MKV is intentionally not a car preset.
            run_cmd(['ffmpeg','-v','error','-y','-f','lavfi','-i',
                     f'testsrc2=size={size}:rate=60','-f','lavfi','-i',
                     'sine=frequency=480:sample_rate=48000','-t','1.25',
                     '-c:v','mpeg4','-q:v','6','-c:a','libopus',
                     '-b:a','80k','-shortest',str(source)])
            run_cmd(['ffmpeg','-v','error','-nostdin','-y','-fflags','+genpts',
                     '-i',str(source),'-map','0:v:0','-map','0:a:0?',
                     *vcodec_args, '-vf',filters,
                     '-pix_fmt','yuv420p','-tag:v','avc1',
                     '-c:a','aac','-profile:a','aac_low',
                     '-b:a','160k','-ar','44100','-ac','2',
                     '-af','aresample=async=1:first_pts=0',
                     '-avoid_negative_ts','make_zero',
                     '-movflags','+faststart','-max_muxing_queue_size','4096',
                     str(output)],timeout=100)
            details = json.loads(run_cmd(['ffprobe','-v','error','-show_entries',
                     'stream=codec_type,codec_name,profile,level,pix_fmt,width,height,avg_frame_rate,sample_rate,channels',
                     '-show_entries','format=format_name','-of','json',
                     str(output)]).stdout)
            streams = details['streams']
            video = next(s for s in streams if s['codec_type']=='video')
            audio = next(s for s in streams if s['codec_type']=='audio')
            assert 'mp4' in details['format']['format_name']
            assert video['codec_name']=='h264'
            assert video['profile'] in ('Baseline','Constrained Baseline')
            assert video['level']<=31 and video['pix_fmt']=='yuv420p'
            assert video['width']<=1280 and video['height']<=720
            if size=='640x360':
                assert video['width']<=640 and video['height']<=360, 'must never upscale'
            num,den=map(int,video['avg_frame_rate'].split('/'))
            assert 0<num/den<=30.01
            assert audio['codec_name']=='aac' and audio['profile']=='LC'
            assert audio['channels']==2 and audio['sample_rate']=='44100'
            print('PASS car MP4 codec profile, audio and frame rate for',size)


if __name__ == '__main__':
    test_compatibility()
    from test_windows_cleanup_537 import test_temporary_locks, test_http_disconnect
    test_temporary_locks()
    test_http_disconnect()
    from test_separate_audio_markers_536 import markers_test,ffmpeg_test
    markers_test()
    ffmpeg_test()
    from test_full_waveform_and_cuts_535 import _check_waveform
    _check_waveform()
    print('PASS older Windows/audio/video regression checks')
