# -*- coding: utf-8 -*-
"""
Mister Muscle Downloader — v17

Novo u odnosu na v16:
  * 3 nacina skidanja: video+zvuk / SAMO video (bez zvuka) / SAMO zvuk (mp3, m4a, wav, flac, opus)
  * izbor rezolucije, H.264 prekidac, ugradnja metapodataka
  * player za označavanje isječka je UGRAĐEN u glavni prozor (Windows + pywin32) -
    ne otvara se više zaseban prozor za pregled/rezanje
  * puni "desktop" raspored: velik prozor koji se moze rastezati i maksimizirati
  * "Provjeri azuriranja" azurira alate koji su joj potrebni za rad (yt-dlp + ffmpeg)
  * ffmpeg se automatski preuzima (bez njega spajanje slike i zvuka i rezanje NE RADE)
  * alati (yt-dlp.exe, ffmpeg.exe) idu u upisiv folder cak i ako je app u Program Files
"""

import os
import re
import sys
import json
import time
import zipfile
import shutil
import traceback
import functools
import http.server
import socketserver
import tempfile
import subprocess
import threading
import multiprocessing
import urllib.request
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

try:
    import webview
    PYWEBVIEW_DOSTUPAN = True
except ImportError:
    PYWEBVIEW_DOSTUPAN = False

try:
    # Opcionalno - koristi se za PRAVU pauzu (suspend/resume yt-dlp.exe procesa)
    # i za pouzdano prekidanje cijelog stabla procesa (yt-dlp + njegov ffmpeg).
    import psutil
    PSUTIL_DOSTUPAN = True
except ImportError:
    PSUTIL_DOSTUPAN = False

try:
    # Opcionalno (samo Windows) - koristi se da se pywebview prozor za pregled
    # videa UGRADI unutar glavnog Tkinter prozora umjesto da iskace zasebno.
    # Bez ovoga player i dalje radi, samo u svom prozoru (kao ranije).
    import win32gui
    import win32con
    WIN32_DOSTUPAN = True
except ImportError:
    WIN32_DOSTUPAN = False


# ============================================================================
#  VERZIJA
# ============================================================================
APP_VERZIJA = "1.1"


def _bazni_folder():
    """Folder gdje stvarno stoji .exe (kad je upakirano PyInstallerom) ili folder
    skripte. Kod --onefile builda __file__ pokazuje na privremeni raspakirani
    folder koji nestaje pri zatvaranju, pa se NE smije koristiti za trajne stvari."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _ikona_putanja():
    """Nalazi 'ikona.ico' - u razvojnom okruzenju pored ove skripte, a u
    upakiranom --onefile .exe-u unutar privremenog raspakiranog resurs-foldera
    (sys._MEIPASS) gdje ga je build_exe.py stavio preko '--add-data'. Vraca
    None ako ne postoji nigdje (npr. .exe je izgradjen bez ikona.ico) - u tom
    slucaju se jednostavno koristi Tkinterova zadana ikona, bez greske."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            put = os.path.join(meipass, "ikona.ico")
            if os.path.isfile(put):
                return put
    put = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ikona.ico")
    return put if os.path.isfile(put) else None


def _je_upisiv(folder):
    """Pravi test upisa - postojanje foldera ne znaci da u njega smijemo pisati
    (Program Files, mrezni disk, OneDrive u read-only stanju...)."""
    try:
        os.makedirs(folder, exist_ok=True)
        proba = os.path.join(folder, ".proba_upisa")
        with open(proba, "w") as f:
            f.write("ok")
        os.remove(proba)
        return True
    except Exception:
        return False


