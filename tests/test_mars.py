"""Tests for the The Daily Martian rebuild. All NASA HTTP is stubbed."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nasa
from cache import cached


# ---------- fakes ----------

class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")


SEARCH_PAYLOAD = {
    "collection": {
        "metadata": {"total_hits": 2},
        "items": [
            {
                "data": [{
                    "nasa_id": "PIA12345",
                    "title": "Mars Test Photo",
                    "description": "A test view of Mars.",
                    "date_created": "2021-03-04T00:00:00Z",
                    "keywords": ["Mars"],
                }],
                "links": [{"href": "https://images-assets.nasa.gov/image/PIA12345/PIA12345~small.jpg"}],
            },
            {
                "data": [{
                    "nasa_id": "PIA99999",
                    "title": "No Links Photo",
                    "description": "",
                    "date_created": "2020-01-01T00:00:00Z",
                }],
                # no links key at all
            },
        ],
    }
}

APOD_PAYLOAD = {
    "date": "2026-10-06",
    "title": "Test APOD",
    "explanation": "An explanation.",
    "url": "https://example.com/apod.jpg",
    "media_type": "image",
}


class FakeCollection:
    def __init__(self):
        self.docs = {}

    def find_one(self, filt):
        return self.docs.get(filt.get("_id"))

    def replace_one(self, filt, doc, upsert=False):
        self.docs[filt["_id"]] = doc


class FakeDB:
    def __init__(self):
        self.cols = {}

    def __getitem__(self, name):
        return self.cols.setdefault(name, FakeCollection())


# ---------- nasa.py ----------

def test_search_parses_items(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params))
        return FakeResponse(SEARCH_PAYLOAD)

    monkeypatch.setattr(nasa.requests, "get", fake_get)
    result = nasa.search_images("mars rover", page=2)
    assert result["total_hits"] == 2
    assert len(result["items"]) == 2
    first = result["items"][0]
    assert first["nasa_id"] == "PIA12345"
    assert first["title"] == "Mars Test Photo"
    assert first["date"] == "2021-03-04"
    assert first["thumb_url"].endswith("PIA12345~small.jpg")
    assert first["large_url"].endswith("PIA12345~large.jpg")
    # item without links falls back to derived urls
    assert result["items"][1]["thumb_url"].endswith("PIA99999~small.jpg")
    assert calls[0][1]["page"] == 2
    assert calls[0][1]["media_type"] == "image"


def test_search_empty_results(monkeypatch):
    monkeypatch.setattr(
        nasa.requests, "get",
        lambda *a, **k: FakeResponse({"collection": {"metadata": {}, "items": []}}),
    )
    result = nasa.search_images("zzz-no-such-thing")
    assert result == {"items": [], "total_hits": 0}


def test_search_http_error_raises(monkeypatch):
    monkeypatch.setattr(
        nasa.requests, "get", lambda *a, **k: FakeResponse({}, status=500)
    )
    with pytest.raises(Exception):
        nasa.search_images("mars")


def test_get_apod(monkeypatch):
    monkeypatch.setattr(
        nasa.requests, "get", lambda *a, **k: FakeResponse(APOD_PAYLOAD)
    )
    apod = nasa.get_apod("DEMO_KEY")
    assert apod["title"] == "Test APOD"
    assert apod["media_type"] == "image"


# ---------- cache.py ----------

def test_cache_hit_avoids_fetch():
    db = FakeDB()
    db["nasa_cache"].docs["k"] = {
        "_id": "k", "data": {"v": 1}, "cached_at": time.time()
    }
    calls = []
    out = cached(db, "k", 24, lambda: calls.append(1) or {"v": 2})
    assert out == {"v": 1}
    assert calls == []


def test_cache_expiry_refetches():
    db = FakeDB()
    db["nasa_cache"].docs["k"] = {
        "_id": "k", "data": {"v": 1}, "cached_at": time.time() - 25 * 3600
    }
    out = cached(db, "k", 24, lambda: {"v": 2})
    assert out == {"v": 2}
    assert db["nasa_cache"].docs["k"]["data"] == {"v": 2}


def test_cache_failure_returns_stale():
    db = FakeDB()
    db["nasa_cache"].docs["k"] = {
        "_id": "k", "data": {"v": 1}, "cached_at": time.time() - 99 * 3600
    }

    def boom():
        raise RuntimeError("nasa is down")

    assert cached(db, "k", 24, boom) == {"v": 1}


def test_cache_failure_no_doc_raises():
    db = FakeDB()

    def boom():
        raise RuntimeError("nasa is down")

    with pytest.raises(RuntimeError):
        cached(db, "missing", 24, boom)


# ---------- Flask app ----------

def _load_app(monkeypatch):
    """Import app with stubbed MongoClient and stubbed NASA HTTP."""
    import pymongo

    dbs = {}

    class FakeClient:
        def __init__(self, uri):
            self.uri = uri

        def __getitem__(self, name):
            return dbs.setdefault(name, FakeDB())

    monkeypatch.setattr(pymongo, "MongoClient", FakeClient)
    monkeypatch.setenv("MONGO_URI", "mongodb://fake:27017/test")

    def fake_get(url, params=None, timeout=None):
        if "apod" in url:
            return FakeResponse(APOD_PAYLOAD)
        return FakeResponse(SEARCH_PAYLOAD)

    monkeypatch.setattr(nasa.requests, "get", fake_get)

    for mod in [m for m in list(sys.modules) if m in ("app", "nasa", "cache")]:
        del sys.modules[mod]
    import app as appmod
    return appmod


def test_pages_200(monkeypatch):
    appmod = _load_app(monkeypatch)
    client = appmod.app.test_client()
    for path in ["/", "/gallery", "/gallery?q=mars&page=2",
                 "/api/search?q=mars", "/api/apod", "/api/topics"]:
        resp = client.get(path)
        assert resp.status_code == 200, path
    # content sanity
    home = client.get("/").get_data(as_text=True)
    assert "The Daily Martian" in home
    assert "Test APOD" in home
    gal = client.get("/gallery").get_data(as_text=True)
    assert "Mars Test Photo" in gal
    api = client.get("/api/search?q=mars").get_json()
    assert api["total_hits"] == 2 and len(api["items"]) == 2


def test_gallery_bad_page_defaults(monkeypatch):
    appmod = _load_app(monkeypatch)
    client = appmod.app.test_client()
    assert client.get("/gallery?page=bogus").status_code == 200


def test_missing_mongo_uri_fails_fast():
    import subprocess
    code = (
        "import os, sys; "
        "os.environ.pop('MONGO_URI', None); "
        "sys.path.insert(0, '/home/hatch/workspace/daily-martian'); "
        "import app"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode != 0
    assert "MONGO_URI" in proc.stderr
