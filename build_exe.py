# -*- coding: utf-8 -*-
"""
Pravi MisterMuscle.exe iz skini_klip_gui.py, PA (ako je Inno Setup instaliran)
odmah nastavi i sam napravi i gotov instalacijski program - sve u jednom
pokretanju, bez rucnog otvaranja Inno Setup GUI-ja svaki put.

Pokretanje:   python build_exe.py
Rezultat:     dist\\MisterMuscle.exe            (goli .exe)
              Output\\MisterMuscle_Setup.exe    (pravi instalater, AKO je
                                                  Inno Setup instaliran)

Sam instalira sto mu treba (pyinstaller, pywebview, psutil) pa se ne mora nista
rucno pripremati. yt-dlp i ffmpeg se NAMJERNO ne pakiraju u .exe - aplikacija ih
skine pri prvom pokretanju i onda ih moze sama azurirati bez novog builda.
"""

import os
import sys
import shutil
import subprocess

OVDJE = os.path.dirname(os.path.abspath(__file__))
SKRIPTA = os.path.join(OVDJE, "skini_klip_gui.py")
ISS_SKRIPTA = os.path.join(OVDJE, "MisterMuscle_Setup.iss")
NAZIV = "MisterMuscle"
IKONA = os.path.join(OVDJE, "ikona.ico")  # neobavezno


def pokreni(naredba, opis):
    print(f"\n=== {opis} ===")
    print(" ".join(naredba))
    rezultat = subprocess.run(naredba)
    if rezultat.returncode != 0:
        print(f"\n!!! Neuspjeh: {opis}")
        sys.exit(rezultat.returncode)


def pronadji_iscc():
    """Trazi ISCC.exe - Inno Setup-ov CLI kompajler koji se automatski instalira
    uz obicni (GUI) Inno Setup, samo ga treba pronaci. NE oslanja se na fiksni
    broj verzije (6, 7...) jer Inno Setup redovito izlazi u novim verzijama -
    umjesto toga sve pretrage rade preko uzorka "Inno Setup*". Redom
    provjerava: 1) PATH, 2) Windows registry (najpouzdanije - Inno Setup
    ondje upise TOCNO gdje je instaliran, bez obzira je li to bila sistemska
    ili "samo za mene" instalacija bez admin prava), 3) direktno pretrazi
    uobicajene foldere (Program Files, Program Files (x86), LOCALAPPDATA) za
    bilo koji "Inno Setup*" podfolder. Vraca None ako ga nema nigdje - u tom
    slucaju se setup jednostavno ne pravi automatski, ne pucamo cijeli build."""
    put = shutil.which("ISCC") or shutil.which("ISCC.exe")
    if put:
        return put

    if os.name == "nt":
        try:
            import winreg
            for koren in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                for podkljuc in (
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                ):
                    try:
                        with winreg.OpenKey(koren, podkljuc) as uninstall_kljuc:
                            i = 0
                            while True:
                                try:
                                    ime = winreg.EnumKey(uninstall_kljuc, i)
                                except OSError:
                                    break
                                i += 1
                                if not ime.startswith("Inno Setup"):
                                    continue
                                try:
                                    with winreg.OpenKey(uninstall_kljuc, ime) as stavka:
                                        instalacija, _ = winreg.QueryValueEx(stavka, "InstallLocation")
                                        kandidat = os.path.join(instalacija, "ISCC.exe")
                                        if os.path.isfile(kandidat):
                                            return kandidat
                                except OSError:
                                    continue
                    except OSError:
                        continue
        except ImportError:
            pass

    for baza in (
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
    ):
        try:
            if not os.path.isdir(baza):
                continue
            for stavka in os.listdir(baza):
                if stavka.lower().startswith("inno setup"):
                    kandidat = os.path.join(baza, stavka, "ISCC.exe")
                    if os.path.isfile(kandidat):
                        return kandidat
        except OSError:
            continue
    return None


