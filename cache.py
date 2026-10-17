"""MongoDB-backed TTL cache for NASA API responses.

Documents look like: {_id: <cache key>, data: <json-able>, cached_at: <epoch>}.
Stale data is served rather than an error page when the upstream API fails.
"""
import time


def cached(db, key, ttl_hours, fetch_fn):
    """Return cached ``data`` if fresh; otherwise call ``fetch_fn`` and store.

    If the fetch raises and a (stale) document exists, the stale data is
    returned. If there is nothing cached at all, the exception propagates.
    """
    coll = db["nasa_cache"]
    now = time.time()
    doc = coll.find_one({"_id": key})
    if doc and now - doc.get("cached_at", 0) < ttl_hours * 3600:
        return doc["data"]
    try:
        data = fetch_fn()
    except Exception:
        if doc:
            return doc["data"]
        raise
    coll.replace_one(
        {"_id": key},
        {"_id": key, "data": data, "cached_at": now},
        upsert=True,
    )
    return data
