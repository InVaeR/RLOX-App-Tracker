; RLOX App Tracker — Inno Setup
#define MyAppName "RLOX App Tracker"
#define MyAppPublisher "RusLOX"
#define MyAppURL "https://github.com/InVaeR/RLOX-App-Tracker"
#define MyAppExeName "RLOXAppTracker.exe"
#define MyLauncherExeName "RLOXLauncher.exe"
#define MyAppId "{{B8A2C3D4-E5F6-7890-ABCD-EF1234567890}}"
#define MyAutostartValue "RLOXAppTracker"

#ifndef AppVersion
  #define AppVersion "2.0.0-alpha.1"
#endif
#ifndef AppVersionNumeric
  #define AppVersionNumeric "2.0.0.1"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersionNumeric}
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
CloseApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
; Лаунчер
Source: "..\dist\launcher\{#MyLauncherExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Версия приложения
Source: "..\dist\RLOXAppTracker\*"; DestDir: "{app}\versions\{#AppVersion}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\versions"
Name: "{app}\state"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--launch"
Name: "{group}\Проверить обновления"; Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--check-updates --interactive"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--launch"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
Name: "autostart"; Description: "Запускать вместе с Windows"; GroupDescription: "Автозапуск:"

[Run]
Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--launch --after-update"; Description: "Запустить {#MyAppName}"; Flags: postinstall nowait

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAutostartValue}"; ValueData: """{app}\{#MyLauncherExeName}"" --launch --background"; Tasks: autostart; Flags: uninsdeletevalue

[UninstallRun]
Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: files; Name: "{app}\state\install.json"
Type: files; Name: "{app}\state\install.json.bak"
Type: dirifempty; Name: "{app}\state"
Type: dirifempty; Name: "{app}\versions"
Type: files; Name: "{app}\launcher.version"
Type: dirifempty; Name: "{app}"

[Code]
var
  DataPage: TInputOptionWizardPage;
  DataPath: string;
  ProductDataRoot: string;
  InstallStatePath: string;
  OldDataFound: Boolean;
  IsUpdate: Boolean;
  PrevVersion: string;

function ExtractVersionFromJson(const FilePath: string): string;
var
  Lines: TArrayOfString;
  Content: string;
  i: Integer;
  QuotePos: Integer;
  EndQuotePos: Integer;
begin
  Result := '';
  if not FileExists(FilePath) then Exit;
  Content := '';
  if LoadStringsFromFile(FilePath, Lines) then
  begin
    for i := 0 to GetArrayLength(Lines) - 1 do
    begin
      if i > 0 then Content := Content + #13#10;
      Content := Content + Lines[i];
    end;
  end;
  QuotePos := Pos('"currentVersion"', Content);
  if QuotePos = 0 then Exit;
  QuotePos := Pos('"', Copy(Content, QuotePos + 16, 50));
  if QuotePos = 0 then Exit;
  EndQuotePos := Pos('"', Copy(Content, QuotePos + 1, 30));
  if EndQuotePos = 0 then Exit;
  Result := Copy(Content, QuotePos + 1, EndQuotePos - 1);
end;

function GetChannelFromVersion(const Version: string): string;
begin
  if Pos('alpha', LowerCase(Version)) > 0 then
    Result := 'dev'
  else if Pos('beta', LowerCase(Version)) > 0 then
    Result := 'beta'
  else
    Result := 'stable';
end;

function EscapeBackslash(const S: string): string;
begin
  Result := S;
  StringChange(Result, '\', '\\');
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  DataPath := ExpandConstant('{localappdata}') + '\RLOX App Tracker\data';
  ProductDataRoot := ExpandConstant('{localappdata}') + '\RLOX App Tracker';
  InstallStatePath := ExpandConstant('{localappdata}\Programs\RLOX App Tracker\state\install.json');
  OldDataFound := DirExists(DataPath);
  IsUpdate := CmdLineParamExists('/UPDATE');

  if IsUpdate then
    PrevVersion := ExtractVersionFromJson(InstallStatePath);
end;

procedure WriteInstallJson;
var
  Json: string;
  StateDir: string;
  EscapedExe: string;
begin
  StateDir := ExpandConstant('{localappdata}\Programs\RLOX App Tracker\state');
  ForceDirectories(StateDir);
  EscapedExe := EscapeBackslash('versions\{#AppVersion}\{#MyAppExeName}');

  Json := '{' + #13#10 +
          '  "schemaVersion": 1,' + #13#10 +
          '  "currentVersion": "{#AppVersion}",' + #13#10 +
          '  "previousVersion": "' + PrevVersion + '",' + #13#10 +
          '  "pendingVersion": "",' + #13#10 +
          '  "channel": "' + GetChannelFromVersion('{#AppVersion}') + '",' + #13#10 +
          '  "installedAt": "' + GetDateTimeString('yyyy-mm-dd", "hh:nn:ss', '-', ':') + '",' + #13#10 +
          '  "appExecutable": "' + EscapedExe + '"' + #13#10 +
          '}';

  SaveStringToFile(StateDir + '\install.json', Json, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WriteInstallJson;
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
        DelTree(ProductDataRoot, True, True, True);
    end;
  end;
end;

function InitializeUninstall: Boolean;
var
  ResultCode: Integer;
  LauncherExe: string;
begin
  Result := True;
  DataPath := ExpandConstant('{localappdata}') + '\RLOX App Tracker\data';
  ProductDataRoot := ExpandConstant('{localappdata}') + '\RLOX App Tracker';
  LauncherExe := ExpandConstant('{app}\{#MyLauncherExeName}');
  if FileExists(LauncherExe) then
  begin
    Exec(LauncherExe, '--shutdown', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
