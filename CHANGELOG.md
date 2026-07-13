# Changelog

## 2.0.0-alpha.1 — предварительный релиз

- Полная переработка архитектуры (см. ARCHITECTURE.md)
- Переименование: RusLOXPy → RLOX App Tracker
- C# лаунчер (.NET 10 WinForms, self-contained, single-file)
- Per-user установщик Inno Setup с поддержкой обновлений
- Миграция данных из RusLOXPy v1.x
- IPC-механизм между экземплярами приложения
- Версионирование переведено на SemVer (статическая версия)
- Автозапуск через лаунчер
- `onedir`-сборка PyInstaller
- CI/CD: ruff + pytest, release pipeline
- Решены все P0 проблемы аудита
- Новая цветовая палитра (зелёная тема: pine-teal, honeydew, ash-grey)
- Логгер с ротацией (2 MB, 3 бэкапа)
- Валидация манифеста обновлений (SemVer, HTTPS, SHA-256, размер)
- 36 Python-тестов, 21 C#-тест (xUnit), ruff clean

## 1.1.1 — последний legacy-релиз RusLOXPy

- Исправления: дизайн таблиц, иконки на дашборде, singleton-выход
- Исправления аудита: shuffle строк в watchlist, DB lock, scroll
- Полная история: [InVaeR/RusLOXPy](https://github.com/InVaeR/RusLOXPy)
