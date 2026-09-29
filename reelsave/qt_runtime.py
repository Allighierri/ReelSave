"""Подготовка Qt на macOS, если среда установки скрыла файлы плагинов."""

import os
import stat
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo


def prepare_qt_plugins() -> None:
    """Qt не ищет плагины с UF_HIDDEN, даже если путь к ним правильный.

    Некоторые среды установки на macOS выставляют этот атрибут для dylib.
    Меняем только этот бит у плагинов текущей установки Qt. На других ОС
    и при обычных атрибутах файлов функция ничего не делает.
    """
    if sys.platform != "darwin":
        return
    root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    for path in root.rglob("*.dylib"):
        if path.is_symlink():
            continue
        flags = path.stat().st_flags
        if flags & stat.UF_HIDDEN:
            os.chflags(path, flags & ~stat.UF_HIDDEN)
