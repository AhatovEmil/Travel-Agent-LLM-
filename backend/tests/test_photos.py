"""Тесты галереи фото направления."""

from app.services.photos import clear_photos_cache, destination_photos


def test_destination_photos_cached(monkeypatch, tmp_path):
    clear_photos_cache()
    calls = {"n": 0}

    fake_payload = {
        "query": {
            "pages": {
                "1": {
                    "title": "File:Batumi Boulevard.jpg",
                    "imageinfo": [
                        {
                            "mime": "image/jpeg",
                            "url": "https://example.com/full.jpg",
                            "thumburl": "https://example.com/thumb.jpg",
                            "thumbwidth": 1200,
                            "thumbheight": 800,
                            "extmetadata": {
                                "Artist": {"value": "Test Author"},
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                            },
                        }
                    ],
                },
                "2": {
                    "title": "File:Batumi map.svg",
                    "imageinfo": [
                        {
                            "mime": "image/svg+xml",
                            "url": "https://example.com/map.svg",
                            "thumburl": "https://example.com/map.svg",
                            "thumbwidth": 800,
                            "thumbheight": 600,
                            "extmetadata": {},
                        }
                    ],
                },
            }
        }
    }

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return fake_payload

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            calls["n"] += 1
            return FakeResp()

    monkeypatch.setattr("app.services.photos.httpx.Client", FakeClient)
    monkeypatch.setattr("app.services.photos._CACHE_PATH", tmp_path / "photos.json")

    a = destination_photos("Батуми", limit=5)
    b = destination_photos("Батуми", limit=5)
    assert len(a) == 1
    assert a[0]["url"] == "https://example.com/thumb.jpg"
    assert "Test Author" in a[0]["credit"]
    assert b == a
    assert calls["n"] == 1


def test_trip_photos_endpoint(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.routers.trips.destination_photos",
        lambda dest, limit=8: [
            {
                "url": "https://example.com/a.jpg",
                "full_url": "https://example.com/a.jpg",
                "title": "Batumi",
                "credit": "CC",
                "source": "wikimedia",
            }
        ],
    )
    trip_id = client.post(
        "/api/trips",
        json={
            "name": "Батуми",
            "brief": "Направление: Батуми. Длительность: 3 дн. достаточно текста для брифа.",
        },
        headers=auth_headers,
    ).json()["id"]
    res = client.get(f"/api/trips/{trip_id}/photos", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["destination"] == "Батуми"
    assert len(body["photos"]) == 1
