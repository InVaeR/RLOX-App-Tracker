# Changelog

## 2.0.0-dev — текущая разработка

- Полная переработка архитектуры (см. ARCHITECTURE.md)
- Переименование: RusLOXPy → RLOX App Tracker
- Новый репозиторий: `InVaeR/RLOX-App-Tracker`
- Python-лаунчер с проверкой обновлений по `latest.json`
- Per-user установщик Inno Setup с поддержкой обновлений
- Миграция данных из RusLOXPy v1.x
- IPC-механизм между экземплярами приложения
- Версионирование переведено на SemVer (статическая версия)
- Автозапуск через лаунчер
- `onedir`-сборка PyInstaller
- CI/CD: ruff + pytest, release pipeline, nightly
- Все 33 теста проходят

## 1.1.1 — последний legacy-релиз RusLOXPy

- Исправления: дизайн таблиц, иконки на дашборде, singleton-выход
- Исправления аудита: shuffle строк в watchlist, DB lock, scroll
- Полная история: [InVaeR/RusLOXPy](https://github.com/InVaeR/RusLOXPy)