def _podaci_folder():
    """%LOCALAPPDATA%\\MisterMuscle (Windows) / ~/.mistermuscle - jedina lokacija
    koja je garantirano upisiva bez admin prava."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "MisterMuscle")
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        return _bazni_folder()
    return folder


def _config_folder():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "MisterMuscle")
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        return _podaci_folder()
    return folder


def _alati_folder():
    """Gdje zive yt-dlp.exe i ffmpeg.exe.

    Prvo pored aplikacije (prakticno - sve na jednom mjestu, i tako je radila v16),
    ali SAMO ako je taj folder stvarno upisiv. Ako nije (app instalirana u
    Program Files), padamo na %LOCALAPPDATA%\\MisterMuscle\\alati. Ovo je bio
    tihi bug u v16: yt-dlp.exe se pokusavao spremiti pored .exe-a i update je
    pucao s permission greskom na svakom racunalu gdje app nije u user folderu."""
    baza = _bazni_folder()
    if _je_upisiv(baza):
        return baza
    folder = os.path.join(_podaci_folder(), "alati")
    os.makedirs(folder, exist_ok=True)
    return folder


IZLAZNI_FOLDER = os.path.join(
    os.path.expanduser("~"), "Videos", "MisterMuscle"
) if os.name == "nt" else os.path.join(_bazni_folder(), "preuzeto")
CONFIG_PATH = os.path.join(_config_folder(), "mister_muscle_config.json")

JE_WINDOWS = os.name == "nt"

_SUBPROCESS_FLAGS = {}
if JE_WINDOWS:
    _SUBPROCESS_FLAGS["creationflags"] = subprocess.CREATE_NO_WINDOW

# Ugradnja pywebview prozora unutar glavnog Tkinter prozora radi preko
# reparentanja OS prozora (SetParent) i moguca je samo na Windowsima uz
# pywin32. Ako nesto od toga fali, player i dalje radi - samo u svom
# zasebnom prozoru, kao u ranijim verzijama.
EMBED_PLAYERA_DOSTUPAN = JE_WINDOWS and WIN32_DOSTUPAN
WEBVIEW_NASLOV_PROZORA = "MisterMuscle_EmbeddedPlayer"


# ============================================================================
#  yt-dlp.exe  (samostalni binarnik s ugradenim self-updateom)
# ============================================================================
YT_DLP_EXE_NAZIV = "yt-dlp.exe" if JE_WINDOWS else "yt-dlp"
YT_DLP_EXE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/" + YT_DLP_EXE_NAZIV


def yt_dlp_exe_putanja():
    """Trazi yt-dlp.exe prvo pored aplikacije (stare instalacije v16), pa u folderu
    alata. Vraca prvu koja postoji, inace onu u koju bismo ga skinuli."""
    kandidati = [
        os.path.join(_bazni_folder(), YT_DLP_EXE_NAZIV),
        os.path.join(_alati_folder(), YT_DLP_EXE_NAZIV),
    ]
    for p in kandidati:
        if os.path.isfile(p):
            return p
    return os.path.join(_alati_folder(), YT_DLP_EXE_NAZIV)


def yt_dlp_dostupan():
    return os.path.isfile(yt_dlp_exe_putanja())


def preuzmi_datoteku(url, cilj, callback_postotak=None, min_velicina=0):
    """Preuzima fajl uz izvjestavanje o postotku. Skida se pod privremenim imenom
    pa se tek na kraju atomicno preimenuje - da nikad ne ostane napola preuzet fajl."""
    privremena = cilj + ".preuzimanje"
    os.makedirs(os.path.dirname(cilj), exist_ok=True)
    zahtjev = urllib.request.Request(url, headers={"User-Agent": "MisterMuscle/" + APP_VERZIJA})
    with urllib.request.urlopen(zahtjev, timeout=60) as odgovor, open(privremena, "wb") as izlaz:
        ukupno = int(odgovor.headers.get("Content-Length") or 0)
        preuzeto = 0
        while True:
            komad = odgovor.read(262144)
            if not komad:
                break
            izlaz.write(komad)
            preuzeto += len(komad)
            if callback_postotak and ukupno:
                callback_postotak(preuzeto / ukupno * 100.0)
    if min_velicina and os.path.getsize(privremena) < min_velicina:
        try:
            os.remove(privremena)
        except OSError:
            pass
        raise RuntimeError("Preuzeti fajl je premalen — prekinuta veza ili pogrešan link.")
    os.replace(privremena, cilj)
    if not JE_WINDOWS:
        try:
            os.chmod(cilj, 0o755)
        except OSError:
            pass
    return cilj


def preuzmi_yt_dlp_exe(callback_status=None, callback_postotak=None):
    putanja = os.path.join(_alati_folder(), YT_DLP_EXE_NAZIV)
    if callback_status:
        callback_status(f"⏳ Preuzimam {YT_DLP_EXE_NAZIV} s GitHub Releases...")
    preuzmi_datoteku(YT_DLP_EXE_URL, putanja, callback_postotak, min_velicina=1_000_000)
    if callback_status:
        callback_status(f"✅ {YT_DLP_EXE_NAZIV} spreman: {putanja}")
    return putanja


def _najnovija_verzija_yt_dlp():
    """Provjerava (GitHub API, BEZ preuzimanja ičega) koja je najnovija objavljena
    verzija yt-dlp-a - koristi se za TIHU provjeru pri pokretanju (vidi
    App._tiha_provjera_azuriranja_pri_pokretanju). Vraca None ako provjera ne
    uspije (npr. nema interneta ili je GitHub trenutno nedostupan) - u tom
    slucaju se jednostavno ne prijavljuje nikakvo azuriranje, ne remeti
    pokretanje app-a."""
    try:
        zahtjev = urllib.request.Request(
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest",
            headers={"User-Agent": "MisterMuscle/" + APP_VERZIJA, "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(zahtjev, timeout=10) as odgovor:
            podaci = json.loads(odgovor.read().decode("utf-8"))
        return (podaci.get("tag_name") or "").strip() or None
    except Exception:
        return None


# Repo iz kojeg SAMA APLIKACIJA (ne yt-dlp) provjerava svoje nove verzije -
# promijeni ovo ako ikad presalis repo na drugi GitHub racun/naziv.
APP_GITHUB_REPO = "wilsoncro/mister-muscle-downloader"


def _usporedi_verzije(v1, v2):
    """Usporedjuje dva broja verzije sastavljena od brojeva odvojenih tockama
    (npr. '1.10' i '1.2') NUMERICKI, ne kao obican tekst - obican tekst bi
    krivo rekao da je '1.10' < '1.2' (jer '1' < '2' na drugom znaku). Vraca
    1 ako je v1 noviji, -1 ako je v1 stariji, 0 ako su isti."""
    def dijelovi(v):
        return [int(x) for x in re.findall(r"\d+", v)] or [0]
    a, b = dijelovi(v1), dijelovi(v2)
    duljina = max(len(a), len(b))
    a += [0] * (duljina - len(a))
    b += [0] * (duljina - len(b))
    if a > b:
        return 1
    if a < b:
        return -1
    return 0


def _najnovija_verzija_app():
    """Provjerava (GitHub API, BEZ preuzimanja ičega) postoji li novija verzija
    SAME APLIKACIJE objavljena kao GitHub Release - i ako postoji, nalazi
    direktan link na .exe instalater prikacen uz taj release (prvi .exe asset
    koji nadje). Vraca (verzija, url) ili (None, None) ako provjera ne uspije
    ili release nema prikacen .exe."""
    try:
        zahtjev = urllib.request.Request(
            f"https://api.github.com/repos/{APP_GITHUB_REPO}/releases/latest",
            headers={"User-Agent": "MisterMuscle/" + APP_VERZIJA, "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(zahtjev, timeout=10) as odgovor:
            podaci = json.loads(odgovor.read().decode("utf-8"))
        tag = (podaci.get("tag_name") or "").strip()
        if not tag:
            return None, None
        url_setup = None
        for asset in podaci.get("assets", []):
            naziv = (asset.get("name") or "").lower()
            if naziv.endswith(".exe"):
                url_setup = asset.get("browser_download_url")
                break
        if not url_setup:
            return None, None
        return tag, url_setup
    except Exception:
        return None, None


def pokreni_yt_dlp(argumenti, **kwargs):
    return subprocess.run(
        [yt_dlp_exe_putanja(), *argumenti],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        **_SUBPROCESS_FLAGS, **kwargs
    )


def pokreni_yt_dlp_popen(argumenti, **kwargs):
    return subprocess.Popen(
        [yt_dlp_exe_putanja(), *argumenti],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        **_SUBPROCESS_FLAGS, **kwargs
    )


# ============================================================================
#  ffmpeg  (OBAVEZAN, ne opcionalan!)
# ============================================================================
# Bez ffmpega NE RADI: spajanje slike i zvuka (bestvideo+bestaudio), rezanje
# isjecka (--download-sections), pretvorba u mp3 i provjera/pretvorba kodeka.
# v16 je racunala da ffmpeg vec postoji na PATH-u - na cistom racunalu ne postoji,
# pa je skidanje "uspjelo" ali je zavrsilo s dva odvojena fajla ili greskom.
FFMPEG_ZIP_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_NAZIV = "ffmpeg.exe" if JE_WINDOWS else "ffmpeg"
FFPROBE_NAZIV = "ffprobe.exe" if JE_WINDOWS else "ffprobe"


def _nadi_alat(naziv):
    """Nas vlastiti primjerak ima prednost pred sistemskim, da svi rade s istom
    poznatom verzijom; ako naseg nema, uzimamo onaj s PATH-a (ako postoji)."""
    for folder in (_alati_folder(), _bazni_folder()):
        p = os.path.join(folder, naziv)
        if os.path.isfile(p):
            return p
    sistemski = shutil.which(naziv)
    return sistemski


def ffmpeg_putanja():
    return _nadi_alat(FFMPEG_NAZIV)


def ffprobe_putanja():
    return _nadi_alat(FFPROBE_NAZIV)


def ffmpeg_dostupan():
    return ffmpeg_putanja() is not None


def preuzmi_ffmpeg(callback_status=None, callback_postotak=None):
    """Skida sluzbeni statican Windows build i vadi SAMO ffmpeg.exe i ffprobe.exe
    (ostatak zipa nam ne treba - stedimo ~200 MB na disku)."""
    if not JE_WINDOWS:
        raise RuntimeError(
            "Automatsko preuzimanje ffmpega podržano je samo na Windowsima.\n"
            "Na Linuxu/macOS-u instaliraj ga ručno (npr. 'sudo apt install ffmpeg' ili 'brew install ffmpeg')."
        )
    cilj_folder = _alati_folder()
    zip_putanja = os.path.join(cilj_folder, "_ffmpeg_privremeno.zip")
    if callback_status:
        callback_status("⏳ Preuzimam ffmpeg (~80 MB, samo prvi put)...")
    preuzmi_datoteku(FFMPEG_ZIP_URL, zip_putanja, callback_postotak, min_velicina=5_000_000)

    if callback_status:
        callback_status("📦 Raspakiravam ffmpeg...")
    izvuceno = 0
    with zipfile.ZipFile(zip_putanja) as z:
        for clan in z.namelist():
            osnovno = os.path.basename(clan)
            if osnovno.lower() in (FFMPEG_NAZIV.lower(), FFPROBE_NAZIV.lower()):
                with z.open(clan) as izvor, open(os.path.join(cilj_folder, osnovno), "wb") as odrediste:
                    shutil.copyfileobj(izvor, odrediste)
                izvuceno += 1
    try:
        os.remove(zip_putanja)
    except OSError:
        pass
    if izvuceno < 2:
        raise RuntimeError("U preuzetom arhivu nisu pronađeni ffmpeg.exe i ffprobe.exe.")
    if callback_status:
        callback_status(f"✅ ffmpeg spreman: {cilj_folder}")
    return cilj_folder


def ffmpeg_argumenti():
    """yt-dlp sam ne zna gdje je nas ffmpeg ako nije na PATH-u - moramo mu reci."""
    put = ffmpeg_putanja()
    if put:
        return ["--ffmpeg-location", os.path.dirname(os.path.abspath(put))]
    return []


# ============================================================================
#  WebView2 Runtime  (OBAVEZAN na Windowsima za player - sistemska komponenta)
# ============================================================================
# Za razliku od yt-dlp.exe/ffmpeg.exe (koje SAMI skidamo kao obicne datoteke),
# WebView2 Runtime je Microsoftova komponenta koju instalira pravi Windows
# instalater (dijele je SVE app na racunalu, ne samo nasa) - bez nje pywebview
# na Windowsima ne moze prikazati NIJEDAN player (ni ugradjeni ni zaseban
# prozor). Na modernim Windows 10/11 racunalima je gotovo uvijek vec tu (sam
# Windows Update je instalira/azurira), ali na starijim/"ocisceniim" sustavima
# zna nedostajati - a bez ove provjere korisnik samo vidi da player ne radi,
# bez ikakvog objasnjenja zasto.
WEBVIEW2_CLIENT_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
# Sluzbeni, trajni Microsoftov link ("Get the Link") za "Evergreen Bootstrapper" -
# mali (~2 MB) instalater koji sam povuce i instalira najnoviju verziju runtime-a
# za arhitekturu tog racunala. Dokumentirano u Microsoftovim WebView2 uputama
# za distribuciju ("Distribute your app and the WebView2 Runtime").
WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def webview2_dostupan():
    """Provjerava (preko registrija - sluzbeno dokumentirana Microsoftova metoda)
    je li WebView2 Runtime vec instaliran. Provjeravaju se SVA tri moguca mjesta
    (HKLM 64-bit, HKLM 32-bit, HKCU per-user) jer je dovoljno da bilo koje od
    njih ima ispravnu (ne "0.0.0.0") verziju."""
    if not JE_WINDOWS:
        return True  # provjera je Windows-specificna, na drugim OS-ima ne blokiramo nista
    try:
        import winreg
    except ImportError:
        return True
    mjesta = [
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\EdgeUpdate\\Clients\\" + WEBVIEW2_CLIENT_GUID),
        (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\" + WEBVIEW2_CLIENT_GUID),
        (winreg.HKEY_CURRENT_USER, "SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\" + WEBVIEW2_CLIENT_GUID),
    ]
    for koren, put in mjesta:
        try:
            with winreg.OpenKey(koren, put) as kljuc:
                verzija, _ = winreg.QueryValueEx(kljuc, "pv")
                if verzija and verzija != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def preuzmi_i_instaliraj_webview2(callback_status=None):
    """Skida sluzbeni Evergreen Bootstrapper i pokrece ga. Instalacija moze
    zatraziti Windows UAC potvrdu (to je normalno i ocekivano - WebView2 je
    sistemska komponenta, ne nasa datoteka, pa joj treba prava razina prava
    da bi je Windows stvarno instalirao)."""
    if not JE_WINDOWS:
        raise RuntimeError("WebView2 Runtime instalacija je moguca samo na Windowsima.")
    cilj = os.path.join(_alati_folder(), "MicrosoftEdgeWebView2Setup.exe")
    if callback_status:
        callback_status("⏳ Preuzimam Microsoft Edge WebView2 Runtime instalater (malen, ~2 MB)...")
    preuzmi_datoteku(WEBVIEW2_BOOTSTRAPPER_URL, cilj, min_velicina=500_000)
    if callback_status:
        callback_status("⏳ Pokrećem WebView2 instalaciju — Windows može zatražiti potvrdu (UAC)...")
    rezultat = subprocess.run([cilj, "/silent", "/install"], timeout=180)
    if rezultat.returncode != 0:
        raise RuntimeError(
            f"WebView2 instalater je završio s kodom {rezultat.returncode} "
            "(korisnik je možda odbio UAC potvrdu, ili je instalacija otkazana)."
        )
    if callback_status:
        callback_status("✅ WebView2 Runtime uspješno instaliran.")


# ============================================================================
#  CONFIG (pamti sve postavke izmedu pokretanja)
# ============================================================================
ZADANI_CONFIG = {
    "izlazni_folder": IZLAZNI_FOLDER,
    "nacin": "video_zvuk",          # video_zvuk | samo_video | samo_zvuk
    "kvaliteta": "Najbolja",
    "video_format": "mp4",
    "audio_format": "mp3",
    "h264": False,
    "metapodaci": False,
    "prozor": "1240x820",
    "jezik": "en",                  # hr | en
    "zadnja_prikazana_verzija": "", # koja je verzija zadnja pokazala "Novosti" dijalog
}


# ============================================================================
#  JEZIK (hrvatski / english)
# ============================================================================
# Prijevodi pokrivaju stalne dijelove sucelja (naslovi, gumbi, izbornici,
# glavne poruke) - dublje dijagnosticke poruke u STATUS logu (tijekom
# skidanja i sl.) ostaju za sada na hrvatskom, da opseg ostane pouzdan i
# provjerljiv. Nedostajuci kljuc se automatski vraca na hrvatski tekst.
PRIJEVODI = {
    "hr": {
        "naslov_prozora": "Mister Muscle Downloader",
        "naslov_app": "💪 Mister Muscle Downloader",
        "podnaslov_app": "YouTube · TikTok · Instagram — video, isječci i zvuk u najboljoj kvaliteti",
        "meni_alati": "Alati",
        "meni_provjeri_azuriranja": "🔄 Provjeri ažuriranja (sve)",
        "meni_azuriraj_ytdlp": "Ažuriraj samo yt-dlp",
        "meni_reinstaliraj_ffmpeg": "Ponovno instaliraj ffmpeg",
        "meni_webview2": "Provjeri/instaliraj WebView2 Runtime",
        "meni_folder_alati": "📂 Otvori folder s alatima",
        "meni_config": "⚙ Otvori config",
        "meni_reset_prozor": "🗔 Resetiraj veličinu prozora",
        "meni_pomoc": "Pomoć",
        "meni_o_aplikaciji": "O aplikaciji",
        "meni_jezik": "Jezik",
        "meni_jezik_hr": "Hrvatski",
        "meni_jezik_en": "English",
        "gumb_azuriranja": "🔄 Provjeri ažuriranja",
        "kartica_1": "LINKOVI (jedan po retku)",
        "kartica_2": "ŠTO SKIDAMO",
        "kartica_3": "GDJE SE SPREMA",
        "placeholder_linkovi": "Zalijepi YouTube / TikTok / Instagram link ovdje...",
        "gumb_pregledaj": "🎬 Pregledaj i označi isječak",
        "gumb_zalijepi": "📋 Zalijepi",
        "gumb_ocisti": "🗑 Očisti",
        "gumb_ponisti_isjecak": "✕ Poništi",
        "nacin_video_zvuk": "🎬  Video + zvuk",
        "nacin_video_zvuk_opis": "spojen mp4 — standardno",
        "nacin_samo_video": "🎞  Samo video (bez zvuka)",
        "nacin_samo_video_opis": "nijemi zapis za montažu / B-roll",
        "nacin_samo_zvuk": "🎵  Samo zvuk",
        "nacin_samo_zvuk_opis": "mp3 / m4a / wav — bez slike",
        "oznaka_kvaliteta": "Kvaliteta",
        "oznaka_format_videa": "Format videa",
        "oznaka_format_zvuka": "Format zvuka",
        "cb_h264": "Premiere-ready (H.264/avc1)",
        "cb_h264_opis": "traži avc1 i po potrebi pretvori — Premiere ga uvijek čita",
        "cb_metapodaci": "Ugradi naslovnicu i metapodatke",
        "cb_metapodaci_opis": "naslov, izvođač i cover u fajl",
        "gumb_odaberi_folder": "📂 Odaberi",
        "gumb_otvori_folder": "👁 Otvori",
        "skini_video": "⬇   SKINI VIDEO",
        "skini_video_bez_zvuka": "⬇   SKINI VIDEO BEZ ZVUKA",
        "skini_zvuk": "⬇   SKINI ZVUK",
        "gumb_pauziraj": "⏸ Pauziraj",
        "gumb_nastavi": "▶ Nastavi",
        "gumb_prekini": "✕ Prekini",
        "status_naslov": "STATUS",
        "player_naslov": "PLAYER",
        "status_sakrij": "▾ sakrij",
        "status_prikazi": "▸ prikaži",
        "gumb_ocisti_log": "🗑 očisti log",
        "player_placeholder": "🎬\n\nPlayer za označavanje isječka\nprikazat će se ovdje kad klikneš\n'Pregledaj i označi isječak'",
        "player_zaseban_prozor": "🎬\n\nPlayer je otvoren u zasebnom prozoru\n(ugradnja u ovaj prozor zahtijeva Windows + pywin32)",
        "o_aplikaciji_naslov": "O aplikaciji",
        "o_aplikaciji_autor": "Razvio: Mr_muscle",
        "o_aplikaciji_prava": "Sva prava pridržana.",
        "o_aplikaciji_auto_update": "Pri svakom pokretanju app tiho provjeri ima li nova verzija yt-dlp-a "
                                    "(mehanizam za skidanje) i ponudi ažuriranje ako je nađe — a ffmpeg i "
                                    "yt-dlp se preuzimaju sami ako uopće nedostaju.",
        "o_aplikaciji_alati": "Alati",
        "o_aplikaciji_postavke": "Postavke",
        "nije_pronadjen": "nije pronađen",
        "provjeravam_alate": "Provjeravam alate...",
        "provjeravam": "🔄 Provjeravam...",
        "skidam": "Skidam...",
        # --- dijaloski okviri i STATUS log poruke (dodano naknadno) ---
        "err_naslov": "Greška",
        "msg_need_pywebview": "ℹ Za '🎬 Pregledaj i označi' treba biblioteka 'pywebview' (pip install pywebview).",
        "msg_need_pywin32": "ℹ Za player UGRAĐEN u prozor treba 'pywin32' (pip install pywin32) — za sad će se otvarati u zasebnom prozoru.",
        "msg_black_player_hint": "ℹ Ako ugrađeni player ostane crn nakon otvaranja, pričekaj sekundu-dvije (automatski se pokušava 'probuditi') ili malo rastegni prozor aplikacije.",
        "msg_window_reset": "🗔 Veličina prozora resetirana na 1240×820.",
        "msg_cannot_open": "Ne mogu otvoriti: {0}\n\n{1}",
        "msg_folder_session_only": "⚠ Folder vrijedi za ovu sesiju, ali ga ne mogu zapamtiti: {0}",
        "msg_folder_saved": "📁 Folder: {0} (zapamćen)",
        "msg_start_marked": "📍 Početak: {0}",
        "msg_end_marked": "📍 Kraj: {0}",
        "webview2_naslov": "WebView2 Runtime",
        "webview2_ok_text": "Sve u redu — WebView2 Runtime je već instaliran.",
        "msg_webview2_missing": "⚠ Microsoft Edge WebView2 Runtime nije pronađen — bez njega player (pregled/rezanje) neće raditi.",
        "webview2_confirm_naslov": "Nedostaje WebView2 Runtime",
        "webview2_confirm_text": "Za prikaz playera (pregled i označavanje isječka) potrebna je Microsoft Edge "
                                 "WebView2 komponenta, a nije pronađena na ovom računalu.\n\n"
                                 "To je jednokratna, službena Microsoftova instalacija (dijele je sve aplikacije "
                                 "na računalu, ne samo ova) - može zatražiti Windows potvrdu (UAC).\n\n"
                                 "Preuzeti i instalirati je sada automatski?",
        "msg_webview2_skipped": "ℹ Preskočeno — player neće raditi dok se WebView2 Runtime ručno ne instalira "
                                "(https://developer.microsoft.com/microsoft-edge/webview2/).",
        "msg_webview2_ready": "ℹ Sad probaj otvoriti player ('🎬 Pregledaj i označi isječak').",
        "msg_webview2_install_failed": "❌ WebView2 instalacija nije uspjela: {0}",
        "webview2_error_text": "Ne mogu instalirati WebView2 Runtime: {0}\n\nProbaj ručno preuzeti s https://developer.microsoft.com/microsoft-edge/webview2/",
        "msg_tool_missing_downloading": "⚠ {0} nedostaje — preuzimam...",
        "msg_ytdlp_download_failed": "❌ Preuzimanje yt-dlp nije uspjelo: {0}",
        "msg_ffmpeg_missing_note": "⚠ ffmpeg nedostaje — bez njega ne rade spajanje slike i zvuka, "
                                   "rezanje isječka ni pretvorba u mp3. Preuzimam...",
        "msg_ffmpeg_download_failed": "❌ Preuzimanje ffmpega nije uspjelo: {0}",
        "update_available_naslov": "Dostupno ažuriranje",
        "update_available_text": "Dostupna je nova verzija yt-dlp-a: {0}\n(trenutno imaš: {1})\n\n"
                                 "yt-dlp se često ažurira da prati promjene na YouTube/TikTok/Instagram — "
                                 "redovito ažuriranje smanjuje šansu za greške pri skidanju.\n\n"
                                 "Preuzeti i instalirati novu verziju sada?",
        "msg_updating_ytdlp": "🔄 Preuzimam noviju verziju yt-dlp-a...",
        "msg_tools_summary": "📦 yt-dlp {0} · {1}",
        "status_tools_unavailable": "nedostupan",
        "status_ffmpeg_missing": "❌ ffmpeg NEDOSTAJE",
        "update_in_progress_naslov": "Skidanje u tijeku",
        "update_in_progress_text": "Ažuriranje se ne smije raditi dok traje skidanje.\nPričekaj da završi ili klikni '✕ Prekini'.",
        "updates_naslov": "Ažuriranja",
        "msg_ytdlp_output": "🔄 yt-dlp: {0}",
        "msg_ytdlp_running_update": "🔄 Pokrećem yt-dlp -U ...",
        "msg_ytdlp_downloaded_first": "✅ yt-dlp: preuzet (prvi put)",
        "msg_ytdlp_download_failed_short": "❌ yt-dlp: preuzimanje nije uspjelo ({0})",
        "msg_ytdlp_update_failed": "❌ yt-dlp: ažuriranje nije uspjelo (detalji u STATUS logu)",
        "msg_ytdlp_already_latest": "✅ yt-dlp: već najnoviji",
        "msg_ytdlp_updated": "🆕 yt-dlp: nadograđen na najnoviju verziju",
        "msg_ytdlp_check_done": "✅ yt-dlp: provjera završena",
        "msg_ytdlp_update_timeout": "❌ yt-dlp: ažuriranje je isteklo (spora veza) — pokušaj ponovno",
        "msg_ytdlp_update_error": "❌ yt-dlp: {0}",
        "msg_ffmpeg_present": "✅ ffmpeg: prisutan",
        "msg_ffmpeg_installed": "🆕 ffmpeg: instaliran",
        "msg_ffmpeg_error": "❌ ffmpeg: {0}",
        "err_pywebview_missing_text": "Biblioteka 'pywebview' nije instalirana.\n\nInstaliraj u terminalu:\n    pip install pywebview",
        "warn_naslov": "Upozorenje",
        "warn_paste_link_first": "Prvo zalijepi link.",
        "err_cant_recognize_youtube": "Ne prepoznajem YouTube video ID iz tog linka.",
        "msg_opening_player": "⏳ Otvaram player...",
        "msg_fetching_preview": "⏳ Dohvaćam pregled videa...",
        "msg_embed_disabled_fallback": "⏳ Embed onemogućen za taj video — preuzimam kraći lokalni pregled...",
        "msg_tiktok_bug_preview": "TikTok trenutno ima poznat problem u yt-dlp (ne u ovoj aplikaciji) — probaj 'Provjeri ažuriranja'.",
        "err_cant_fetch_preview": "Ne mogu dohvatiti pregled videa: {0}",
        "msg_preview_failed_log": "❌ Pregled nije uspio:\n{0}",
        "err_cant_prepare_player": "Ne mogu pripremiti player: {0}",
        "msg_embedded_ready": "✅ Player ugrađen i spreman.",
        "msg_embed_load_failed": "⚠ Ne mogu učitati ugrađeni player: {0} — koristim zaseban prozor.",
        "msg_need_psutil_pause": "ℹ Prava pauza traži 'psutil' (pip install psutil) — bez njega skidanje nastavlja u pozadini.",
        "msg_cant_pause_resume": "⚠ Ne mogu {0} proces: {1}",
        "akcija_pauzirati": "pauzirati",
        "akcija_nastaviti": "nastaviti",
        "msg_cancelled_by_user": "✕ Prekinuto na zahtjev korisnika.",
        "warn_no_link_naslov": "Nema linka",
        "warn_no_link_text": "Zalijepi barem jedan link.",
        "ffmpeg_missing_naslov": "Nedostaje ffmpeg",
        "ffmpeg_missing_confirm_text": "Za spajanje slike i zvuka, rezanje isječka i pretvorbu u mp3 potreban je ffmpeg, "
                                       "a nije pronađen.\n\nPreuzeti ga sada automatski?",
        "warn_download_in_progress_text": "Pričekaj da trenutno skidanje završi pa pokušaj ponovno.",
        "ffmpeg_missing_multi_text": "Za rezanje isječaka potreban je ffmpeg, a nije pronađen.\n\n"
                                     "Idi na 'Alati → Provjeri ažuriranja' da ga preuzmeš, pa pokušaj ponovno.",
        "err_cant_download_tool": "Ne mogu preuzeti {0}: {1}",
        "msg_merging": "🔗 Spajam sliku i zvuk...",
        "msg_extracting_audio": "🎵 Izvlačim i pretvaram zvuk...",
        "msg_silent_video_done": "🔇 Skinut nijemi video (bez audio zapisa).",
        "msg_error_generic": "❌ Greška: {0}",
        "err_cant_start_tool": "Ne mogu pokrenuti {0}: {1}",
        "msg_no_separate_video_stream": "ℹ Ovaj izvor nema odvojeni video zapis — skidam cijeli pa uklanjam zvuk...",
        "msg_tiktok_bug_download": "ℹ️ Poznat obrazac greške (TikTok je promijenio JS 'izazov'). Klikni "
                                   "'🔄 Provjeri ažuriranja' pa pokušaj ponovno.",
        "msg_retry_attempt": "⏳ Pokušaj {0} nije uspio — pokušavam ponovno...",
        "msg_full_error_details": "🔍 Puni detalji greške:\n{0}",
        "msg_no_ffmpeg_kept_audio": "⚠ Nema ffmpega — fajl je ostao sa zvukom.",
        "msg_audio_removed": "🔇 Zvuk uklonjen.",
        "msg_duration_fixed": "🩹 Ispravljeno trajanje isječka u zaglavlju fajla.",
        "msg_codec_check_skipped": "⚠ Preskačem provjeru kodeka (nema ffmpeg/ffprobe).",
        "msg_converting_codec": "🎞 Video je {0} — pretvaram u H.264 za Premiere...",
        "msg_codec_converted": "✅ Pretvoreno u H.264.",
        "msg_codec_convert_failed": "⚠ Pretvorba nije uspjela — fajl je ostao u originalnom kodeku.",
        "msg_codec_check_failed": "⚠ Provjera kodeka nije uspjela: {0}",
        "msg_download_cancelled": "\n✕ Skidanje prekinuto.",
        "done_naslov": "Gotovo",
        "msg_all_done_log": "\n🎉 Gotovo! Folder: {0}",
        "msg_all_done_text": "Sve je uspješno preuzeto!",
        "msg_partial_log": "\n⚠ Djelomično: {0} OK, {1} neuspješno.",
        "partial_naslov": "Djelomično gotovo",
        "msg_partial_text": "{0} uspješno, {1} nije uspjelo.\nPogledaj STATUS log.",
        "msg_all_failed_log": "\n❌ Nijedno skidanje nije uspjelo.",
        "failed_naslov": "Nije uspjelo",
        "msg_all_failed_text": "Skidanje nije uspjelo.\nPogledaj crveni ❌ redak u STATUS logu.",
        "isjecak_label": "✂ Isječak: {0} → {1}",
        "isjecak_pocetak": "početak",
        "isjecak_kraj": "kraj",
        "msg_embed_prep_failed": "⚠ Ugrađeni player se nije uspio pripremiti: {0}",
        "msg_embed_not_found": "⚠ Ugrađeni player nije pronađen — koristit će se zaseban prozor.",
        "msg_embed_failed": "⚠ Ugradnja playera nije uspjela: {0}",
        "app_update_naslov": "Dostupna nova verzija",
        "app_update_text": "Dostupna je nova verzija aplikacije: v{0}\n(trenutno imaš: v{1})\n\n"
                           "Preuzeti i pokrenuti instalaciju sada? Aplikacija će se zatvoriti da bi se "
                           "mogla nadograditi.",
        "msg_downloading_app_update": "⏳ Preuzimam novu verziju aplikacije...",
        "msg_launching_installer": "⏳ Pokrećem instalaciju nove verzije — aplikacija se sada zatvara...",
        "msg_app_update_failed": "❌ Ažuriranje aplikacije nije uspjelo: {0}",
    },
    "en": {
        "naslov_prozora": "Mister Muscle Downloader",
        "naslov_app": "💪 Mister Muscle Downloader",
        "podnaslov_app": "YouTube · TikTok · Instagram — video, clips and audio in the best quality",
        "meni_alati": "Tools",
        "meni_provjeri_azuriranja": "🔄 Check for updates (all)",
        "meni_azuriraj_ytdlp": "Update yt-dlp only",
        "meni_reinstaliraj_ffmpeg": "Reinstall ffmpeg",
        "meni_webview2": "Check/install WebView2 Runtime",
        "meni_folder_alati": "📂 Open tools folder",
        "meni_config": "⚙ Open config",
        "meni_reset_prozor": "🗔 Reset window size",
        "meni_pomoc": "Help",
        "meni_o_aplikaciji": "About",
        "meni_jezik": "Language",
        "meni_jezik_hr": "Hrvatski",
        "meni_jezik_en": "English",
        "gumb_azuriranja": "🔄 Check for updates",
        "kartica_1": "LINKS (one per line)",
        "kartica_2": "WHAT TO DOWNLOAD",
        "kartica_3": "WHERE TO SAVE",
        "placeholder_linkovi": "Paste a YouTube / TikTok / Instagram link here...",
        "gumb_pregledaj": "🎬 Preview & mark clip",
        "gumb_zalijepi": "📋 Paste",
        "gumb_ocisti": "🗑 Clear",
        "gumb_ponisti_isjecak": "✕ Clear",
        "nacin_video_zvuk": "🎬  Video + audio",
        "nacin_video_zvuk_opis": "merged mp4 — standard",
        "nacin_samo_video": "🎞  Video only (no audio)",
        "nacin_samo_video_opis": "silent clip for editing / B-roll",
        "nacin_samo_zvuk": "🎵  Audio only",
        "nacin_samo_zvuk_opis": "mp3 / m4a / wav — no video",
        "oznaka_kvaliteta": "Quality",
        "oznaka_format_videa": "Video format",
        "oznaka_format_zvuka": "Audio format",
        "cb_h264": "Premiere-ready (H.264/avc1)",
        "cb_h264_opis": "requests avc1 and converts if needed — Premiere always reads it",
        "cb_metapodaci": "Embed thumbnail and metadata",
        "cb_metapodaci_opis": "title, artist and cover art in the file",
        "gumb_odaberi_folder": "📂 Choose",
        "gumb_otvori_folder": "👁 Open",
        "skini_video": "⬇   DOWNLOAD VIDEO",
        "skini_video_bez_zvuka": "⬇   DOWNLOAD VIDEO (NO AUDIO)",
        "skini_zvuk": "⬇   DOWNLOAD AUDIO",
        "gumb_pauziraj": "⏸ Pause",
        "gumb_nastavi": "▶ Resume",
        "gumb_prekini": "✕ Cancel",
        "status_naslov": "STATUS",
        "player_naslov": "PLAYER",
        "status_sakrij": "▾ hide",
        "status_prikazi": "▸ show",
        "gumb_ocisti_log": "🗑 clear log",
        "player_placeholder": "🎬\n\nThe clip-marking player will\nappear here once you click\n'Preview & mark clip'",
        "player_zaseban_prozor": "🎬\n\nThe player opened in a separate window\n(embedding it here requires Windows + pywin32)",
        "o_aplikaciji_naslov": "About",
        "o_aplikaciji_autor": "Developed by Mr_muscle",
        "o_aplikaciji_prava": "All rights reserved.",
        "o_aplikaciji_auto_update": "On every launch, the app quietly checks whether a newer version of "
                                    "yt-dlp (the download engine) is available and offers to update it if "
                                    "found — ffmpeg and yt-dlp are downloaded automatically if missing.",
        "o_aplikaciji_alati": "Tools",
        "o_aplikaciji_postavke": "Settings",
        "nije_pronadjen": "not found",
        "provjeravam_alate": "Checking tools...",
        "provjeravam": "🔄 Checking...",
        "skidam": "Downloading...",
        # --- dialogs and STATUS log messages (added later) ---
        "err_naslov": "Error",
        "msg_need_pywebview": "ℹ️ The '🎬 Preview & mark clip' feature needs the 'pywebview' library (pip install pywebview).",
        "msg_need_pywin32": "ℹ️ An in-window EMBEDDED player needs 'pywin32' (pip install pywin32) — for now it will open in a separate window.",
        "msg_black_player_hint": "ℹ️ If the embedded player stays black after opening, wait a second or two (it auto-retries) or slightly resize the app window.",
        "msg_window_reset": "🗔 Window size reset to 1240×820.",
        "msg_cannot_open": "Can't open: {0}\n\n{1}",
        "msg_folder_session_only": "⚠️ The folder works for this session, but I can't remember it: {0}",
        "msg_folder_saved": "📁 Folder: {0} (saved)",
        "msg_start_marked": "📍 Start: {0}",
        "msg_end_marked": "📍 End: {0}",
        "webview2_naslov": "WebView2 Runtime",
        "webview2_ok_text": "All good — WebView2 Runtime is already installed.",
        "msg_webview2_missing": "⚠️ Microsoft Edge WebView2 Runtime was not found — without it the player (preview/trim) won't work.",
        "webview2_confirm_naslov": "WebView2 Runtime missing",
        "webview2_confirm_text": "Displaying the player (previewing and marking a clip) requires the Microsoft "
                                 "Edge WebView2 component, which wasn't found on this computer.\n\n"
                                 "This is a one-time, official Microsoft installation (shared by every app on this "
                                 "computer, not just this one) — it may prompt for Windows confirmation (UAC).\n\n"
                                 "Download and install it automatically now?",
        "msg_webview2_skipped": "ℹ️ Skipped — the player won't work until WebView2 Runtime is installed manually "
                                "(https://developer.microsoft.com/microsoft-edge/webview2/).",
        "msg_webview2_ready": "ℹ️ Now try opening the player ('🎬 Preview & mark clip').",
        "msg_webview2_install_failed": "❌ WebView2 installation failed: {0}",
        "webview2_error_text": "Can't install WebView2 Runtime: {0}\n\nTry downloading it manually from https://developer.microsoft.com/microsoft-edge/webview2/",
        "msg_tool_missing_downloading": "⚠️ {0} is missing — downloading...",
        "msg_ytdlp_download_failed": "❌ Downloading yt-dlp failed: {0}",
        "msg_ffmpeg_missing_note": "⚠️ ffmpeg is missing — without it, merging video+audio, trimming clips, and "
                                   "converting to mp3 won't work. Downloading...",
        "msg_ffmpeg_download_failed": "❌ Downloading ffmpeg failed: {0}",
        "update_available_naslov": "Update available",
        "update_available_text": "A new version of yt-dlp is available: {0}\n(you currently have: {1})\n\n"
                                 "yt-dlp updates often to keep up with YouTube/TikTok/Instagram changes — "
                                 "updating regularly reduces the chance of download errors.\n\n"
                                 "Download and install the new version now?",
        "msg_updating_ytdlp": "🔄 Downloading the newer yt-dlp version...",
        "msg_tools_summary": "📦 yt-dlp {0} · {1}",
        "status_tools_unavailable": "unavailable",
        "status_ffmpeg_missing": "❌ ffmpeg MISSING",
        "update_in_progress_naslov": "Download in progress",
        "update_in_progress_text": "Updating can't be done while a download is running.\nWait for it to finish or click '✕ Cancel'.",
        "updates_naslov": "Updates",
        "msg_ytdlp_output": "🔄 yt-dlp: {0}",
        "msg_ytdlp_running_update": "🔄 Running yt-dlp -U ...",
        "msg_ytdlp_downloaded_first": "✅ yt-dlp: downloaded (first time)",
        "msg_ytdlp_download_failed_short": "❌ yt-dlp: download failed ({0})",
        "msg_ytdlp_update_failed": "❌ yt-dlp: update failed (see STATUS log for details)",
        "msg_ytdlp_already_latest": "✅ yt-dlp: already up to date",
        "msg_ytdlp_updated": "🆕 yt-dlp: updated to the latest version",
        "msg_ytdlp_check_done": "✅ yt-dlp: check complete",
        "msg_ytdlp_update_timeout": "❌ yt-dlp: update timed out (slow connection) — try again",
        "msg_ytdlp_update_error": "❌ yt-dlp: {0}",
        "msg_ffmpeg_present": "✅ ffmpeg: present",
        "msg_ffmpeg_installed": "🆕 ffmpeg: installed",
        "msg_ffmpeg_error": "❌ ffmpeg: {0}",
        "err_pywebview_missing_text": "The 'pywebview' library isn't installed.\n\nInstall it in a terminal:\n    pip install pywebview",
        "warn_naslov": "Warning",
        "warn_paste_link_first": "Paste a link first.",
        "err_cant_recognize_youtube": "I can't recognize a YouTube video ID in that link.",
        "msg_opening_player": "⏳ Opening player...",
        "msg_fetching_preview": "⏳ Fetching video preview...",
        "msg_embed_disabled_fallback": "⏳ Embedding disabled for this video — downloading a shorter local preview...",
        "msg_tiktok_bug_preview": "TikTok currently has a known issue in yt-dlp (not in this app) — try 'Check for updates'.",
        "err_cant_fetch_preview": "Can't fetch the video preview: {0}",
        "msg_preview_failed_log": "❌ Preview failed:\n{0}",
        "err_cant_prepare_player": "Can't prepare the player: {0}",
        "msg_embedded_ready": "✅ Player embedded and ready.",
        "msg_embed_load_failed": "⚠️ Can't load the embedded player: {0} — using a separate window instead.",
        "msg_need_psutil_pause": "ℹ️ A real pause needs 'psutil' (pip install psutil) — without it, the download continues in the background.",
        "msg_cant_pause_resume": "⚠️ Can't {0} the process: {1}",
        "akcija_pauzirati": "pause",
        "akcija_nastaviti": "resume",
        "msg_cancelled_by_user": "✕ Cancelled by the user.",
        "warn_no_link_naslov": "No link",
        "warn_no_link_text": "Paste at least one link.",
        "ffmpeg_missing_naslov": "ffmpeg missing",
        "ffmpeg_missing_confirm_text": "Merging video+audio, trimming a clip, and converting to mp3 all need "
                                       "ffmpeg, which wasn't found.\n\nDownload it automatically now?",
        "warn_download_in_progress_text": "Wait for the current download to finish, then try again.",
        "ffmpeg_missing_multi_text": "Trimming clips needs ffmpeg, which wasn't found.\n\n"
                                     "Go to 'Tools → Check for updates' to download it, then try again.",
        "err_cant_download_tool": "Can't download {0}: {1}",
        "msg_merging": "🔗 Merging video and audio...",
        "msg_extracting_audio": "🎵 Extracting and converting audio...",
        "msg_silent_video_done": "🔇 Downloaded a silent video (no audio track).",
        "msg_error_generic": "❌ Error: {0}",
        "err_cant_start_tool": "Can't start {0}: {1}",
        "msg_no_separate_video_stream": "ℹ️ This source has no separate video stream — downloading the full file and removing the audio...",
        "msg_tiktok_bug_download": "ℹ️ Known error pattern (TikTok changed its JS 'challenge'). Click "
                                   "'🔄 Check for updates' and try again.",
        "msg_retry_attempt": "⏳ Attempt {0} failed — retrying...",
        "msg_full_error_details": "🔍 Full error details:\n{0}",
        "msg_no_ffmpeg_kept_audio": "⚠️ No ffmpeg — the file kept its audio.",
        "msg_audio_removed": "🔇 Audio removed.",
        "msg_duration_fixed": "🩹 Fixed the clip's duration in the file header.",
        "msg_codec_check_skipped": "⚠️ Skipping codec check (no ffmpeg/ffprobe).",
        "msg_converting_codec": "🎞 Video is {0} — converting to H.264 for Premiere...",
        "msg_codec_converted": "✅ Converted to H.264.",
        "msg_codec_convert_failed": "⚠️ Conversion failed — the file stayed in its original codec.",
        "msg_codec_check_failed": "⚠️ Codec check failed: {0}",
        "msg_download_cancelled": "\n✕ Download cancelled.",
        "done_naslov": "Done",
        "msg_all_done_log": "\n🎉 Done! Folder: {0}",
        "msg_all_done_text": "Everything downloaded successfully!",
        "msg_partial_log": "\n⚠ Partial: {0} OK, {1} failed.",
        "partial_naslov": "Partially done",
        "msg_partial_text": "{0} succeeded, {1} failed.\nSee the STATUS log.",
        "msg_all_failed_log": "\n❌ No downloads succeeded.",
        "failed_naslov": "Failed",
        "msg_all_failed_text": "The download failed.\nSee the red ❌ line in the STATUS log.",
        "isjecak_label": "✂ Clip: {0} → {1}",
        "isjecak_pocetak": "start",
        "isjecak_kraj": "end",
        "msg_embed_prep_failed": "⚠️ Failed to prepare the embedded player: {0}",
        "msg_embed_not_found": "⚠️ Embedded player not found — using a separate window instead.",
        "msg_embed_failed": "⚠️ Embedding the player failed: {0}",
        "app_update_naslov": "New version available",
        "app_update_text": "A new app version is available: v{0}\n(you currently have: v{1})\n\n"
                           "Download and run the installer now? The app will close so it can be updated.",
        "msg_downloading_app_update": "⏳ Downloading the new app version...",
        "msg_launching_installer": "⏳ Launching the new version's installer — the app is closing now...",
        "msg_app_update_failed": "❌ App update failed: {0}",
    },
}


# ============================================================================
#  NOVOSTI / BUGFIX DIJALOG (prikaze se JEDNOM po verziji, pri prvom
#  pokretanju te verzije - ne svaki put)
# ============================================================================
# ZA SVAKU SLJEDECU VERZIJU: dodaj novi "APP_VERZIJA: {...}" blok ovdje (isti
# broj kao APP_VERZIJA gore) - sadrzaj je lista kratkih recenica (hr i en) sto
# je promijenjeno/popravljeno u toj verziji. Ako za trenutnu APP_VERZIJA ne
# postoji unos ovdje, dijalog se jednostavno ne prikaze (bez greske).
PROMJENE = {
    "1.1": {
        "hr": [
            "Popravljeno: isječci su nakon skidanja ponekad pokazivali pogrešno "
            "(izvorno, puno duže) trajanje umjesto stvarnog trajanja isječka, pa "
            "se nije moglo normalno premotavati.",
            "Popravljeno: VLC je za isječke prikazivao staro trajanje čak i kad "
            "je Premiere prikazivao točno vrijeme.",
            "Dodano: HH:MM:SS prikaz vremena (umjesto samo minuta:sekunda) pri "
            "označavanju isječka u playeru.",
            "Uklonjeni opisi ispod načina skidanja i checkboxovi 'Premiere-ready' "
            "/ 'Ugradi naslovnicu i metapodatke' — više se ne prikazuju.",
        ],
        "en": [
            "Fixed: after downloading, clips sometimes showed the wrong "
            "(original, much longer) duration instead of the actual clip "
            "length, which broke seeking.",
            "Fixed: VLC showed the old duration for clips even when Premiere "
            "displayed the correct time.",
            "Added: HH:MM:SS time display (instead of just minutes:seconds) "
            "when marking a clip in the player.",
            "Removed the descriptions under the download modes and the "
            "'Premiere-ready' / 'Embed thumbnail and metadata' checkboxes.",
        ],
    },
    "1.2": {
        "hr": [
            "Dodano: aplikacija sada sama provjerava GitHub za nove verzije "
            "SEBE (ne samo yt-dlp-a) i može se sama ažurirati — preuzme i "
            "pokrene instalaciju nove verzije jednim klikom.",
        ],
        "en": [
            "Added: the app now checks GitHub for new versions of ITSELF "
            "(not just yt-dlp) and can self-update — download and launch the "
            "new version's installer with one click.",
        ],
    },
    "1.3": {
        "hr": [
            "Popravljeno: greška u kodiranju znakova koja je mogla oštetiti "
            "emoji/posebne znakove u sučelju nakon nadogradnje verzije.",
            "Poboljšano: dodatni popravak trajanja isječaka za VLC — vremenske "
            "oznake unutar isječka se sad ispravno resetiraju na početak, "
            "umjesto da ostanu na originalnoj poziciji iz izvornog videa.",
        ],
        "en": [
            "Fixed: a character-encoding bug that could corrupt emoji/special "
            "characters in the interface after a version update.",
            "Improved: additional clip-duration fix for VLC — timestamps "
            "inside a clip are now correctly reset to the start, instead of "
            "staying at their original position from the source video.",
        ],
    },
    "1.4": {
        "hr": [
            "Dodano: sad možeš povući (drag) izravno po traci u playeru da "
            "označiš isječak, umjesto da moraš koristiti samo 'Postavi OD/DO' "
            "dugmad — dok povlačiš, iznad trake se prikazuje raspon uživo.",
            "Dodano: postojeći isječak na traci sad ima hvatišta na rubovima — "
            "povuci lijevo/desno da pomjeriš početak ili kraj bez pravljenja "
            "nove selekcije, ili povuci sredinu da pomjeriš cijeli isječak.",
            "Dodano: red u listi isječaka se sad vizualno istakne (plavi okvir) "
            "kad klikneš na njegovo Od/Do polje.",
        ],
        "en": [
            "Added: you can now drag directly on the player's timeline to mark "
            "a clip, instead of only using the 'Set start/end' buttons — a "
            "live time range tooltip shows above the timeline while dragging.",
            "Added: an existing clip on the timeline now has edge handles — "
            "drag left/right to move the start or end without creating a new "
            "selection, or drag the middle to move the whole clip.",
            "Added: a clip's row in the list is now visually highlighted (blue "
            "border) when you click its Start/End field.",
        ],
    },
}


def ucitaj_config():
    podaci = dict(ZADANI_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            spremljeno = json.load(f)
        if isinstance(spremljeno, dict):
            podaci.update({k: v for k, v in spremljeno.items() if k in ZADANI_CONFIG})
    except Exception:
        pass
    if not os.path.isdir(str(podaci.get("izlazni_folder", ""))):
        podaci["izlazni_folder"] = IZLAZNI_FOLDER
    return podaci


def spremi_config(podaci):
    """Vraca None ako uspije, inace tekst greske (da se moze prikazati korisniku)."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(podaci, f, ensure_ascii=False, indent=2)
        return None
    except Exception as err:
        return str(err)


