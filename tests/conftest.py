import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from reelsave.storage import Storage
from reelsave.qt_runtime import prepare_qt_plugins


@pytest.fixture
def storage(tmp_path):
    return Storage(tmp_path / "data")


@pytest.fixture(scope="session")
def app():
    prepare_qt_plugins()
    return QApplication.instance() or QApplication([])
