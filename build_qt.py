"""Build a fully self-contained Windows application. Requires 64-bit Python and Windows."""
import os,sys,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parent
if sys.platform!='win32': raise SystemExit('Build must run on Windows x64.')
if sys.maxsize<2**32: raise SystemExit('64-bit Python required.')
# Resolve required standalone tools from tools/, the repository root, or PATH.
# Keep executables in tools/ before packaging so new installations work offline.
(root/'tools').mkdir(exist_ok=True)
for name in ('yt-dlp.exe','ffmpeg.exe','ffprobe.exe'):
    destination = root/'tools'/name
    if not destination.is_file():
        candidate = next((item for item in (root/name,) if item.is_file()), None)
        if candidate is None:
            found = shutil.which(name)
            candidate = Path(found) if found else None
        if candidate is None or not candidate.is_file():
            raise SystemExit(f'Missing {name}. Put it in tools/ (or repository root) or add it to PATH before publishing.')
        shutil.copy2(candidate, destination)
# Deno is optional for the build itself; include it when available for supported sources.
if not (root/'tools'/'deno.exe').is_file():
    found = (root/'deno.exe') if (root/'deno.exe').is_file() else shutil.which('deno.exe')
    if found: shutil.copy2(found, root/'tools'/'deno.exe')
# gallery-dl: download official standalone executable during build if missing.
if not (root/'tools'/'gallery-dl.exe').is_file():
    import json, urllib.request
    api='https://codeberg.org/api/v1/repos/mikf/gallery-dl/releases/latest'
    try:
        req=urllib.request.Request(api,headers={'User-Agent':'MisterMuscleBuilder/1.0'})
        with urllib.request.urlopen(req,timeout=20) as response:release=json.load(response)
        assets=release.get('assets',[])
        asset=next((a for a in assets if a.get('name','').lower()=='gallery-dl.exe'),None)
        if not asset:raise RuntimeError('gallery-dl.exe asset missing from latest release')
        url=asset.get('browser_download_url','')
        if not url.startswith('https://codeberg.org/'):raise RuntimeError('Unexpected gallery-dl download host')
        req=urllib.request.Request(url,headers={'User-Agent':'MisterMuscleBuilder/1.0'})
        target=root/'tools'/'gallery-dl.exe'
        temp=target.with_suffix('.download')
        with urllib.request.urlopen(req,timeout=120) as response,temp.open('wb') as dest:
            shutil.copyfileobj(response,dest)
        if temp.stat().st_size<100000:raise RuntimeError('gallery-dl download too small')
        temp.replace(target)
    except Exception as exc:
        raise SystemExit(f'gallery-dl download failed: {exc}. Place gallery-dl.exe in tools and retry.')
try: import PySide6.QtWebEngineWidgets, PySide6.QtWebChannel, PySide6.QtMultimedia, PySide6.QtMultimediaWidgets
except ImportError as exc: raise SystemExit(f'Missing PySide6 component: {exc}')
try: import PyInstaller
except ImportError: raise SystemExit('Install PyInstaller: py -m pip install pyinstaller')
cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir',
 '--name','MisterMuscle','--distpath',str(root/'dist'),'--workpath',str(root/'build'),
 '--specpath',str(root), '--collect-all','PySide6.QtWebEngineCore',
 '--collect-all','PySide6.QtWebEngineWidgets','--collect-all','PySide6.QtWebChannel',
 '--collect-all','PySide6.QtMultimedia','--collect-all','PySide6.QtMultimediaWidgets',
 '--hidden-import','mister_muscle_original_player',
 '--hidden-import','pro_timeline',
 '--hidden-import','phase4_lab', '--hidden-import','phase3_engine',
 '--hidden-import','beta_studio']
if (root/'ikona.ico').is_file():cmd+=['--icon',str(root/'ikona.ico')]
if (root/'assets').is_dir():cmd+=['--add-data',str(root/'assets')+os.pathsep+'assets']
if (root/'CHANGELOG.md').is_file():cmd+=['--add-data',str(root/'CHANGELOG.md')+os.pathsep+'.']
cmd.append(str(root/'mister_muscle_qt.py'))
subprocess.run(cmd,cwd=root,check=True)
out=root/'dist'/'MisterMuscle'
(out/'tools').mkdir(exist_ok=True)
for name in ('yt-dlp.exe','ffmpeg.exe','ffprobe.exe','gallery-dl.exe','deno.exe'):
    if (root/'tools'/name).is_file():shutil.copy2(root/'tools'/name,out/'tools'/name)
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
