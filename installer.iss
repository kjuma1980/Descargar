; =====================================================================
; Turbo Descargar v3.0 - Script de Instalacion Inno Setup
; Paquete Completo Offline: Incluye Python Embed, CustomTkinter,
; yt-dlp, FFmpeg, FFprobe y Deno
; =====================================================================

#define MyAppName "Turbo Descargar"
#define MyAppVersion "3.0"
#define MyAppPublisher "Turbo Descargar"
#define MyAppExeName "TurboDescargar.exe"

[Setup]
AppId={{E68A5F23-9D45-4B82-9B7C-8D4C82A13E50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=d:\yt_Downloader\Descargar\Output
OutputBaseFilename=TurboDescargar_v3.0_Setup
SetupIconFile=d:\yt_Downloader\Descargar\dist\TurboDescargar\_internal\customtkinter\assets\icons\CustomTkinter_icon_Windows.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion=3.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductVersion=3.0.0.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Todos los archivos de la aplicacion (Binario, _internal con Python embed, CustomTkinter, yt-dlp, FFmpeg, FFprobe y Deno)
Source: "d:\yt_Downloader\Descargar\dist\TurboDescargar\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*Descargas\*,*.mp4,*.m4a,*.webm,*.mp3"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\customtkinter\assets\icons\CustomTkinter_icon_Windows.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\_internal\customtkinter\assets\icons\CustomTkinter_icon_Windows.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
