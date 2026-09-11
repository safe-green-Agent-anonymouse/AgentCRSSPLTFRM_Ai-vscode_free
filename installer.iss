; Installateur Windows professionnel (Inno Setup 6).
; Build : iscc /DAppVersion=1.0.1 installer.iss   (apres build-exe.bat)
; Sortie : release\EDAC-Console-Setup-<version>.exe

#ifndef AppVersion
  #define AppVersion "1.0.1"
#endif

#define AppName "Expert Dev Autopilot Console"
#define AppShort "EDAC Console"
#define AppExe "EDAC-Console.exe"
#define AppPublisher "Expert Dev Autopilot"
#define AppUrl "https://github.com/safe-green-Agent-anonymouse/AgentCRSSPLTFRM_Ai-vscode_free"

[Setup]
AppId={{7C4E2C60-4C2E-4C2B-9E4A-5B4F3D2A1E90}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoCompany={#AppPublisher}
DefaultDirName={autopf}\EDAC
DefaultGroupName={#AppShort}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=release
OutputBaseFilename=EDAC-Console-Setup-{#AppVersion}
SetupIconFile=assets\icon.ico
LicenseFile=LICENSE
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
ChangesEnvironment=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\RESUME.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "docs\architecture.png"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppShort}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstaller {#AppShort}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppShort}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppShort}"; Filename: "{app}\{#AppExe}"; Tasks: quicklaunchicon

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"
Name: "quicklaunchicon"; Description: "Creer un raccourci de lancement rapide"; GroupDescription: "Raccourcis :"; Flags: unchecked
Name: "addtopath"; Description: "Ajouter EDAC au PATH utilisateur (commande EDAC-Console dans cmd/PowerShell)"; GroupDescription: "Integration systeme :"

; PATH utilisateur uniquement : aucune modification systeme, desinstallation propre.
[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent
Filename: "{#AppUrl}#readme"; Description: "Ouvrir la documentation"; Flags: postinstall shellexec skipifsilent unchecked

; La desinstallation Windows retire le programme ; les donnees utilisateur
; (configuration et journaux) sont supprimees ci-dessous.
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\ExpertDevAutopilot"
Type: filesandordirs; Name: "{localappdata}\ExpertDevAutopilot"

[Code]
function NeedsPath(Dir: string): Boolean;
var
  Existing: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Existing) then
    Existing := '';
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Existing) + ';') = 0;
end;
