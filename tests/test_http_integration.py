"""Настоящий yt-dlp и локальный HTTP: подменяется только получение метаданных Instagram."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor

from reelsave.downloader import DownloadService
from reelsave.models import DownloadOptions, Status


def test_real_ytdlp_downloads_bytes_and_resumes_history(storage, tmp_path):
    payload = b"local HTTP download fixture\n" * 4096

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    media_url = f"http://127.0.0.1:{server.server_port}/video.mp4"

    class LocalReelIE(InfoExtractor):
        _VALID_URL = r"https://www\.instagram\.com/reel/(?P<id>localfixture)/"

        def _real_extract(self, url):
            return {"id": "localfixture", "title": "HTTP fixture", "uploader_id": "tester",
                    "url": media_url, "ext": "mp4"}

    def factory(options):
        ydl = YoutubeDL(options, auto_init=False)
        ydl.add_info_extractor(LocalReelIE())
        return ydl

    try:
        service = DownloadService(storage, factory)
        options = DownloadOptions(tmp_path / "Мои видео")
        result = service.download("https://www.instagram.com/reel/localfixture/", options, Event())
        assert result.status == Status.DONE, result.message
        assert result.path.read_bytes() == payload
        # Второй запуск проверяет уже существующий файл на уровне настоящего yt-dlp.
        second = service.download(result.url, options, Event())
        assert second.status == Status.DONE
        storage.record(result)
        assert service.download(result.url, options, Event()).status == Status.SKIPPED
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
