from reelsave.models import DownloadResult, Status
from reelsave.storage import Storage

URL = "https://www.instagram.com/reel/abc/"


def test_history_persists_and_skip_requires_existing_file_in_same_folder(storage, tmp_path):
    video = tmp_path / "видео.mp4"
    video.write_bytes(b"video")
    storage.record(DownloadResult(URL, Status.DONE, video, "Test"))
    reopened = Storage(storage.directory)
    assert reopened.history()[0]["title"] == "Test"
    assert reopened.existing_file(URL, tmp_path) == video
    assert reopened.existing_file(URL, tmp_path / "another") is None
    video.unlink()
    assert reopened.existing_file(URL, tmp_path) is None


def test_zero_length_files_are_not_skipped(storage, tmp_path):
    path = tmp_path / "empty.mp4"
    path.touch()
    storage.record(DownloadResult(URL, Status.DONE, path))
    assert storage.existing_file(URL, tmp_path) is None


def test_settings_unicode_and_corruption(storage):
    storage.save_settings("/tmp/Мои видео")
    assert storage.load_settings() == {"output_dir": "/tmp/Мои видео"}
    storage.settings_path.write_text("{broken", encoding="utf-8")
    assert storage.load_settings() == {}
    storage.settings_path.write_text("[]", encoding="utf-8")
    assert storage.load_settings() == {}


def test_legacy_history_is_translated_and_still_skipped(storage, tmp_path):
    video = tmp_path / "legacy.mp4"
    video.write_bytes(b"video")
    storage.record(DownloadResult(URL, Status.DONE, video, "Original title"))
    with storage.connection() as db:
        db.execute("UPDATE downloads SET status=?", ("Скачано",))
    reopened = Storage(storage.directory)
    assert reopened.history()[0]["status"] == "Завантажено"
    assert reopened.history()[0]["title"] == "Original title"
    assert reopened.existing_file(URL, tmp_path) == video
    assert Storage(storage.directory).history() == reopened.history()
