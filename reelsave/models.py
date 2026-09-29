"""Общие типы данных; этот модуль не зависит от Qt."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Status(StrEnum):
    WAITING = "У черзі"
    FETCHING = "Отримання відео"
    DOWNLOADING = "Завантаження"
    DONE = "Завантажено"
    SKIPPED = "Уже завантажено"
    ERROR = "Помилка"
    CANCELLED = "Зупинено"


@dataclass(frozen=True)
class DownloadOptions:
    output_dir: Path
    cookies_file: Path | None = None


@dataclass(frozen=True)
class Progress:
    status: Status
    percent: int | None = None
    speed: float | None = None
    eta: float | None = None


@dataclass(frozen=True)
class DownloadResult:
    url: str
    status: Status
    path: Path | None = None
    title: str = ""
    message: str = ""


@dataclass
class QueueItem:
    url: str
    status: Status = Status.WAITING
    path: Path | None = None
    message: str = ""
