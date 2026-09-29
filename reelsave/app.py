"""Точка входа GUI и проверка доступности локального хранилища."""

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from .gui import MainWindow
from .qt_runtime import prepare_qt_plugins
from .storage import Storage
from .theme import STYLE


def main() -> int:
    try:
        prepare_qt_plugins()
    except OSError as exc:
        print(f"Не вдалося підготувати плагіни Qt. Перевстанови залежності в доступне для запису середовище .venv: {exc}", file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setApplicationName("ReelSave")
    app.setOrganizationName("ReelSave")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI" if sys.platform == "win32" else "Helvetica Neue" if sys.platform == "darwin" else "DejaVu Sans", 10))
    app.setStyleSheet(STYLE)
    try:
        storage = Storage()
    except Exception as exc:
        QMessageBox.critical(None, "ReelSave — помилка запуску", f"Не вдалося відкрити налаштування та історію:\n{exc}")
        return 1
    window = MainWindow(storage)
    window.show()
    return app.exec()
