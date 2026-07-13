# RLOX App Tracker

[![CI](https://github.com/InVaeR/RLOX-App-Tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/InVaeR/RLOX-App-Tracker/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/InVaeR/RLOX-App-Tracker)](https://github.com/InVaeR/RLOX-App-Tracker/releases/latest)

Отслеживание времени использования выбранных пользователем приложений на **Windows** (только x64).

Основано на **RusLOXPy** v1.1.1 ([legacy](https://github.com/InVaeR/RusLOXPy)).

## Возможности

- Добавление приложений в белый список (из запущенных процессов или выбор .exe вручную)
- Учёт времени только для выбранных приложений
- Определение активного окна через WinAPI
- Разделение на активное и фоновое время
- Статистика за день / неделю / месяц / всё время
- Экспорт статистики в CSV
- Работа в фоне (сворачивание в трей)
- Автозапуск через лаунчер
- Настраиваемые: порог простоя, интервал опроса
- Единый экземпляр приложения (IPC)
- Горячие клавиши: Ctrl+1/2/3 — навигация, Delete — удаление из списка
- Автоматические обновления через лаунчер

## Быстрый старт (из исходников)

### Требования

- Python 3.11+
- Windows 10/11 x64

### Установка

```bash
cd app
pip install -r requirements.txt
```

### Запуск

```bash
cd app/src
python -m rlox_app_tracker
```

### Разработка

```bash
cd app
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Установка (для пользователей)

Скачайте установщик со [страницы релизов](https://github.com/InVaeR/RLOX-App-Tracker/releases/latest):

```
RLOX-App-Tracker-Setup-x64.exe
```

Установщик:

- устанавливает лаунчер и приложение;
- создаёт ярлыки в меню «Пуск» (и опционально на рабочем столе);
- регистрирует программу в списке установленных приложений Windows;
- поддерживает автозапуск;
- импортирует данные из RusLOXPy (если найдены);
- не требует прав администратора.

## Структура проекта

```
RLOX-App-Tracker/
├── app/                    # Основное Python/PySide6-приложение
│   ├── src/
│   │   └── rlox_app_tracker/  # Пакет приложения
│   ├── tests/              # Тесты (pytest)
│   └── requirements*.txt
├── launcher/               # Лаунчер на Python
│   └── src/launcher.py
├── installer/              # Inno Setup скрипты
├── build/                  # Скрипты сборки
├── docs/                   # Документация
└── release/                # Манифесты обновлений
```

## Технологии

| Компонент  | Библиотека                       |
| ---------- | -------------------------------- |
| GUI        | PySide6 (Qt)                     |
| Процессы   | psutil                           |
| WinAPI     | pywin32 (win32gui, win32process) |
| БД         | SQLite3 (встроенная)             |
| Сборка     | PyInstaller (onedir)             |
| Установка  | Inno Setup 6                     |

## Версия

Используется SemVer: `2.0.0-dev`, `2.0.0`, `2.0.1`, `2.1.0` и т.д.

Версия задаётся в `app/src/rlox_app_tracker/version.py` и соответствует Git-тегу.

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Протокол обновления](docs/UPDATE_PROTOCOL.md)
- [Релизный процесс](docs/RELEASE.md)
- [Миграция](docs/MIGRATION.md)
- [Безопасность](docs/SECURITY.md)
- [Тестирование](docs/TESTING.md)

## Лицензия

MIT. Основано на [RusLOXPy](https://github.com/InVaeR/RusLOXPy).
