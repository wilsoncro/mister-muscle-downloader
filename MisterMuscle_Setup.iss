; ============================================================================
;  MisterMuscle_Setup.iss
;  Inno Setup skripta koja od VEÄ† IZGRAÄENOG dist\MisterMuscle.exe (napravljenog
;  preko "python build_exe.py") pravi pravi Windows instalacijski program -
;  s ikonicom u Start meniju, preÄicom na Desktopu i "Ukloni program" opcijom.
;
;  KAKO KORISTITI (jednom, na SVOM Windows raÄunalu):
;    1) Prvo napravi MisterMuscle.exe:
;         python build_exe.py
;       (mora se pokrenuti na Windowsu - .exe se ne moÅ¾e napraviti na
;        Linuxu/Macu za Windows)
;
;    2) Skini i instaliraj Inno Setup (besplatan, ~5 min):
;         https://jrsoftware.org/isdl.php
;
;    3) Desni klik na ovu datoteku (MisterMuscle_Setup.iss) â†’ "Compile"
;       (ili je otvori u Inno Setup Compileru pa Build â†’ Compile / F9)
;
;    4) Rezultat je:  Output\MisterMuscle_Setup.exe
;       TO je jedina datoteka koju Å¡aljeÅ¡/dijeliÅ¡ korisnicima. Oni je
;       pokrenu, kliknu "Dalje" par puta, i gotovo - ne treba im Python,
;       yt-dlp ni ffmpeg, aplikacija to sve sama skine kod prvog pokretanja.
;
;  Ova skripta instalira u pravi Program Files (traÅ¾i admin/UAC potvrdu pri
;  instalaciji - to je normalno za Program Files) - alati (yt-dlp/ffmpeg) i
;  postavke svejedno idu u korisnikov profil (ne u Program Files), kako app
;  sama vec radi, pa nema problema s pravima pisanja ni nakon instalacije.
; ============================================================================

#define MyAppName "Mister Muscle Downloader"
#define MyAppVersion "1.9"
#define MyAppPublisher "Mister Muscle"
#define MyAppExeName "MisterMuscle.exe"

[Setup]
AppId={{7C1E9F2A-4B3D-4E7A-9C2F-6A1D8E5B3F90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppSupportURL=https://github.com/yt-dlp/yt-dlp
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=MisterMuscle_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
; Ikona instalera - ako "ikona.ico" postoji u istom folderu kao ova skripta,
; koristi se; ako ne postoji, Inno Setup jednostavno koristi svoju zadanu.
#ifexist "ikona.ico"
SetupIconFile=ikona.ico
#endif

[Languages]
; Napomena: "Croatian.isl" NIJE ugraden u Inno Setup po defaultu (samo engleski
; jest) - zato je ranije pucalo s "Couldn't open include file". Ako ipak zelis
; hrvatski TEKST SAMOG INSTALERA (dugmad "Dalje"/"Instaliraj" i sl. - ovo je
; odvojeno od jezika UNUTAR same aplikacije, koji se vec bira u njenom
; "Jezik" meniju), skini "Croatian.isl" s https://jrsoftware.org/files/istrans/
; i stavi ga u "C:\Program Files (x86)\Inno Setup 6\Languages\", pa vrati red
; ispod (ukloni ";" na pocetku):
; Name: "croatian"; MessagesFile: "compiler:Languages\Croatian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; PRIJE compile-anja ove skripte mora vec postojati dist\MisterMuscle.exe -
; napravi ga sa "python build_exe.py" (vidi upute na vrhu ove datoteke).
Source: "dist\MisterMuscle.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Instalacija sad ide u Program Files, a Program Files NIJE upisiv bez admin
; prava - app to sama otkrije i onda yt-dlp.exe/ffmpeg.exe skida odvojeno, u
; %LOCALAPPDATA%\MisterMuscle\alati (vidi _alati_folder() u kodu), NE pored
; .exe-a u {app}. To znaci da se ti preuzeti alati NE brisu automatski kad se
; ova app deinstalira (Inno Setup brise samo ono sto je sam instalirao pod
; {app}) - namjerno ih ostavljamo, da ponovna instalacija ne mora sve iznova
; skidati. Isto vrijedi za config u %APPDATA%\MisterMuscle. Ako ipak zelis da
; se i to obrise pri deinstalaciji, otkomentiraj redove ispod:
; Type: filesandordirs; Name: "{localappdata}\MisterMuscle"
; Type: filesandordirs; Name: "{userappdata}\MisterMuscle"
