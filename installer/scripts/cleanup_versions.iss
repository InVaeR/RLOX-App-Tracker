; Удаление старых версий кроме current и previous
; Вызывается после успешного обновления

procedure CleanupOldVersions;
var
  VersionsDir: string;
  FindRec: TFindRec;
  CurrentVer, PreviousVer, DirName: string;
begin
  VersionsDir := ExpandConstant('{localappdata}') + '\Programs\RLOX App Tracker\versions';
  CurrentVer := '{#AppVersion}';
  PreviousVer := '';
  if FindFirst(VersionsDir + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0 then
        begin
          DirName := FindRec.Name;
          if (DirName <> '.') and (DirName <> '..') and
             (DirName <> CurrentVer) and (DirName <> PreviousVer) then
          begin
            DelTree(VersionsDir + '\' + DirName, True, True, True);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;
