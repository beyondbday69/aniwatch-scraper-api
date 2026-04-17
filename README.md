# AniwatchTV Unofficial API Scraper

A FastAPI application that scrapes anime data and video streaming links from `aniwatchtv.to`.

## Endpoints

- **`GET /popular`**: Returns the most popular anime list from the home page.
- **`GET /search?q={query}`**: Searches for an anime and returns items with their `anime_id`.
- **`GET /anime/{anime_id_or_slug}`**: Fetches full anime details, including description, images, metadata, and all seasons.
- **`GET /episodes/{anime_id}`**: Fetches the full list of episodes for a specific anime.
- **`GET /servers/{ep_id}`**: Fetches available video servers (VidSrc, MegaCloud, etc.) for a specific episode.
- **`GET /sources/{server_id}`**: Fetches the final embed link/iframe for a specific server.

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
vercel --prod
```
