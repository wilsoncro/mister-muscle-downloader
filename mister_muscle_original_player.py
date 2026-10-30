# Original timeline player extracted without modifying its HTML, JS, timeline or controls.
# Source: user's original Mister Muscle Downloader 4.10.
import json
# Original player HTML and JavaScript retained; palette adapted to the Qt shell.
CARD="#151a31"
ACCENT="#7659ef"
ACCENT_HOVER="#8c70ff"
TEXT="#f7f8ff"
SUBTEXT="#949dbb"
BORDER="#2b3153"
SUCCESS="#55dcb1"
DANGER="#ff9b9b"
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
        "back5_title": "Natrag 5 sekundi",
        "playpause_title": "Reprodukcija / Pauza",
        "playpause_text": "⏯ Reprodukcija/Pauza",
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
        "add_another_hint": "Dodaj još jedan isječak (možeš ga povući/rastegnuti nakon)",
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
        "add_another_hint": "Add another clip (you can drag/resize it afterward)",
        "drag_hint": "Drag on the timeline to mark a clip, or click to seek",
    },
}

def _player_html(platform, video_id=None, video_src=None, jezik="en"):
    PT = _PLAYER_PRIJEVODI.get(jezik, _PLAYER_PRIJEVODI["en"])
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
      function pozovi_lokalni_pregled_fallback() {{
        // Zajednicka, sigurna verzija poziva prema Pythonu - probamo VISE
        // puta ako 'window.pywebview.api' jos nije spreman (pywebview most
        // izmedju JS i Pythona zna zatrebati koji trenutak nakon ucitavanja
        // stranice da se uspostavi - nasi automatski (bez klika korisnika)
        // pokusaji mogu stici PRIJE toga), i GRESKU STVARNO PRIKAZEMO u
        // statusnoj traci playera umjesto da nestane bez traga ako poziv
        // ipak ne uspije.
        var pokusaji = 0;
        function pokusaj() {{
          pokusaji++;
          try {{
            if (window.pywebview && window.pywebview.api && window.pywebview.api.zatrazi_lokalni_pregled) {{
              window.pywebview.api.zatrazi_lokalni_pregled();
            }} else if (pokusaji < 20) {{
              setTimeout(pokusaj, 250);
            }} else {{
              document.getElementById('status-bar').innerText =
                '❌ pywebview API nikad nije postao dostupan (window.pywebview.api ne postoji).';
            }}
          }} catch (err) {{
            document.getElementById('status-bar').innerText =
              '❌ Greška pri pozivu fallbacka: ' + (err && err.message ? err.message : err);
          }}
        }}
        pokusaj();
      }}

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

      // SIGURNOSNA MREZA (razina 1, sira od one u onPlayerReady): ako se
      // YouTube-ova iframe_api skripta uopce ne ucita/pokrene ispravno (npr.
      // mrezni/firewall problem specifican za WebView2 kontekst, ili YouTube
      // blokira bas ovaj tip ugradnje), 'onYouTubeIframeAPIReady' se NIKAD
      // ne pozove - sto znaci da ni 'player' varijabla nikad ne postane
      // pravi objekt, pa NI onPlayerReady NI onPlayerError nikad nemaju
      // priliku ni pokusati (oba su vezana UZ player objekt koji ovdje
      // uopce ne postoji). Bez ove provjere, ostali bismo zaglavljeni
      // zauvijek na golom "Player ugraden i spreman" bez ikakvog daljnjeg
      // pomaka - ni greske, ni videa, ni fallbacka.
      setTimeout(function() {{
        if (!player && !fallbackPokrenut) {{
          fallbackPokrenut = true;
          document.getElementById('status-bar').innerText = '{PT["embed_fallback_status"]}';
          pozovi_lokalni_pregled_fallback();
        }}
      }}, 8000);

      function onPlayerReady(e) {{
        spreman = true;
        trajanjeVid = player.getDuration();
        document.getElementById('vrijeme-ukupno').innerText = formatiraj(trajanjeVid);
        document.getElementById('status-bar').innerText = "{PT['spremno']}";
        setInterval(azurirajPlayhead, 250);
        // v7.12: do not autoplay when a link is pasted. The user starts playback manually.
        // YouTube may legitimately report UNSTARTED (-1) until the first click.
        try {{ player.cueVideoById({video_id_json}); }} catch (err) {{}}

        // SIGURNOSNA MREZA: YouTube zna prikazati SVOJU "Video unavailable"
        // poruku UNUTAR iframea a da onPlayerError uopce ne pozove nas kod
        // (ne za sve razloge nedostupnosti postoji sluzbeni error-kod koji
        // YouTube-ova IFrame API stvarno posalje) - u tom slucaju bi ostali
        // zaglavljeni zauvijek, bez ikakvog fallbacka. Zato provjerimo SAMI,
        // par sekundi nakon "ready": ako trajanje nije ispravno dohvaceno
        // (0 ili NaN) ili se stanje playera nikad nije pomaknulo dalje od
        // "unstarted", tretiramo to kao da je embed propao i sami pokrenemo
        // isti fallback (lokalni pregled) koji bi inace pokrenuo onPlayerError.
        setTimeout(function() {{
          if (fallbackPokrenut) return;
          var trajanjeOk = trajanjeVid && !isNaN(trajanjeVid) && trajanjeVid > 0;
          var stanje = player.getPlayerState();
          if (!trajanjeOk) {{
            fallbackPokrenut = true;
            document.getElementById('status-bar').innerText = '{PT["embed_fallback_status"]}';
            pozovi_lokalni_pregled_fallback();
          }}
        }}, 6000);
      }}

      function onPlayerError(e) {{
        var poruke = {{
          2: '{PT["err_invalid_id"]}',
          5: '{PT["err_html5"]}',
          100: '{PT["err_removed"]}',
          101: '{PT["err_embed_disabled"]}',
          150: '{PT["err_embed_disabled"]}'
        }};
        if (!fallbackPokrenut) {{
          // v2.2: fallback se sad pokusa za BILO KOJI kod greske, ne samo
          // 101/150 - neki razlozi nedostupnosti YouTube prijavi drugim
          // kodovima (ili uopce ne pozove ovaj handler, vidi timeout gore u
          // onPlayerReady), pa je siri pokusaj pouzdaniji nego uski popis.
          fallbackPokrenut = true;
          document.getElementById('status-bar').innerText = '{PT["embed_fallback_status"]}';
          pozovi_lokalni_pregled_fallback();
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
          radial-gradient(circle at 85% 100%, rgba(156,45,79,0.26), transparent 55%),
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
        flex-shrink: 0;
        /* BEZ ovoga, kad ukupna visina fali (npr. vertikalan TikTok/Instagram
           video u #player-wrap trazi vise prostora), flexbox po defaultu
           STISKA i ovaj element ispod njegove zadane 38px visine da nadje
           mjesta - traka onda ispadne kao tanka crta umjesto prave trake za
           rezanje. flex-shrink:0 to sprijeci - ova traka ZADRZAVA 38px bez
           obzira sto se desava s ostatkom rasporeda. */
      }}
      #timeline-container:hover {{ border-color: {ACCENT}; }}
      #timeline-selection {{
        position: absolute; top: 0; bottom: 0; background: rgba(156, 45, 79, 0.32);
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
      #dodaj-plus {{
        position: absolute; top: 50%; right: -26px; transform: translateY(-50%);
        width: 20px; height: 20px; border-radius: 50%; background: {ACCENT};
        color: white; font-size: 14px; font-weight: bold; line-height: 1;
        display: none; align-items: center; justify-content: center; cursor: pointer;
        z-index: 6; box-shadow: 0 2px 6px rgba(0,0,0,0.5); user-select: none;
      }}
      #dodaj-plus:hover {{ background: {ACCENT_HOVER}; transform: translateY(-50%) scale(1.12); }}
      #drag-tooltip {{
        position: absolute; bottom: calc(100% + 8px); transform: translateX(-50%);
        background: {CARD}; color: {TEXT}; border: 1px solid {ACCENT};
        border-radius: 10px; padding: 5px 10px; font-size: 11px; font-weight: 700;
        white-space: nowrap; pointer-events: none; display: none; z-index: 5;
        box-shadow: 0 4px 14px rgba(0,0,0,0.4);
      }}
      .timeline-hint {{ font-size: 10px; color: {SUBTEXT}; text-align: center; margin-top: 6px; flex-shrink: 0; }}

      .info-red {{ display:flex; justify-content:space-between; width:100%; margin-top:10px; font-size:12px; color:{SUBTEXT}; flex-shrink: 0; }}
      .info-red span {{ font-weight: 600; color: {TEXT}; }}

      .kontrole {{ margin-top:14px; display:flex; align-items:center; gap:8px; width:100%; justify-content:center; flex-wrap:wrap; flex-shrink: 0; }}
      button {{
        background: linear-gradient(135deg, {ACCENT}, #5e5ce6);
        color:white; border:none; border-radius:999px;
        padding:10px 18px; font-size:12px; font-weight:600; cursor:pointer;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), 0 4px 14px rgba(156,45,79,0.35);
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
        flex-shrink: 0;
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
        background: rgba(156,45,79,0.16); color: {ACCENT}; border: 1px solid rgba(156,45,79,0.5);
        box-shadow: none;
      }}
      .btn-dodaj-odabir:hover {{ background: rgba(156,45,79,0.28); filter: none; }}

      /* --- lista više isječaka odjednom --- */
      #multi-panel {{ width: 100%; margin-top: 12px; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }}
      #lista-selekcija {{
        display: flex; flex-direction: column; gap: 6px;
        max-height: 168px; overflow-y: auto; padding-right: 2px;
        /* BITNO: body ima overflow:hidden (nema skrolanja stranice), a ova
           lista (flex-shrink:0 na #multi-panel) je znala narasti VISE od
           dostupnog prostora kod 6+ isjecaka - dugme "Skini sve isjecke"
           (koje je ISPOD ove liste, ne unutar nje) je time postajalo fizicki
           nedohvatljivo, bez ikakvog nacina da mu se dođe. Sad se SAMO ova
           lista skrola interno (max-height + overflow-y), a dugme ostaje
           uvijek vidljivo ispod nje, koliko god isjecaka bilo dodano. */
      }}
      #lista-selekcija::-webkit-scrollbar {{ width: 6px; }}
      #lista-selekcija::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}
      .selekcija-red {{
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
        border-radius: 14px; padding: 10px 14px; display: flex; align-items: center; gap: 14px;
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.14);
        transition: border-color 0.2s, background 0.2s;
      }}
      .selekcija-red.aktivna {{
        border-color: {ACCENT}; background: rgba(156,45,79,0.10);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.14), 0 0 0 1px rgba(156,45,79,0.35);
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
        position: absolute; top: 0; bottom: 0; background: rgba(156, 45, 79, 0.28);
        border-left: 2px solid {ACCENT}; border-right: 2px solid {ACCENT}; border-radius: 14px;
        cursor: grab; z-index: 2;
      }}
      .timeline-multi-blok:active {{ cursor: grabbing; }}
      .multi-blok-handle {{
        position: absolute; top: 0; bottom: 0; width: 12px; cursor: ew-resize;
        z-index: 4; display: flex; align-items: center; justify-content: center;
      }}
      .multi-blok-handle::after {{
        content: ""; width: 3px; height: 55%; border-radius: 3px;
        background: rgba(255,255,255,0.85); box-shadow: 0 0 3px rgba(0,0,0,0.4);
      }}
      .multi-blok-handle-left {{ left: -6px; }}
      .multi-blok-handle-right {{ right: -6px; }}

      #status-bar {{ margin-top: 10px; font-size: 12px; font-weight: 600; color: {SUCCESS}; text-align: center; min-height: 16px; flex-shrink: 0; }}

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
          <div id="dodaj-plus" title="{PT['add_another_hint']}">+</div>
        </div>
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
      var selectionBox = document.getElementById('timeline-selection');
      var pocSec = null, krajSec = null;
      var seekTimeout = null;
      var spreman = false;
      var ccUkljucen = false;
      var muted = false;
      var fallbackPokrenut = false;

      // Auto-formatiranje "Trenutni odabir" OD/DO polja dok korisnik rucno
      // upisuje vrijeme - sam ubacuje ":" na ispravna mjesta (HH:MM:SS) dok
      // tipka, umjesto da korisnik mora sam paziti na dvotocke.
      function autoFormatirajVrijeme(e) {{
        var el = e.target;
        var cifre = el.value.replace(/\\D/g, '').slice(0, 6);  // samo znamenke, max 6 (HHMMSS)
        var formatirano = '';
        for (var i = 0; i < cifre.length; i++) {{
          if (i === 2 || i === 4) formatirano += ':';
          formatirano += cifre[i];
        }}
        el.value = formatirano;
      }}
      document.getElementById('input-od').addEventListener('input', autoFormatirajVrijeme);
      document.getElementById('input-do').addEventListener('input', autoFormatirajVrijeme);

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
          document.getElementById('dodaj-plus').style.display = 'flex';
          document.getElementById('trajanje-isjecka-info').innerText =
            "{PT['isjecak_prefix']}: " + formatiraj(pocSec) + " → " + formatiraj(krajSec) +
            "  (" + formatiraj(krajSec - pocSec) + ")";
        }}
      }}

      // ---- lista više isječaka odjednom ----
      var brojacSelekcija = 0;

      function dodajRedUListu(odVal, doVal) {{
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
        azurirajListu();
        return id;
      }}

      function dodajUListu() {{
        var odVal = document.getElementById('input-od').value;
        var doVal = document.getElementById('input-do').value;
        if (!odVal || !doVal) {{
          document.getElementById('status-bar').innerText = '{PT["add_selection_warn"]}';
          return;
        }}
        dodajRedUListu(odVal, doVal);

        // ocisti "trenutni odabir" polja da je spremno za sljedece oznacavanje
        document.getElementById('input-od').value = '';
        document.getElementById('input-do').value = '';
        pocSec = null; krajSec = null;
        selectionBox.style.display = 'none';
        document.getElementById('dodaj-plus').style.display = 'none';
        document.getElementById('trajanje-isjecka-info').innerText = '{PT["isjecak_prefix"]}: {PT["nije_oznaceno"]}';
      }}

      // ---- "+" na kraju hvatista - odmah doda JOS JEDAN isjecak (kratak,
      // odmah nakon trenutnog, ili prije njega ako nema mjesta iza) direktno
      // u listu, spreman da ga korisnik povuce/rastegne na tocno mjesto koje
      // zeli - brzi precac umjesto rucnog povlacenja nove selekcije od nule ----
      document.getElementById('dodaj-plus').addEventListener('click', function(e) {{
        e.stopPropagation();
        if (pocSec === null || krajSec === null || !trajanjeVid) return;
        var trajanjeNovog = Math.min(krajSec - pocSec, 10);
        var noviOd = krajSec;
        var noviDo = Math.min(noviOd + trajanjeNovog, trajanjeVid);
        if (noviDo - noviOd < 0.5) {{
          // nema dovoljno prostora NAKON trenutne selekcije - probaj PRIJE nje
          noviDo = pocSec;
          noviOd = Math.max(noviDo - trajanjeNovog, 0);
        }}
        if (noviDo - noviOd < 0.5) return;  // ni tu nema mjesta (video prekratak) - odustani tiho
        dodajRedUListu(formatiraj(noviOd), formatiraj(noviDo));
      }});

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

          var hLijevo = document.createElement('div');
          hLijevo.className = 'multi-blok-handle multi-blok-handle-left';
          var hDesno = document.createElement('div');
          hDesno.className = 'multi-blok-handle multi-blok-handle-right';
          blok.appendChild(hLijevo);
          blok.appendChild(hDesno);

          var redId = red.id;
          hLijevo.addEventListener('mousedown', function(e) {{ zapocniPomjeranjeMultiRuba(e, redId, 'od'); }});
          hDesno.addEventListener('mousedown', function(e) {{ zapocniPomjeranjeMultiRuba(e, redId, 'do'); }});
          blok.addEventListener('mousedown', function(e) {{
            if (e.target === hLijevo || e.target === hDesno) return;
            zapocniPomjeranjeMultiCijelog(e, redId, od, doo);
          }});

          document.getElementById('timeline-container').appendChild(blok);
        }});
      }}

      // ---- povlacenje VEC DODANIH isjecaka izravno na traci - sinkronizira
      // se s Od/Do poljima u listi ispod (koja su "izvor istine"), pa se
      // azurirajTimelineSelekcije() samo ponovno iscrta prema njima ----
      function zapocniPomjeranjeMultiRuba(e, redId, kojiRub) {{
        e.stopPropagation();
        var red = document.getElementById(redId);
        var odInput = red.querySelector('.sel-od');
        var doInput = red.querySelector('.sel-do');

        function naPomicanje(ev) {{
          var nova = pozicijaUSekundama(ev.clientX);
          var trenOd = parseVrijemeJS(odInput.value);
          var trenDo = parseVrijemeJS(doInput.value);
          if (kojiRub === 'od') {{
            nova = Math.min(nova, trenDo - 0.1);
            odInput.value = formatiraj(nova);
            prikaziTooltip(nova, trenDo);
          }} else {{
            nova = Math.max(nova, trenOd + 0.1);
            doInput.value = formatiraj(nova);
            prikaziTooltip(trenOd, nova);
          }}
          azurirajTimelineSelekcije();
        }}
        function naOtpustanje() {{
          document.removeEventListener('mousemove', naPomicanje);
          document.removeEventListener('mouseup', naOtpustanje);
          dragTooltip.style.display = 'none';
        }}
        document.addEventListener('mousemove', naPomicanje);
        document.addEventListener('mouseup', naOtpustanje);
      }}

      function zapocniPomjeranjeMultiCijelog(e, redId, pocOd, pocDo) {{
        e.stopPropagation();
        var red = document.getElementById(redId);
        var odInput = red.querySelector('.sel-od');
        var doInput = red.querySelector('.sel-do');
        var trajanjeIsjecka = pocDo - pocOd;
        var pocetniX = e.clientX;

        function naPomicanje(ev) {{
          var pomakSek = pozicijaUSekundama(ev.clientX) - pozicijaUSekundama(pocetniX);
          var od = Math.min(Math.max(pocOd + pomakSek, 0), trajanjeVid - trajanjeIsjecka);
          odInput.value = formatiraj(od);
          doInput.value = formatiraj(od + trajanjeIsjecka);
          azurirajTimelineSelekcije();
          prikaziTooltip(od, od + trajanjeIsjecka);
        }}
        function naOtpustanje() {{
          document.removeEventListener('mousemove', naPomicanje);
          document.removeEventListener('mouseup', naOtpustanje);
          dragTooltip.style.display = 'none';
        }}
        document.addEventListener('mousemove', naPomicanje);
        document.addEventListener('mouseup', naOtpustanje);
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
