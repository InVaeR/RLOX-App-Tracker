# Процесс релиза

1. Обновить версию в `app/src/rlox_app_tracker/version.py`
2. Обновить CHANGELOG.md
3. Создать тег: `git tag v2.0.1`
4. Запушить тег: `git push origin v2.0.1`
5. GitHub Actions соберёт релиз автоматически

## Ручная сборка

```powershell
# 1. Собрать приложение
.\build\build_app.ps1 -Version "2.0.0"

# 2. Собрать лаунчер
.\build\build_launcher.ps1

# 3. Собрать установщик (требует Inno Setup)
.\build\build_installer.ps1 -Version "2.0.0"

# 4. Сгенерировать манифест
python build\generate_manifest.py dist\RLOX-App-Tracker-Setup-2.0.0-x64.exe 2.0.0
```
