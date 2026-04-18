# AniwatchTV Unofficial API

A clean, JSON-only FastAPI application that scrapes anime data, metadata, and streaming sources from `aniwatchtv.to`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API Welcome and endpoint directory. |
| `GET /home` | Fetches trending, spotlights, genres, and latest episodes. |
| `GET /search?q={query}` | Search for anime by title. |
| `GET /anime/{id_or_slug}` | Get full details, metadata, and season list. |
| `GET /episodes/{anime_id}` | List all episodes for a specific series. |
| `GET /servers/{ep_id}` | List available streaming servers for an episode. |
| `GET /sources/{server_id}` | Get final iframe embed links. |
| `GET /megaplay/{ep_id}` | Direct megaplay.buzz iframe utility links. |
| `GET /genre/{name}` | Fetch anime list for a specific genre. |

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
Educational purposes only.
