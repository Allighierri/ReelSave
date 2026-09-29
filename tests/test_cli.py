from pathlib import Path

import pytest

from reelsave.cli import main
from reelsave.models import DownloadResult, Status


def test_cli_rejects_invalid_links_before_downloading(capsys):
    with pytest.raises(SystemExit) as error:
        main(["https://example.org/reel/abc/"])
    assert error.value.code == 2
    assert "instagram.com" in capsys.readouterr().err


def test_cli_reports_missing_file(capsys, tmp_path):
    assert main(["--file", str(tmp_path / "missing.txt")]) == 1
    assert "Помилка" in capsys.readouterr().err


def test_cli_batch_continues_after_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("REELSAVE_DATA_DIR", str(tmp_path / "data"))
    calls = []

    def download(self, url, options, stop):
        calls.append(url)
        return DownloadResult(url, Status.ERROR if "broken" in url else Status.SKIPPED)

    monkeypatch.setattr("reelsave.cli.DownloadService.download", download)
    text_file = tmp_path / "links.txt"
    text_file.write_text("instagram.com/reel/broken/\ninstagram.com/reel/good/", encoding="utf-8-sig")
    assert main(["--file", str(text_file)]) == 1
    assert len(calls) == 2
    assert "Уже завантажено" in capsys.readouterr().out
