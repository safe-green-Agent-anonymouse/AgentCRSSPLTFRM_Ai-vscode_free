; Installateur Windows optionnel (Inno Setup 6).
; Build : iscc installer.iss  (apres build-exe.bat)

#define AppName "Expert Dev Autopilot Console"
#define AppVersion "1.0.0"
#define AppExe "EDAC-Console.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\EDAC
DefaultGroupName={#AppName}
OutputDir=release
OutputBaseFilename=EDAC-Console-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent

; La desinstallation Windows retire le programme ; les donnees utilisateur
; (configuration et journaux) sont supprimees ci-dessous.
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\ExpertDevAutopilot"
Type: filesandordirs; Name: "{localappdata}\ExpertDevAutopilot"
