; Скрипт миграции старого RusLOXPy (вызывается из основного .iss при необходимости)
; Проверяет наличие %APPDATA%\RusLOXPy и предлагает перенести данные.

function IsLegacyInstallation: Boolean;
begin
  Result := DirExists(ExpandConstant('{userappdata}') + '\RusLOXPy');
end;

function GetLegacyDbPath: string;
begin
  Result := ExpandConstant('{userappdata}') + '\RusLOXPy\tracker.db';
end;

procedure MigrateLegacyData;
var
  LegacyDb: string;
  NewDbDir: string;
begin
  LegacyDb := GetLegacyDbPath;
  NewDbDir := ExpandConstant('{localappdata}') + '\RLOX App Tracker\data';
  if FileExists(LegacyDb) then
  begin
    if not DirExists(NewDbDir) then
      CreateDir(NewDbDir);
    if FileCopy(LegacyDb, NewDbDir + '\tracker.db', False) then
      Log('Migrated legacy DB: ' + LegacyDb + ' -> ' + NewDbDir + '\tracker.db');
  end;
end;
