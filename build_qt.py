"""Build a fully self-contained Windows application. Requires Python 3.12/3.13 x64."""
import os,sys,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
if sys.platform!='win32': raise SystemExit('Build must run on Windows x64.')
if sys.maxsize<2**32: raise SystemExit('64-bit Python required.')
for name in ('yt-dlp.exe','ffmpeg.exe','ffprobe.exe'):
    if not (root/'tools'/name).is_file(): raise SystemExit(f'Missing tools\\{name}. See README_RELEASE.txt')
try: import PySide6.QtWebEngineWidgets, PySide6.QtWebChannel, PySide6.QtMultimedia, PySide6.QtMultimediaWidgets
except ImportError as exc: raise SystemExit(f'Missing PySide6 component: {exc}')
try: import PyInstaller
except ImportError: raise SystemExit('Install PyInstaller: py -m pip install pyinstaller')
cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir',
 '--name','MisterMuscle','--icon',str(root/'ikona.ico'),'--distpath',str(root/'dist'),'--workpath',str(root/'build'),
 '--specpath',str(root), '--collect-all','PySide6.QtWebEngineCore',
 '--collect-all','PySide6.QtWebEngineWidgets','--collect-all','PySide6.QtWebChannel',
 '--collect-all','PySide6.QtMultimedia','--collect-all','PySide6.QtMultimediaWidgets',
 '--add-data',str(root/'assets')+os.pathsep+'assets',
 '--hidden-import','mister_muscle_original_player',str(root/'mister_muscle_qt.py')]
subprocess.run(cmd,cwd=root,check=True)
out=root/'dist'/'MisterMuscle'
(out/'tools').mkdir(exist_ok=True)
for name in ('yt-dlp.exe','ffmpeg.exe','ffprobe.exe'): shutil.copy2(root/'tools'/name,out/'tools'/name)
if not (out/'MisterMuscle.exe').is_file(): raise SystemExit('EXE missing')
compiler=shutil.which('ISCC.exe')
if not compiler:
    for base in (os.environ.get('ProgramFiles(x86)',''),os.environ.get('ProgramFiles','')):
        if not base: continue
        for version in ('Inno Setup 7', 'Inno Setup 6'):
            test=Path(base)/version/'ISCC.exe'
            if test.is_file():
                compiler=str(test)
                break
        if compiler: break
if not compiler: raise SystemExit('Install Inno Setup 6/7 (ISCC.exe) and rerun build')
# Only compile the installer. Do not run the built app or installer.
subprocess.run([compiler,str(root/'MisterMuscle_Setup.iss')],cwd=root,check=True)
setup=root/'Output'/'MisterMuscle_Setup.exe'
if not setup.is_file(): raise SystemExit('Setup missing')
print('READY:',setup)
