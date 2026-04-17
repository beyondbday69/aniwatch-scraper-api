# AniwatchTV API (Unofficial)

FastAPI-based scraper and API for `aniwatchtv.to`. Fetches anime details, search results, episode lists, and streaming sources.

## Live Demo
- **API Base & Docs:** [https://aniwatch-scraper-kappa.vercel.app](https://aniwatch-scraper-kappa.vercel.app)
- **Iframe & Event Tester:** [/tester](https://aniwatch-scraper-kappa.vercel.app/tester)

## Features
- **Beautiful UI:** Built-in Swagger documentation at `/docs` for interactive testing.
- **Iframe Tester:** Debug MegaPlay and other iframes with live `postMessage` event logging.
- **Slug Resolution:** Automatically resolves numeric IDs (e.g., `37`) to full slugs (`monster-37`).
- **Rich Metadata:** Home page endpoint provides spotlight, trending, genres, and sidebar data.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /home` | Full homepage data (spotlight, trending, airing, popular, genres). |
| `GET /popular` | Top trending anime on home page. |
| `GET /search?q={query}` | Search anime. Returns full slugs. |
| `GET /anime/{id_or_slug}` | Detailed metadata, synopsis, and season list. |
| `GET /episodes/{anime_id}` | Full episode list with IDs. |
| `GET /servers/{ep_id}` | Available servers (VidSrc, MegaCloud, etc.). |
| `GET /megaplay/{ep_id}` | Direct Megaplay.buzz sub/dub iframe URLs. |
| `GET /sources/{server_id}` | Final embed link/iframe URL. |
| `GET /tester` | Web interface to test iframes and capture events. |

## Local Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run server:**
   ```bash
   python app.py
   ```
   API runs at `http://localhost:6969`.

## Deployment
Deploy to Vercel:
```bash
vercel --prod
```

## Disclaimer
This project is for educational purposes only. All content belongs to the original site.
