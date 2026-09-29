import time
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from reelsave.gui import MainWindow
from reelsave.models import DownloadResult, Progress, Status


def wait_until(app, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(5)
    assert predicate(), "GUI operation timed out"


class TestService:
    __test__ = False

    def __init__(self, storage, block=False):
        self.storage = storage
        self.block = block
        self.called = []

    def download(self, url, options, stop, notify):
        self.called.append(url)
        notify(Progress(Status.FETCHING))
        if self.block:
            stop.wait(timeout=3)
            return DownloadResult(url, Status.CANCELLED)
        if "broken" in url:
            return DownloadResult(url, Status.ERROR, message="Тестова помилка")
        notify(Progress(Status.DOWNLOADING, 55))
        options.output_dir.mkdir(parents=True, exist_ok=True)
        path = options.output_dir / "test.mp4"
        path.write_bytes(b"test")
        return DownloadResult(url, Status.DONE, path, "Test video")


def test_gui_batch_keeps_working_after_error_and_persists_history(app, storage, tmp_path):
    service = TestService(storage)
    window = MainWindow(storage, service)
    window.output_input.setText(str(tmp_path / "out"))
    window.show()
    try:
        window.url_input.setPlainText("instagram.com/reel/broken/\ninstagram.com/reel/good/")
        QTest.mouseClick(window.add_button, Qt.MouseButton.LeftButton)
        assert len(window.items) == 2
        QTest.mouseClick(window.start_button, Qt.MouseButton.LeftButton)
        assert not window.input_card.isEnabled()
        wait_until(app, lambda: window.worker is None)
        assert [item.status for item in window.items] == [Status.ERROR, Status.DONE]
        assert len(storage.history()) == 2
        assert window.start_button.isEnabled()  # Ошибку можно повторить.
        window._navigate(1)
        assert window.history_table.rowCount() == 2
        window._navigate(0)
        window._clear_completed()
        assert len(window.items) == 1
    finally:
        window.close()


def test_gui_invalid_links_and_duplicates(app, storage):
    window = MainWindow(storage)
    try:
        window.url_input.setPlainText("https://example.org/reel/abc/")
        window._add_urls()
        assert not window.items
        assert window.notice.property("error")
        for _ in range(2):
            window.url_input.setPlainText("instagram.com/reel/abc/")
            window._add_urls()
        assert len(window.items) == 1
        window.queue_table.selectRow(0)
        window._remove_selected()
        assert window.queue_stack.currentIndex() == 0
        assert not window.start_button.isEnabled()
    finally:
        window.close()


def test_stop_does_not_start_next_item_and_close_waits_for_worker(app, storage, tmp_path):
    service = TestService(storage, block=True)
    window = MainWindow(storage, service)
    window.output_input.setText(str(tmp_path))
    window.show()
    window.url_input.setPlainText("instagram.com/reel/first/\ninstagram.com/reel/second/")
    window._add_urls()
    window._start()
    wait_until(app, lambda: bool(service.called))
    window.close()
    wait_until(app, lambda: window.worker is None)
    assert len(service.called) == 1
    assert window.items[0].status == Status.CANCELLED
    assert window.items[1].status == Status.WAITING
    assert not window.isVisible()
