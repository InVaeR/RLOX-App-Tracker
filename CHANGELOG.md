# Changelog

## 2.0.2

- Исправлен поиск лаунчера из приложения (добавлен INSTALL_DIR в кандидаты)
- Отложено расширение `{app}` до PostInstall — исправлена ошибка "constant expanded before initialization"
- Оптимизация process scan: один `list_running_apps()` вместо N `process_iter` на приложение
- Удалён мёртвый код: `_manual_check_update`, `get_running_process_names`, `MANIFEST_URL`
- Type hints: `Optional` вместо `= None` в signatures
- Заменён `__import__("datetime")` на нормальный импорт
- Нормализация путей в `IsAppRunning` (`Path.GetFullPath`)
- `latest.json` обновляется только для stable-канала
- `fail_on_unmatched_files: false` в release workflow
- Версия лаунчера/ installer/ version_info синхронизированы

## 2.0.1

- Исправлено зависание при первом запуске (порядок инициализации, обработчик исключений)
- Исправлено удаление программы (принудительное завершение процессов, очистка versions/state)
- Устойчивый singleton (ping/pong перед выводом «уже запущено»)
- IPC через readyRead без блокировки UI
- Fallback-запуск любой установленной версии при неудачном rollback
- Grace-period 60с перед откатом pending-версии
- Каналы обновлений: dev/beta/stable через отдельные манифесты
- Миграция: повреждённая БД считается ошибкой, повтор при failed-маркере

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
