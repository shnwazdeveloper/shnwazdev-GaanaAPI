# shnwazdev-GaanaAPI

Unofficial Gaana metadata API built with Flask. This version keeps the original `/result/` API route, adds Vercel-friendly aliases, includes a clean docs website, and exposes health checks for uptime monitoring.

Original project: [cyberboysumanjay/GaanaAPI](https://github.com/cyberboysumanjay/GaanaAPI)

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` or `/docs` | API docs website with health and request tester |
| `GET` | `/health` | Service health JSON |
| `GET` | `/api/health` | Health alias for API clients |
| `GET` | `/api` | JSON index of docs and endpoints |
| `GET` or `POST` | `/result/` | Original song metadata endpoint |
| `GET` or `POST` | `/api/result` | Vercel-style song metadata alias |

## API Usage

```bash
curl "http://localhost:5555/result/?url=https://gaana.com/song/alone-1435&lyrics=true"
```

Query parameters:

| Name | Required | Description |
| --- | --- | --- |
| `url` | Yes | Full Gaana song URL |
| `lyrics` | No | Set to `true` to fetch lyrics when available |

Successful song lookups return a JSON array:

```json
[
  {
    "status": true,
    "title": "Song title",
    "album": "Album name",
    "artist": "Artist name",
    "thumb": "https://...",
    "duration": "2min 39sec",
    "link": "https://..."
  }
]
```

Errors return JSON with `status: false` and an `error` message.

## Local Development

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open [http://localhost:5555](http://localhost:5555).

## Vercel Deployment

Vercel can deploy Flask apps directly when the root project exports a Flask instance named `app` from `app.py`.

```bash
vercel deploy
```

For local Vercel emulation after installing the Vercel CLI:

```bash
vercel dev --listen 5555
```

The static docs stylesheet lives in `public/styles.css`, which Vercel serves from the Edge Network. The Flask route for `/styles.css` keeps the same UI working when running with `python app.py`.

## Notes

Gaana page structure and regional access can affect upstream scraping reliability. `/health` only checks that this Flask service is online; it does not call Gaana.

The current Gaana web payload can provide metadata while withholding a decryptable stream URL. In that case, the API still returns the song data and sets `link` to `null`.

## License

This project keeps the original MIT license from `cyberboysumanjay/GaanaAPI`.
