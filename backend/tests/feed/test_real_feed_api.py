from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

LIVE_FEEDS = [
    pytest.param("rss2", "https://hnrss.org/frontpage", id="real-rss-hacker-news"),
    pytest.param("atom", "https://xkcd.com/atom.xml", id="real-atom-xkcd"),
]


@pytest.mark.network
@pytest.mark.parametrize(("expected_format", "url"), LIVE_FEEDS)
def test_real_rss_and_atom_sources_parse_via_api(
    client: TestClient,
    expected_format: str,
    url: str,
) -> None:
    response = client.post("/feeds/parse", json={"url": url})

    assert response.status_code != 500, response.text
    if response.status_code in {502, 504}:
        pytest.skip(f"Live feed source is temporarily unavailable: {url}")

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["format"] == expected_format
    assert payload["title"].strip()
    assert payload["feed_url"].startswith("http")
    assert len(payload["entries"]) > 0

    first_entry = payload["entries"][0]
    populated_core_fields = [
        bool(first_entry.get("title", "").strip()),
        bool(first_entry.get("url", "").strip()),
        bool(first_entry.get("published_at", "").strip()),
    ]
    assert sum(populated_core_fields) >= 2
