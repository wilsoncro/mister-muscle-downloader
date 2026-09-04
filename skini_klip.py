import os
import re
import sys
import json
import functools
import http.server
import socketserver
import tempfile
import subprocess
import threading
import multiprocessing
import urllib.request
import importlib.metadata
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

try:
    import yt_dlp
    from yt_dlp.utils import download_range_func
except ImportError:
    print("Nedostaje biblioteka 'yt-dlp'. Instaliraj je naredbom:")
    print("    pip install yt-dlp")
    sys.exit(1)

try:
    import webview
    PYWEBVIEW_DOSTUPAN = True
except ImportError:
    PYWEBVIEW_DOSTUPAN = False


IZLAZNI_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preuzeto")

# --- MODERNI DIZAJN (Dark Cyber-Glass) ---
BG = "#09090d"
CARD = "#13131a"
ACCENT = "#8a2be2"
ACCENT_HOVER = "#9d4edd"
TEXT = "#f1f1f6"
SUBTEXT = "#9a9aa8"
LOG_BG = "#050507"
LOG_TEXT = "#00f5d4"
BORDER = "#20202c"
TROUGH = "#1c1c26"
PAUSE_BG = "#1c1c26"
SUCCESS = "#00f5d4"


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
    else:
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
    """Izvlaci YouTube video ID iz linka - bez mrežnog poziva, cisti regex."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


class PlayerAPI:
    def __init__(self, queue_sanjac):
        self.queue_sanjac = queue_sanjac

    def oznaci_pocetak(self, sekunde):
        self.queue_sanjac.put(("od", sekunde))

    def oznaci_kraj(self, sekunde):
        self.queue_sanjac.put(("do", sekunde))

    def skini_shorts_iz_player(self, od_vr, do_vr):
        self.queue_sanjac.put(("skini_short", (od_vr, do_vr)))


def _player_html(video_id):
    video_id_json = json.dumps(video_id)
    return f"""
    <html>
    <head>
    <style>
      body {{ margin:0; background:#09090d; font-family: Segoe UI, sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; overflow:hidden; color:#f1f1f6; user-select:none; padding: 10px; box-sizing: border-box; }}
      #omot {{ display:flex; flex-direction:column; align-items:center; width:100%; max-width:980px; }}
      #player-wrap {{ width:100%; max-height:360px; aspect-ratio: 16/9; background:#000; border-radius:10px; overflow:hidden; border: 1px solid #20202c; }}
      #player {{ width:100%; height:100%; }}
      #timeline-container {{
        width: 100%; height: 34px; background: #13131a; border-radius: 8px;
        margin-top: 10px; position: relative; cursor: pointer;
        border: 1px solid #20202c;
      }}
      #timeline-selection {{
        position: absolute; top: 0; bottom: 0; background: rgba(138, 43, 226, 0.35);
        border-left: 2px solid #8a2be2; border-right: 2px solid #8a2be2;
        pointer-events: none; display: none;
      }}
      #timeline-playhead {{
        position: absolute; top: 0; bottom: 0; width: 3px; background: #00f5d4; left: 0%;
        pointer-events: none; box-shadow: 0 0 10px #00f5d4; z-index: 3;
      }}
      .info-red {{ display:flex; justify-content:space-between; width:100%; margin-top:8px; font-size:12px; color:#9a9aa8; }}
      .info-red span {{ font-weight: 600; color: #f1f1f6; }}
      .kontrole {{ margin-top:10px; display:flex; align-items:center; gap:6px; width:100%; justify-content:center; flex-wrap:wrap; }}
      button {{
        background:#8a2be2; color:white; border:none; border-radius:6px;
        padding:8px 14px; font-size:12px; font-weight:600; cursor:pointer;
        transition: background 0.2s;
      }}
      button:hover {{ background:#9d4edd; }}
      button.secondary {{ background:#1c1c26; border: 1px solid #2e2e3d; }}
      button.secondary:hover {{ background:#282836; }}

      .shorts-panel {{
        margin-top: 12px; background: #13131a; border: 1px solid #20202c; border-radius: 8px;
        padding: 10px 14px; width: 100%; box-sizing: border-box; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;
      }}
      .shorts-panel label {{ font-size: 12px; font-weight: bold; color: #9a9aa8; }}
      .shorts-panel input {{
        background: #0f0f14; border: 1px solid #20202c; color: #f1f1f6; border-radius: 4px; padding: 5px 8px; width: 80px; font-size: 12px; text-align: center; outline: none;
      }}
      .btn-download-short {{ background: #00f5d4; color: #09090d; font-weight: bold; }}
      .btn-download-short:hover {{ background: #00c4a7; }}
      #status-bar {{ margin-top: 6px; font-size: 12px; font-weight: 600; color: #00f5d4; text-align: center; }}
    </style>
    </head>
    <body>
    <div id="omot">
      <div id="player-wrap"><div id="player"></div></div>
      <div id="timeline-container" onclick="skociNaPoziciju(event)">
        <div id="timeline-selection"></div>
        <div id="timeline-playhead"></div>
      </div>
      <div class="info-red">
        <div>Trenutno: <span id="vrijeme-trenutno">0:00</span></div>
        <div id="trajanje-isječka-info" style="color:#00f5d4; font-weight:bold;">Isječak: Nije označeno</div>
        <div>Ukupno: <span id="vrijeme-ukupno">0:00</span></div>
      </div>
      <div class="kontrole">
        <button class="secondary" onclick="pomakniZa(-5)">⏪ -5s</button>
        <button class="secondary" onclick="togglePlay()">⏯ Play / Pauza</button>
        <button class="secondary" onclick="pomakniZa(5)">⏩ +5s</button>
        <button onclick="oznaciPocetak()">📍 Postavi OD</button>
        <button onclick="oznaciKraj()">📍 Postavi DO</button>
      </div>

      <div class="shorts-panel">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="color:#f1f1f6; font-size:12px; font-weight:bold;">🎬 Skini Shorts:</span>
          <label>Od:</label>
          <input type="text" id="input-od" placeholder="0:00">
          <label>Do:</label>
          <input type="text" id="input-do" placeholder="0:00">
        </div>
        <div>
          <button class="btn-download-short" onclick="pokreniSkidanjeShortsa()">⬇ Skini Short</button>
        </div>
      </div>

      <div id="status-bar">Učitavam player...</div>
    </div>
    <script src="https://www.youtube.com/iframe_api"></script>
    <script>
      var player;
      var trajanjeVid = 0;
      var playhead = document.getElementById('timeline-playhead');
      var selectionBox = document.getElementById('timeline-selection');
      var pocSec = null, krajSec = null;
      var seekTimeout = null;
      var spreman = false;

      function formatiraj(t) {{
        if (isNaN(t)) return "0:00";
        t = Math.floor(t);
        var m = Math.floor(t/60), s = t%60;
        return m + ":" + (s<10 ? "0"+s : s);
      }}

      function onYouTubeIframeAPIReady() {{
        player = new YT.Player('player', {{
          videoId: {video_id_json},
          playerVars: {{ playsinline: 1, controls: 0, disablekb: 1, modestbranding: 1, rel: 0, origin: window.location.origin }},
          events: {{
            'onReady': onPlayerReady,
            'onError': onPlayerError
          }}
        }});
      }}

      function onPlayerReady(e) {{
        spreman = true;
        trajanjeVid = player.getDuration();
        document.getElementById('vrijeme-ukupno').innerText = formatiraj(trajanjeVid);
        document.getElementById('status-bar').innerText = "Spremno.";
        setInterval(azurirajPlayhead, 250);
      }}

      function onPlayerError(e) {{
        var poruke = {{
          2: 'Neispravan video ID',
          5: 'Greška HTML5 playera',
          100: 'Video ne postoji ili je uklonjen',
          101: 'Vlasnik je onemogućio embed prikaz ovog videa',
          150: 'Vlasnik je onemogućio embed prikaz ovog videa'
        }};
        document.getElementById('status-bar').innerText =
          '❌ ' + (poruke[e.data] || ('Greška kod ' + e.data));
      }}

      function azurirajPlayhead() {{
        if (!spreman || !trajanjeVid) return;
        var t = player.getCurrentTime();
        playhead.style.left = (t / trajanjeVid) * 100 + '%';
        document.getElementById('vrijeme-trenutno').innerText = formatiraj(t);
      }}

      function skociNaPoziciju(e) {{
        if (!spreman || !trajanjeVid) {{
          document.getElementById('status-bar').innerText = '⏳ Video se još učitava, pričekaj trenutak...';
          return;
        }}
        var rect = e.currentTarget.getBoundingClientRect();
        var klikPozicija = (e.clientX - rect.left) / rect.width;
        klikPozicija = Math.min(Math.max(klikPozicija, 0), 1);
        var novaPozicija = klikPozicija * trajanjeVid;

        playhead.style.left = (klikPozicija * 100) + '%';
        document.getElementById('vrijeme-trenutno').innerText = formatiraj(novaPozicija);

        if (seekTimeout) clearTimeout(seekTimeout);
        seekTimeout = setTimeout(function() {{
            player.seekTo(novaPozicija, true);
        }}, 120);
      }}

      function pomakniZa(s) {{
        if (!spreman) return;
        player.seekTo(Math.max(0, player.getCurrentTime() + s), true);
      }}

      function togglePlay() {{
        if (!spreman) return;
        var stanje = player.getPlayerState();
        if (stanje === 1) player.pauseVideo(); else player.playVideo();
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
          document.getElementById('trajanje-isječka-info').innerText = "Isječak: " + Math.round(krajSec - pocSec) + "s";
        }}
      }}

      function pokreniSkidanjeShortsa() {{
        var odVal = document.getElementById('input-od').value;
        var doVal = document.getElementById('input-do').value;
        window.pywebview.api.skini_shorts_iz_player(odVal, doVal);
        document.getElementById('status-bar').innerText = "Preuzimanje shortsa pokrenuto...";
      }}
    </script>
    </body>
    </html>
    """


def pokreni_lokalni_server(temp_dir):
    """Pokrece mali HTTP server na 127.0.0.1 - potreban da YouTube iframe API radi ispravno
    (embed s file:// ili html= porijeklom cesto ne radi zbog YouTubeovih origin provjera)."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=temp_dir)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return port


def pokreni_webview_proces(preview_url, queue_sanjac):
    api = PlayerAPI(queue_sanjac)
    webview.create_window("Mister Muscle — Timeline Player", url=preview_url, js_api=api, width=1020, height=640)
    webview.start()


class App:
    def __init__(self, root):
        self.root = root
        root.title("Mister Muscle — Podcast Short Clipper")
        root.geometry("600x670")
        root.resizable(False, False)
        root.configure(bg=BG)

        self.pause_event = threading.Event()
        self.pause_event.set()
        self.aktivno_preuzimanje = False
        self.player_proces = None
        self.queue_sanjac = multiprocessing.Queue()
        self.trenutni_folder = IZLAZNI_FOLDER

        self.temp_dir = tempfile.mkdtemp(prefix="mister_muscle_")
        self.http_port = pokreni_lokalni_server(self.temp_dir) if PYWEBVIEW_DOSTUPAN else None
        
        self.od_sek = None
        self.do_sek = None

        menubar = tk.Menu(root, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT, relief="flat")
        help_menu = tk.Menu(menubar, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
        help_menu.add_command(label="Provjeri ažuriranja (Check for Updates)", command=self.provjeri_azuriranja)
        menubar.add_cascade(label="Meni", menu=help_menu)
        root.config(menu=menubar)

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=24, pady=(14, 4))
        tk.Label(header, text="Mister Muscle Shorts", font=("Segoe UI Semibold", 18), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(header, text="Precizno rezanje podcast isječaka u Premiere-kompatibilnom formatu", font=("Segoe UI", 9), bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(2, 0))

        card = tk.Frame(root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=24, pady=(10, 0))

        top_row = tk.Frame(card, bg=CARD)
        top_row.pack(fill="x", padx=16, pady=(14, 2))
        tk.Label(top_row, text="PODCAST LINK", font=("Segoe UI", 8, "bold"), bg=CARD, fg=SUBTEXT).pack(side="left")

        self.btn_player = tk.Button(top_row, text="🎬 Otvori Timeline Player", font=("Segoe UI", 8, "bold"), bg=PAUSE_BG, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT, relief="flat", bd=0, cursor="hand2", padx=10, pady=4, command=self.otvori_player)
        self.btn_player.pack(side="right")

        self.text_links = tk.Text(card, width=64, height=3, font=("Segoe UI", 10), bg="#0f0f14", fg=TEXT, insertbackground=TEXT, relief="flat", highlightbackground=BORDER, highlightthickness=1, wrap="word")
        self.text_links.pack(padx=16, pady=(6, 12), fill="x")
        self._placeholder = "Zalijepi link podcasta ovdje..."
        self._postavi_placeholder()
        self.text_links.bind("<FocusIn>", self._obrisi_placeholder)
        self.text_links.bind("<FocusOut>", self._vrati_placeholder)

        self.context_menu = tk.Menu(root, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
        self.context_menu.add_command(label="Zalijepi (Paste)", command=self.zalijepi_tekst)
        self.text_links.bind("<Button-3>", self.prikazi_desni_klik)

        folder_row = tk.Frame(card, bg=CARD)
        folder_row.pack(fill="x", padx=16, pady=(0, 16))
        tk.Label(folder_row, text="Spremi u folder:", font=("Segoe UI", 8, "bold"), bg=CARD, fg=SUBTEXT).pack(anchor="w", pady=(0, 2))
        
        f_sub = tk.Frame(folder_row, bg=CARD)
        f_sub.pack(fill="x")

        self.lbl_folder = tk.Label(f_sub, text=self.trenutni_folder, font=("Segoe UI", 8), bg="#0f0f14", fg=TEXT, anchor="w", padx=8, highlightbackground=BORDER, highlightthickness=1)
        self.lbl_folder.pack(side="left", fill="x", expand=True, ipady=5)

        self.btn_browse = tk.Button(f_sub, text="📂 Odaberi...", font=("Segoe UI", 8, "bold"), bg=PAUSE_BG, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT, relief="flat", bd=0, cursor="hand2", padx=10, command=self.odaberi_folder)
        self.btn_browse.pack(side="left", padx=(8, 0))

        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(fill="x", padx=24, pady=14)

        self.btn_download = tk.Button(btn_frame, text="⬇ Skini video (Premiere Ready)", font=("Segoe UI", 11, "bold"), bg=ACCENT, fg="white", activebackground=ACCENT_HOVER, activeforeground="white", relief="flat", bd=0, height=2, cursor="hand2", command=self.pokreni_preuzimanje)
        self.btn_download.pack(side="left", fill="x", expand=True)

        self.btn_pause = tk.Button(btn_frame, text="⏸ Pauziraj", font=("Segoe UI", 10, "bold"), bg=PAUSE_BG, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT, relief="flat", bd=0, height=2, width=10, cursor="hand2", state="disabled", command=self.toggle_pauza)
        self.btn_pause.pack(side="left", padx=(8, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cyber.Horizontal.TProgressbar", troughcolor=TROUGH, background=SUCCESS, bordercolor=TROUGH, thickness=8)
        self.progress = ttk.Progressbar(root, style="Cyber.Horizontal.TProgressbar", orient="horizontal", mode="determinate", maximum=100, value=0)
        self.progress.pack(fill="x", padx=24, pady=(0, 2))

        self.lbl_postotak = tk.Label(root, text="0%", font=("Segoe UI", 9, "bold"), bg=BG, fg=SUCCESS)
        self.lbl_postotak.pack(anchor="e", padx=24, pady=(0, 6))

        log_frame = tk.Frame(root, bg=LOG_BG, highlightbackground=BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True, padx=24, pady=(4, 20))

        self.log = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), state="disabled", bg=LOG_BG, fg=LOG_TEXT, relief="flat", highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        self.provjeri_queue()

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

    def odaberi_folder(self):
        odabrani_dir = filedialog.askdirectory(initialdir=self.trenutni_folder)
        if odabrani_dir:
            self.trenutni_folder = odabrani_dir
            self.lbl_folder.config(text=self.trenutni_folder)
            self.ispisi(f"📁 Folder: {self.trenutni_folder}")

    def ispisi(self, poruka):
        self.log.configure(state="normal")
        self.log.insert("end", poruka + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def azuriraj_progress(self, val):
        self.progress["value"] = val
        self.lbl_postotak.config(text=f"{val:.0f}%")

    def provjeri_queue(self):
        while not self.queue_sanjac.empty():
            try:
                podatak = self.queue_sanjac.get_nowait()
                if isinstance(podatak, tuple) and len(podatak) == 2:
                    tip, vrijednost = podatak
                    if tip == "od":
                        self.od_sek = parse_vrijeme(vrijednost)
                        self.ispisi(f"📍 Postavljen početak: {formatiraj_trajanje(self.od_sek)}")
                    elif tip == "do":
                        self.do_sek = parse_vrijeme(vrijednost)
                        self.ispisi(f"📍 Postavljen kraj: {formatiraj_trajanje(self.do_sek)}")
                    elif tip == "skini_short":
                        od_vr, do_vr = vrijednost
                        self.od_sek = parse_vrijeme(od_vr)
                        self.do_sek = parse_vrijeme(do_vr)
                        self.pokreni_preuzimanje()
            except Exception:
                break
        self.root.after(100, self.provjeri_queue)

    def provjeri_azuriranja(self):
        self.ispisi("🔄 Provjeravam novije verzije paketa (yt-dlp)...")
        threading.Thread(target=self._izvedi_provjeru_updatea, daemon=True).start()

    def _izvedi_provjeru_updatea(self):
        try:
            trenutni_yt_dlp = importlib.metadata.version("yt-dlp")
            
            req = urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=5)
            data = json.loads(req.read().decode())
            najnoviji_yt_dlp = data["info"]["version"]

            poruka_info = f"Trenutna verzija yt-dlp: {trenutni_yt_dlp}\nNajnovija na PyPI: {najnoviji_yt_dlp}"
            
            if trenutni_yt_dlp != najnoviji_yt_dlp:
                self.root.after(0, lambda nv=najnoviji_yt_dlp: self._upit_za_nadogradnju(nv))
            else:
                self.root.after(0, lambda pi=poruka_info: messagebox.showinfo("Ažuriranja", f"Sve je već najnovije!\n\n{pi}"))
                self.root.after(0, lambda: self.ispisi("✅ Sustav je potpuno ažuran."))
        except Exception as err:
            err_msg = str(err)
            self.root.after(0, lambda em=err_msg: messagebox.showerror("Greška", f"Ne mogu provjeriti ažuriranja: {em}"))

    def _upit_za_nadogradnju(self, nova_verzija):
        odgovor = messagebox.askyesno("Dostupno ažuriranje", f"Pronađena je nova verzija yt-dlp ({nova_verzija}).\nŽeliš li pokrenuti automatsku nadogradnju?")
        if odgovor:
            self.ispisi("⏳ Nadograđujem yt-dlp...")
            threading.Thread(target=self._pokreni_pip_upgrade, daemon=True).start()

    def _pokreni_pip_upgrade(self):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
            self.root.after(0, lambda: self.ispisi("🎉 yt-dlp je uspješno nadograđen! Ponovno pokreni aplikaciju."))
            self.root.after(0, lambda: messagebox.showinfo("Uspjeh", "Ažuriranje je završeno! Molimo ponovno pokrenite aplikaciju."))
        except Exception as err:
            err_msg = str(err)
            self.root.after(0, lambda em=err_msg: self.ispisi(f"❌ Greška kod nadogradnje: {em}"))
            self.root.after(0, lambda em=err_msg: messagebox.showerror("Greška", f"Nadogradnja nije uspjela: {em}"))

    def otvori_player(self):
        if not PYWEBVIEW_DOSTUPAN:
            messagebox.showerror("Greška", "Biblioteka 'pywebview' nije instalirana.")
            return
        url = self._prvi_link()
        if not url:
            messagebox.showwarning("Upozorenje", "Prvo zalijepi link.")
            return

        video_id = izvuci_video_id(url)
        if not video_id:
            messagebox.showerror("Greška", "Ne prepoznajem YouTube video ID iz tog linka.")
            return

        if self.player_proces and self.player_proces.is_alive():
            try:
                self.player_proces.terminate()
            except Exception:
                pass

        self.ispisi("⏳ Otvaram player...")
        threading.Thread(target=self._pripremi_i_pokreni, args=(video_id,), daemon=True).start()

    def _pripremi_i_pokreni(self, video_id):
        html = _player_html(video_id)
        naziv_fajla = f"preview_{video_id}.html"
        putanja = os.path.join(self.temp_dir, naziv_fajla)
        try:
            with open(putanja, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as err_z:
            self.root.after(0, lambda em=str(err_z): messagebox.showerror("Greška", f"Ne mogu pripremiti player: {em}"))
            return

        preview_url = f"http://127.0.0.1:{self.http_port}/{naziv_fajla}"
        self.player_proces = multiprocessing.Process(target=pokreni_webview_proces, args=(preview_url, self.queue_sanjac))
        self.player_proces.start()

    def toggle_pauza(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.btn_pause.config(text="▶ Nastavi", bg=ACCENT)
        else:
            self.pause_event.set()
            self.btn_pause.config(text="⏸ Pauziraj", bg=PAUSE_BG)

    def pokreni_preuzimanje(self):
        if self.aktivno_preuzimanje:
            return
        sirovi = self.text_links.get("1.0", "end").strip()
        if not sirovi or sirovi == self._placeholder:
            messagebox.showwarning("Greška", "Nema linka.")
            return
        linkovi = [l.strip() for l in sirovi.splitlines() if l.strip()]

        od_sek = self.od_sek
        do_sek = self.do_sek

        self.aktivno_preuzimanje = True
        self.pause_event.set()
        self.btn_download.config(state="disabled", text="Skidam...")
        self.btn_pause.config(state="normal")
        self.azuriraj_progress(0)

        threading.Thread(target=self.skini_sve, args=(linkovi, od_sek, do_sek), daemon=True).start()

    def skini_sve(self, linkovi, od_sek, do_sek):
        napravi_folder(self.trenutni_folder)

        def progress_hook(d):
            self.pause_event.wait()
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                
                if total and total > 0:
                    procent = (downloaded / total) * 100
                    self.root.after(0, self.azuriraj_progress, min(procent, 100.0))
                else:
                    p_str = d.get("_percent_str", "0%").strip().replace("%", "")
                    try:
                        procent = float(p_str)
                        self.root.after(0, self.azuriraj_progress, min(procent, 100.0))
                    except ValueError:
                        pass
                        
            elif d["status"] == "finished":
                self.root.after(0, self.azuriraj_progress, 100)
                self.root.after(0, self.ispisi, "✅ Obrada i spajanje isječka...")

        ydl_opts = {
            "format": "bestvideo[vcodec^=avc1]+bestaudio/bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(self.trenutni_folder, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "noplaylist": True
        }

        if od_sek is not None or do_sek is not None:
            ydl_opts["download_ranges"] = download_range_func(None, [(od_sek or 0, do_sek or float("inf"))])

        for i, url in enumerate(linkovi, start=1):
            self.root.after(0, self.ispisi, f"\n[{i}/{len(linkovi)}] {url}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as err_d:
                err_msg = str(err_d)
                self.root.after(0, lambda em=err_msg: self.ispisi(f"❌ Greška: {em}"))

        self.root.after(0, self.ispisi, f"\n🎉 Gotovo! Folder: {self.trenutni_folder}")
        self.root.after(0, lambda: self.btn_download.config(state="normal", text="⬇ Skini video (Premiere Ready)"))
        self.root.after(0, lambda: self.btn_pause.config(state="disabled"))
        self.root.after(0, lambda: setattr(self, "aktivno_preuzimanje", False))
        self.root.after(0, lambda: messagebox.showinfo("Gotovo", "Preuzeto u formatu spremnom za Premiere!"))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = App(root)
    root.mainloop()