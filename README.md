# RusLOXPy

[![Release](https://img.shields.io/github/v/release/InVaeR/RusLOXPy)](https://github.com/InVaeR/RusLOXPy/releases/latest)

> Скачать готовый `.exe`: [Releases](https://github.com/InVaeR/RusLOXPy/releases/latest)

Отслеживание времени использования выбранных пользователем приложений на **Windows** (только x64).

## Возможности

- Добавление приложений в белый список (из запущенных процессов или выбор .exe вручную)
- Учёт времени только для выбранных приложений
- Определение активного окна через WinAPI
- Разделение на активное и фоновое время
- Статистика за день / неделю / месяц / всё время
- Экспорт статистики в CSV
- Работа в фоне (сворачивание в трей)
- Автозапуск через реестр
- Настраиваемые: порог простоя, интервал опроса, автостарт
- Единый экземпляр приложения (защита от дублирования)
- Горячие клавиши: Ctrl+1/2/3 — навигация, Delete — удаление из списка

## Технологии

| Компонент  | Библиотека                       |
| ---------- | -------------------------------- |
| GUI        | PySide6 (Qt)                     |
| Процессы   | psutil                           |
| WinAPI     | pywin32 (win32gui, win32process) |
| БД         | sqlite3 (встроенная)             |
| Автозапуск | winreg                           |

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Версия

Версия формируется автоматически при запуске: `{major}.{minor}.{patch}-{YYYYMMDD}` (дата сборки).  
Хранится в `version.py`.  
Проверка обновлений: Настройки → О программе → «Проверить обновления».

## Сборка в .exe

### Требования

```bash
pip install -r requirements-dev.txt   # pyinstaller, pillow
```

### Быстрая сборка

```bat
.\build.bat
```

### Ручная сборка

```bash
# 1. Сгенерировать иконку
python gen_icon.py

# 2. Сгенерировать version_info.txt
python gen_version.py

# 3. Собрать
pyinstaller build.spec --clean

# Результат: dist/RusLOXPy.exe
```