def main():
    # PyInstaller odbija raditi ako je trenutni radni direktorij C:\Windows\
    # System32 (sigurnosna provjera - dogodi se npr. kad se cmd otvori preko
    # "Run as administrator" iz Start menija, koji tamo pocinje po defaultu).
    # Da build radi bez obzira odakle je "python build_exe.py" pokrenut,
    # eksplicitno predjemo u folder GDJE JE OVA SKRIPTA prije ičega drugog.
    os.chdir(OVDJE)

    if not os.path.isfile(SKRIPTA):
        print(f"Ne nalazim {SKRIPTA}")
        sys.exit(1)

    alati_za_instalirati = ["pyinstaller", "pywebview", "psutil"]
    if os.name == "nt":
        # pywin32 postoji samo na Windowsima; treba nam za ugradnju playera
        # (SetParent) unutar glavnog prozora umjesto zasebnog pop-up prozora.
        alati_za_instalirati.append("pywin32")
    pokreni([sys.executable, "-m", "pip", "install", "--upgrade",
             *alati_za_instalirati], "Instaliram alate za build")

    for folder in ("build", "dist"):
        put = os.path.join(OVDJE, folder)
        if os.path.isdir(put):
            shutil.rmtree(put, ignore_errors=True)

    argumenti = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",           # sve u jedan .exe
        "--windowed",          # bez crnog konzolnog prozora iza GUI-ja
        "--name", NAZIV,
        "--collect-all", "webview",   # pywebview vuce podatke koje PyInstaller sam ne nade
        "--hidden-import", "psutil",
        "--distpath", os.path.join(OVDJE, "dist"),
        "--workpath", os.path.join(OVDJE, "build"),
        "--specpath", os.path.join(OVDJE, "build"),
    ]
    if os.path.isfile(IKONA):
        argumenti += ["--icon", IKONA]
        # Ovo ugradjuje ikona.ico i KAO RESURS unutar .exe-a (ne samo kao
        # "vanjsku" ikonu .exe fajla u Exploreru) - tako je skini_klip_gui.py
        # moze pri pokretanju uzeti preko sys._MEIPASS i postaviti kao pravu
        # ikonu prozora (naslovna traka, taskbar dok app radi), ne samo kao
        # ikonu .exe fajla u Exploreru/prečicama.
        razdjelnik = ";" if os.name == "nt" else ":"
        argumenti += ["--add-data", f"{IKONA}{razdjelnik}."]
    if os.name == "nt":
        # win32timezone je cest "skriveni" ovisnik pywin32 paketa - bez njega
        # zna raditi na razvojnom racunalu, a puknuti tek na tudem (gdje
        # pywin32 nikad nije rucno "post-install" konfiguriran).
        argumenti += ["--hidden-import", "win32gui", "--hidden-import", "win32con",
                      "--hidden-import", "win32timezone"]
    argumenti.append(SKRIPTA)

    pokreni(argumenti, "Gradim .exe (traje 1-3 minute)")

    gotov = os.path.join(OVDJE, "dist", NAZIV + (".exe" if os.name == "nt" else ""))
    print("\n" + "=" * 60)
    if not os.path.isfile(gotov):
        print("Build je zavrsio, ali .exe nije na ocekivanom mjestu — pogledaj ispis iznad.")
        print("=" * 60)
        return

    mb = os.path.getsize(gotov) / 1024 / 1024
    print(f"GOTOVO:  {gotov}   ({mb:.1f} MB)")
    print("=" * 60)

    # ---- automatski nastavi i napravi pravi instalacijski program (Inno Setup) ----
    if not os.path.isfile(ISS_SKRIPTA):
        print(f"\n(Napomena: {os.path.basename(ISS_SKRIPTA)} nije nadjena pored ove skripte - "
              "preskačem izradu setupa, gotov je samo goli .exe.)")
        return
    if os.name != "nt":
        print("\n(Napomena: izrada .exe instalatera moguca je samo na Windowsu - "
              "preskačem taj korak.)")
        return

    iscc = pronadji_iscc()
    if not iscc:
        print("\n" + "-" * 60)
        print("Napomena: Inno Setup (ISCC.exe) nije pronađen na ovom računalu, pa")
        print("setup NIJE napravljen automatski. Ili:")
        print("  a) instaliraj Inno Setup (besplatan) s https://jrsoftware.org/isdl.php")
        print("     pa ponovno pokreni 'python build_exe.py' - sljedeći put će sve")
        print("     ići u jednom potezu, bez ičega ručno;")
        print(f"  b) ili sad ručno otvori {os.path.basename(ISS_SKRIPTA)} u Inno Setupu i pritisni F9.")
        print("-" * 60)
        return

    pokreni([iscc, ISS_SKRIPTA], "Gradim instalacijski program (Inno Setup)")

    setup_gotov = os.path.join(OVDJE, "Output", "MisterMuscle_Setup.exe")
    print("\n" + "=" * 60)
    if os.path.isfile(setup_gotov):
        mb2 = os.path.getsize(setup_gotov) / 1024 / 1024
        print(f"GOTOV I SETUP:  {setup_gotov}   ({mb2:.1f} MB)")
        print("To je JEDINA datoteka koju sad šalješ/dijeliš korisnicima.")
    else:
        print("Inno Setup je završio, ali Output\\MisterMuscle_Setup.exe nije na očekivanom mjestu.")
    print("=" * 60)


if __name__ == "__main__":
    # Ako se ova skripta pokrene dvoklikom (umjesto iz vec otvorenog cmd-a),
    # Windows zatvori prozor CIM skripta zavrsi - pa se ni ispis ni eventualna
    # greska ne stignu procitati. "input()" na kraju drzi prozor otvoren dok
    # korisnik sam ne pritisne Enter, bez obzira zavrsi li build uspjesno,
    # neuspjesno (sys.exit u pokreni()) ili s neocekivanom greskom.
    try:
        main()
    except SystemExit:
        pass
    except Exception as err:
        print(f"\n!!! Neočekivana greška: {err}")
    input("\nPritisni Enter za izlaz...")
