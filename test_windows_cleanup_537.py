"""v5.3.7 regression: Windows file locks and benign player HTTP disconnects.

Runs on GitHub's Windows runner without launching the GUI. Covers prior
full-length waveform and independent A1/V1 cutting tests too.
"""
import ast
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAIN = (ROOT / 'mister_muscle_qt.py').read_text(encoding='utf-8')
TIMELINE = (ROOT / 'pro_timeline.py').read_text(encoding='utf-8')
INSTALLER = (ROOT / 'MisterMuscle_Setup.iss').read_text(encoding='utf-8')

assert "APP_VERSION = '5.3.7'" in MAIN
assert '#define MyAppVersion "5.3.7"' in INSTALLER
assert 'AppVerName={#MyAppName} v{#MyAppVersion}' in INSTALLER
assert 'UninstallDisplayName={#MyAppName} v{#MyAppVersion}' in INSTALLER
assert 'DISPLAY_VERSION = APP_VERSION.lstrip(' in MAIN
assert 'ignore_cleanup_errors=True' in MAIN and 'ignore_cleanup_errors=True' in TIMELINE
assert "self.original_web.setUrl(QUrl('about:blank'))" in MAIN
assert "self.player.setSource(QUrl())" in MAIN
assert "self._original_server_thread.join(timeout=2)" in MAIN
assert 'self._preview_dirs.clear()' in MAIN

TREE = ast.parse(MAIN)

def top_function(name):
    node = next(x for x in TREE.body
                if isinstance(x, ast.FunctionDef) and x.name == name)
    code = compile(ast.fix_missing_locations(
        ast.Module(body=[node], type_ignores=[])), '<extracted function>', 'exec')
    namespace = {'Path': Path, 'time': time, 'shutil': shutil, 'tempfile': tempfile}
    exec(code, namespace)
    return namespace[name]


def class_method(class_name, method_name):
    cls = next(x for x in ast.walk(TREE)
               if isinstance(x, ast.ClassDef) and x.name == class_name)
    return next(x for x in cls.body
                if isinstance(x, ast.FunctionDef) and x.name == method_name)


def test_temporary_locks():
    cleanup = top_function('_cleanup_temporary_directory')
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / 'locked_preview'
        target.mkdir()
        (target / 'preview.mp4').write_bytes(b'not a real media file')

        class Locked:
            name = str(target)
            calls = 0
            def cleanup(self):
                self.calls += 1
                if self.calls < 3:
                    raise PermissionError(32, 'File is held by WebEngine')
                shutil.rmtree(self.name)

        job = Locked()
        assert cleanup(job, attempts=5, pause=0) is True
        assert job.calls == 3
        assert not target.exists()

        target.mkdir()
        class ForeverLocked:
            name = str(target)
            def cleanup(self):
                raise PermissionError(32, 'In use')
        assert cleanup(ForeverLocked(), attempts=2, pause=0) is False
        shutil.rmtree(target)

    assert cleanup(None) is True
    print('PASS locked Windows temp directory cleanup with bounded retry')


def test_http_disconnect():
    harmless = top_function('_is_expected_player_disconnect')
    assert harmless(ConnectionResetError(10054, 'Connection reset'))
    assert harmless(ConnectionAbortedError(10053, 'Connection aborted'))
    assert harmless(BrokenPipeError(32, 'Broken pipe'))
    other = OSError('socket closed')
    other.winerror = 10058
    assert harmless(other)
    assert not harmless(RuntimeError('corrupt media'))
    assert not harmless(PermissionError(13, 'Source file cannot be read'))

    events = []

    class Base:
        error_to_raise = None
        def copyfile(self, src, dst):
            if self.error_to_raise:
                raise self.error_to_raise
            return 'copied'

    handler_method = class_method('PlayerHTTPHandler', 'copyfile')
    handler_cls = ast.ClassDef(
        name='PlayerHTTPHandler', bases=[ast.Name(id='Base', ctx=ast.Load())],
        keywords=[], body=[handler_method], decorator_list=[])
    body = ast.fix_missing_locations(ast.Module(body=[handler_cls], type_ignores=[]))
    context = {'Base': Base, '_is_expected_player_disconnect': harmless}
    exec(compile(body, '<player handler>', 'exec'), context)
    handler = context['PlayerHTTPHandler']()
    handler.log_message = lambda *args: events.append(args)
    handler.error_to_raise = ConnectionResetError(10054, 'browser seeked')
    assert handler.copyfile(None, None) is None
    assert events
    handler.error_to_raise = RuntimeError('unexpected read problem')
    try:
        handler.copyfile(None, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Unexpected HTTP handler problems must not be suppressed')

    errors = []
    server_method = class_method('PlayerHTTPServer', 'handle_error')
    server_cls = ast.ClassDef(
        name='PlayerHTTPServer', bases=[ast.Name(id='object', ctx=ast.Load())],
        keywords=[], body=[server_method], decorator_list=[])
    server_module = ast.fix_missing_locations(ast.Module(body=[server_cls], type_ignores=[]))
    server_scope = {
        'sys': sys, 'traceback': traceback, '_is_expected_player_disconnect': harmless,
        'app_logger': lambda level, source, message: errors.append((level, source, message))}
    exec(compile(server_module, '<player server>', 'exec'), server_scope)
    server = server_scope['PlayerHTTPServer']()
    try:
        raise ConnectionResetError(10054, 'browser canceled')
    except ConnectionResetError:
        server.handle_error(None, None)
    assert errors[-1][0] == 'DEBUG', errors[-1]
    try:
        raise RuntimeError('unrelated server crash')
    except RuntimeError:
        server.handle_error(None, None)
    assert errors[-1][0] == 'ERROR', errors[-1]
    print('PASS normal browser disconnects suppressed, unexpected server crashes retained')


if __name__ == '__main__':
    test_temporary_locks()
    test_http_disconnect()
    from test_separate_audio_markers_536 import markers_test, ffmpeg_test
    markers_test()
    ffmpeg_test()
    from test_full_waveform_and_cuts_535 import _check_waveform
    _check_waveform()
    print('PASS prior independent audio and full waveform regressions')
