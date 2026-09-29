from pathlib import Path
from threading import Event

import pytest
from yt_dlp.utils import DownloadError

from reelsave.downloader import DownloadService
from reelsave.models import DownloadOptions, Status

URL = "https://www.instagram.com/reel/abc/"


class FakeYDL:
    def __init__(self, options):
        self.options = options
        self.path = Path(options["paths"]["home"]) / "test_abc.mp4"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download):
        for hook in self.options["progress_hooks"]:
            hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})
        self.path.write_bytes(b"test payload")
        for hook in self.options["progress_hooks"]:
            hook({"status": "finished", "filename": str(self.path)})
        return {"id": "abc", "title": "Test reel"}

    def prepare_filename(self, info):
        return str(self.path)


def test_success_progress_and_skip(storage, tmp_path):
    service = DownloadService(storage, FakeYDL)
    events = []
    options = DownloadOptions(tmp_path / "video")
    result = service.download(URL, options, Event(), events.append)
    assert result.status == Status.DONE
    assert result.path.read_bytes() == b"test payload"
    assert events[-1].percent == 50
    storage.record(result)
    assert service.download(URL, options, Event()).status == Status.SKIPPED
    result.path.unlink()
    assert service.download(URL, options, Event()).status == Status.DONE


def test_cancellation_during_progress(storage, tmp_path):
    stop = Event()

    def on_progress(progress):
        if progress.status == Status.DOWNLOADING:
            stop.set()

    result = DownloadService(storage, FakeYDL).download(URL, DownloadOptions(tmp_path), stop, on_progress)
    assert result.status == Status.CANCELLED


def test_cancel_before_network(storage, tmp_path):
    stop = Event()
    stop.set()
    service = DownloadService(storage, lambda _: pytest.fail("Network must not start"))
    assert service.download(URL, DownloadOptions(tmp_path), stop).status == Status.CANCELLED


@pytest.mark.parametrize("message,expected", [
    ("Login required", "cookies"), ("HTTP Error 429", "обмежив"),
    ("Connection timed out", "інтернет"), ("Video unavailable", "недоступний"),
])
def test_actionable_errors(storage, tmp_path, message, expected):
    class BrokenYDL(FakeYDL):
        def extract_info(self, *args, **kwargs):
            raise DownloadError(message)

    result = DownloadService(storage, BrokenYDL).download(URL, DownloadOptions(tmp_path), Event())
    assert result.status == Status.ERROR
    assert expected in result.message


def test_missing_file_is_not_reported_as_success(storage, tmp_path):
    class EmptyYDL(FakeYDL):
        def extract_info(self, *args, **kwargs):
            return {"title": "No file"}

    result = DownloadService(storage, EmptyYDL).download(URL, DownloadOptions(tmp_path), Event())
    assert result.status == Status.ERROR


def test_output_is_a_file(storage, tmp_path):
    target = tmp_path / "not_a_directory"
    target.write_text("occupied")
    result = DownloadService(storage, FakeYDL).download(URL, DownloadOptions(target), Event())
    assert result.status == Status.ERROR
