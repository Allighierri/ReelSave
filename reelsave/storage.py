"""Настройки JSON и история SQLite. Соединение с БД открывается на одну операцию."""

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import DownloadResult, Status


def data_directory() -> Path:
    # Переопределение полезно для тестов и переносимой установки.
    if override := os.environ.get("REELSAVE_DATA_DIR"):
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "ReelSave"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/ReelSave"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "reelsave"


class Storage:
    def __init__(self, directory: Path | None = None):
        self.directory = directory if directory is not None else data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db_path = self.directory / "history.sqlite3"
        self.settings_path = self.directory / "settings.json"
        with self.connection() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    path TEXT,
                    message TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS downloads_url ON downloads(url)")
            # Сумісність з історією першої, російськомовної версії.
            legacy_statuses = {
                "В очереди": Status.WAITING,
                "Получение видео": Status.FETCHING,
                "Скачивание": Status.DOWNLOADING,
                "Скачано": Status.DONE,
                "Уже скачано": Status.SKIPPED,
                "Ошибка": Status.ERROR,
                "Остановлено": Status.CANCELLED,
            }
            db.executemany(
                "UPDATE downloads SET status=? WHERE status=?",
                [(str(status), legacy) for legacy, status in legacy_statuses.items()],
            )

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def load_settings(self) -> dict:
        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return settings if isinstance(settings, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_settings(self, output_dir: str) -> None:
        # Cookies и пути к ним намеренно не сохраняются в настройках.
        temporary = self.settings_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"output_dir": output_dir}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.settings_path)

    def record(self, result: DownloadResult) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO downloads(created_at, url, title, status, path, message) VALUES(?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), result.url,
                 result.title, str(result.status), str(result.path) if result.path else None, result.message),
            )

    def history(self, limit: int = 300) -> list[dict]:
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM downloads ORDER BY id DESC LIMIT ?", (limit,)
            )]

    def existing_file(self, url: str, output_dir: Path) -> Path | None:
        with self.connection() as db:
            rows = db.execute(
                "SELECT path FROM downloads WHERE url=? AND status IN (?,?) ORDER BY id DESC",
                (url, str(Status.DONE), str(Status.SKIPPED)),
            ).fetchall()
        for row in rows:
            if row["path"]:
                path = Path(row["path"])
                if path.parent.resolve() == output_dir.resolve() and path.is_file() and path.stat().st_size:
                    return path
        return None
