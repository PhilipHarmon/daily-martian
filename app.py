"""The Daily Martian — a NASA imagery explorer.

Powered by the NASA Image & Video Library (no key needed) and the Astronomy
Picture of the Day API. Responses are cached in MongoDB so the app stays fast
and far under rate limits.

Required env vars:
    MONGO_URI       full MongoDB Atlas connection string

Optional env vars:
    NASA_API_KEY    api.nasa.gov key (default: DEMO_KEY, 30 req/hour)
    MONGO_DB_NAME   database name (default: mars_app)
    PORT            local dev port (default: 5000)
"""
import os

from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient

import nasa
from cache import cached

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable is not set.")

NASA_API_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
DB_NAME = os.environ.get("MONGO_DB_NAME", "mars_app")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Curated starting points for the gallery (label, search query).
TOPICS = [
    ("Mars Rovers", "mars rover"),
    ("Martian Landscapes", "mars landscape"),
    ("Jezero Crater", "jezero crater"),
    ("Olympus Mons", "olympus mons"),
    ("Valles Marineris", "valles marineris"),
    ("Curiosity Rover", "mars curiosity rover"),
]

SEARCH_TTL_HOURS = 24
APOD_TTL_HOURS = 24

app = Flask(__name__)


def get_search(query, page):
    key = f"search:{query.strip().lower()}:{page}"
    return cached(
        db, key, SEARCH_TTL_HOURS, lambda: nasa.search_images(query, page=page)
    )


@app.route("/")
def index():
    apod = cached(db, "apod", APOD_TTL_HOURS, lambda: nasa.get_apod(NASA_API_KEY))
    strips = []
    for label, query in TOPICS[:3]:
        result = get_search(query, 1)
        strips.append(
            {"label": label, "query": query, "items": result["items"][:8]}
        )
    return render_template("index.html", apod=apod, strips=strips, topics=TOPICS)


@app.route("/gallery")
def gallery():
    query = request.args.get("q", "mars rover").strip() or "mars rover"
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    result = get_search(query, page)
    total = result["total_hits"]
    pages = max(1, -(-total // nasa.PAGE_SIZE))
    return render_template(
        "gallery.html",
        items=result["items"],
        query=query,
        page=page,
        total=total,
        pages=min(pages, 100),
        topics=TOPICS,
    )


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "mars rover").strip() or "mars rover"
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    result = get_search(query, page)
    return jsonify(
        {
            "query": query,
            "page": page,
            "total_hits": result["total_hits"],
            "items": result["items"],
        }
    )


@app.route("/api/apod")
def api_apod():
    return jsonify(
        cached(db, "apod", APOD_TTL_HOURS, lambda: nasa.get_apod(NASA_API_KEY))
    )


@app.route("/api/topics")
def api_topics():
    return jsonify([{"label": label, "query": query} for label, query in TOPICS])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
