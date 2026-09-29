"""Дополнительный консольный интерфейс для автоматизации."""

import argparse
import sqlite3
import sys
from pathlib import Path
from threading import Event

from .downloader import DownloadService
from .models import DownloadOptions, Status
from .storage import Storage
from .urls import parse_urls


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ReelSave — завантажити Instagram Reels")
    parser.add_argument("urls", nargs="*", help="Посилання на окремі Reels")
    parser.add_argument("--file", type=Path, help="Текстовий файл із посиланнями, UTF-8")
    parser.add_argument("-o", "--output", type=Path, default=Path.home() / "Downloads/ReelSave")
    parser.add_argument("--cookies", type=Path, help="Файл cookies у форматі Netscape")
    args = parser.parse_args(argv)
    try:
        text = "\n".join(args.urls)
        if args.file:
            text += "\n" + args.file.read_text(encoding="utf-8-sig")
        urls, errors = parse_urls(text)
        if errors or not urls:
            parser.error("\n".join(errors) if errors else "Додай посилання або --file.")
        if args.cookies and not args.cookies.is_file():
            parser.error("Файл cookies не знайдено.")
        storage = Storage()
        service = DownloadService(storage)
        failures = 0
        for url in urls:
            result = service.download(url, DownloadOptions(args.output, args.cookies), Event())
            storage.record(result)
            print(f"{result.status}: {url}\n  {result.path or result.message}")
            failures += result.status == Status.ERROR
        return 1 if failures else 0
    except KeyboardInterrupt:
        print("\nЗавантаження перервано.", file=sys.stderr)
        return 130
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Помилка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
