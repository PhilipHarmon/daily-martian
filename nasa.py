"""NASA API access: Image & Video Library + APOD.

All calls go through plain ``requests`` with a short timeout. Results are
normalized to small, JSON-serializable dicts so they can be cached in MongoDB.
"""
import requests

IMAGE_API = "https://images-api.nasa.gov"
APOD_URL = "https://api.nasa.gov/planetary/apod"
TIMEOUT = 10
PAGE_SIZE = 24


def image_urls(nasa_id):
    """Derive the images-assets URLs for a NASA image ID (no extra fetch)."""
    base = f"https://images-assets.nasa.gov/image/{nasa_id}/{nasa_id}"
    return {
        "thumb": f"{base}~thumb.jpg",
        "small": f"{base}~small.jpg",
        "medium": f"{base}~medium.jpg",
        "large": f"{base}~large.jpg",
    }


def normalize_item(item):
    """Shrink one images-api search item to the fields the app needs."""
    data = (item.get("data") or [{}])[0]
    nasa_id = data.get("nasa_id") or ""
    urls = image_urls(nasa_id)
    links = item.get("links") or []
    thumb = links[0].get("href") if links else urls["small"]
    return {
        "nasa_id": nasa_id,
        "title": data.get("title") or "Untitled",
        "description": data.get("description") or "",
        "date": (data.get("date_created") or "")[:10],
        "keywords": data.get("keywords") or [],
        "thumb_url": thumb,
        "medium_url": urls["medium"],
        "large_url": urls["large"],
    }


def search_images(query, page=1, page_size=PAGE_SIZE):
    """Search the NASA Image Library. Returns {"items", "total_hits"}.

    Raises requests.HTTPError (or friends) when the API is unreachable —
    callers decide how to degrade.
    """
    params = {
        "q": query,
        "media_type": "image",
        "page": max(1, page),
        "page_size": page_size,
    }
    resp = requests.get(f"{IMAGE_API}/search", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    collection = resp.json().get("collection", {})
    items = [
        normalize_item(it)
        for it in collection.get("items", [])
        if (it.get("data") or [{}])[0].get("nasa_id")
    ]
    try:
        total = int(collection.get("metadata", {}).get("total_hits", 0))
    except (TypeError, ValueError):
        total = 0
    return {"items": items, "total_hits": total}


def get_apod(api_key="DEMO_KEY"):
    """Fetch today's Astronomy Picture of the Day."""
    resp = requests.get(APOD_URL, params={"api_key": api_key}, timeout=TIMEOUT)
    resp.raise_for_status()
    d = resp.json()
    return {
        "date": d.get("date", ""),
        "title": d.get("title", ""),
        "explanation": d.get("explanation", ""),
        "url": d.get("url", ""),
        "hdurl": d.get("hdurl") or d.get("url", ""),
        "media_type": d.get("media_type", "image"),
        "thumbnail_url": d.get("thumbnail_url", ""),
    }
