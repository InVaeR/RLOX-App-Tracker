; RLOX App Tracker — Inno Setup
#define MyAppName "RLOX App Tracker"
#define MyAppPublisher "RusLOX"
#define MyAppURL "https://github.com/InVaeR/RLOX-App-Tracker"
#define MyAppExeName "RLOXAppTracker.exe"
#define MyLauncherExeName "RLOXLauncher.exe"
#define MyAppId "{B8A2C3D4-E5F6-7890-ABCD-EF1234567890}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=RLOX-App-Tracker-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyLauncherExeName}
DisableWelcomePage=no
DisableReadyPage=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; Лаунчер
Source: "..\dist\launcher\{#MyLauncherExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Версия приложения
Source: "..\dist\app\versions\{#AppVersion}\*"; DestDir: "{app}\versions\{#AppVersion}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Update manifest
Source: "..\release\install.json"; DestDir: "{app}\state"; Flags: ignoreversion

[Dirs]
Name: "{app}\versions"
Name: "{app}\state"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--launch"
Name: "{group}\Проверить обновления"; Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--check-updates --interactive"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--launch"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
Name: "autostart"; Description: "Запускать вместе с Windows"; GroupDescription: "Автозапуск:"

[Run]
Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--launch"; Description: "Запустить {#MyAppName}"; Flags: postinstall nowait skipifsilent

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyLauncherExeName}"" --launch --background"; Tasks: autostart; Flags: uninsdeletevalue

[UninstallRun]
Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesifnotempty; Name: "{app}\state\install.json"
Type: dirifempty; Name: "{app}\state"
Type: dirifempty; Name: "{app}\versions"
Type: dirifempty; Name: "{app}"

[Code]
var
  DataPage: TInputOptionWizardPage;
  DataPath: string;
  OldDataFound: Boolean;

function InitializeSetup: Boolean;
begin
  Result := True;
  DataPath := ExpandConstant('{localappdata}') + '\RLOX App Tracker\data';
  OldDataFound := DirExists(DataPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if OldDataFound then
      Log('Пользовательские данные сохранены: ' + DataPath);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  Answer: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if DirExists(DataPath) then
    begin
      Answer := MsgBox('Удалить также статистику и настройки?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
      if Answer = IDYES then
        DelTree(DataPath, True, True, True);
    end;
  end;
end;
