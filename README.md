# AniwatchTV Unofficial API

A clean, JSON-only FastAPI application that scrapes anime data, metadata, and streaming sources.

## Hybrid Targeting
The API supports hybrid targeting between two distinct domains:
- `aniwatchtv.to` (Default, `provider=tv`)
- `aniwatch.co.at` (`provider=co`)

You can switch the target backend on any endpoint by passing the `?provider=` query parameter (e.g., `/search?q=naruto&provider=co`).

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | API Welcome and endpoint directory. |
| `GET /home` | Fetches trending, spotlights, genres, and latest episodes. |
| `GET /search?q={query}&provider={tv|co}` | Search for anime by title. |
| `GET /anime/{id_or_slug}&provider={tv|co}` | Get full details, metadata, and season list. |
| `GET /episodes/{anime_id}&provider={tv|co}` | List all episodes for a specific series. |
| `GET /servers/{ep_id}&provider={tv|co}` | List available streaming servers for an episode. |
| `GET /sources/{server_id}&provider={tv|co}` | Get final iframe embed links. |
| `GET /megaplay/{ep_id}` | Direct megaplay.buzz iframe utility links. |
| `GET /megaplay/mal/{mal_id}/{ep_num}` | Get megaplay.buzz iframe URLs using MyAnimeList ID and Episode Number. |
| `GET /mal/search?q={query}` | Full MyAnimeList (MAL) search. Returns MAL IDs, titles, and metadata. |
| `GET /genre/{name}&provider={tv|co}` | Fetch anime list for a specific genre. |

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
