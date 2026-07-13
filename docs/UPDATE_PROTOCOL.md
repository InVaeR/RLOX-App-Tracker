# Протокол обновления

## Манифест latest.json

```json
{
  "schemaVersion": 1,
  "product": "rlox-app-tracker",
  "channel": "stable",
  "version": "2.0.1",
  "minimumLauncherVersion": "1.0.0",
  "publishedAt": "2026-07-13T12:00:00Z",
  "mandatory": false,
  "installer": {
    "url": "...",
    "sha256": "hex",
    "size": 123456789
  },
  "releaseNotesUrl": "..."
}
```

## Состояние установки install.json

```json
{
  "schemaVersion": 1,
  "currentVersion": "2.0.1",
  "previousVersion": "2.0.0",
  "channel": "stable",
  "installedAt": "...",
  "appExecutable": "versions\\2.0.1\\RLOXAppTracker.exe"
}
```

## IPC-команды (QLocalSocket)

- `show` — показать окно
- `shutdown` — завершить приложение
- `shutdown-for-update` — завершить для обновления
- `ping` — проверка активности
