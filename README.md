# The Daily Martian

A NASA imagery explorer — browse thousands of real Mars photos from NASA's
Image & Video Library, plus the daily Astronomy Picture of the Day. A modern
rebuild of the 2020 Mars scraper: no scraping, no browser automation, just
free official NASA APIs.

## NASA APIs used

- **NASA Image & Video Library** (`images-api.nasa.gov`) — free, no key
  required. Searchable Mars imagery: rover photos, landscapes, craters.
- **Astronomy Picture of the Day** (`api.nasa.gov/planetary/apod`) — free key
  from https://api.nasa.gov. Works with the shared `DEMO_KEY`, but that's
  rate-limited to 30 requests/hour, so set your own `NASA_API_KEY`.

> Note: the old `api.nasa.gov/mars-photos` rover API was a community Heroku
> app that was shut down in 2025 — this rebuild deliberately uses the Image
> Library instead, which is official, keyless, and actively maintained.

## Environment variables

| Name          | Required | Default   | Purpose                              |
|---------------|----------|-----------|--------------------------------------|
| `MONGO_URI`   | yes      | —         | MongoDB Atlas connection string      |
| `NASA_API_KEY`| no       | `DEMO_KEY`| api.nasa.gov key (APOD only)         |
| `MONGO_DB_NAME`| no      | `mars_app`| Mongo database name                  |

API responses are cached in MongoDB (`nasa_cache` collection, 24h TTL), so
the app stays fast and far under rate limits. Stale cache is served rather
than an error page if NASA's APIs hiccup.

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
MONGO_URI="mongodb+srv://..." python app.py
```

## Deploy on Render

1. Push this folder to a GitHub repo.
2. Render dashboard → **New → Blueprint** → select the repo → **Apply**.
3. Open the service → **Environment** → set `MONGO_URI` (and optionally
   `NASA_API_KEY` — get a free one at https://api.nasa.gov).
4. In Atlas → Network Access, allow `0.0.0.0/0` so Render can connect.

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
```
