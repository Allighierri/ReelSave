"""Сервис загрузки. Не зависит от интерфейса и используется также из CLI."""

from pathlib import Path
from threading import Event
from typing import Callable

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .models import DownloadOptions, DownloadResult, Progress, Status
from .storage import Storage
from .urls import normalize_url


class DownloadCancelled(Exception):
    """Кооперативная остановка из progress hook, без уничтожения потока."""


def readable_error(error: Exception) -> str:
    raw = str(error)
    lower = raw.lower()
    if any(word in lower for word in ("login", "log in", "sign in", "cookies", "private")):
        return "Instagram вимагає входу. Підключи cookies.txt облікового запису, якому доступний ролик."
    if any(word in lower for word in ("429", "rate limit", "too many requests")):
        return "Instagram обмежив запити. Зачекай і повтори завантаження пізніше."
    if any(word in lower for word in ("404", "not available", "unavailable", "not found")):
        return "Ролик видалено або він недоступний цьому обліковому запису. Перевір посилання в браузері."
    if any(word in lower for word in ("timed out", "timeout", "connection", "resolve", "network")):
        return "Немає відповіді від Instagram. Перевір інтернет і повтори спробу."
    if isinstance(error, OSError):
        return f"Не вдалося прочитати або зберегти файл: {raw}"
    return f"Не вдалося завантажити ролик. Спробуй cookies або онови yt-dlp. {raw[:350]}"


class DownloadService:
    def __init__(self, storage: Storage, ydl_factory=YoutubeDL):
        self.storage = storage
        self.ydl_factory = ydl_factory

    def download(
        self,
        url: str,
        options: DownloadOptions,
        stop: Event,
        notify: Callable[[Progress], None] = lambda _: None,
    ) -> DownloadResult:
        url = normalize_url(url)
        output = options.output_dir.expanduser().resolve()
        completed_files: list[Path] = []

        def check_cancelled():
            if stop.is_set():
                raise DownloadCancelled()

        def progress_hook(data: dict):
            check_cancelled()
            if data["status"] == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate")
                percent = min(99, int(data.get("downloaded_bytes", 0) * 100 / total)) if total else None
                notify(Progress(Status.DOWNLOADING, percent, data.get("speed"), data.get("eta")))
            elif data["status"] == "finished":
                completed_files.append(Path(data["filename"]))

        try:
            check_cancelled()
            output.mkdir(parents=True, exist_ok=True)
            if existing := self.storage.existing_file(url, output):
                return DownloadResult(url, Status.SKIPPED, existing, existing.stem)
            if options.cookies_file and not options.cookies_file.is_file():
                raise OSError("Файл cookies.txt не знайдено.")
            notify(Progress(Status.FETCHING))
            settings = {
                "format": "best",  # Найкращий готовий потік із відео та звуком, без FFmpeg.
                "paths": {"home": str(output)},
                "outtmpl": "%(uploader_id|instagram)s_%(id)s.%(ext)s",
                "windowsfilenames": True,
                "noplaylist": True,
                "overwrites": False,
                "continuedl": True,
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "progress_delta": 0.2,
                "retries": 2,
                "fragment_retries": 2,
                "extractor_retries": 1,
                "socket_timeout": 15,
                "cachedir": False,
                "progress_hooks": [progress_hook],
            }
            if options.cookies_file:
                settings["cookiefile"] = str(options.cookies_file.expanduser().resolve())
            with self.ydl_factory(settings) as ydl:
                info = ydl.extract_info(url, download=True)
                check_cancelled()
                if not info:
                    raise DownloadError("Instagram не повернув інформацію про ролик.")
                # У уже существующего файла hook может не сработать.
                completed_files.append(Path(ydl.prepare_filename(info)))
            path = next((p.resolve() for p in completed_files if p.is_file() and p.stat().st_size), None)
            if path is None:
                raise DownloadError("Завантажувач завершив роботу, але відеофайл не знайдено.")
            return DownloadResult(url, Status.DONE, path, info.get("title") or path.stem)
        except DownloadCancelled:
            return DownloadResult(url, Status.CANCELLED, message="Завантаження можна запустити повторно.")
        except (DownloadError, OSError) as exc:
            if stop.is_set():
                return DownloadResult(url, Status.CANCELLED, message="Завантаження зупинено.")
            return DownloadResult(url, Status.ERROR, message=readable_error(exc))
