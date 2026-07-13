# Архитектура RLOX App Tracker

## Компоненты

- **RLOXAppTracker.exe** — основное Python/PySide6 приложение для отслеживания времени.
- **RLOXLauncher.exe** — точка входа, проверяет обновления и запускает приложение.
- **RLOX-App-Tracker-Setup-x64.exe** — установщик (Inno Setup).

## Структура каталогов

```
%LOCALAPPDATA%\Programs\RLOX App Tracker\
├── RLOXLauncher.exe
├── versions\<version>\RLOXAppTracker.exe
└── state\install.json

%LOCALAPPDATA%\RLOX App Tracker\
├── data\tracker.db
├── config\app.json
├── logs\
├── updates\downloads\
└── migration\
```

## Поток запуска

1. Пользователь запускает RLOXLauncher.exe
2. Launcher проверяет install.json
3. При необходимости проверяет latest.json
4. Запускает RLOXAppTracker.exe из versions/<version>/
5. Приложение создаёт трей-иконку и начинает трекинг

## Обновление

1. Launcher скачивает latest.json
2. Сравнивает SemVer
3. Скачивает установщик
4. Проверяет SHA-256
5. Закрывает приложение через IPC
6. Запускает установщик
7. Установщик обновляет файлы
8. Запускается новый лаунчер
