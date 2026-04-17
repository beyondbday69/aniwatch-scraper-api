# Aniwatch Unofficial API Scraper

A FastAPI application that scrapes anime data and video streaming links from `aniwatch.co.at`.

## Endpoints

- `GET /popular`: Returns the most popular anime list.
- `GET /search?q={query}`: Searches for an anime.
- `GET /episode?url={episode_url}`: Fetches the video servers and iframe links for a given episode URL.

## Local Testing

1. Create virtual environment and install requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```
   The API will be available on `http://127.0.0.1:6969`.

## Deployment

Deploy this project on Vercel:
```bash
npm i -g vercel
vercel
```
