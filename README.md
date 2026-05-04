# shnwazdev-GaanaAPI

Unofficial Gaana metadata API built with Flask, redesigned for Vercel deployment and local development. It includes a clean docs website, health checks, song lookup, album lookup, search, artwork, lyrics, stream status, URL resolve helpers, and a machine-readable endpoint catalog.

Dev by `SHNWAZ`.

[Original project](https://github.com/cyberboysumanjay/GaanaAPI) by Sumanjay. This repo is a modernized fork for `shnwazdeveloper`.

## Features

- Flask API ready for Vercel serverless deployment
- Local development server on port `5555`
- Clean web docs at `/` and `/docs`
- Health checks at `/health` and `/api/health`
- Song metadata by Gaana URL or seokey
- Album metadata with track lists
- Search endpoint for songs, albums, artists, playlists, and mixed results
- Artwork, lyrics, stream-status, sample, and resolve helper endpoints
- CORS headers enabled for frontend clients

## Live Local URL

After starting the app, open:

```text
http://localhost:5555
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The app runs at:

```text
http://localhost:5555
```

## API Examples

Fetch one song:

```bash
curl "http://localhost:5555/api/song/alone-1435"
```

Fetch song metadata using the original route:

```bash
curl "http://localhost:5555/result/?url=https://gaana.com/song/alone-1435&lyrics=true"
```

Search songs:

```bash
curl "http://localhost:5555/api/search?q=alone&type=song&limit=5"
```

Fetch album tracks:

```bash
curl "http://localhost:5555/api/album/alone-english-2016-4"
```

List every endpoint:

```bash
curl "http://localhost:5555/api/endpoints"
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Documentation website |
| `GET` | `/docs` | Documentation website alias |
| `GET` | `/styles.css` | Docs page stylesheet |
| `GET` | `/health` | Service health check |
| `GET` | `/api/health` | API health check alias |
| `GET` | `/api` | JSON service index |
| `GET` | `/api/endpoints` | Machine-readable endpoint catalog |
| `GET` | `/api/sample` | Static sample song payload |
| `GET`, `POST` | `/result/` | Original song lookup route, returns an array |
| `GET`, `POST` | `/api/result` | Vercel-style alias for `/result/` |
| `GET`, `POST` | `/api/song` | One song by `url` or `seokey` |
| `GET` | `/api/song/<seokey>` | One song by path seokey |
| `GET`, `POST` | `/api/lyrics` | Lyrics by `url` or `seokey` when available |
| `GET` | `/api/lyrics/<seokey>` | Lyrics by path seokey |
| `GET`, `POST` | `/api/artwork` | Song title, album, artist, and artwork |
| `GET`, `POST` | `/api/stream` | Stream availability, bitrate, and link when decryptable |
| `GET`, `POST` | `/api/album` | Album metadata with track list |
| `GET` | `/api/album/<seokey>` | Album metadata and tracks by path seokey |
| `GET` | `/api/search` | Search with `q`, `type`, and `limit` |
| `GET`, `POST` | `/api/resolve` | Resolve Gaana URL/path into type and seokey |

## Query Parameters

| Parameter | Used By | Description |
| --- | --- | --- |
| `url` | song, result, lyrics, artwork, stream, album, resolve | Full Gaana URL |
| `seokey` | song, lyrics, artwork, stream, album | Gaana URL slug, such as `alone-1435` |
| `lyrics` | song, result, album | Set to `true` to include lyrics when available |
| `q` | search | Search query |
| `type` | search | `all`, `song`, `album`, `artist`, or `playlist` |
| `limit` | search | Number of results, max `50` |
| `path` | resolve | Gaana path such as `/song/alone-1435` |

## Example Song Response

```json
{
  "status": true,
  "title": "Alone",
  "album": "Alone",
  "artist": "Alan Walker",
  "thumb": "https://a10.gaanacdn.com/gn_img/albums/DwPKOxB3qV/wPKOpPzk3q/size_l.jpg",
  "language": "English",
  "gaana_url": "https://gaana.com/song/alone-1435",
  "duration": "2min 39sec",
  "released": "2016-12-02",
  "bitrate": "128",
  "link": null
}
```

## Vercel Deployment

Vercel can deploy this Flask app directly because `app.py` exports a Flask instance named `app`.

```bash
vercel deploy
```

For local Vercel emulation:

```bash
vercel dev --listen 5555
```

## Project Structure

```text
.
|-- app.py              # Flask routes, docs, health, and API responses
|-- gaana.py            # Gaana page parsing and data normalization
|-- public/styles.css   # Docs UI styles
|-- templates/index.html
|-- requirements.txt
|-- runtime.txt
|-- vercel.json
`-- ABOUT.md
```

## Notes

Gaana page structure and regional access can affect upstream scraping reliability. `/health` only checks that this Flask service is online; it does not call Gaana.

The current Gaana web payload can provide metadata while withholding a decryptable stream URL. In that case, the API still returns song data and sets `link` to `null`.

## License

This project keeps the original MIT license from `cyberboysumanjay/GaanaAPI`.