def je_poznati_tiktok_challenge_bug(tekst_greske):
    """Prepoznaje obrazac greske kod kojeg je TikTok promijenio svoj JS 'izazov'
    a trenutna verzija yt-dlp.exe ga jos ne zna rijesiti. Ovo NIJE nesto sto se
    popravlja u ovoj skripti - ceka se popravak u samom yt-dlp projektu."""
    t = tekst_greske.lower()
    return "solve_challenge_and_set_cookies" in t or (
        "unable to extract" in t and ("webpage video data" in t or "rehydration" in t)
    )


# --- DIZAJN: "Liquid Glass" (po uzoru na iOS/iPhone stakleno-prozirne,
# zaobljene panele). Tkinter nema ugradjenu podrsku ni za pravu prozirnost/
# blur ni za zaobljene rubove, pa se ovdje taj dojam gradi bez rizicnih
# custom widgeta - kroz boje, tanke svjetlije "staklene" linije (odsjaj
# svjetla na vrhu kartica) i generozan razmak. Player prozor (ugradjeni ili
# fallback zaseban) je zaseban HTML/CSS dokument - TAMO CSS stvarno podrzava
# backdrop-filter blur i potpuno zaobljene rubove, pa ondje staklo izgleda
# "pravo" (vidi _player_html nize).
BG = "#0a0b18"           # duboka indigo pozadina prozora
CARD = "#1b1d38"         # "staklena" ploha kartica
CARD_LIGHT = "#242748"   # ugnjezdeni/isticuci paneli (npr. info o isjecku)
ACCENT = "#0a84ff"       # iOS-plava - glavni akcent
ACCENT_HOVER = "#3aa0ff"
TEXT = "#f5f6fc"
SUBTEXT = "#9aa0c8"
LOG_BG = "#0c0d1e"
LOG_TEXT = "#5ee6c8"
BORDER = "#3a3d68"       # tanak "stakleni" rub kartica
TROUGH = "#20223f"
PAUSE_BG = "#242748"
PAUSE_HOVER = "#2f335c"
SUCCESS = "#32d74b"      # iOS-zelena
DANGER = "#ff453a"       # iOS-crvena
INPUT_BG = "#12142a"

# "Caacupé One" (besplatan Google Font, SIL OFL licenca) je referenca za
# veliki naslov aplikacije - gust, "display" font. Ako nije instaliran na
# racunalu, Tkinter automatski i tiho koristi zamjenski font (bez greske),
# pa je siguran za koristiti bez instalacije. Za pravi izgled instaliraj ga s
# https://github.com/googlefonts/caacupe
FONT_NASLOV = "Caacupé One"


def posvijetli(hex_boja, faktor):
    """Vraca hex boju posvijetljenu prema bijeloj (faktor 0..1). Cista
    funkcija bez sporednih efekata - koristi se samo za boju tanke 'sjaj'
    linije na vrhu kartica (staklena_linija)."""
    hex_boja = hex_boja.lstrip("#")
    r, g, b = (int(hex_boja[i:i + 2], 16) for i in (0, 2, 4))
    r = int(r + (255 - r) * faktor)
    g = int(g + (255 - g) * faktor)
    b = int(b + (255 - b) * faktor)
    return f"#{r:02x}{g:02x}{b:02x}"


def staklena_linija(parent, boja, visina=1):
    """Tanka, svjetlija linija (obican Frame) tik uz gornji rub kartice -
    simulira odsjaj svjetla na staklenoj povrsini. Sigurna, standardna
    tk.Frame - bez custom widgeta koji bi mogli remetiti geometriju."""
    return tk.Frame(parent, bg=boja, height=visina)

