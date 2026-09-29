"""Последовательная очередь в отдельном потоке; GUI меняется только через сигналы."""

from threading import Event

from PySide6.QtCore import QThread, Signal

from .downloader import DownloadService
from .models import DownloadOptions, DownloadResult, Status


class DownloadWorker(QThread):
    progress = Signal(int, object)
    result = Signal(int, object)
    warning = Signal(str)

    def __init__(self, jobs: list[tuple[int, str]], options: DownloadOptions, service: DownloadService):
        super().__init__()
        self.jobs = jobs
        self.options = options
        self.service = service
        self.stop_event = Event()

    def cancel(self):
        self.stop_event.set()

    def run(self):
        for index, url in self.jobs:
            if self.stop_event.is_set():
                break
            try:
                result = self.service.download(
                    url, self.options, self.stop_event,
                    lambda progress, row=index: self.progress.emit(row, progress),
                )
            except Exception as exc:
                # Граница потока: неожиданный сбой одного видео не ломает очередь.
                result = DownloadResult(url, Status.ERROR, message=f"Помилка завантажувача: {str(exc)[:350]}")
            try:
                self.service.storage.record(result)
            except Exception as exc:
                self.warning.emit(f"Не вдалося записати історію: {exc}")
            self.result.emit(index, result)
