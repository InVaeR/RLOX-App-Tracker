; RLOX App Tracker — Inno Setup
#define MyAppName "RLOX App Tracker"
#define MyAppPublisher "RusLOX"
#define MyAppURL "https://github.com/InVaeR/RLOX-App-Tracker"
#define MyAppExeName "RLOXAppTracker.exe"
#define MyLauncherExeName "RLOXLauncher.exe"
#define MyAppId "{{B8A2C3D4-E5F6-7890-ABCD-EF1234567890}}"
#define MyAutostartValue "RLOXAppTracker"

#ifndef AppVersion
  #define AppVersion "2.0.4"
#endif
#ifndef AppVersionNumeric
  #define AppVersionNumeric "2.0.4.0"
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
CloseApplications=force
CloseApplicationsFilter=RLOXLauncher.exe,RLOXAppTracker.exe
RestartApplications=no

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
; Мягкое завершение приложения через IPC
Filename: "{app}\{#MyLauncherExeName}"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated; RunOnceId: "ShutdownApp"

[UninstallDelete]
Type: files; Name: "{app}\state\install.json"
Type: files; Name: "{app}\state\install.json.bak"
Type: dirifempty; Name: "{app}\state"
Type: dirifempty; Name: "{app}\versions"
Type: files; Name: "{app}\launcher.version"
Type: dirifempty; Name: "{app}"

[Code]
var
  DataPath: string;
  ProductDataRoot: string;
  OldDataFound: Boolean;
  IsUpdate: Boolean;
  ExistingCurrentVersion: string;
  ExistingPreviousVersion: string;

function LoadTextFile(const FilePath: string): string;
var
  Lines: TArrayOfString;
  i: Integer;
begin
  Result := '';
  if not FileExists(FilePath) then Exit;
  if not LoadStringsFromFile(FilePath, Lines) then Exit;
  for i := 0 to GetArrayLength(Lines) - 1 do
  begin
    if i > 0 then Result := Result + #13#10;
    Result := Result + Lines[i];
  end;
end;

function ExtractJsonString(const FilePath: string; const Key: string): string;
var
  Content: string;
  Tail: string;
  KeyPos: Integer;
  ColonPos: Integer;
  QuotePos: Integer;
  EndQuotePos: Integer;
begin
  Result := '';
  Content := LoadTextFile(FilePath);
  if Content = '' then Exit;

  KeyPos := Pos('"' + Key + '"', Content);
  if KeyPos = 0 then Exit;

  Tail := Copy(Content, KeyPos + Length(Key) + 2, Length(Content));
  ColonPos := Pos(':', Tail);
  if ColonPos = 0 then Exit;

  Tail := Copy(Tail, ColonPos + 1, Length(Tail));
  QuotePos := Pos('"', Tail);
  if QuotePos = 0 then Exit;

  Tail := Copy(Tail, QuotePos + 1, Length(Tail));
  EndQuotePos := Pos('"', Tail);
  if EndQuotePos = 0 then Exit;

  Result := Copy(Tail, 1, EndQuotePos - 1);
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

function JsonNullableString(const S: string): string;
begin
  if S = '' then
    Result := 'null'
  else
    Result := '"' + S + '"';
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  DataPath := ExpandConstant('{localappdata}') + '\RLOX App Tracker\data';
  ProductDataRoot := ExpandConstant('{localappdata}') + '\RLOX App Tracker';
  OldDataFound := DirExists(DataPath);
  IsUpdate := CompareText(ExpandConstant('{param:UPDATE|0}'), '1') = 0;

  ExistingCurrentVersion := '';
  ExistingPreviousVersion := '';
end;

procedure WriteInstallJson;
var
  Json: string;
  StateDir: string;
  StatePath: string;
  TempPath: string;
  EscapedExe: string;
  CurrentVersionJson: string;
  PreviousVersionJson: string;
  PendingVersionJson: string;
begin
  StateDir := ExpandConstant('{app}\state');
  ForceDirectories(StateDir);
  StatePath := StateDir + '\install.json';
  TempPath := StatePath + '.tmp';

  if FileExists(StatePath) then
  begin
    ExistingCurrentVersion := ExtractJsonString(StatePath, 'currentVersion');
    ExistingPreviousVersion := ExtractJsonString(StatePath, 'previousVersion');
  end;

  EscapedExe := EscapeBackslash('versions\{#AppVersion}\{#MyAppExeName}');

  if IsUpdate and (ExistingCurrentVersion <> '') then
  begin
    CurrentVersionJson := JsonNullableString(ExistingCurrentVersion);
    PreviousVersionJson := JsonNullableString(ExistingPreviousVersion);
    PendingVersionJson := JsonNullableString('{#AppVersion}');
  end
  else
  begin
    CurrentVersionJson := JsonNullableString('{#AppVersion}');
    PreviousVersionJson := 'null';
    PendingVersionJson := 'null';
  end;

  Json := '{' + #13#10 +
          '  "schemaVersion": 1,' + #13#10 +
          '  "currentVersion": ' + CurrentVersionJson + ',' + #13#10 +
          '  "previousVersion": ' + PreviousVersionJson + ',' + #13#10 +
          '  "pendingVersion": ' + PendingVersionJson + ',' + #13#10 +
          '  "launchAttemptedAt": null,' + #13#10 +
          '  "startupConfirmed": false,' + #13#10 +
          '  "channel": "' + GetChannelFromVersion('{#AppVersion}') + '",' + #13#10 +
          '  "installedAt": "' + GetDateTimeString('yyyy-mm-dd"T"hh:nn:ss', '-', ':') + '",' + #13#10 +
          '  "appExecutable": "' + EscapedExe + '"' + #13#10 +
          '}';

  if FileExists(TempPath) then DeleteFile(TempPath);
  if not SaveStringToFile(TempPath, Json, False) then
    RaiseException('Не удалось записать временный install.json');

  if FileExists(StatePath) then
  begin
    if not FileCopy(StatePath, StatePath + '.bak', False) then
      Log('Не удалось создать install.json.bak');
    if not DeleteFile(StatePath) then
      RaiseException('Не удалось заменить install.json');
  end;

  if not RenameFile(TempPath, StatePath) then
    RaiseException('Не удалось активировать новый install.json');
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

procedure KillProcess(const ExeName: string);
var
  ResultCode: Integer;
begin
  Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/F /IM ' + ExeName,
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  );
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  Answer: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    KillProcess('{#MyAppExeName}');
    KillProcess('{#MyLauncherExeName}');
    Sleep(1500);

    RegDeleteValue(
      HKEY_CURRENT_USER,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      '{#MyAutostartValue}'
    );
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    DelTree(ExpandConstant('{app}\versions'), True, True, True);
    DelTree(ExpandConstant('{app}\state'), True, True, True);

    if DirExists(DataPath) then
    begin
      Answer := MsgBox('Удалить также статистику и настройки?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
      if Answer = IDYES then
        DelTree(ProductDataRoot, True, True, True);
    end;

    RemoveDir(ExpandConstant('{app}'));
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
    Sleep(1000);
  end;
  KillProcess('{#MyAppExeName}');
  KillProcess('{#MyLauncherExeName}');
  Sleep(1000);
end;
