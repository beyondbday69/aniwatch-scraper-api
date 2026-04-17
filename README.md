# AniwatchTV API (Unofficial)

FastAPI-based scraper and API for `aniwatchtv.to`. Fetches anime details, search results, episode lists, and streaming sources.

## Live Demo
- **API Base:** [https://aniwatch-scraper-kappa.vercel.app](https://aniwatch-scraper-kappa.vercel.app)
- **Iframe Tester:** [/tester](https://aniwatch-scraper-kappa.vercel.app/tester)

## Features
- **Slug Resolution:** Automatically resolves numeric IDs (e.g., `37`) to full slugs (`monster-37`).
- **AJAX Support:** Mimics official site requests to bypass dynamic loading.
- **Iframe Tester:** Built-in tool to verify streaming links.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /popular` | Top trending anime on home page. |
| `GET /search?q={query}` | Search anime by title or ID. Returns full slugs. |
| `GET /anime/{id_or_slug}` | Detailed metadata, description, and season list. |
| `GET /episodes/{anime_id}` | Full episode list with IDs for a series. |
| `GET /servers/{ep_id}` | List of available servers (VidSrc, MegaCloud, etc.). |
| `GET /sources/{server_id}` | Final embed link/iframe URL. |
| `GET /tester` | Web interface to test iframe URLs. |

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
