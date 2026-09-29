import pytest

from reelsave.urls import normalize_url, parse_urls


@pytest.mark.parametrize("value", [
    "https://www.instagram.com/reel/Ab_12-x/?igsh=tracking#fragment",
    "instagram.com/reels/Ab_12-x",
    " https://m.instagram.com/reel/Ab_12-x/ ",
])
def test_normalizes_equivalent_links(value):
    assert normalize_url(value) == "https://www.instagram.com/reel/Ab_12-x/"


@pytest.mark.parametrize("value", [
    "https://instagram.com.evil.test/reel/abc/", "http://instagram.com/reel/abc/",
    "https://instagram.com@evil.test/reel/abc/", "https://user@instagram.com/reel/abc/",
    "https://instagram.com/reels/audio/123/", "https://instagram.com/some_profile/",
    "https://instagram.com/reel/abc/extra", "file:///reel/abc/", "",
    "https://instagram.com:999/reel/abc/", "https://instagram.com:invalid/reel/abc/",
])
def test_rejects_other_resources(value):
    with pytest.raises(ValueError):
        normalize_url(value)


def test_batch_deduplication_and_line_errors():
    urls, errors = parse_urls("\n# Comment\ninstagram.com/reel/abc/\n"
                              "https://www.instagram.com/reels/abc/?igsh=1\ninvalid\n")
    assert urls == ["https://www.instagram.com/reel/abc/"]
    assert len(errors) == 1
    assert "Рядок 5" in errors[0]