KVALITETE = ["Najbolja", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"]
VIDEO_FORMATI = ["mp4", "mkv", "webm", "mov", "original (bez pretvorbe)"]
AUDIO_FORMATI = ["mp3", "m4a", "wav", "flac", "opus", "original (bez pretvorbe)"]


def visina_iz_kvalitete(tekst):
    m = re.match(r"(\d+)p", str(tekst))
    return int(m.group(1)) if m else None


def napravi_folder(putanja):
    if not os.path.exists(putanja):
        os.makedirs(putanja)


def parse_vrijeme(tekst):
    tekst = str(tekst).strip()
    if not tekst:
        return None
    if ":" in tekst:
        dijelovi = tekst.split(":")
        try:
            dijelovi = [int(d) for d in dijelovi]
        except ValueError:
            return None
        sekunde = 0
        for d in dijelovi:
            sekunde = sekunde * 60 + d
        return sekunde
    try:
        return float(tekst)
    except ValueError:
        return None


def formatiraj_trajanje(sekunde):
    if sekunde is None:
        return "?"
    sekunde = int(sekunde)
    h, ostatak = divmod(sekunde, 3600)
    m, s = divmod(ostatak, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def izvuci_video_id(url):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def prepoznaj_platformu(url):
    url_l = url.lower()
    if "youtube.com" in url_l or "youtu.be" in url_l:
        return "youtube"
    return "generic"


def _sigurni_id_za_url(url):
    import hashlib
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:16]


def _bez_duplikata(format_izraz):
    """'best/best' -> 'best'. Kad nema filtera visine neke se grane izraza poklope,
    a yt-dlp bi ih onda bezveze probavao dvaput."""
    vidjeno, rezultat = set(), []
    for dio in format_izraz.split("/"):
        if dio not in vidjeno:
            vidjeno.add(dio)
            rezultat.append(dio)
    return "/".join(rezultat)


def izgradi_format_string(platforma, nacin, visina, h264):
    """Slaze yt-dlp '-f' izraz. Odvojeno od GUI-ja da se moze testirati sam za sebe.

      nacin = 'samo_zvuk'  -> uzmi samo audio stream (slika se uopce ne skida)
      nacin = 'samo_video' -> uzmi samo video stream (nijemi fajl, ~30% manji)
      nacin = 'video_zvuk' -> klasicno, oba pa spoji (treba ffmpeg)
    """
    hf = f"[height<={visina}]" if visina else ""

    if nacin == "samo_zvuk":
        return "bestaudio/best"

    if nacin == "samo_video":
        if h264:
            return _bez_duplikata(f"bestvideo[vcodec^=avc1]{hf}/bestvideo{hf}/bestvideo")
        return _bez_duplikata(f"bestvideo{hf}/bestvideo")

    if platforma == "youtube":
        if h264:
            return _bez_duplikata(f"bestvideo[vcodec^=avc1]{hf}+bestaudio/bestvideo{hf}+bestaudio/best{hf}/best")
        return _bez_duplikata(f"bestvideo{hf}+bestaudio/best{hf}/best")

    # TikTok/Instagram/ostalo: cesto dolazi kao jedan gotov (progressive) fajl.
    if h264:
        return _bez_duplikata(f"best[vcodec^=avc1]{hf}/bestvideo[vcodec^=avc1]{hf}+bestaudio/"
                          f"bestvideo{hf}+bestaudio/best{hf}/best")
    return _bez_duplikata(f"bestvideo{hf}+bestaudio/best{hf}/best")


class PlayerAPI:
    def __init__(self, queue_sanjac):
        self.queue_sanjac = queue_sanjac

    def oznaci_pocetak(self, sekunde):
        self.queue_sanjac.put(("od", sekunde))

    def oznaci_kraj(self, sekunde):
        self.queue_sanjac.put(("do", sekunde))

    def skini_shorts_iz_player(self, od_vr, do_vr):
        self.queue_sanjac.put(("skini_short", (od_vr, do_vr)))

    def skini_visestruke_isjecke(self, lista):
        self.queue_sanjac.put(("skini_visestruke", lista))

    def zatrazi_lokalni_pregled(self):
        self.queue_sanjac.put(("lokalni_pregled", None))


_PLAYER_PRIJEVODI = {
    "hr": {
        "html_lang": "hr",
        "cc_title": "Uključi/isključi titlove",
        "cc_off": "💬 CC: isključeno",
        "cc_on": "💬 CC: uključeno",
        "spremno": "Spremno — klikni po traci ili koristi dugmad ispod.",
        "err_invalid_id": "Neispravan video ID",
        "err_html5": "Greška HTML5 playera",
        "err_removed": "Video ne postoji ili je uklonjen",
        "err_embed_disabled": "Vlasnik je onemogućio embed prikaz ovog videa",
        "embed_fallback_status": "⏳ Vlasnik je onemogućio YouTube embed za ovaj video — preuzimam kraći lokalni pregled...",
        "err_code_prefix": "Greška kod ",
        "err_generic_video": "❌ Ne mogu učitati video (link je istekao, privatan je ili nije podržan).",
        "trenutno": "Trenutno",
        "isjecak_prefix": "Isječak",
        "nije_oznaceno": "nije označeno",
        "ukupno": "Ukupno",
        "back5_title": "Nazad 5 sekundi",
        "playpause_title": "Play / Pauza",
        "playpause_text": "⏯ Play/Pauza",
        "fwd5_title": "Naprijed 5 sekundi",
        "set_start_title": "Označi trenutnu poziciju kao početak isječka",
        "set_start_text": "📍 Postavi OD",
        "set_end_title": "Označi trenutnu poziciju kao kraj isječka",
        "set_end_text": "📍 Postavi DO",
        "current_selection": "🎬 Trenutni odabir:",
        "od_label": "Od:",
        "do_label": "Do:",
        "od_label_short": "Od",
        "do_label_short": "Do",
        "add_selection": "+ Dodaj odabir",
        "download_all_clips": "⬇ Skini sve isječke",
        "loading_player": "Učitavam player...",
        "pause_text": "⏸ Pauziraj",
        "play_text": "▶ Pusti",
        "still_loading": "⏳ Video se još učitava, pričekaj trenutak...",
        "add_selection_warn": "⚠ Prvo označi Od i Do (📍 gumbi iznad ili upiši ručno), pa klikni + Dodaj odabir.",
        "remove_clip_title": "Ukloni ovaj isječak",
        "add_clip_warn": "⚠ Dodaj barem jedan isječak prije skidanja.",
        "download_started": "Preuzimanje {0} isječaka pokrenuto — pogledaj glavni prozor.",
        "drag_hint": "Povuci po traci da označiš isječak, ili klikni za premotavanje",
    },
    "en": {
        "html_lang": "en",
        "cc_title": "Toggle captions",
        "cc_off": "💬 CC: off",
        "cc_on": "💬 CC: on",
        "spremno": "Ready — click the timeline or use the buttons below.",
        "err_invalid_id": "Invalid video ID",
        "err_html5": "HTML5 player error",
        "err_removed": "Video does not exist or was removed",
        "err_embed_disabled": "The owner has disabled embedded playback for this video",
        "embed_fallback_status": "⏳ The owner disabled YouTube embedding for this video — downloading a shorter local preview...",
        "err_code_prefix": "Error code ",
        "err_generic_video": "❌ Can not load the video (the link expired, is private, or is not supported).",
        "trenutno": "Current",
        "isjecak_prefix": "Clip",
        "nije_oznaceno": "not marked",
        "ukupno": "Total",
        "back5_title": "Back 5 seconds",
        "playpause_title": "Play / Pause",
        "playpause_text": "⏯ Play/Pause",
        "fwd5_title": "Forward 5 seconds",
        "set_start_title": "Mark the current position as the clip start",
        "set_start_text": "📍 Set start",
        "set_end_title": "Mark the current position as the clip end",
        "set_end_text": "📍 Set end",
        "current_selection": "🎬 Current selection:",
        "od_label": "Start:",
        "do_label": "End:",
        "od_label_short": "Start",
        "do_label_short": "End",
        "add_selection": "+ Add selection",
        "download_all_clips": "⬇ Download all clips",
        "loading_player": "Loading player...",
        "pause_text": "⏸ Pause",
        "play_text": "▶ Play",
        "still_loading": "⏳ Video is still loading, please wait...",
        "add_selection_warn": "⚠️ First mark Start and End (📍 buttons above or type manually), then click + Add selection.",
        "remove_clip_title": "Remove this clip",
        "add_clip_warn": "⚠️ Add at least one clip before downloading.",
        "download_started": "Download of {0} clips started — check the main window.",
        "drag_hint": "Drag on the timeline to mark a clip, or click to seek",
    },
}


def _player_html(platform, video_id=None, video_src=None, jezik="hr"):
    PT = _PLAYER_PRIJEVODI.get(jezik, _PLAYER_PRIJEVODI["hr"])
    video_id_json = json.dumps(video_id)
    video_src_json = json.dumps(video_src)
    je_youtube = (platform == "youtube")

    head_script = '<script src="https://www.youtube.com/iframe_api"></script>' if je_youtube else ""
    player_element = '<div id="player"></div>' if je_youtube else '<video id="player" playsinline></video>'
    cc_dugme = (
        f'<button class="secondary icon-btn" id="btn-cc" onclick="toggleCC()" '
        f'title="{PT["cc_title"]}">{PT["cc_off"]}</button>'
        if je_youtube else ""
    )

    if je_youtube:
        init_script = f"""
      function onYouTubeIframeAPIReady() {{
        player = new YT.Player('player', {{
          videoId: {video_id_json},
          playerVars: {{
            playsinline: 1, controls: 0, disablekb: 1, modestbranding: 1,
            rel: 0, origin: window.location.origin, cc_load_policy: 0
          }}
        }});
        player.addEventListener('onReady', onPlayerReady);
        player.addEventListener('onError', onPlayerError);
      }}

      function onPlayerReady(e) {{
        spreman = true;
        trajanjeVid = player.getDuration();
        document.getElementById('vrijeme-ukupno').innerText = formatiraj(trajanjeVid);
        document.getElementById('status-bar').innerText = "{PT['spremno']}";
        setInterval(azurirajPlayhead, 250);
      }}

      function onPlayerError(e) {{
        var poruke = {{
          2: '{PT["err_invalid_id"]}',
          5: '{PT["err_html5"]}',
          100: '{PT["err_removed"]}',
          101: '{PT["err_embed_disabled"]}',
          150: '{PT["err_embed_disabled"]}'
        }};
        if ((e.data === 101 || e.data === 150) && !fallbackPokrenut) {{
          // Vlasnik je iskljucio YouTubeov sluzbeni embed player za ovaj video -
          // to je ogranicenje koje YouTube nametne po videu i ne moze se
          // zaobici u sluzbenom iframe playeru. Umjesto toga automatski
          // trazimo od Pythona da skine kraci lokalni pregled (isto kao za
          // TikTok/Instagram) i ucita GA - i dalje unutar ovog istog playera.
          fallbackPokrenut = true;
          document.getElementById('status-bar').innerText = '{PT["embed_fallback_status"]}';
          window.pywebview.api.zatrazi_lokalni_pregled();
          return;
        }}
        document.getElementById('status-bar').innerText =
          '❌ ' + (poruke[e.data] || ('{PT["err_code_prefix"]}' + e.data));
      }}

      function toggleCC() {{
        if (!spreman) return;
        ccUkljucen = !ccUkljucen;
        var btn = document.getElementById('btn-cc');
        if (ccUkljucen) {{
          player.loadModule('captions');
          player.setOption('captions', 'track', {{}});
          btn.innerText = '{PT["cc_on"]}';
          btn.classList.add('aktivno');
        }} else {{
          player.unloadModule('captions');
          btn.innerText = '{PT["cc_off"]}';
          btn.classList.remove('aktivno');
        }}
      }}
"""
    else:
        init_script = f"""
      function pokreniGenericPlayer() {{
        var vid = document.getElementById('player');
        vid.src = {video_src_json};
        player = {{
          getCurrentTime: function() {{ return vid.currentTime || 0; }},
          getDuration: function() {{ return vid.duration || 0; }},
          seekTo: function(t) {{ vid.currentTime = t; }},
          playVideo: function() {{ vid.play(); }},
          pauseVideo: function() {{ vid.pause(); }},
          getPlayerState: function() {{ return vid.paused ? 2 : 1; }},
          mute: function() {{ vid.muted = true; }},
          unMute: function() {{ vid.muted = false; }},
          setVolume: function(v) {{ vid.volume = v / 100; }}
        }};
        vid.addEventListener('loadedmetadata', function() {{
          spreman = true;
          trajanjeVid = player.getDuration();
          document.getElementById('vrijeme-ukupno').innerText = formatiraj(trajanjeVid);
          document.getElementById('status-bar').innerText = "{PT['spremno']}";
          setInterval(azurirajPlayhead, 250);
        }});
        vid.addEventListener('error', function() {{
          document.getElementById('status-bar').innerText = '{PT["err_generic_video"]}';
        }});
      }}
      window.addEventListener('DOMContentLoaded', pokreniGenericPlayer);
"""

    return f"""<!DOCTYPE html>
    <html lang="{PT['html_lang']}">
    <head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <style>
      * {{ box-sizing: border-box; }}
      html, body {{ height: 100%; }}
      body {{
        margin:0;
        background:
          radial-gradient(circle at 15% 0%, rgba(94,92,230,0.32), transparent 55%),
          radial-gradient(circle at 85% 100%, rgba(10,132,255,0.26), transparent 55%),
          linear-gradient(160deg, #0e1030 0%, #0a0b18 100%);
        font-family: "Segoe UI", "Segoe UI Emoji", sans-serif;
        display:flex; flex-direction:column; align-items:stretch; justify-content:flex-start;
        height:100vh; overflow:hidden; color:{TEXT}; user-select:none; padding: 14px;
      }}
      /* v17.0.3: #omot i #player-wrap su sad fleksibilni (flex:1) umjesto fiksne
         max-sirine/max-visine - player sad ispunjava sav raspoloziv prostor u
         desnom panelu umjesto da bude mali okvir centriran s praznim prostorom
         oko sebe. object-fit:contain na #player i dalje cuva omjer slike pa se
         video ne rasteze/izoblici, samo se crna pozadina prosiri da popuni okvir. */
      #omot {{
        display:flex; flex-direction:column; align-items:stretch;
        width:100%; height:100%; min-height:0; flex:1 1 auto;
      }}
      #player-wrap {{
        width:100%; flex:1 1 auto; min-height:0; background:#000;
        border-radius:18px; overflow:hidden; border: 1px solid rgba(255,255,255,0.14); position: relative;
        box-shadow: 0 12px 40px rgba(0,0,0,0.55);
      }}
      #player {{ width:100%; height:100%; object-fit: contain; background:#000; }}

      /* Pravo "staklo": prava prozirnost + blur pozadine iza - u ovom HTML/CSS
      okruzenju (za razliku od glavnog Tkinter prozora aplikacije) preglednik
      stvarno podrzava backdrop-filter, pa je ovo "pravi" iOS-stil glass. */
      #timeline-container {{
        width: 100%; height: 38px; background: rgba(255,255,255,0.06); border-radius: 14px;
        margin-top: 14px; position: relative; cursor: pointer;
        border: 1px solid rgba(255,255,255,0.14);
        backdrop-filter: blur(18px) saturate(160%);
        -webkit-backdrop-filter: blur(18px) saturate(160%);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18);
        transition: border-color 0.15s;
      }}
      #timeline-container:hover {{ border-color: {ACCENT}; }}
      #timeline-selection {{
        position: absolute; top: 0; bottom: 0; background: rgba(10, 132, 255, 0.32);
        border-left: 2px solid {ACCENT}; border-right: 2px solid {ACCENT};
        pointer-events: auto; display: none; border-radius: 14px; cursor: grab;
      }}
      #timeline-selection:active {{ cursor: grabbing; }}
      .selection-handle {{
        position: absolute; top: 0; bottom: 0; width: 14px; cursor: ew-resize;
        z-index: 4; display: flex; align-items: center; justify-content: center;
      }}
      .selection-handle::after {{
        content: ""; width: 4px; height: 60%; border-radius: 3px;
        background: rgba(255,255,255,0.9); box-shadow: 0 0 4px rgba(0,0,0,0.4);
      }}
      #handle-left {{ left: -7px; }}
      #handle-right {{ right: -7px; }}
      #timeline-playhead {{
        position: absolute; top: 0; bottom: 0; width: 3px; background: {SUCCESS}; left: 0%;
        pointer-events: none; box-shadow: 0 0 10px {SUCCESS}; z-index: 3;
      }}
      #drag-tooltip {{
        position: absolute; bottom: calc(100% + 8px); transform: translateX(-50%);
        background: {CARD}; color: {TEXT}; border: 1px solid {ACCENT};
        border-radius: 10px; padding: 5px 10px; font-size: 11px; font-weight: 700;
        white-space: nowrap; pointer-events: none; display: none; z-index: 5;
        box-shadow: 0 4px 14px rgba(0,0,0,0.4);
      }}
      .timeline-hint {{ font-size: 10px; color: {SUBTEXT}; text-align: center; margin-top: 6px; }}

      .info-red {{ display:flex; justify-content:space-between; width:100%; margin-top:10px; font-size:12px; color:{SUBTEXT}; }}
      .info-red span {{ font-weight: 600; color: {TEXT}; }}

      .kontrole {{ margin-top:14px; display:flex; align-items:center; gap:8px; width:100%; justify-content:center; flex-wrap:wrap; }}
      button {{
        background: linear-gradient(135deg, {ACCENT}, #5e5ce6);
        color:white; border:none; border-radius:999px;
        padding:10px 18px; font-size:12px; font-weight:600; cursor:pointer;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), 0 4px 14px rgba(10,132,255,0.35);
        transition: filter 0.15s, transform 0.1s;
      }}
      button:hover {{ filter: brightness(1.12); }}
      button:active {{ transform: scale(0.96); }}
      button.secondary {{
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.16);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.15);
        backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      }}
      button.secondary:hover {{ background: rgba(255,255,255,0.14); }}
      button.secondary.aktivno {{ background: linear-gradient(135deg, {ACCENT}, #5e5ce6); border-color: transparent; }}
      button.icon-btn {{ padding: 10px 14px; }}

      .shorts-panel {{
        margin-top: 16px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
        border-radius: 18px; padding: 14px 18px; width: 100%; display: flex; align-items: center;
        justify-content: space-between; gap: 12px; flex-wrap: wrap;
        backdrop-filter: blur(18px) saturate(160%); -webkit-backdrop-filter: blur(18px) saturate(160%);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18);
      }}
      .shorts-panel label {{ font-size: 12px; font-weight: bold; color: {SUBTEXT}; }}
      .shorts-panel input {{
        background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.16); color: {TEXT};
        border-radius: 10px; padding: 7px 10px; width: 80px; font-size: 12px; text-align: center; outline: none;
      }}
      .shorts-panel input:focus {{ border-color: {ACCENT}; }}
      .btn-download-short {{ background: linear-gradient(135deg, {SUCCESS}, #28b446); color: #06210c; font-weight: bold; }}
      .btn-download-short:hover {{ filter: brightness(1.1); }}
      .btn-dodaj-odabir {{
        background: rgba(10,132,255,0.16); color: {ACCENT}; border: 1px solid rgba(10,132,255,0.5);
        box-shadow: none;
      }}
      .btn-dodaj-odabir:hover {{ background: rgba(10,132,255,0.28); filter: none; }}

      /* --- lista više isječaka odjednom --- */
      #multi-panel {{ width: 100%; margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }}
      .selekcija-red {{
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
        border-radius: 14px; padding: 10px 14px; display: flex; align-items: center; gap: 14px;
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.14);
        transition: border-color 0.2s, background 0.2s;
      }}
      .selekcija-red.aktivna {{
        border-color: {ACCENT}; background: rgba(10,132,255,0.10);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.14), 0 0 0 1px rgba(10,132,255,0.35);
      }}
      .selekcija-broj {{ font-weight: 700; font-size: 13px; color: {SUBTEXT}; min-width: 16px; }}
      .selekcija-polja {{ flex: 1; display: flex; gap: 18px; flex-wrap: wrap; }}
      .selekcija-polje {{ display: flex; flex-direction: column; gap: 4px; }}
      .selekcija-polje label {{
        font-size: 9px; font-weight: 700; color: {SUBTEXT}; text-transform: uppercase; letter-spacing: .05em;
      }}
      .selekcija-polje input {{
        background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.16); color: {TEXT};
        border-radius: 8px; padding: 6px 10px; font-size: 12px; width: 110px; outline: none;
      }}
      .selekcija-polje input:focus {{ border-color: {ACCENT}; }}
      .sel-obrisi {{
        background: rgba(255,69,58,0.15); color: {DANGER}; border: 1px solid rgba(255,69,58,0.35);
        padding: 8px 10px; box-shadow: none;
      }}
      .sel-obrisi:hover {{ background: rgba(255,69,58,0.28); filter: none; }}
      #btn-skini-vise {{ width: 100%; display: none; }}

      .timeline-multi-blok {{
        position: absolute; top: 0; bottom: 0; background: rgba(10, 132, 255, 0.28);
        border-left: 2px solid {ACCENT}; border-right: 2px solid {ACCENT}; border-radius: 14px;
        pointer-events: none;
      }}

      #status-bar {{ margin-top: 10px; font-size: 12px; font-weight: 600; color: {SUCCESS}; text-align: center; min-height: 16px; }}

      #volume-wrap {{
        position: absolute; bottom: 12px; right: 12px; display:flex; align-items:center;
        gap: 6px; background: rgba(10,11,24,0.55); padding: 7px 12px; border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.15);
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
      }}
      #volume-slider {{ width: 70px; accent-color: {ACCENT}; cursor: pointer; }}
    </style>
    </head>
    <body>
    <div id="omot">
      <div id="player-wrap">
        {player_element}
        <div id="volume-wrap">
          <button class="icon-btn secondary" id="btn-mute" onclick="toggleMute()" style="padding:5px 9px;">🔊</button>
          <input type="range" id="volume-slider" min="0" max="100" value="100" oninput="promijeniGlasnocu(this.value)">
        </div>
      </div>

      <div id="timeline-container">
        <div id="timeline-selection">
          <div class="selection-handle" id="handle-left"></div>
          <div class="selection-handle" id="handle-right"></div>
        </div>
        <div id="timeline-playhead"></div>
        <div id="drag-tooltip"></div>
      </div>
      <div class="timeline-hint">{PT['drag_hint']}</div>

      <div class="info-red">
        <div>{PT['trenutno']}: <span id="vrijeme-trenutno">00:00:00</span></div>
        <div id="trajanje-isjecka-info" style="color:{SUCCESS}; font-weight:bold;">{PT['isjecak_prefix']}: {PT['nije_oznaceno']}</div>
        <div>{PT['ukupno']}: <span id="vrijeme-ukupno">00:00:00</span></div>
      </div>

      <div class="kontrole">
        <button class="secondary icon-btn" onclick="pomakniZa(-5)" title="{PT['back5_title']}">⏪ -5s</button>
        <button class="secondary icon-btn" id="btn-play" onclick="togglePlay()" title="{PT['playpause_title']}">{PT['playpause_text']}</button>
        <button class="secondary icon-btn" onclick="pomakniZa(5)" title="{PT['fwd5_title']}">⏩ +5s</button>
        {cc_dugme}
        <button onclick="oznaciPocetak()" title="{PT['set_start_title']}">{PT['set_start_text']}</button>
        <button onclick="oznaciKraj()" title="{PT['set_end_title']}">{PT['set_end_text']}</button>
      </div>

      <div class="shorts-panel">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <span style="color:{TEXT}; font-size:12px; font-weight:bold;">{PT['current_selection']}</span>
          <label>{PT['od_label']}</label>
          <input type="text" id="input-od" placeholder="00:00:00">
          <label>{PT['do_label']}</label>
          <input type="text" id="input-do" placeholder="00:00:00">
        </div>
        <div>
          <button class="btn-dodaj-odabir" onclick="dodajUListu()">{PT['add_selection']}</button>
        </div>
      </div>

      <div id="multi-panel">
        <div id="lista-selekcija"></div>
        <button class="btn-download-short" id="btn-skini-vise" onclick="skiniViseIsjecaka()">{PT['download_all_clips']}</button>
      </div>

      <div id="status-bar">{PT['loading_player']}</div>
    </div>
    {head_script}
    <script>
      var player;
      var trajanjeVid = 0;
      var playhead = document.getElementById('timeline-playhead');
      var selectionBox = document.getElementById('timeline-selection');
      var pocSec = null, krajSec = null;
      var seekTimeout = null;
      var spreman = false;
      var ccUkljucen = false;
      var muted = false;
      var fallbackPokrenut = false;

      function formatiraj(t) {{
        // HH:MM:SS - uvijek prikazuje sat/minutu/sekundu (npr. "00:03:45"),
        // ne samo minute:sekunde, da bude jasno i za dulje videe.
        if (isNaN(t)) return "00:00:00";
        t = Math.max(0, Math.floor(t));
        var h = Math.floor(t / 3600);
        var m = Math.floor((t % 3600) / 60);
        var s = t % 60;
        var dvocifreno = function(n) {{ return (n < 10 ? "0" : "") + n; }};
        return dvocifreno(h) + ":" + dvocifreno(m) + ":" + dvocifreno(s);
      }}
{init_script}
      function azurirajPlayhead() {{
        if (!spreman || !trajanjeVid) return;
        var t = player.getCurrentTime();
        playhead.style.left = (t / trajanjeVid) * 100 + '%';
        document.getElementById('vrijeme-trenutno').innerText = formatiraj(t);
        var stanje = player.getPlayerState();
        document.getElementById('btn-play').innerText = (stanje === 1) ? '{PT["pause_text"]}' : '{PT["play_text"]}';
      }}

      // ---- klik za premotavanje ILI povlacenje (drag) da izravno oznacis
      // isjecak na traci - stil kao u referentnom editoru (NVIDIA ShadowPlay).
      // Klik (bez pomicanja) na praznu traku = premotaj. Povlacenje po praznoj
      // traci = napravi novu selekciju. Povlacenje LIJEVOG/DESNOG hvatista
      // postojece selekcije = pomjeri POCETAK ili KRAJ. Povlacenje SREDINE
      // postojece selekcije = pomjeri CIJELI isjecak (zadrzavajuci trajanje). ----
      var dragTooltip = document.getElementById('drag-tooltip');
      var timelineEl = document.getElementById('timeline-container');
      var handleLijevo = document.getElementById('handle-left');
      var handleDesno = document.getElementById('handle-right');
      var dragPocetnaX = null, dragJePravaSelekcija = false;

      function pozicijaUSekundama(clientX) {{
        var rect = timelineEl.getBoundingClientRect();
        var udio = (clientX - rect.left) / rect.width;
        udio = Math.min(Math.max(udio, 0), 1);
        return udio * trajanjeVid;
      }}

      function prikaziTooltip(sekOd, sekDo) {{
        if (!trajanjeVid) return;
        var sredina = ((sekOd + sekDo) / 2 / trajanjeVid) * 100;
        dragTooltip.style.left = sredina + '%';
        dragTooltip.innerText = formatiraj(Math.min(sekOd, sekDo)) + ' → ' + formatiraj(Math.max(sekOd, sekDo));
        dragTooltip.style.display = 'block';
      }}

      function primijeniOdDo(od, doo) {{
        pocSec = od; krajSec = doo;
        document.getElementById('input-od').value = formatiraj(pocSec);
        document.getElementById('input-do').value = formatiraj(krajSec);
        window.pywebview.api.oznaci_pocetak(pocSec);
        window.pywebview.api.oznaci_kraj(krajSec);
        azurirajRaspon();
      }}

      function zapocniPomjeranjeRuba(e, rubKojiSePomjera) {{
        e.stopPropagation();
        function naPomicanje(ev) {{
          var nova = pozicijaUSekundama(ev.clientX);
          var od = (rubKojiSePomjera === 'od') ? Math.min(nova, krajSec - 0.1) : pocSec;
          var doo = (rubKojiSePomjera === 'do') ? Math.max(nova, pocSec + 0.1) : krajSec;
          selectionBox.style.left = (od / trajanjeVid * 100) + '%';
          selectionBox.style.width = ((doo - od) / trajanjeVid * 100) + '%';
          prikaziTooltip(od, doo);
        }}
        function naOtpustanje(ev) {{
          document.removeEventListener('mousemove', naPomicanje);
          document.removeEventListener('mouseup', naOtpustanje);
          dragTooltip.style.display = 'none';
          var nova = pozicijaUSekundama(ev.clientX);
          var od = (rubKojiSePomjera === 'od') ? Math.min(nova, krajSec - 0.1) : pocSec;
          var doo = (rubKojiSePomjera === 'do') ? Math.max(nova, pocSec + 0.1) : krajSec;
          primijeniOdDo(od, doo);
        }}
        document.addEventListener('mousemove', naPomicanje);
        document.addEventListener('mouseup', naOtpustanje);
      }}

      function zapocniPomjeranjeCijele(e) {{
        e.stopPropagation();
        var trajanjeIsjecka = krajSec - pocSec;
        var pocetniX = e.clientX;
        var pocetniOd = pocSec;
        function naPomicanje(ev) {{
          var pomakSek = pozicijaUSekundama(ev.clientX) - pozicijaUSekundama(pocetniX);
          var od = Math.min(Math.max(pocetniOd + pomakSek, 0), trajanjeVid - trajanjeIsjecka);
          var doo = od + trajanjeIsjecka;
          selectionBox.style.left = (od / trajanjeVid * 100) + '%';
          selectionBox.style.width = ((doo - od) / trajanjeVid * 100) + '%';
          prikaziTooltip(od, doo);
        }}
        function naOtpustanje(ev) {{
          document.removeEventListener('mousemove', naPomicanje);
          document.removeEventListener('mouseup', naOtpustanje);
          dragTooltip.style.display = 'none';
          var pomakSek = pozicijaUSekundama(ev.clientX) - pozicijaUSekundama(pocetniX);
          var od = Math.min(Math.max(pocetniOd + pomakSek, 0), trajanjeVid - trajanjeIsjecka);
          primijeniOdDo(od, od + trajanjeIsjecka);
        }}
        document.addEventListener('mousemove', naPomicanje);
        document.addEventListener('mouseup', naOtpustanje);
      }}

      handleLijevo.addEventListener('mousedown', function(e) {{ zapocniPomjeranjeRuba(e, 'od'); }});
      handleDesno.addEventListener('mousedown', function(e) {{ zapocniPomjeranjeRuba(e, 'do'); }});
      selectionBox.addEventListener('mousedown', function(e) {{
        if (pocSec === null || krajSec === null) return;
        zapocniPomjeranjeCijele(e);
      }});

      timelineEl.addEventListener('mousedown', function(e) {{
        if (!spreman || !trajanjeVid) {{
          document.getElementById('status-bar').innerText = '{PT["still_loading"]}';
          return;
        }}
        dragPocetnaX = e.clientX;
        dragJePravaSelekcija = false;

        function naPomicanje(ev) {{
          if (Math.abs(ev.clientX - dragPocetnaX) < 6) return;  // ne racunaj sitne pomake kao drag
          dragJePravaSelekcija = true;
          var sekPocetak = pozicijaUSekundama(dragPocetnaX);
          var sekTrenutno = pozicijaUSekundama(ev.clientX);
          var od = Math.min(sekPocetak, sekTrenutno), doo = Math.max(sekPocetak, sekTrenutno);
          selectionBox.style.left = (od / trajanjeVid * 100) + '%';
          selectionBox.style.width = ((doo - od) / trajanjeVid * 100) + '%';
          selectionBox.style.display = 'block';
          prikaziTooltip(od, doo);
        }}

        function naOtpustanje(ev) {{
          document.removeEventListener('mousemove', naPomicanje);
          document.removeEventListener('mouseup', naOtpustanje);
          dragTooltip.style.display = 'none';

          if (!dragJePravaSelekcija) {{
            // obican klik (bez povlacenja) - samo premotaj, kao prije
            var novaPozicija = pozicijaUSekundama(ev.clientX);
            playhead.style.left = (novaPozicija / trajanjeVid * 100) + '%';
            document.getElementById('vrijeme-trenutno').innerText = formatiraj(novaPozicija);
            if (seekTimeout) clearTimeout(seekTimeout);
            seekTimeout = setTimeout(function() {{ player.seekTo(novaPozicija, true); }}, 120);
            return;
          }}

          // stvarno povlacenje po PRAZNOJ traci - napravi novu selekciju
          // (povlacenje hvatista/sredine postojece selekcije se hvata gore,
          // prije nego stigne ovamo - e.stopPropagation() to sprijeci)
          var sekPocetak = pozicijaUSekundama(dragPocetnaX);
          var sekKraj = pozicijaUSekundama(ev.clientX);
          primijeniOdDo(Math.min(sekPocetak, sekKraj), Math.max(sekPocetak, sekKraj));
        }}

        document.addEventListener('mousemove', naPomicanje);
        document.addEventListener('mouseup', naOtpustanje);
      }});

      function pomakniZa(s) {{
        if (!spreman) return;
        player.seekTo(Math.max(0, player.getCurrentTime() + s), true);
      }}

      function togglePlay() {{
        if (!spreman) return;
        var stanje = player.getPlayerState();
        if (stanje === 1) player.pauseVideo(); else player.playVideo();
      }}

      function toggleMute() {{
        if (!spreman) return;
        muted = !muted;
        var btnMute = document.getElementById('btn-mute');
        var slider = document.getElementById('volume-slider');
        if (muted) {{
          player.mute();
          btnMute.innerText = '🔇';
        }} else {{
          player.unMute();
          btnMute.innerText = '🔊';
          if (parseInt(slider.value) === 0) {{ slider.value = 50; player.setVolume(50); }}
        }}
      }}

      function promijeniGlasnocu(v) {{
        if (!spreman) return;
        player.setVolume(v);
        var btnMute = document.getElementById('btn-mute');
        if (parseInt(v) === 0) {{
          muted = true;
          btnMute.innerText = '🔇';
        }} else {{
          if (muted) {{ player.unMute(); }}
          muted = false;
          btnMute.innerText = '🔊';
        }}
      }}

      function oznaciPocetak() {{
        if (!spreman) return;
        pocSec = player.getCurrentTime();
        var tFmt = formatiraj(pocSec);
        document.getElementById('input-od').value = tFmt;
        window.pywebview.api.oznaci_pocetak(pocSec);
        azurirajRaspon();
      }}

      function oznaciKraj() {{
        if (!spreman) return;
        krajSec = player.getCurrentTime();
        var tFmt = formatiraj(krajSec);
        document.getElementById('input-do').value = tFmt;
        window.pywebview.api.oznaci_kraj(krajSec);
        azurirajRaspon();
      }}

      function azurirajRaspon() {{
        if (pocSec !== null && krajSec !== null && trajanjeVid) {{
          selectionBox.style.left = (pocSec / trajanjeVid) * 100 + '%';
          selectionBox.style.width = ((krajSec - pocSec) / trajanjeVid) * 100 + '%';
          selectionBox.style.display = 'block';
          document.getElementById('trajanje-isjecka-info').innerText =
            "{PT['isjecak_prefix']}: " + formatiraj(pocSec) + " → " + formatiraj(krajSec) +
            "  (" + formatiraj(krajSec - pocSec) + ")";
        }}
      }}

      // ---- lista više isječaka odjednom ----
      var brojacSelekcija = 0;

      function dodajUListu() {{
        var odVal = document.getElementById('input-od').value;
        var doVal = document.getElementById('input-do').value;
        if (!odVal || !doVal) {{
          document.getElementById('status-bar').innerText = '{PT["add_selection_warn"]}';
          return;
        }}
        brojacSelekcija += 1;
        var id = brojacSelekcija;
        var red = document.createElement('div');
        red.className = 'selekcija-red';
        red.id = 'sel-' + id;
        red.innerHTML =
          '<span class="selekcija-broj"></span>' +
          '<div class="selekcija-polja">' +
            '<div class="selekcija-polje"><label>{PT["od_label_short"]}</label><input type="text" class="sel-od" value="' + odVal + '"></div>' +
            '<div class="selekcija-polje"><label>{PT["do_label_short"]}</label><input type="text" class="sel-do" value="' + doVal + '"></div>' +
          '</div>' +
          '<button class="secondary icon-btn sel-obrisi" onclick="obrisiSelekciju(' + id + ')" title="{PT["remove_clip_title"]}">🗑</button>';
        document.getElementById('lista-selekcija').appendChild(red);
        red.querySelector('.sel-od').addEventListener('input', azurirajTimelineSelekcije);
        red.querySelector('.sel-do').addEventListener('input', azurirajTimelineSelekcije);
        red.querySelector('.sel-od').addEventListener('focus', function() {{ oznaciAktivnuSelekciju(id); }});
        red.querySelector('.sel-do').addEventListener('focus', function() {{ oznaciAktivnuSelekciju(id); }});
        oznaciAktivnuSelekciju(id);

        // ocisti "trenutni odabir" polja da je spremno za sljedece oznacavanje
        document.getElementById('input-od').value = '';
        document.getElementById('input-do').value = '';
        pocSec = null; krajSec = null;
        selectionBox.style.display = 'none';
        document.getElementById('trajanje-isjecka-info').innerText = '{PT["isjecak_prefix"]}: {PT["nije_oznaceno"]}';

        azurirajListu();
      }}

      function obrisiSelekciju(id) {{
        var el = document.getElementById('sel-' + id);
        if (el) el.remove();
        azurirajListu();
      }}

      function oznaciAktivnuSelekciju(id) {{
        document.querySelectorAll('.selekcija-red').forEach(function(red) {{
          red.classList.toggle('aktivna', red.id === 'sel-' + id);
        }});
      }}

      function azurirajListu() {{
        var redovi = document.querySelectorAll('.selekcija-red');
        redovi.forEach(function(red, i) {{
          red.querySelector('.selekcija-broj').innerText = (i + 1) + '.';
        }});
        var btn = document.getElementById('btn-skini-vise');
        if (redovi.length > 0) {{
          btn.style.display = 'block';
          btn.innerText = '{PT["download_all_clips"]} (' + redovi.length + ')';
        }} else {{
          btn.style.display = 'none';
        }}
        azurirajTimelineSelekcije();
      }}

      function azurirajTimelineSelekcije() {{
        document.querySelectorAll('.timeline-multi-blok').forEach(function(e) {{ e.remove(); }});
        if (!trajanjeVid) return;
        document.querySelectorAll('.selekcija-red').forEach(function(red) {{
          var od = parseVrijemeJS(red.querySelector('.sel-od').value);
          var doo = parseVrijemeJS(red.querySelector('.sel-do').value);
          if (od === null || doo === null || doo <= od) return;
          var blok = document.createElement('div');
          blok.className = 'timeline-multi-blok';
          blok.style.left = (od / trajanjeVid * 100) + '%';
          blok.style.width = ((doo - od) / trajanjeVid * 100) + '%';
          document.getElementById('timeline-container').appendChild(blok);
        }});
      }}

      function parseVrijemeJS(tekst) {{
        tekst = (tekst || '').trim();
        if (!tekst) return null;
        if (tekst.indexOf(':') >= 0) {{
          var dijelovi = tekst.split(':').map(Number);
          if (dijelovi.some(isNaN)) return null;
          var sek = 0;
          dijelovi.forEach(function(d) {{ sek = sek * 60 + d; }});
          return sek;
        }}
        var v = parseFloat(tekst);
        return isNaN(v) ? null : v;
      }}

      function skiniViseIsjecaka() {{
        var lista = [];
        document.querySelectorAll('.selekcija-red').forEach(function(red) {{
          var od = red.querySelector('.sel-od').value;
          var doo = red.querySelector('.sel-do').value;
          if (od && doo) lista.push([od, doo]);
        }});
        if (lista.length === 0) {{
          document.getElementById('status-bar').innerText = '{PT["add_clip_warn"]}';
          return;
        }}
        window.pywebview.api.skini_visestruke_isjecke(lista);
        document.getElementById('status-bar').innerText =
          '{PT["download_started"]}'.replace('{{0}}', lista.length);
      }}
    </script>
    </body>
    </html>
    """


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler prosiren podrskom za HTTP Range zahtjeve.
    Standardni SimpleHTTPRequestHandler NE podrzava Range, pa <video> tag ne moze
    premotavati (seek) - motor ne zna kako dohvatiti proizvoljni dio fajla, pa
    dopusta samo puštanje od pocetka do kraja bez skakanja po traci."""
    protocol_version = "HTTP/1.1"

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        file_len = os.fstat(f.fileno()).st_size
        ctype = self.guess_type(path)
        range_header = self.headers.get("Range")

        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                start_s, end_s = m.groups()
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else file_len - 1
                end = min(end, file_len - 1)
                if start > end or start >= file_len:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_len}")
                    self.end_headers()
                    f.close()
                    return None
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_len}")
                self.send_header("Content-Length", str(length))
                self.end_headers()
                f.seek(start)
                self._raspon_duljina = length
                return f

        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(file_len))
        self.end_headers()
        self._raspon_duljina = None
        return f

    def copyfile(self, source, outputfile):
        duljina = getattr(self, "_raspon_duljina", None)
        if duljina is None:
            return super().copyfile(source, outputfile)
        preostalo = duljina
        while preostalo > 0:
            komad = source.read(min(65536, preostalo))
            if not komad:
                break
            try:
                outputfile.write(komad)
            except (BrokenPipeError, ConnectionAbortedError):
                break
            preostalo -= len(komad)


def pokreni_lokalni_server(temp_dir):
    """Pokrece mali HTTP server na 127.0.0.1 - potreban da YouTube iframe API radi ispravno
    (embed s file:// ili html= porijeklom cesto ne radi zbog YouTubeovih origin provjera),
    i da lokalno servirani preview video (TikTok/ostalo) moze podrzavati premotavanje
    (Range zahtjevi) - vidi RangeRequestHandler."""
    handler = functools.partial(RangeRequestHandler, directory=temp_dir)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return port


def pokreni_webview_proces(preview_url, queue_sanjac):
    api = PlayerAPI(queue_sanjac)
    webview.create_window("Mister Muscle — Timeline Player", url=preview_url, js_api=api, width=1180, height=760)
    webview.start()



class App:
    def __init__(self, root):
        self.root = root
        self.cfg = ucitaj_config()
        self.jezik = self.cfg.get("jezik", "en")
        if self.jezik not in PRIJEVODI:
            self.jezik = "en"

        root.title(self.t("naslov_prozora"))
        # Ikona prozora (naslovna traka, taskbar dok app radi) - ista ikona kao
        # .exe fajl u Exploreru. Ako 'ikona.ico' iz nekog razloga ne postoji
        # (npr. .exe je izgradjen bez nje), ovo se tiho preskace - app i dalje
        # normalno radi, samo s Tkinterovom zadanom ikonom.
        try:
            _ip = _ikona_putanja()
            if _ip:
                root.iconbitmap(_ip)
        except Exception:
            pass
        # Prisilno postavi "normal" (ne-maksimizirano) stanje prije nego sto
        # uopce postavimo geometriju - da smo sto sigurniji da prozor NIJE
        # zaglavljen u zoomed/maksimiziranom stanju iz bilo kojeg razloga.
        try:
            root.state("normal")
        except Exception:
            pass
        root.geometry(self.cfg.get("prozor", "1240x820"))
        # Sigurnosna mreza za poznat problem - ako je app ZADNJI
        # PUT zatvorena dok je bila maksimizirana (ili je spremljena velicina s
        # NEKOG DRUGOG, veceg monitora), geometry() moze vratiti/postaviti
        # velicinu koja pokriva (skoro) citav trenutni ekran - pa prozor bude
        # ogroman iako tehnicki NIJE maksimiziran, i "Restore" gumb nista ne
        # mijenja jer je spremljena velicina VEC = ekran. Koristimo i
        # winfo_vrootwidth/height (pokriva slucaj vise monitora) uz obicni
        # winfo_screenwidth/height, sto god od to dvoje je veci broj.
        root.update_idletasks()
        try:
            ekran_sirina = max(root.winfo_screenwidth(), root.winfo_vrootwidth())
            ekran_visina = max(root.winfo_screenheight(), root.winfo_vrootheight())
            if (root.winfo_width() >= ekran_sirina * 0.95
                    or root.winfo_height() >= ekran_visina * 0.90):
                root.geometry("1240x820")
                root.update_idletasks()
        except Exception:
            pass
        # v17.0.5: dosta manji minsize - prozor sad smije biti i malen/uzak
        # (npr. kao suzena Discord kartica), ne samo veliki "desktop" raspored.
        # Stvarna prilagodba rasporeda (lijevo+desno jedno pored drugog naspram
        # jedno ispod drugog) radi se u _na_promjenu_velicine_prozora().
        root.minsize(360, 480)
        root.resizable(True, True)
        root.configure(bg=BG)
        self._centriraj_prozor()

        # ---- stanje ----
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.aktivno_preuzimanje = False
        self.otkazano = False
        self.aktivni_proces = None
        self.player_proces = None          # fallback: zaseban prozor (bez ugradnje)
        self._webview_window = None        # ugradjeni player (Windows + pywin32)
        self._webview_hwnd = None
        self._webview_spreman = threading.Event()
        self._blink_token = 0
        self.queue_sanjac = multiprocessing.Queue()
        self.trenutni_folder = self.cfg["izlazni_folder"]
        self.temp_dir = tempfile.mkdtemp(prefix="mister_muscle_")
        self.http_port = pokreni_lokalni_server(self.temp_dir) if PYWEBVIEW_DOSTUPAN else None
        self.od_sek = None
        self.do_sek = None
        self._auto_ucitaj_after_id = None      # zakazani (debounced) poziv auto-ucitavanja playera
        self._zadnji_auto_ucitani_link = None  # da se isti link ne ucitava iznova u krug

        self.var_nacin = tk.StringVar(value=self.cfg["nacin"])
        self.var_kvaliteta = tk.StringVar(value=self.cfg["kvaliteta"])
        self.var_video_format = tk.StringVar(value=self.cfg.get("video_format", "mp4"))
        self.var_audio_format = tk.StringVar(value=self.cfg["audio_format"])
        self.var_h264 = tk.BooleanVar(value=bool(self.cfg["h264"]))
        self.var_metapodaci = tk.BooleanVar(value=bool(self.cfg["metapodaci"]))

        self._pripremi_stilove()
        self._izgradi_meni()
        self._izgradi_zaglavlje()
        self._izgradi_glavni_dio()
        self._izgradi_donju_traku()
        self._izgradi_statusnu_traku()

        self.root.protocol("WM_DELETE_WINDOW", self.zatvori)

        self.ispisi(f"💪 {self.t('podnaslov_app')}")
        if not PYWEBVIEW_DOSTUPAN:
            self.ispisi(self.t("msg_need_pywebview"))
        elif not EMBED_PLAYERA_DOSTUPAN:
            self.ispisi(self.t("msg_need_pywin32"))
        elif PYWEBVIEW_DOSTUPAN and EMBED_PLAYERA_DOSTUPAN:
            self.ispisi(self.t("msg_black_player_hint"))
        self._osvjezi_stanje_nacina()
        threading.Thread(target=self._provjera_alata_pri_pokretanju, daemon=True).start()
        if PYWEBVIEW_DOSTUPAN and JE_WINDOWS:
            self.root.after(800, lambda: self._provjeri_webview2_pri_pokretanju(tih=True))
        if PYWEBVIEW_DOSTUPAN and EMBED_PLAYERA_DOSTUPAN:
            self._pripremi_ugradjeni_webview()
        self.root.after(400, self._provjeri_i_prikazi_novosti)
        self.provjeri_queue()

    # ------------------------------------------------------------------ UI ---
    def t(self, kljuc):
        """Vraca prevedeni tekst za trenutno odabrani jezik (self.jezik) - ako
        kljuc nedostaje u odabranom jeziku, tiho pada natrag na hrvatski, a ako
        ni tamo ne postoji, vraca sam kljuc (da UI nikad ne ostane prazan)."""
        return PRIJEVODI.get(self.jezik, {}).get(kljuc) or PRIJEVODI["hr"].get(kljuc, kljuc)

    def _postavi_jezik(self, novi_jezik):
        if novi_jezik == self.jezik:
            return
        self.jezik = novi_jezik
        self.cfg["jezik"] = novi_jezik
        spremi_config(self.cfg)
        messagebox.showinfo(
            "Jezik / Language",
            "Postavka je spremljena. Ponovno pokreni aplikaciju da se promjena primijeni.\n\n"
            "Setting saved. Restart the application for the change to take effect."
        )

    def _centriraj_prozor(self):
        self.root.update_idletasks()
        try:
            s, v = self.root.geometry().split("+")[0].split("x")
            s, v = int(s), int(v)
        except Exception:
            s, v = 1240, 820
        x = max(0, (self.root.winfo_screenwidth() - s) // 2)
        y = max(0, (self.root.winfo_screenheight() - v) // 3)
        self.root.geometry(f"{s}x{v}+{x}+{y}")

    def _pripremi_stilove(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cyber.Horizontal.TProgressbar",
                        troughcolor=TROUGH, background=SUCCESS, bordercolor=TROUGH, thickness=10)
        style.configure("Cyber.TCombobox",
                        fieldbackground=INPUT_BG, background=PAUSE_BG, foreground=TEXT,
                        arrowcolor=TEXT, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        style.map("Cyber.TCombobox",
                  fieldbackground=[("readonly", INPUT_BG)],
                  selectbackground=[("readonly", INPUT_BG)],
                  selectforeground=[("readonly", TEXT)],
                  foreground=[("readonly", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

    def _izgradi_meni(self):
        menubar = tk.Menu(self.root, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT, relief="flat")

        m_alati = tk.Menu(menubar, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
        m_alati.add_command(label=self.t("meni_provjeri_azuriranja"), command=self.provjeri_azuriranja)
        m_alati.add_separator()
        m_alati.add_command(label=self.t("meni_azuriraj_ytdlp"), command=lambda: self.provjeri_azuriranja(samo="yt-dlp"))
        m_alati.add_command(label=self.t("meni_reinstaliraj_ffmpeg"), command=lambda: self.provjeri_azuriranja(samo="ffmpeg"))
        if JE_WINDOWS:
            m_alati.add_command(label=self.t("meni_webview2"), command=self._provjeri_webview2_pri_pokretanju)
        m_alati.add_separator()
        m_alati.add_command(label=self.t("meni_folder_alati"), command=lambda: self._otvori_putanju(_alati_folder()))
        m_alati.add_command(label=self.t("meni_config"), command=lambda: self._otvori_putanju(os.path.dirname(CONFIG_PATH)))
        m_alati.add_separator()
        m_alati.add_command(label=self.t("meni_reset_prozor"), command=self.resetiraj_velicinu_prozora)
        menubar.add_cascade(label=self.t("meni_alati"), menu=m_alati)

        m_jezik = tk.Menu(menubar, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
        self.var_jezik_meni = tk.StringVar(value=self.jezik)
        m_jezik.add_radiobutton(label=self.t("meni_jezik_hr"), value="hr", variable=self.var_jezik_meni,
                                command=lambda: self._postavi_jezik("hr"))
        m_jezik.add_radiobutton(label=self.t("meni_jezik_en"), value="en", variable=self.var_jezik_meni,
                                command=lambda: self._postavi_jezik("en"))
        menubar.add_cascade(label=self.t("meni_jezik"), menu=m_jezik)

        m_pomoc = tk.Menu(menubar, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
        m_pomoc.add_command(label=self.t("meni_o_aplikaciji"), command=self.o_aplikaciji)
        menubar.add_cascade(label=self.t("meni_pomoc"), menu=m_pomoc)

        self.root.config(menu=menubar)

    def _izgradi_zaglavlje(self):
        traka = tk.Frame(self.root, bg=BG)
        traka.pack(fill="x", padx=22, pady=(16, 4))

        lijevo = tk.Frame(traka, bg=BG)
        lijevo.pack(side="left")
        tk.Label(lijevo, text=self.t("naslov_app"), font=(FONT_NASLOV, 20),
                 bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(lijevo, text=self.t("podnaslov_app"),
                 font=("Segoe UI", 9), bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(2, 0))

        self.btn_update = self._napravi_dugme(traka, self.t("gumb_azuriranja"), self.provjeri_azuriranja,
                                              bg=PAUSE_BG, hover=PAUSE_HOVER, font_size=9, padx=14, pady=8)
        self.btn_update.pack(side="right", pady=(6, 0))

    # Ispod ove sirine prozora (u pikselima) lijevi i desni panel idu jedan ispod
    # drugog umjesto jedan pored drugog - da app moze biti i malen/uzak prozor,
    # ne samo puni "desktop" raspored.
    PRAG_UZANOG_RASPOREDA = 900
    SIRINA_LIJEVOG_STUPCA = 460  # koristi se SAMO u sirokom (dvostupcnom) rasporedu

    def _izgradi_glavni_dio(self):
        self.glavni = tk.Frame(self.root, bg=BG)
        self.glavni.pack(fill="both", expand=True, padx=22, pady=(8, 0))

        self.lijevo = tk.Frame(self.glavni, bg=BG)
        self.desno = tk.Frame(self.glavni, bg=BG)

        self._kartica_linkovi(self.lijevo)
        self._kartica_opcije(self.lijevo)
        self._kartica_folder(self.lijevo)
        self._panel_desno(self.desno)

        self._raspored_je_uzak = None  # None = jos nepoznato, postavlja se u nastavku
        self._primijeni_raspored(uzak=False)
        self.root.bind("<Configure>", self._na_promjenu_velicine_prozora)

    def _na_promjenu_velicine_prozora(self, event):
        if event.widget is not self.root:
            return
        uzak = event.width < self.PRAG_UZANOG_RASPOREDA
        if uzak != self._raspored_je_uzak:
            self._primijeni_raspored(uzak)

    def _primijeni_raspored(self, uzak):
        """Prebacuje izmedu 'desktop' rasporeda (lijevo+desno jedno pored drugog)
        i 'kompaktnog' rasporeda za uske prozore (lijevo pa desno jedno ispod
        drugog, oba preko cijele sirine) - slicno kako se npr. Discord prozor
        preslaze kad ga jako suzis."""
        self._raspored_je_uzak = uzak
        self.lijevo.grid_forget()
        self.desno.grid_forget()

        if uzak:
            self.glavni.columnconfigure(0, minsize=0, weight=1)
            self.glavni.columnconfigure(1, weight=0)
            self.glavni.rowconfigure(0, weight=0)
            self.glavni.rowconfigure(1, weight=1, minsize=220)
            self.lijevo.grid(row=0, column=0, sticky="new")
            self.desno.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        else:
            self.glavni.columnconfigure(0, minsize=self.SIRINA_LIJEVOG_STUPCA, weight=0)
            self.glavni.columnconfigure(1, weight=1)
            self.glavni.rowconfigure(0, weight=1)
            self.glavni.rowconfigure(1, weight=0)
            self.lijevo.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
            self.desno.grid(row=0, column=1, sticky="nsew")

    def _naslov_kartice(self, roditelj, broj, tekst):
        red = tk.Frame(roditelj, bg=BG)
        red.pack(fill="x", pady=(0, 6))
        tk.Label(red, text=f"{broj}", font=("Segoe UI", 9, "bold"), bg=ACCENT, fg="white",
                 width=3, pady=2).pack(side="left")
        tk.Label(red, text=f"  {tekst}", font=("Segoe UI", 9, "bold"), bg=BG, fg=SUBTEXT).pack(side="left")
        return red

    def _kartica_linkovi(self, roditelj):
        self._naslov_kartice(roditelj, "1", self.t("kartica_1"))
        card = tk.Frame(roditelj, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 14))
        staklena_linija(card, posvijetli(CARD, 0.22)).pack(fill="x", side="top")

        self.text_links = tk.Text(card, height=5, font=("Segoe UI", 10), bg=INPUT_BG, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", highlightbackground=BORDER,
                                  highlightthickness=1, wrap="word")
        self.text_links.pack(padx=14, pady=(14, 8), fill="x")
        self._placeholder = self.t("placeholder_linkovi")
        self._postavi_placeholder()
        self.text_links.edit_modified(False)  # placeholder ne smije brojati kao "promjena"
        self.text_links.bind("<FocusIn>", self._obrisi_placeholder)
        self.text_links.bind("<FocusOut>", self._vrati_placeholder)
        # <<Modified>> se okine na SVAKU promjenu sadrzaja (tipkanje, paste preko
        # Ctrl+V, paste preko desnog klika/"Zalijepi" gumba - sve to na kraju ide
        # kroz insert/delete na ovom Text widgetu) - to koristimo da AUTOMATSKI
        # otvorimo/osvjezimo player cim prepoznamo valjan link, bez klika na gumb.
        self.text_links.bind("<<Modified>>", self._na_promjenu_linkova)

        self.context_menu = tk.Menu(self.root, tearoff=0, bg=CARD, fg=TEXT,
                                    activebackground=ACCENT, activeforeground=TEXT)
        self.context_menu.add_command(label=self.t("gumb_zalijepi"), command=self.zalijepi_tekst)
        self.text_links.bind("<Button-3>", self.prikazi_desni_klik)

        red = tk.Frame(card, bg=CARD)
        red.pack(fill="x", padx=14, pady=(0, 12))
        self.btn_player = self._napravi_dugme(red, self.t("gumb_pregledaj"), self.otvori_player,
                                              bg=PAUSE_BG, hover=PAUSE_HOVER, font_size=9, padx=12, pady=6)
        self.btn_player.pack(side="left")
        self._napravi_dugme(red, self.t("gumb_zalijepi"), self.zalijepi_tekst, bg=PAUSE_BG, hover=PAUSE_HOVER,
                            font_size=9, padx=12, pady=6).pack(side="left", padx=(8, 0))
        self._napravi_dugme(red, self.t("gumb_ocisti"), self.ocisti_linkove, bg=PAUSE_BG, hover=PAUSE_HOVER,
                            font_size=9, padx=12, pady=6).pack(side="left", padx=(8, 0))

        self.isjecak_frame = tk.Frame(card, bg=CARD_LIGHT)
        self.lbl_isjecak = tk.Label(self.isjecak_frame, text="", font=("Segoe UI", 9, "bold"),
                                    bg=CARD_LIGHT, fg=SUCCESS, anchor="w")
        self.lbl_isjecak.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        self.btn_ocisti_isjecak = tk.Button(self.isjecak_frame, text=self.t("gumb_ponisti_isjecak"), font=("Segoe UI", 8, "bold"),
                                            bg=CARD_LIGHT, fg=SUBTEXT, activebackground=CARD_LIGHT,
                                            activeforeground=TEXT, relief="flat", bd=0, cursor="hand2",
                                            command=self.ponisti_isjecak)
        self.btn_ocisti_isjecak.pack(side="right", padx=(0, 10))

    def _kartica_opcije(self, roditelj):
        self._naslov_kartice(roditelj, "2", self.t("kartica_2"))
        card = tk.Frame(roditelj, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 14))
        staklena_linija(card, posvijetli(CARD, 0.22)).pack(fill="x", side="top")

        nacini = [
            ("video_zvuk", self.t("nacin_video_zvuk")),
            ("samo_video", self.t("nacin_samo_video")),
            ("samo_zvuk", self.t("nacin_samo_zvuk")),
        ]
        for vrijednost, naslov in nacini:
            red = tk.Frame(card, bg=CARD)
            red.pack(fill="x", padx=14, pady=(10 if vrijednost == "video_zvuk" else 2, 2))
            tk.Radiobutton(red, text=naslov, value=vrijednost, variable=self.var_nacin,
                           command=self._osvjezi_stanje_nacina, font=("Segoe UI", 10, "bold"),
                           bg=CARD, fg=TEXT, activebackground=CARD, activeforeground=TEXT,
                           selectcolor=INPUT_BG, highlightthickness=0, bd=0,
                           cursor="hand2", anchor="w").pack(side="left")

        razdjelnik = tk.Frame(card, bg=BORDER, height=1)
        razdjelnik.pack(fill="x", padx=14, pady=(12, 12))

        red_kv = tk.Frame(card, bg=CARD)
        red_kv.pack(fill="x", padx=14, pady=(0, 14))

        tk.Label(red_kv, text=self.t("oznaka_kvaliteta"), font=("Segoe UI", 8, "bold"), bg=CARD, fg=SUBTEXT).grid(
            row=0, column=0, sticky="w", pady=(0, 3))
        self.cb_kvaliteta = ttk.Combobox(red_kv, values=KVALITETE, textvariable=self.var_kvaliteta,
                                         state="readonly", style="Cyber.TCombobox", width=16)
        self.cb_kvaliteta.grid(row=1, column=0, sticky="w")

        tk.Label(red_kv, text=self.t("oznaka_format_videa"), font=("Segoe UI", 8, "bold"), bg=CARD, fg=SUBTEXT).grid(
            row=0, column=1, sticky="w", padx=(18, 0), pady=(0, 3))
        self.cb_video_format = ttk.Combobox(red_kv, values=VIDEO_FORMATI, textvariable=self.var_video_format,
                                            state="readonly", style="Cyber.TCombobox", width=18)
        self.cb_video_format.grid(row=1, column=1, sticky="w", padx=(18, 0))

        tk.Label(red_kv, text=self.t("oznaka_format_zvuka"), font=("Segoe UI", 8, "bold"), bg=CARD, fg=SUBTEXT).grid(
            row=0, column=2, sticky="w", padx=(18, 0), pady=(0, 3))
        self.cb_audio = ttk.Combobox(red_kv, values=AUDIO_FORMATI, textvariable=self.var_audio_format,
                                     state="readonly", style="Cyber.TCombobox", width=20)
        self.cb_audio.grid(row=1, column=2, sticky="w", padx=(18, 0))

        tk.Frame(card, bg=CARD).pack(pady=4)

    def _kartica_folder(self, roditelj):
        self._naslov_kartice(roditelj, "3", self.t("kartica_3"))
        card = tk.Frame(roditelj, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x")
        staklena_linija(card, posvijetli(CARD, 0.22)).pack(fill="x", side="top")

        red = tk.Frame(card, bg=CARD)
        red.pack(fill="x", padx=14, pady=14)
        self.lbl_folder = tk.Label(red, text=self.trenutni_folder, font=("Segoe UI", 8), bg=INPUT_BG,
                                   fg=TEXT, anchor="w", padx=8, highlightbackground=BORDER, highlightthickness=1)
        self.lbl_folder.pack(side="left", fill="x", expand=True, ipady=6)
        self._napravi_dugme(red, self.t("gumb_odaberi_folder"), self.odaberi_folder, bg=PAUSE_BG, hover=PAUSE_HOVER,
                            font_size=8, padx=10, pady=6).pack(side="left", padx=(8, 0))
        self._napravi_dugme(red, self.t("gumb_otvori_folder"), self.otvori_output_folder, bg=PAUSE_BG, hover=PAUSE_HOVER,
                            font_size=8, padx=10, pady=6).pack(side="left", padx=(8, 0))

    def _panel_desno(self, roditelj):
        """Desna kolona: JEDAN panel koji dijeli isto mjesto između playera za
        označavanje isječka (UGRAĐEN, bez zasebnog OS prozora koji iskače) i
        STATUS logova - klikom na zaglavlje se sadržaj otvara/zatvara, a
        svjetlo u zaglavlju pokazuje stanje (sivo = mirno, plavo = skidanje u
        tijeku, crveno = greška, zeleno treperi 5s = uspješno skinuto)."""
        roditelj.rowconfigure(0, weight=1)
        roditelj.columnconfigure(0, weight=1)

        self.desni_panel = tk.Frame(roditelj, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.desni_panel.grid(row=0, column=0, sticky="nsew")
        staklena_linija(self.desni_panel, posvijetli(CARD, 0.22)).pack(fill="x", side="top")

        # ---- zaglavlje (klikni za otvori/zatvori sadržaj ispod) ----
        self._status_expanded = True
        self._desni_mod = "log"  # "log" ili "player" - koji sadrzaj trenutno dijeli mjesto ispod
        zaglavlje = tk.Frame(self.desni_panel, bg=CARD, cursor="hand2")
        zaglavlje.pack(fill="x", side="top")

        self.status_svjetlo = tk.Canvas(zaglavlje, width=14, height=14, bg=CARD, highlightthickness=0, cursor="hand2")
        self._svjetlo_id = self.status_svjetlo.create_oval(2, 2, 13, 13, fill=SUBTEXT, outline="")
        self.status_svjetlo.pack(side="left", padx=(12, 8), pady=9)

        self.lbl_status_naslov = tk.Label(zaglavlje, text=self.t("status_naslov"), font=("Segoe UI", 9, "bold"),
                                          bg=CARD, fg=SUBTEXT, cursor="hand2")
        self.lbl_status_naslov.pack(side="left", pady=9)

        self.lbl_status_strelica = tk.Label(zaglavlje, text=self.t("status_sakrij"), font=("Segoe UI", 8),
                                            bg=CARD, fg=SUBTEXT, cursor="hand2")
        self.lbl_status_strelica.pack(side="right", padx=12, pady=9)

        tk.Button(zaglavlje, text=self.t("gumb_ocisti_log"), font=("Segoe UI", 8), bg=CARD, fg=SUBTEXT,
                  activebackground=CARD, activeforeground=TEXT, relief="flat", bd=0, cursor="hand2",
                  command=self.ocisti_log).pack(side="right", padx=(0, 4), pady=9)

        for widget in (zaglavlje, self.status_svjetlo, self.lbl_status_naslov, self.lbl_status_strelica):
            widget.bind("<Button-1>", self._toggle_status)

        staklena_linija(self.desni_panel, posvijetli(CARD, 0.14)).pack(fill="x", side="top")

        # ---- sadržaj: dijeljeno mjesto - ILI player ILI STATUS log, nikad oboje ----
        self.desni_sadrzaj = tk.Frame(self.desni_panel, bg=CARD)
        self.desni_sadrzaj.pack(fill="both", expand=True, side="top")

        # -- player: placeholder dok se ne otvori, pa ugrađeni prozor preko njega --
        self.player_placeholder = tk.Label(
            self.desni_sadrzaj,
            text=self.t("player_placeholder"),
            font=("Segoe UI", 10), bg=CARD, fg=SUBTEXT, justify="center"
        )
        self.player_embed_frame = tk.Frame(self.desni_sadrzaj, bg="black")
        # namjerno se NE prikazuje odmah - postavlja se tek kad se player stvarno otvori
        self.player_embed_frame.bind("<Configure>", lambda e: self._namjesti_velicinu_playera())

        # -- STATUS log + napredak --
        self.status_body = tk.Frame(self.desni_sadrzaj, bg=BG)

        okvir = tk.Frame(self.status_body, bg=LOG_BG, highlightbackground=BORDER, highlightthickness=1)
        okvir.pack(fill="both", expand=True, pady=(8, 0))
        self.log = scrolledtext.ScrolledText(okvir, height=10, font=("Consolas", 9), state="disabled",
                                             bg=LOG_BG, fg=LOG_TEXT, relief="flat", highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        napredak = tk.Frame(self.status_body, bg=BG)
        napredak.pack(fill="x", pady=(10, 0))
        self.progress = ttk.Progressbar(napredak, style="Cyber.Horizontal.TProgressbar",
                                        orient="horizontal", mode="determinate", maximum=100, value=0)
        self.progress.pack(fill="x")

        red = tk.Frame(self.status_body, bg=BG)
        red.pack(fill="x", pady=(4, 0))
        self.lbl_brzina = tk.Label(red, text="", font=("Segoe UI", 8), bg=BG, fg=SUBTEXT)
        self.lbl_brzina.pack(side="left")
        self.lbl_postotak = tk.Label(red, text="0%", font=("Segoe UI", 9, "bold"), bg=BG, fg=SUCCESS)
        self.lbl_postotak.pack(side="right")

        self._prikazi_sadrzaj("log")

    def _toggle_status(self, event=None):
        self._status_expanded = not self._status_expanded
        if self._status_expanded:
            self.desni_sadrzaj.pack(fill="both", expand=True, side="top")
            self.lbl_status_strelica.config(text=self.t("status_sakrij"))
        else:
            self.desni_sadrzaj.pack_forget()
            self.lbl_status_strelica.config(text=self.t("status_prikazi"))

    def _prikazi_sadrzaj(self, mod):
        """Prebacuje ono sto je prikazano u zajednickom prostoru (self.desni_sadrzaj)
        izmedju playera za oznacavanje isjecka i STATUS logova - oboje dijele
        isto mjesto (umjesto zasebnih okvira kao ranije), nikad se ne prikazuju
        istovremeno. 'mod' je 'player' ili 'log'. Ako je panel trenutno skupljen,
        automatski se otvara da se novi sadrzaj stvarno i vidi."""
        self._desni_mod = mod
        self.player_placeholder.place_forget()
        self.player_embed_frame.place_forget()
        self.status_body.pack_forget()
        if mod == "player":
            self.lbl_status_naslov.config(text=self.t("player_naslov"))
            if EMBED_PLAYERA_DOSTUPAN:
                self.player_embed_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            else:
                self.player_placeholder.config(text=self.t("player_zaseban_prozor"))
                self.player_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.lbl_status_naslov.config(text=self.t("status_naslov"))
            self.status_body.pack(fill="both", expand=True)
        if not self._status_expanded:
            self._toggle_status()

    # ------------------------------------------------------- status svjetlo ---
    def _status_light(self, boja):
        """Postavlja boju svjetla na STATUS traci i prekida bilo koje treperenje u tijeku."""
        self._blink_token += 1
        try:
            self.status_svjetlo.itemconfig(self._svjetlo_id, fill=boja)
        except Exception:
            pass

    def _status_blink_uspjeh(self, trajanje=6.0, interval_ms=400):
        """Zeleno svjetlo treperi 'trajanje' sekundi kad skidanje uspješno završi."""
        self._blink_token += 1
        moj_token = self._blink_token
        krajnje_vrijeme = time.time() + trajanje

        def _tik(upaljeno=True):
            if moj_token != self._blink_token:
                return  # u međuvremenu je pokrenuto nešto drugo (nova greška/skidanje)
            if time.time() >= krajnje_vrijeme:
                try:
                    self.status_svjetlo.itemconfig(self._svjetlo_id, fill=SUCCESS)
                except Exception:
                    pass
                return
            boja = SUCCESS if upaljeno else CARD
            try:
                self.status_svjetlo.itemconfig(self._svjetlo_id, fill=boja)
            except Exception:
                pass
            self.root.after(interval_ms, lambda: _tik(not upaljeno))

        _tik(True)

    # -------------------------------------------------------- ugradnja playera ---
    def _namjesti_velicinu_playera(self):
        """Kad se 'player_embed_frame' promijeni veličine (npr. korisnik rastegne
        prozor), ugrađeni OS prozor se ručno preslaguje na istu veličinu - Windows
        to ne radi sam za reparentani prozor."""
        if not self._webview_hwnd or not WIN32_DOSTUPAN:
            return
        self.player_embed_frame.update_idletasks()
        sirina = self.player_embed_frame.winfo_width()
        visina = self.player_embed_frame.winfo_height()
        if sirina > 1 and visina > 1:
            try:
                win32gui.MoveWindow(self._webview_hwnd, 0, 0, sirina, visina, True)
            except Exception:
                pass

    def _pripremi_ugradjeni_webview(self):
        """Stvara JEDAN pywebview prozor koji živi cijelo vrijeme rada aplikacije.

        VAŽNO (v17.0.1): 'webview.create_window()' smije se pozvati iz bilo koje
        niti I PRIJE nego se pokrene 'webview.start()' - prozor se tada samo
        registrira, a stvarno se stvara kad GUI petlja krene. Sam 'webview.start()'
        MORA biti pozvan iz glavne niti aplikacije (tvrdo ograničenje biblioteke -
        otud greška "pywebview must be run on a main thread" kad se pozivao iz
        pozadinske niti). Zato se ovdje SAMO registrira prozor i pokreće nit koja
        čeka da se on stvarno pojavi kao OS prozor pa ga ugrađuje (reparenta);
        sam 'webview.start()' zove se na dnu datoteke, u glavnom pokretačkom bloku."""
        try:
            api = PlayerAPI(self.queue_sanjac)
            self._player_api = api
            self._webview_window = webview.create_window(
                WEBVIEW_NASLOV_PROZORA, url="about:blank", js_api=api, width=100, height=100
            )
            threading.Thread(target=self._cekaj_pa_ugradi_webview, daemon=True).start()
        except Exception as err:
            self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_embed_prep_failed").format(em)))

    def _cekaj_pa_ugradi_webview(self):
        hwnd = None
        for _ in range(150):  # do ~15s čekanja da OS stvarno stvori prozor
            hwnd = win32gui.FindWindow(None, WEBVIEW_NASLOV_PROZORA)
            if hwnd:
                break
            time.sleep(0.1)
        if not hwnd:
            self.root.after(0, self.ispisi, self.t("msg_embed_not_found"))
            return
        try:
            parent_hwnd = self.player_embed_frame.winfo_id()
            stil = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            stil = (stil & ~win32con.WS_POPUP & ~win32con.WS_CAPTION & ~win32con.WS_THICKFRAME
                    & ~win32con.WS_SYSMENU & ~win32con.WS_MAXIMIZEBOX & ~win32con.WS_MINIMIZEBOX)
            stil |= win32con.WS_CHILD
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, stil)
            win32gui.SetParent(hwnd, parent_hwnd)
            self._webview_hwnd = hwnd
            self.root.after(0, self._namjesti_velicinu_playera)
            # WebView2 (Edge) crta preko DirectComposition-a i zna "izgubiti"
            # kompoziciju čim se prozor reparenta drugom vlasniku - rezultat je
            # potpuno crn player iako je stranica ispod haube stvarno učitana.
            # SWP_FRAMECHANGED prisiljava Windows da ponovno izračuna stil/okvir,
            # a mali "kick" veličine (smanji pa vrati) prisiljava WebView2 da
            # ponovno izračuna svoj compositing target i stvarno nacrta sadržaj.
            win32gui.SetWindowPos(
                hwnd, None, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
            )
            self.root.after(200, self._forsiraj_repaint_playera)
            self._webview_spreman.set()
        except Exception as err:
            self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_embed_failed").format(em)))

    def _forsiraj_repaint_playera(self):
        """Nakon SetParent-a, WebView2 zna ostati crn dok se veličina prozora
        stvarno ne promijeni. Ovo simulira tu promjenu (smanji pa odmah vrati)
        da natjera WebView2 da ponovno nacrta sadržaj. Bezopasno je pozvati
        više puta - koristi se i nakon svakog promjene veličine glavnog prozora."""
        if not self._webview_hwnd or not WIN32_DOSTUPAN:
            return
        try:
            rect = win32gui.GetWindowRect(self._webview_hwnd)
            sirina = rect[2] - rect[0]
            visina = rect[3] - rect[1]
            if sirina <= 2 or visina <= 2:
                self.root.after(200, self._forsiraj_repaint_playera)
                return
            win32gui.MoveWindow(self._webview_hwnd, 0, 0, sirina - 1, visina, True)
            self.root.after(60, lambda: win32gui.MoveWindow(self._webview_hwnd, 0, 0, sirina, visina, True))
        except Exception:
            pass

    def _izgradi_donju_traku(self):
        traka = tk.Frame(self.root, bg=BG)
        traka.pack(fill="x", padx=22, pady=(14, 6))

        self.btn_download = self._napravi_dugme(traka, self.t("skini_video"), self.pokreni_preuzimanje,
                                                bg=ACCENT, hover=ACCENT_HOVER, font_size=12, height=2)
        self.btn_download.pack(side="left", fill="x", expand=True)

        self.btn_pause = self._napravi_dugme(traka, self.t("gumb_pauziraj"), self.toggle_pauza, bg=PAUSE_BG,
                                             hover=PAUSE_HOVER, font_size=10, height=2, width=12)
        self.btn_pause.pack(side="left", padx=(10, 0))
        self.btn_pause.config(state="disabled")

        self.btn_prekini = self._napravi_dugme(traka, self.t("gumb_prekini"), self.prekini_preuzimanje, bg=PAUSE_BG,
                                               hover=PAUSE_HOVER, font_size=10, height=2, width=12)
        self.btn_prekini.pack(side="left", padx=(10, 0))
        self.btn_prekini.config(state="disabled")

    def _izgradi_statusnu_traku(self):
        traka = tk.Frame(self.root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        traka.pack(fill="x", side="bottom")
        self.lbl_status_alati = tk.Label(traka, text=self.t("provjeravam_alate"), font=("Segoe UI", 8),
                                         bg=CARD, fg=SUBTEXT, anchor="w")
        self.lbl_status_alati.pack(side="left", padx=12, pady=5)

    def _napravi_dugme(self, parent, tekst, komanda, bg, hover, font_size=10, bold=True,
                       height=None, width=None, padx=14, pady=None):
        kwargs = dict(
            text=tekst, font=("Segoe UI", font_size, "bold" if bold else "normal"),
            bg=bg, fg="white" if bg == ACCENT else TEXT,
            activebackground=hover, activeforeground="white" if bg == ACCENT else TEXT,
            relief="flat", bd=0, cursor="hand2", command=komanda, padx=padx,
        )
        if height is not None:
            kwargs["height"] = height
        if width is not None:
            kwargs["width"] = width
        if pady is not None:
            kwargs["pady"] = pady
        btn = tk.Button(parent, **kwargs)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover) if btn["state"] != "disabled" else None)
        btn.bind("<Leave>", lambda e: btn.config(bg=bg) if btn["state"] != "disabled" else None)
        return btn

    # ------------------------------------------------------- male pomocne ---
    def _osvjezi_stanje_nacina(self):
        """Sivi opcije koje za odabrani nacin nemaju smisla - da korisnik ne bira
        rezoluciju za mp3 ili audio format za nijemi video."""
        nacin = self.var_nacin.get()
        self.cb_audio.config(state="readonly" if nacin == "samo_zvuk" else "disabled")
        self.cb_video_format.config(state="disabled" if nacin == "samo_zvuk" else "readonly")
        self.cb_kvaliteta.config(state="disabled" if nacin == "samo_zvuk" else "readonly")
        oznake = {"video_zvuk": self.t("skini_video"), "samo_video": self.t("skini_video_bez_zvuka"),
                  "samo_zvuk": self.t("skini_zvuk")}
        if not self.aktivno_preuzimanje:
            self.btn_download.config(text=oznake.get(nacin, self.t("skini_video")))

    def _spremi_postavke(self):
        self.cfg.update({
            "izlazni_folder": self.trenutni_folder,
            "nacin": self.var_nacin.get(),
            "kvaliteta": self.var_kvaliteta.get(),
            "video_format": self.var_video_format.get(),
            "audio_format": self.var_audio_format.get(),
            "h264": self.var_h264.get(),
            "metapodaci": self.var_metapodaci.get(),
        })
        try:
            # NE spremaj velicinu dok je prozor maksimiziran ("zoomed") - u tom
            # stanju geometry() vraca velicinu CIJELOG EKRANA, a ne "normalnu"
            # velicinu prozora prije maksimiziranja. Da smo je ovdje spremili,
            # svako sljedece pokretanje app bi bio ogroman prozor koji izgleda
            # kao da NIJE maksimiziran (jer tehnicki i nije) ali se svejedno ne
            # da smanjiti klikom - upravo problem koji je korisnik prijavio.
            if self.root.state() != "zoomed":
                self.cfg["prozor"] = self.root.geometry().split("+")[0]
        except Exception:
            pass
        return spremi_config(self.cfg)

    def zatvori(self):
        self._spremi_postavke()
        if self.player_proces and self.player_proces.is_alive():
            try:
                self.player_proces.terminate()
            except Exception:
                pass
        if self._webview_window is not None:
            try:
                self._webview_window.destroy()
            except Exception:
                pass
        self.root.destroy()
        if PYWEBVIEW_DOSTUPAN and EMBED_PLAYERA_DOSTUPAN:
            # sigurnosna mreža: ako webview.start() u glavnoj niti iz bilo kojeg
            # razloga ne vrati kontrolu čim se zadnji prozor uništi, ugasi proces
            # nasilno nakon kratke pauze - bolje to nego app koji "visi" u pozadini.
            threading.Timer(2.0, lambda: os._exit(0)).start()

    def resetiraj_velicinu_prozora(self):
        """Rucni, pouzdan izlaz iz nužde - vraca prozor na razumnu pocetnu
        velicinu (1240x820) i normalno (ne-maksimizirano) stanje, bez obzira
        sto je uzrokovalo da prozor ostane ogroman. Namjerno ne ovisi ni o
        kakvoj automatskoj detekciji - samo silom postavi poznato dobro stanje."""
        try:
            self.root.state("normal")
        except Exception:
            pass
        self.root.geometry("1240x820")
        self._centriraj_prozor()
        self.cfg["prozor"] = "1240x820"
        spremi_config(self.cfg)
        self.ispisi(self.t("msg_window_reset"))

    def _provjeri_i_prikazi_novosti(self):
        """Ako je ovo prvi put da se OVA verzija pokrece na ovom racunalu, prikaze
        kratak dijalog sto je promijenjeno/popravljeno (iz PROMJENE recnika) - i
        onda to zapamti, tako da se dijalog ne ponavlja na svako pokretanje, nego
        samo jednom po verziji (opet ce se pojaviti tek kad izadje sljedeca)."""
        if self.cfg.get("zadnja_prikazana_verzija") == APP_VERZIJA:
            return
        stavke = PROMJENE.get(APP_VERZIJA, {}).get(self.jezik) or PROMJENE.get(APP_VERZIJA, {}).get("hr")
        if stavke:
            tekst = "\n\n".join(f"• {s}" for s in stavke)
            naslov = f"Novosti u v{APP_VERZIJA}" if self.jezik == "hr" else f"What's new in v{APP_VERZIJA}"
            messagebox.showinfo(naslov, tekst)
        self.cfg["zadnja_prikazana_verzija"] = APP_VERZIJA
        spremi_config(self.cfg)

    def o_aplikaciji(self):
        messagebox.showinfo(
            self.t("o_aplikaciji_naslov"),
            f"💪 Mister Muscle Downloader\n"
            f"{'Verzija' if self.jezik == 'hr' else 'Version'} {APP_VERZIJA}\n"
            f"{self.t('o_aplikaciji_autor')}\n"
            f"{self.t('o_aplikaciji_prava')}\n\n"
            f"{self.t('podnaslov_app')}\n\n"
            f"{self.t('o_aplikaciji_auto_update')}\n\n"
            f"{self.t('o_aplikaciji_alati')}: {_alati_folder()}\n"
            f"{self.t('o_aplikaciji_postavke')}: {CONFIG_PATH}\n"
            f"yt-dlp: {yt_dlp_exe_putanja()}\n"
            f"ffmpeg: {ffmpeg_putanja() or self.t('nije_pronadjen')}"
        )

    def _otvori_putanju(self, putanja):
        try:
            napravi_folder(putanja)
            if JE_WINDOWS:
                os.startfile(putanja)
            else:
                subprocess.Popen(["xdg-open", putanja])
        except Exception as err:
            messagebox.showerror(self.t("err_naslov"), self.t("msg_cannot_open").format(err, putanja))

    def prikazi_desni_klik(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def zalijepi_tekst(self):
        try:
            clipboard_tekst = self.root.clipboard_get()
            if self.text_links.get("1.0", "end").strip() == self._placeholder:
                self.text_links.delete("1.0", "end")
                self.text_links.config(fg=TEXT)
            self.text_links.insert("insert", clipboard_tekst)
        except Exception:
            pass

    def ocisti_linkove(self):
        self.text_links.delete("1.0", "end")
        self._postavi_placeholder()
        if self._auto_ucitaj_after_id:
            self.root.after_cancel(self._auto_ucitaj_after_id)
            self._auto_ucitaj_after_id = None
        self._zadnji_auto_ucitani_link = None

    # ---------------------------------------------------- auto-ucitaj player ---
    def _na_promjenu_linkova(self, event=None):
        """Poziva se na SVAKU promjenu teksta u polju za linkove (<<Modified>>).
        Ne radimo nista tesko ovdje - samo (re)zakazemo provjeru malo kasnije,
        da ne pokusavamo otvarati player na svaki pojedini pritisak tipke dok
        korisnik jos tipka/lijepi (debounce)."""
        if not self.text_links.edit_modified():
            return
        self.text_links.edit_modified(False)  # mora se rucno resetirati da se event opet okine
        if self._auto_ucitaj_after_id:
            self.root.after_cancel(self._auto_ucitaj_after_id)
        self._auto_ucitaj_after_id = self.root.after(600, self._auto_ucitaj_player)

    def _auto_ucitaj_player(self):
        """Ako prvi redak izgleda kao pravi link i razlikuje se od zadnjeg koji
        smo vec automatski otvorili, otvori/osvjezi player - BEZ da korisnik mora
        kliknuti '🎬 Pregledaj i označi isječak'."""
        self._auto_ucitaj_after_id = None
        if not PYWEBVIEW_DOSTUPAN:
            return
        if self.aktivno_preuzimanje:
            return  # ne diraj player dok skidanje vec traje
        url = self._prvi_link()
        if not url or not re.match(r"^https?://", url, re.IGNORECASE):
            return
        if url == self._zadnji_auto_ucitani_link:
            return
        self._zadnji_auto_ucitani_link = url
        self.otvori_player()

    def ocisti_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _postavi_placeholder(self):
        self.text_links.insert("1.0", self._placeholder)
        self.text_links.config(fg=SUBTEXT)

    def _obrisi_placeholder(self, event=None):
        if self.text_links.get("1.0", "end").strip() == self._placeholder:
            self.text_links.delete("1.0", "end")
            self.text_links.config(fg=TEXT)

    def _vrati_placeholder(self, event=None):
        if not self.text_links.get("1.0", "end").strip():
            self._postavi_placeholder()

    def _prvi_link(self):
        sirovi = self.text_links.get("1.0", "end").strip()
        if not sirovi or sirovi == self._placeholder:
            return None
        return sirovi.splitlines()[0].strip()

    def otvori_output_folder(self):
        self._otvori_putanju(self.trenutni_folder)

    def odaberi_folder(self):
        odabrani_dir = filedialog.askdirectory(initialdir=self.trenutni_folder)
        if odabrani_dir:
            self.trenutni_folder = odabrani_dir
            self.lbl_folder.config(text=self.trenutni_folder)
            greska = self._spremi_postavke()
            if greska:
                self.ispisi(self.t("msg_folder_session_only").format(greska))
            else:
                self.ispisi(self.t("msg_folder_saved").format(self.trenutni_folder))

    def ispisi(self, poruka):
        self.log.configure(state="normal")
        self.log.insert("end", poruka + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        if "❌" in poruka:
            self._status_light(DANGER)

    def azuriraj_progress(self, val):
        self.progress["value"] = val
        self.lbl_postotak.config(text=f"{val:.0f}%")

    def azuriraj_brzinu(self, tekst):
        self.lbl_brzina.config(text=tekst)

    def ponisti_isjecak(self):
        self.od_sek = None
        self.do_sek = None
        self.azuriraj_isjecak_prikaz()

    def azuriraj_isjecak_prikaz(self):
        if self.od_sek is None and self.do_sek is None:
            self.isjecak_frame.pack_forget()
            return
        od_txt = formatiraj_trajanje(self.od_sek) if self.od_sek is not None else self.t("isjecak_pocetak")
        do_txt = formatiraj_trajanje(self.do_sek) if self.do_sek is not None else self.t("isjecak_kraj")
        self.lbl_isjecak.config(text=self.t("isjecak_label").format(od_txt, do_txt))
        self.isjecak_frame.pack(fill="x", padx=14, pady=(0, 12))

    def provjeri_queue(self):
        while not self.queue_sanjac.empty():
            try:
                podatak = self.queue_sanjac.get_nowait()
                if isinstance(podatak, tuple) and len(podatak) == 2:
                    tip, vrijednost = podatak
                    if tip == "od":
                        self.od_sek = parse_vrijeme(vrijednost)
                        self.ispisi(self.t("msg_start_marked").format(formatiraj_trajanje(self.od_sek)))
                        self.azuriraj_isjecak_prikaz()
                    elif tip == "do":
                        self.do_sek = parse_vrijeme(vrijednost)
                        self.ispisi(self.t("msg_end_marked").format(formatiraj_trajanje(self.do_sek)))
                        self.azuriraj_isjecak_prikaz()
                    elif tip == "skini_short":
                        od_vr, do_vr = vrijednost
                        self.od_sek = parse_vrijeme(od_vr)
                        self.do_sek = parse_vrijeme(do_vr)
                        self.azuriraj_isjecak_prikaz()
                        self.pokreni_preuzimanje()
                    elif tip == "skini_visestruke":
                        self.pokreni_preuzimanje_visestrukih_isjecaka(vrijednost)
                    elif tip == "lokalni_pregled":
                        self._fallback_lokalni_pregled()
            except Exception:
                break
        self.root.after(100, self.provjeri_queue)

    def _provjeri_webview2_pri_pokretanju(self, tih=False):
        """Provjerava (na glavnoj niti, jer po potrebi prikazuje dijalog) je li
        Microsoft Edge WebView2 Runtime instaliran - bez njega player uopce ne
        moze raditi na Windowsima (ni ugradjen ni u zasebnom prozoru). Ako
        nedostaje, pita korisnika smije li ga automatski preuzeti i instalirati
        (instalacija moze zatraziti Windows UAC potvrdu, zato pitamo prije).
        'tih=True' (koristi se pri pokretanju app-a) ne javlja nista ako je
        sve u redu - 'tih=False' (klik iz menija) uvijek potvrdi rezultat."""
        if webview2_dostupan():
            if not tih:
                messagebox.showinfo(self.t("webview2_naslov"), self.t("webview2_ok_text"))
            return
        self.ispisi(self.t("msg_webview2_missing"))
        odgovor = messagebox.askyesno(
            self.t("webview2_confirm_naslov"),
            self.t("webview2_confirm_text")
        )
        if not odgovor:
            self.ispisi(self.t("msg_webview2_skipped"))
            return
        threading.Thread(target=self._instaliraj_webview2_u_pozadini, daemon=True).start()

    def _instaliraj_webview2_u_pozadini(self):
        try:
            preuzmi_i_instaliraj_webview2(callback_status=lambda p: self.root.after(0, self.ispisi, p))
            self.root.after(0, self.ispisi, self.t("msg_webview2_ready"))
        except Exception as err:
            self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_webview2_install_failed").format(em)))
            self.root.after(0, lambda em=str(err): messagebox.showerror(
                self.t("err_naslov"), self.t("webview2_error_text").format(em)))

    # ------------------------------------------------------ alati / update ---
    def _provjera_alata_pri_pokretanju(self):
        """Pri svakom pokretanju provjeri jesu li yt-dlp i ffmpeg tu; ako nisu,
        skini ih automatski. Time korisnik NE MORA nista rucno instalirati."""
        if not yt_dlp_dostupan():
            self.root.after(0, self.ispisi, self.t("msg_tool_missing_downloading").format(YT_DLP_EXE_NAZIV))
            try:
                preuzmi_yt_dlp_exe(callback_status=lambda p: self.root.after(0, self.ispisi, p))
            except Exception as err:
                self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_ytdlp_download_failed").format(em)))

        if not ffmpeg_dostupan():
            self.root.after(0, self.ispisi, self.t("msg_ffmpeg_missing_note"))
            try:
                preuzmi_ffmpeg(callback_status=lambda p: self.root.after(0, self.ispisi, p),
                               callback_postotak=lambda p: self.root.after(0, self.azuriraj_progress, p))
                self.root.after(0, self.azuriraj_progress, 0)
            except Exception as err:
                self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_ffmpeg_download_failed").format(em)))

        self.root.after(0, self._osvjezi_statusnu_traku)
        self.root.after(0, self._tiha_provjera_azuriranja_pri_pokretanju)

    def _tiha_provjera_azuriranja_pri_pokretanju(self):
        """Svaki put pri pokretanju, u pozadini i bez ikakvog vidljivog UI-a dok
        traje, provjerava ima li nova verzija yt-dlp-a (mehanizma za skidanje,
        koji se najcesce mijenja jer prati YouTube/TikTok/Instagram promjene).
        Ako ima, PRIJE nego sto korisnik pocne bilo sto skidati, ponudi mu
        (dijalogom) da je odmah preuzme - nista se ne skida bez pitanja."""
        threading.Thread(target=self._tijek_tihe_provjere, daemon=True).start()

    def _tijek_tihe_provjere(self):
        if not yt_dlp_dostupan():
            return  # tek ce se preuzeti (ili se upravo preuzima) - provjera ovdje nema smisla
        try:
            rez = pokreni_yt_dlp(["--version"], timeout=15)
            trenutna = (rez.stdout or rez.stderr).strip()
        except Exception:
            trenutna = None
        if trenutna:
            najnovija = _najnovija_verzija_yt_dlp()
            if najnovija and najnovija != trenutna:
                self.root.after(0, lambda: self._ponudi_azuriranje_yt_dlp(trenutna, najnovija))

        # provjeri i samu aplikaciju (ne samo yt-dlp) - preko GitHub Releases
        app_verzija, app_url = _najnovija_verzija_app()
        if app_verzija and app_url and _usporedi_verzije(app_verzija, APP_VERZIJA) > 0:
            self.root.after(0, lambda: self._ponudi_azuriranje_app(app_verzija, app_url))

    def _ponudi_azuriranje_app(self, nova_verzija, url_setup):
        if self.aktivno_preuzimanje:
            return  # ne prekidaj ponudom vec pokrenuto skidanje - provjerit ce se opet sljedeci put
        odgovor = messagebox.askyesno(
            self.t("app_update_naslov"),
            self.t("app_update_text").format(nova_verzija, APP_VERZIJA)
        )
        if odgovor:
            threading.Thread(target=self._preuzmi_i_pokreni_azuriranje_app, args=(url_setup,), daemon=True).start()

    def _preuzmi_i_pokreni_azuriranje_app(self, url_setup):
        """Preuzima novi Setup.exe s GitHub Releasea i pokrece ga - app se zatim
        SAMA zatvara (kroz self.zatvori(), koji vec cisti player/webview i sprema
        postavke) da instalater moze zamijeniti trenutno pokrenuti .exe. Setup
        se skida u sistemski temp folder (ne u folder aplikacije), pa radi cak i
        ako je app instalirana u Program Files bez pisackih prava tamo."""
        try:
            self.root.after(0, self.ispisi, self.t("msg_downloading_app_update"))
            cilj = os.path.join(tempfile.gettempdir(), "MisterMuscle_Setup_update.exe")
            preuzmi_datoteku(url_setup, cilj,
                             callback_postotak=lambda p: self.root.after(0, self.azuriraj_progress, p),
                             min_velicina=1_000_000)
            self.root.after(0, self.azuriraj_progress, 0)
            self.root.after(0, self.ispisi, self.t("msg_launching_installer"))
            subprocess.Popen([cilj], close_fds=True)
            self.root.after(800, self.zatvori)
        except Exception as err:
            self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_app_update_failed").format(em)))
            self.root.after(0, lambda em=str(err): messagebox.showerror(
                self.t("err_naslov"), self.t("msg_app_update_failed").format(em)))

    def _ponudi_azuriranje_yt_dlp(self, trenutna, najnovija):
        if self.aktivno_preuzimanje:
            return  # ne prekidaj ponudom vec pokrenuto skidanje - provjerit ce se opet sljedeci put
        odgovor = messagebox.askyesno(
            self.t("update_available_naslov"),
            self.t("update_available_text").format(najnovija, trenutna)
        )
        if odgovor:
            self.ispisi(self.t("msg_updating_ytdlp"))
            threading.Thread(target=self._azuriraj_yt_dlp_i_prijavi, daemon=True).start()

    def _azuriraj_yt_dlp_i_prijavi(self):
        poruka = self._azuriraj_yt_dlp()
        self.root.after(0, self.ispisi, poruka)
        self.root.after(0, self._osvjezi_statusnu_traku)

    def _osvjezi_statusnu_traku(self):
        try:
            rez = pokreni_yt_dlp(["--version"], timeout=20)
            yt_verzija = (rez.stdout or rez.stderr).strip() or "?"
        except Exception:
            yt_verzija = self.t("status_tools_unavailable")
        ff = "✅ ffmpeg" if ffmpeg_dostupan() else self.t("status_ffmpeg_missing")
        self.lbl_status_alati.config(text=f"yt-dlp {yt_verzija}   ·   {ff}   ·   alati: {_alati_folder()}")
        self.ispisi(self.t("msg_tools_summary").format(yt_verzija, ff))

    def provjeri_azuriranja(self, samo=None):
        if self.aktivno_preuzimanje:
            messagebox.showwarning(self.t("update_in_progress_naslov"), self.t("update_in_progress_text"))
            return
        self.btn_update.config(state="disabled", text=self.t("provjeravam"))
        threading.Thread(target=self._tijek_azuriranja, args=(samo,), daemon=True).start()

    def _tijek_azuriranja(self, samo=None):
        sazetak = []

        # --- 1) yt-dlp ---
        if samo in (None, "yt-dlp"):
            sazetak.append(self._azuriraj_yt_dlp())

        # --- 2) ffmpeg ---
        if samo in (None, "ffmpeg"):
            sazetak.append(self._osiguraj_ffmpeg(prisilno=(samo == "ffmpeg")))

        self.root.after(0, self._osvjezi_statusnu_traku)
        self.root.after(0, lambda: self.btn_update.config(state="normal", text=self.t("gumb_azuriranja")))
        self.root.after(0, lambda s="\n".join(sazetak): messagebox.showinfo(self.t("updates_naslov"), s))

    def _azuriraj_yt_dlp(self):
        if not yt_dlp_dostupan():
            try:
                preuzmi_yt_dlp_exe(callback_status=lambda p: self.root.after(0, self.ispisi, p))
                return self.t("msg_ytdlp_downloaded_first")
            except Exception as err:
                return self.t("msg_ytdlp_download_failed_short").format(err)
        try:
            # "yt-dlp.exe -U" je sluzbeni ugradeni self-update samostalnog binarnika:
            # sam sebe prepise najnovijom verzijom, bez pipa i bez Pythona. Zato radi
            # i unutar naseg PyInstaller .exe-a (za razliku od "pip install --upgrade").
            # Timeout je 300 s, ne 60 - skida se ~17 MB i na sporijoj vezi 60 s zna
            # isteci usred zapisivanja, sto ostavlja pokvaren yt-dlp.exe.
            self.root.after(0, self.ispisi, self.t("msg_ytdlp_running_update"))
            rezultat = pokreni_yt_dlp(["-U"], timeout=300)
            izlaz = (rezultat.stdout + "\n" + rezultat.stderr).strip()
            self.root.after(0, lambda iz=izlaz: self.ispisi(self.t("msg_ytdlp_output").format(iz)))
            nizak = izlaz.lower()
            if "error" in nizak or rezultat.returncode != 0:
                return self.t("msg_ytdlp_update_failed")
            if "up to date" in nizak or "up-to-date" in nizak or "latest version" in nizak:
                return self.t("msg_ytdlp_already_latest")
            if "updated" in nizak or "updating to" in nizak:
                return self.t("msg_ytdlp_updated")
            return self.t("msg_ytdlp_check_done")
        except subprocess.TimeoutExpired:
            return self.t("msg_ytdlp_update_timeout")
        except Exception as err:
            return self.t("msg_ytdlp_update_error").format(err)

    def _osiguraj_ffmpeg(self, prisilno=False):
        if ffmpeg_dostupan() and not prisilno:
            return self.t("msg_ffmpeg_present")
        try:
            preuzmi_ffmpeg(callback_status=lambda p: self.root.after(0, self.ispisi, p),
                           callback_postotak=lambda p: self.root.after(0, self.azuriraj_progress, p))
            self.root.after(0, self.azuriraj_progress, 0)
            return self.t("msg_ffmpeg_installed")
        except Exception as err:
            return self.t("msg_ffmpeg_error").format(err)

    # ------------------------------------------------------------- player ---
    def otvori_player(self):
        if not PYWEBVIEW_DOSTUPAN:
            messagebox.showerror(self.t("err_naslov"), self.t("err_pywebview_missing_text"))
            return
        url = self._prvi_link()
        if not url:
            messagebox.showwarning(self.t("warn_naslov"), self.t("warn_paste_link_first"))
            return

        platforma = prepoznaj_platformu(url)
        if platforma == "youtube":
            video_id = izvuci_video_id(url)
            if not video_id:
                messagebox.showerror(self.t("err_naslov"), self.t("err_cant_recognize_youtube"))
                return
            identifikator = video_id
        else:
            identifikator = _sigurni_id_za_url(url)

        # fallback prozor (ako ugradnja nije dostupna) - ugasi prethodni prije novog
        if self.player_proces and self.player_proces.is_alive():
            try:
                self.player_proces.terminate()
            except Exception:
                pass

        if identifikator != getattr(self, "_zadnji_video_id", None):
            self.ponisti_isjecak()
        self._zadnji_video_id = identifikator
        self._zadnji_url = url

        self._prikazi_sadrzaj("player")

        self.ispisi(self.t("msg_opening_player") if platforma == "youtube" else self.t("msg_fetching_preview"))
        threading.Thread(target=self._pripremi_i_pokreni, args=(platforma, url, identifikator), daemon=True).start()

    def _fallback_lokalni_pregled(self):
        """Kad sluzbeni YouTube iframe player javi da je vlasnik onemogucio embed
        (kod 101/150), player (JS) sam trazi ovo - umjesto sluzbenog iframea,
        skida se kraci lokalni pregled isto kao za TikTok/Instagram i ucitava
        se u ISTI prozor playera. Dizajn/izgled playera se uopce ne mijenja,
        samo nacin dohvata videa za taj konkretan slucaj."""
        url = getattr(self, "_zadnji_url", None)
        identifikator = getattr(self, "_zadnji_video_id", None)
        if not url or not identifikator:
            return
        self.ispisi(self.t("msg_embed_disabled_fallback"))
        threading.Thread(target=self._pripremi_i_pokreni, args=("generic", url, identifikator), daemon=True).start()

    def _pripremi_i_pokreni(self, platforma, url, identifikator):
        if platforma == "youtube":
            html = _player_html("youtube", video_id=identifikator, jezik=self.jezik)
        else:
            try:
                naziv_video_fajla = self._skini_generic_preview(url, identifikator)
            except Exception as err_p:
                puni_trag = traceback.format_exc()
                kratka_poruka = str(err_p).strip() or type(err_p).__name__
                if je_poznati_tiktok_challenge_bug(puni_trag):
                    kratka_poruka = self.t("msg_tiktok_bug_preview")
                self.root.after(0, lambda em=kratka_poruka: messagebox.showerror(
                    self.t("err_naslov"), self.t("err_cant_fetch_preview").format(em)))
                self.root.after(0, lambda pt=puni_trag: self.ispisi(self.t("msg_preview_failed_log").format(pt)))
                return
            html = _player_html("generic", video_src=f"/{naziv_video_fajla}", jezik=self.jezik)

        naziv_fajla = f"preview_{identifikator}.html"
        putanja = os.path.join(self.temp_dir, naziv_fajla)
        try:
            with open(putanja, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as err_z:
            self.root.after(0, lambda em=str(err_z): messagebox.showerror(
                self.t("err_naslov"), self.t("err_cant_prepare_player").format(em)))
            return

        preview_url = f"http://127.0.0.1:{self.http_port}/{naziv_fajla}"

        if EMBED_PLAYERA_DOSTUPAN and self._webview_window is not None:
            # cekaj (kratko) da je prozor vec ugradjen prvi put, pa mu samo promijeni URL
            self._webview_spreman.wait(timeout=15)
            try:
                self._webview_window.load_url(preview_url)
                self.root.after(400, self._forsiraj_repaint_playera)
                self.root.after(0, self.ispisi, self.t("msg_embedded_ready"))
            except Exception as err:
                self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_embed_load_failed").format(em)))
                self._pokreni_fallback_prozor(preview_url)
        else:
            self._pokreni_fallback_prozor(preview_url)

    def _pokreni_fallback_prozor(self, preview_url):
        """Ako ugradnja nije dostupna (nije Windows / fali pywin32 / nešto je puklo),
        player se otvara u svom zasebnom prozoru - kao u ranijim verzijama."""
        self.player_proces = multiprocessing.Process(target=pokreni_webview_proces,
                                                     args=(preview_url, self.queue_sanjac))
        self.player_proces.start()

    def _skini_generic_preview(self, url, identifikator):
        """Skida manju kopiju videa lokalno - TikTokov CDN link trazi ista HTTP
        zaglavlja kojima ga je yt-dlp izvukao, pa <video src="..."> direktno cesto
        vrati 403. Lokalna kopija to zaobilazi."""
        if not yt_dlp_dostupan():
            preuzmi_yt_dlp_exe()
        naziv_fajla = f"preview_{identifikator}.mp4"
        putanja = os.path.join(self.temp_dir, naziv_fajla)
        argumenti = [
            url, "-f", "best[height<=480][ext=mp4]/best[height<=480]/best",
            "-o", putanja, "--no-playlist", "--playlist-items", "1", "--quiet", "--no-warnings",
            "--impersonate", "chrome",
            *ffmpeg_argumenti(),
        ]
        rezultat = pokreni_yt_dlp(argumenti, timeout=180)
        if rezultat.returncode != 0 or not os.path.exists(putanja):
            detalji = (rezultat.stdout + "\n" + rezultat.stderr).strip()
            raise RuntimeError(detalji or f"yt-dlp je završio s greškom (kod {rezultat.returncode}).")
        return naziv_fajla

    # ------------------------------------------------- pauza / prekid / DL ---
    def toggle_pauza(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text=self.t("gumb_nastavi"), bg=ACCENT)
            self._primijeni_pauzu(True)
        else:
            self.pause_event.set()
            self.btn_pause.config(text=self.t("gumb_pauziraj"), bg=PAUSE_BG)
            self._primijeni_pauzu(False)

    def _primijeni_pauzu(self, pauziraj):
        proc = self.aktivni_proces
        if not proc or proc.poll() is not None:
            return
        if not PSUTIL_DOSTUPAN:
            if pauziraj:
                self.ispisi(self.t("msg_need_psutil_pause"))
            return
        try:
            p = psutil.Process(proc.pid)
            for dijete in p.children(recursive=True):
                dijete.suspend() if pauziraj else dijete.resume()
            p.suspend() if pauziraj else p.resume()
        except Exception as err:
            akcija = self.t("akcija_pauzirati") if pauziraj else self.t("akcija_nastaviti")
            self.ispisi(self.t("msg_cant_pause_resume").format(akcija, err))

    def prekini_preuzimanje(self):
        if not self.aktivno_preuzimanje:
            return
        self.otkazano = True
        self.pause_event.set()
        proc = self.aktivni_proces
        if proc and proc.poll() is None:
            try:
                if PSUTIL_DOSTUPAN:
                    p = psutil.Process(proc.pid)
                    for dijete in p.children(recursive=True):
                        # yt-dlp pokrece ffmpeg kao dijete - ubijanje samo roditelja
                        # ostavi ffmpeg da i dalje melje u pozadini.
                        dijete.resume()
                        dijete.kill()
                    p.resume()
                proc.kill()
            except Exception:
                pass
        self.ispisi(self.t("msg_cancelled_by_user"))

    def pokreni_preuzimanje(self):
        if self.aktivno_preuzimanje:
            return
        sirovi = self.text_links.get("1.0", "end").strip()
        if not sirovi or sirovi == self._placeholder:
            messagebox.showwarning(self.t("warn_no_link_naslov"), self.t("warn_no_link_text"))
            return
        linkovi = [l.strip() for l in sirovi.splitlines() if l.strip()]

        nacin = self.var_nacin.get()
        treba_ffmpeg = (nacin != "samo_video") or (self.od_sek is not None or self.do_sek is not None)
        if treba_ffmpeg and not ffmpeg_dostupan():
            if messagebox.askyesno(
                self.t("ffmpeg_missing_naslov"),
                self.t("ffmpeg_missing_confirm_text")
            ):
                threading.Thread(target=lambda: (self._osiguraj_ffmpeg(), self.root.after(0, self._osvjezi_statusnu_traku)),
                                 daemon=True).start()
            return

        self._spremi_postavke()
        self.aktivno_preuzimanje = True
        self.otkazano = False
        self.pause_event.set()
        self.btn_download.config(state="disabled", text=self.t("skidam"), bg=PAUSE_BG)
        self.btn_pause.config(state="normal")
        self.btn_prekini.config(state="normal")
        self.azuriraj_progress(0)
        self._status_light(ACCENT)
        self._prikazi_sadrzaj("log")

        threading.Thread(target=self.skini_sve,
                         args=(linkovi, self.od_sek, self.do_sek, nacin), daemon=True).start()

    def pokreni_preuzimanje_visestrukih_isjecaka(self, isjecci):
        """Skida VIŠE isječaka odjednom (svaki iz 'isjecci' kao zaseban fajl), za
        sve zalijepljene linkove - poziva ga player kad se klikne '⬇ Skini sve
        isječke' u listi odabira ('isjecci' je lista [od_string, do_string] parova
        koje je poslao JS, npr. [["0:48","1:12"], ["3:00","3:20"]])."""
        if self.aktivno_preuzimanje:
            self.root.after(0, lambda: messagebox.showwarning(
                self.t("update_in_progress_naslov"), self.t("warn_download_in_progress_text")))
            return
        if not isjecci:
            return
        sirovi = self.text_links.get("1.0", "end").strip()
        if not sirovi or sirovi == self._placeholder:
            self.root.after(0, lambda: messagebox.showwarning(self.t("warn_no_link_naslov"), self.t("warn_no_link_text")))
            return
        linkovi = [l.strip() for l in sirovi.splitlines() if l.strip()]

        if not ffmpeg_dostupan():
            self.root.after(0, lambda: messagebox.showwarning(
                self.t("ffmpeg_missing_naslov"),
                self.t("ffmpeg_missing_multi_text")))
            return

        nacin = self.var_nacin.get()
        self._spremi_postavke()
        self.aktivno_preuzimanje = True
        self.otkazano = False
        self.pause_event.set()
        self.btn_download.config(state="disabled", text=self.t("skidam"), bg=PAUSE_BG)
        self.btn_pause.config(state="normal")
        self.btn_prekini.config(state="normal")
        self.azuriraj_progress(0)
        self._status_light(ACCENT)
        self._prikazi_sadrzaj("log")

        threading.Thread(target=self._skini_visestruke_isjecke,
                         args=(linkovi, isjecci, nacin), daemon=True).start()

    def _skini_visestruke_isjecke(self, linkovi, isjecci, nacin):
        napravi_folder(self.trenutni_folder)

        if not yt_dlp_dostupan():
            try:
                preuzmi_yt_dlp_exe(callback_status=lambda p: self.root.after(0, self.ispisi, p))
            except Exception as err:
                self.root.after(0, lambda em=str(err): messagebox.showerror(
                    self.t("err_naslov"), self.t("err_cant_download_tool").format(YT_DLP_EXE_NAZIV, em)))
                self._zavrsi_preuzimanje(0, len(linkovi) * len(isjecci))
                return

        zajednicki = [
            "--no-playlist",
            # "--no-playlist" sprjecava skidanje CIJELE prepoznate playliste, ali
            # neke stranice (cesto opcenite/adult stranice bez posebnog yt-dlp
            # "extractora") vracaju stranicu kao gomilu pronadjenih video linkova
            # (preporuceni/povezani klipovi, reklame...) preko GENERICKOG
            # extractora - "--playlist-items 1" to dodatno osigurava: cak i tada
            # se skine SAMO prvi (traženi) video, ne svih ~100 pronađenih.
            "--playlist-items", "1",
            "--newline",
            "--concurrent-fragments", "8",
            "--http-chunk-size", "10M",
            "--retries", "10",
            "--fragment-retries", "10",
            "--buffer-size", "1M",
            "--trim-filenames", "120",
            *ffmpeg_argumenti(),
        ]

        uspjesni = 0
        neuspjesni = 0
        ukupno = len(linkovi) * len(isjecci)
        brojac = 0

        for idx, par in enumerate(isjecci, start=1):
            if self.otkazano:
                break
            try:
                od_str, do_str = par
            except (TypeError, ValueError):
                continue
            od_sek = parse_vrijeme(od_str)
            do_sek = parse_vrijeme(do_str)
            if od_sek is None or do_sek is None or do_sek <= od_sek:
                self.root.after(0, self.ispisi,
                                f"⚠ Isječak {idx}. preskočen — neispravan raspon ({od_str} → {do_str}).")
                neuspjesni += len(linkovi)
                continue

            raspon = ["--download-sections", f"*{od_sek}-{do_sek}", "--force-keyframes-at-cuts"]
            sufiks = f" (isječak {idx}, {formatiraj_trajanje(od_sek)}-{formatiraj_trajanje(do_sek)})"

            for url in linkovi:
                brojac += 1
                if self.otkazano:
                    break
                self.root.after(0, self.ispisi,
                                f"\n[{brojac}/{ukupno}] Isječak {idx}. "
                                f"({formatiraj_trajanje(od_sek)}–{formatiraj_trajanje(do_sek)}): {url}")
                platforma = prepoznaj_platformu(url)
                argumenti_url = [url, *self._argumenti_za_nacin(nacin, platforma, sufiks=sufiks),
                                 *zajednicki, *raspon]
                if platforma != "youtube":
                    argumenti_url += ["--format-sort", "res,fps,tbr,vbr,size", "--impersonate", "chrome"]

                vrijeme_prije = time.time()
                uspjelo, zadnja_greska = self._skini_jedan(argumenti_url, nacin, platforma, vrijeme_prije)
                if uspjelo:
                    uspjesni += 1
                elif not self.otkazano:
                    neuspjesni += 1
                    self.root.after(0, lambda em=zadnja_greska: self.ispisi(self.t("msg_error_generic").format(em)))

        self._zavrsi_preuzimanje(uspjesni, neuspjesni)

    def _argumenti_za_nacin(self, nacin, platforma, sufiks=""):
        """Slaze dio yt-dlp argumenata koji ovisi o odabranom nacinu skidanja.
        'sufiks' (npr. ' (isječak 2, 0:48-1:12)') se ubacuje u naziv fajla -
        koristi se kod skidanja VIŠE isječaka iz istog videa odjednom, da se
        ne prepisuju međusobno."""
        visina = visina_iz_kvalitete(self.var_kvaliteta.get())
        h264 = self.var_h264.get()
        format_str = izgradi_format_string(platforma, nacin, visina, h264)
        argumenti = ["-f", format_str]

        if nacin == "samo_zvuk":
            odabir = self.var_audio_format.get()
            if not odabir.startswith("original"):
                argumenti += ["-x", "--audio-format", odabir, "--audio-quality", "0"]
            if self.var_metapodaci.get():
                argumenti += ["--embed-thumbnail", "--embed-metadata"]
            predlozak = f"%(title)s{sufiks}.%(ext)s"
        elif nacin == "samo_video":
            # Nijemi zapis - nema sto spajati (nema audio streama), ali kontejner
            # (mp4/mkv/webm/mov) i dalje mozemo promijeniti - "remux" samo
            # presloji video u drugi kontejner bez ponovnog kodiranja (brzo,
            # bez gubitka kvalitete); ako izvorni kodek nije kompatibilan s
            # odabranim kontejnerom, yt-dlp ce prijaviti gresku pri tom koraku.
            video_format = self.var_video_format.get()
            if not video_format.startswith("original"):
                argumenti += ["--remux-video", video_format]
            predlozak = f"%(title)s{sufiks} [bez zvuka].%(ext)s"
        else:
            video_format = self.var_video_format.get()
            if not video_format.startswith("original"):
                argumenti += ["--merge-output-format", video_format]
            if self.var_metapodaci.get():
                argumenti += ["--embed-metadata"]
            predlozak = f"%(title)s{sufiks}.%(ext)s"

        argumenti += ["-o", os.path.join(self.trenutni_folder, predlozak)]
        return argumenti

    def skini_sve(self, linkovi, od_sek, do_sek, nacin):
        napravi_folder(self.trenutni_folder)

        if not yt_dlp_dostupan():
            try:
                preuzmi_yt_dlp_exe(callback_status=lambda p: self.root.after(0, self.ispisi, p))
            except Exception as err:
                self.root.after(0, lambda em=str(err): messagebox.showerror(
                    self.t("err_naslov"), self.t("err_cant_download_tool").format(YT_DLP_EXE_NAZIV, em)))
                self._zavrsi_preuzimanje(0, len(linkovi))
                return

        zajednicki = [
            "--no-playlist",
            "--playlist-items", "1",
            "--newline",
            "--concurrent-fragments", "8",
            "--http-chunk-size", "10M",
            "--retries", "10",
            "--fragment-retries", "10",
            "--buffer-size", "1M",
            "--trim-filenames", "120",   # duga TikTok imena zna probiti Windows limit putanje
            *ffmpeg_argumenti(),
        ]

        raspon = []
        if od_sek is not None or do_sek is not None:
            pocetak = od_sek if od_sek is not None else 0
            kraj = do_sek if do_sek is not None else 999999999
            # "--force-keyframes-at-cuts" je BITAN - bez njega yt-dlp/ffmpeg samo
            # "zalijepi" na najblizi keyframe (brzo, ali fajl u sebi ponekad
            # zadrzi POGRESNO (originalno, puno duze) trajanje u zaglavlju/
            # metapodacima - zato je pisalo npr. "2h" za isjecak od 3 minute i
            # nije se moglo premotavati). S ovom zastavicom ffmpeg stvarno
            # re-enkodira tocno na rezove, pa izlazni fajl ima ISPRAVNO trajanje.
            raspon = ["--download-sections", f"*{pocetak}-{kraj}", "--force-keyframes-at-cuts"]

        uspjesni = 0
        neuspjesni = 0

        for i, url in enumerate(linkovi, start=1):
            if self.otkazano:
                break
            self.root.after(0, self.ispisi, f"\n[{i}/{len(linkovi)}] {url}")
            platforma = prepoznaj_platformu(url)

            argumenti_url = [url, *self._argumenti_za_nacin(nacin, platforma), *zajednicki, *raspon]
            if platforma != "youtube":
                argumenti_url += ["--format-sort", "res,fps,tbr,vbr,size", "--impersonate", "chrome"]

            vrijeme_prije = time.time()
            uspjelo, zadnja_greska = self._skini_jedan(argumenti_url, nacin, platforma, vrijeme_prije)

            if uspjelo:
                uspjesni += 1
            elif not self.otkazano:
                neuspjesni += 1
                self.root.after(0, lambda em=zadnja_greska: self.ispisi(self.t("msg_error_generic").format(em)))

        self._zavrsi_preuzimanje(uspjesni, neuspjesni)

    def _skini_jedan(self, argumenti_url, nacin, platforma, vrijeme_prije):
        MAX_POKUSAJA = 3
        zadnja_greska_tekst = None

        for pokusaj in range(1, MAX_POKUSAJA + 1):
            if self.otkazano:
                return False, "prekinuto"
            self.root.after(0, self.azuriraj_progress, 0)
            izlaz_redovi = []
            try:
                proc = pokreni_yt_dlp_popen(argumenti_url)
            except Exception as err_pokretanje:
                return False, self.t("err_cant_start_tool").format(YT_DLP_EXE_NAZIV, err_pokretanje)

            self.aktivni_proces = proc
            if not self.pause_event.is_set():
                self._primijeni_pauzu(True)

            for redak in proc.stdout:
                redak = redak.rstrip("\n")
                if not redak:
                    continue
                izlaz_redovi.append(redak)
                m = re.search(r"\[download\]\s+([\d.]+)%", redak)
                if m:
                    try:
                        self.root.after(0, self.azuriraj_progress, min(float(m.group(1)), 100.0))
                    except ValueError:
                        pass
                    brzina = re.search(r"at\s+([\d.]+\s*\w+/s)", redak)
                    eta = re.search(r"ETA\s+([\d:]+)", redak)
                    opis = []
                    if brzina:
                        opis.append(brzina.group(1))
                    if eta:
                        opis.append(f"preostalo {eta.group(1)}")
                    if opis:
                        self.root.after(0, self.azuriraj_brzinu, "  ·  ".join(opis))
                elif "[Merger]" in redak or "Merging formats" in redak:
                    self.root.after(0, self.ispisi, self.t("msg_merging"))
                elif "[ExtractAudio]" in redak:
                    self.root.after(0, self.ispisi, self.t("msg_extracting_audio"))

            proc.wait()
            self.aktivni_proces = None
            self.root.after(0, self.azuriraj_brzinu, "")
            puni_izlaz = "\n".join(izlaz_redovi)

            if self.otkazano:
                return False, "prekinuto"

            if proc.returncode == 0:
                if nacin == "samo_video":
                    self.root.after(0, self.ispisi, self.t("msg_silent_video_done"))
                if nacin != "samo_zvuk" and platforma != "youtube" and self.var_h264.get():
                    self._osiguraj_h264(vrijeme_prije)
                if nacin != "samo_zvuk" and "--download-sections" in argumenti_url:
                    self._popravi_trajanje_isjecka(vrijeme_prije)
                self.root.after(0, self.azuriraj_progress, 100)
                return True, None

            zadnja_greska_tekst = puni_izlaz.strip() or f"{YT_DLP_EXE_NAZIV} je završio s kodom {proc.returncode}"
            donji = zadnja_greska_tekst.lower()

            # TikTok nekad uopce nema odvojeni video stream - tada 'samo_video' pada
            # na "requested format is not available". Rjesenje: skini normalno pa
            # ffmpegom izbaci audio zapis.
            if nacin == "samo_video" and "requested format" in donji:
                self.root.after(0, self.ispisi, self.t("msg_no_separate_video_stream"))
                return self._skini_pa_ukloni_zvuk(argumenti_url, vrijeme_prije)

            if je_poznati_tiktok_challenge_bug(puni_izlaz):
                self.root.after(0, lambda: self.ispisi(self.t("msg_tiktok_bug_download")))
                return False, zadnja_greska_tekst

            prolazna = any(t in donji for t in [
                "unable to extract", "rehydration", "webpage video data",
                "http error 5", "timed out", "timeout", "connection",
            ])
            if prolazna and pokusaj < MAX_POKUSAJA:
                self.root.after(0, lambda p=pokusaj: self.ispisi(self.t("msg_retry_attempt").format(p)))
                time.sleep(2)
                continue
            self.root.after(0, lambda pt=puni_izlaz: self.ispisi(self.t("msg_full_error_details").format(pt)))
            return False, zadnja_greska_tekst

        return False, zadnja_greska_tekst

    def _skini_pa_ukloni_zvuk(self, argumenti_url, vrijeme_prije):
        """Fallback za 'samo video' kad izvor nema odvojeni video stream."""
        argumenti = list(argumenti_url)
        if "-f" in argumenti:
            idx = argumenti.index("-f")
            argumenti[idx + 1] = "best"
        rezultat = pokreni_yt_dlp(argumenti, timeout=3600)
        if rezultat.returncode != 0:
            return False, (rezultat.stdout + rezultat.stderr).strip()
        putanja = self._zadnji_fajl(vrijeme_prije)
        if not putanja:
            return True, None
        ffmpeg = ffmpeg_putanja()
        if not ffmpeg:
            self.root.after(0, self.ispisi, self.t("msg_no_ffmpeg_kept_audio"))
            return True, None
        bez_zvuka = putanja + ".nijemi.mp4"
        subprocess.run([ffmpeg, "-y", "-i", putanja, "-c", "copy", "-an", bez_zvuka],
                       capture_output=True, timeout=1800, **_SUBPROCESS_FLAGS)
        if os.path.exists(bez_zvuka) and os.path.getsize(bez_zvuka) > 0:
            os.remove(putanja)
            korijen, nastavak = os.path.splitext(putanja)
            putanja = f"{korijen} [bez zvuka]{nastavak}"
            os.rename(bez_zvuka, putanja)
            self.root.after(0, self.ispisi, self.t("msg_audio_removed"))
        if "--download-sections" in argumenti_url:
            self._popravi_trajanje_isjecka(vrijeme_prije)
        return True, None

    def _popravi_trajanje_isjecka(self, vrijeme_prije):
        """Nakon rezanja isjecka (--download-sections) izlazni fajl ZNA u sebi
        zadrzati POGRESNO (izvorno, puno duze) trajanje - iz VISE mogucih razloga
        koje razliciti playeri razlicito citaju:
          1) u STRUKTURNOM zaglavlju kontejnera (mvhd/moov) - ovo popravlja
             sam remux (ffmpeg ga UVIJEK ispravno izracuna iz stvarnih paketa
             pri remuxanju).
          2) u UGRADJENOJ METAPODATAK OZNACI "duration" koju je yt-dlp upisao
             JOS PRIJE rezanja (odrazava ORIGINALNI, neodrezani video) - obican
             '-c copy' remux tu oznaku PO DEFAULTU prenese netaknutu u novi
             fajl (ffmpeg kopira metapodatke ako mu se izricito ne kaze da ne
             kopira). Rjesava se s '-map_metadata -1'.
          3) VREMENSKE OZNAKE (timestamps) unutar samog isjecka mogu ostati na
             ORIGINALNIM vrijednostima s pocetka rezanja (npr. isjecak od
             48. do 51. minute originala moze u sebi zadrzati brojeve 48:00-
             51:00 umjesto da se resetiraju na 0:00-3:00) - neki playeri
             (VLC) trajanje racunaju iz NAJVECE pronadjene vremenske oznake,
             pa prikazu "traje do 51. minute" iako je stvarni sadrzaj samo 3
             minute dug. Rjesava se s '-fflags +genpts -avoid_negative_ts
             make_zero', koji tjera ffmpeg da PONOVNO IZGRADI vremenske
             oznake od nule za ovaj (novi, odrezani) fajl."""
        ffmpeg = ffmpeg_putanja()
        if not ffmpeg:
            return
        putanja = self._zadnji_fajl(vrijeme_prije)
        if not putanja:
            return
        privremena = putanja + ".popravljeno" + os.path.splitext(putanja)[1]
        try:
            rezultat = subprocess.run(
                [ffmpeg, "-y", "-fflags", "+genpts", "-i", putanja, "-map", "0", "-c", "copy",
                 "-map_metadata", "-1", "-avoid_negative_ts", "make_zero",
                 "-movflags", "+faststart", privremena],
                capture_output=True, timeout=600, **_SUBPROCESS_FLAGS
            )
            if rezultat.returncode == 0 and os.path.exists(privremena) and os.path.getsize(privremena) > 0:
                os.remove(putanja)
                os.rename(privremena, putanja)
                self.root.after(0, self.ispisi, self.t("msg_duration_fixed"))
            elif os.path.exists(privremena):
                os.remove(privremena)
        except Exception:
            if os.path.exists(privremena):
                try:
                    os.remove(privremena)
                except OSError:
                    pass
            # "best effort" popravak - ako ne uspije, fajl ostaje kakav je bio
            # (sadrzaj je i dalje tocno odrezan, samo zaglavlje moze biti krivo)

    def _zadnji_fajl(self, vrijeme_prije):
        try:
            kandidati = [
                os.path.join(self.trenutni_folder, f)
                for f in os.listdir(self.trenutni_folder)
                if f.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))
            ]
            kandidati = [f for f in kandidati if os.path.getmtime(f) >= vrijeme_prije - 1]
            return max(kandidati, key=os.path.getmtime) if kandidati else None
        except Exception:
            return None

    def _osiguraj_h264(self, vrijeme_prije):
        """Nakon skidanja provjeri je li video zapis H.264. Ako je izvor dao HEVC/AV1,
        Premiere ga na Windowsima bez dodatnih kodeka ne cita - pa transkodiramo."""
        ffprobe = ffprobe_putanja()
        ffmpeg = ffmpeg_putanja()
        if not ffprobe or not ffmpeg:
            self.root.after(0, self.ispisi, self.t("msg_codec_check_skipped"))
            return
        try:
            putanja = self._zadnji_fajl(vrijeme_prije)
            if not putanja:
                return
            rezultat = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_name", "-of", "csv=p=0", putanja],
                capture_output=True, text=True, timeout=20, **_SUBPROCESS_FLAGS
            )
            kodek = rezultat.stdout.strip().lower()
            if kodek in ("h264", "avc1", ""):
                return
            self.root.after(0, self.ispisi, self.t("msg_converting_codec").format(kodek.upper()))
            privremena = putanja + ".h264.mp4"
            subprocess.run(
                [ffmpeg, "-y", "-i", putanja, "-c:v", "libx264", "-crf", "18",
                 "-preset", "medium", "-c:a", "aac", "-b:a", "192k", privremena],
                capture_output=True, timeout=3600, **_SUBPROCESS_FLAGS
            )
            if os.path.exists(privremena) and os.path.getsize(privremena) > 0:
                os.remove(putanja)
                os.rename(privremena, putanja)
                self.root.after(0, self.ispisi, self.t("msg_codec_converted"))
            else:
                self.root.after(0, self.ispisi, self.t("msg_codec_convert_failed"))
        except Exception as err:
            self.root.after(0, lambda em=str(err): self.ispisi(self.t("msg_codec_check_failed").format(em)))

    def _zavrsi_preuzimanje(self, uspjesni, neuspjesni):
        if self.otkazano:
            self.root.after(0, self.ispisi, self.t("msg_download_cancelled"))
            self.root.after(0, lambda: self._status_light(SUBTEXT))
        elif uspjesni and not neuspjesni:
            self.root.after(0, self.ispisi, self.t("msg_all_done_log").format(self.trenutni_folder))
            self.root.after(0, lambda: messagebox.showinfo(self.t("done_naslov"), self.t("msg_all_done_text")))
            self.root.after(0, self._status_blink_uspjeh)
        elif uspjesni and neuspjesni:
            self.root.after(0, self.ispisi, self.t("msg_partial_log").format(uspjesni, neuspjesni))
            self.root.after(0, lambda u=uspjesni, n=neuspjesni: messagebox.showwarning(
                self.t("partial_naslov"), self.t("msg_partial_text").format(u, n)))
            self.root.after(0, lambda: self._status_light(DANGER))
        elif neuspjesni:
            self.root.after(0, self.ispisi, self.t("msg_all_failed_log"))
            self.root.after(0, lambda: messagebox.showerror(
                self.t("failed_naslov"), self.t("msg_all_failed_text")))
            self.root.after(0, lambda: self._status_light(DANGER))

        self.root.after(0, lambda: self.btn_download.config(state="normal", bg=ACCENT))
        self.root.after(0, self._osvjezi_stanje_nacina)
        self.root.after(0, lambda: self.btn_pause.config(state="disabled", text=self.t("gumb_pauziraj"), bg=PAUSE_BG))
        self.root.after(0, lambda: self.btn_prekini.config(state="disabled"))
        self.root.after(0, lambda: setattr(self, "aktivno_preuzimanje", False))
        self.root.after(0, lambda: setattr(self, "otkazano", False))
        self.root.after(0, self.ponisti_isjecak)
        self.root.after(0, self.azuriraj_brzinu, "")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    def _pokreni_tkinter():
        """Stvara root prozor I pokreće mainloop() u ISTOJ niti - Tcl/Tk interpreter
        je na Windowsima vezan uz COM 'apartman' niti u kojoj je stvoren, pa se root
        NE SMIJE stvoriti u jednoj niti a mainloop() zvati u drugoj (to je davalo
        'Calling Tcl from different apartment' / 'main thread is not in main loop').
        Ovoj niti ne treba biti baš OS glavna nit procesa - samo mora biti DOSLJEDNO
        ista nit za sve Tk pozive, što ovdje i jest."""
        root = tk.Tk()
        App(root)
        root.mainloop()

    if PYWEBVIEW_DOSTUPAN and EMBED_PLAYERA_DOSTUPAN:
        # 'webview.start()' mora biti pozvan iz GLAVNE niti (ograničenje same
        # biblioteke - inače puca "pywebview must be run on a main thread").
        # Zato CIJELI Tkinter (stvaranje root prozora + mainloop, zajedno) ide u
        # posebnu nit koju nam webview sam pokrene preko 'func' parametra.
        #
        # VAŽNO (v17.0.2): noviji pywebview (>= verzija koja se sad skida s PyPI-ja)
        # zahtijeva da PRIJE poziva 'webview.start()' već postoji BAREM JEDAN
        # stvoren prozor - inače odmah puca:
        #   webview.errors.WebViewException: You must create a window first
        #   before calling this function
        # Stvarni prozor za ugrađeni player stvara se tek KASNIJE, iz pozadinske
        # niti (App._pripremi_ugradjeni_webview), pošto Tkinter app uopće krene -
        # u trenutku ovog poziva još ne postoji nijedan prozor pa je pucalo odmah,
        # prije nego što bi 'func' (Tkinter) stigao i pokrenuti. Rješenje: napravimo
        # mali nevidljiv "čuvar mjesta" prozor SAMO da zadovoljimo taj uvjet -
        # stvarni, vidljivi player-prozor i dalje nastaje kako je bilo, kasnije.
        webview.create_window(
            "MisterMuscle_Init", url="about:blank", width=1, height=1, hidden=True
        )
        webview.start(func=_pokreni_tkinter, debug=False)
    else:
        _pokreni_tkinter()
