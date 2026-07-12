from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from services.updater import check_for_update


class UpdateSignals(QObject):
    done = Signal(object)


class _UpdateTask(QRunnable):
    def __init__(self, signals: UpdateSignals):
        super().__init__()
        self._signals = signals

    def run(self):
        self._signals.done.emit(check_for_update())


def check_for_update_async(callback) -> UpdateSignals:
    signals = UpdateSignals()
    signals.done.connect(callback)
    QThreadPool.globalInstance().start(_UpdateTask(signals))
    return signals
