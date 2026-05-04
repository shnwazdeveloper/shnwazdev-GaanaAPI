import os
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_from_directory

import gaana


SERVICE_NAME = "shnwazdev-GaanaAPI"
API_VERSION = "1.1.0"
SAMPLE_URL = "https://gaana.com/song/alone-1435"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gaanaapi-local-dev-key")


ENDPOINTS = [
    {
        "group": "Website",
        "method": "GET",
        "path": "/",
        "summary": "Clean documentation page with health and API tester.",
        "params": "none",
    },
    {
        "group": "Website",
        "method": "GET",
        "path": "/docs",
        "summary": "Alias for the documentation page.",
        "params": "none",
    },
    {
        "group": "Website",
        "method": "GET",
        "path": "/styles.css",
        "summary": "Stylesheet for the docs page.",
        "params": "none",
    },
    {
        "group": "Core",
        "method": "GET",
        "path": "/health",
        "summary": "Lightweight service health check.",
        "params": "none",
    },
    {
        "group": "Core",
        "method": "GET",
        "path": "/api/health",
        "summary": "API health check alias.",
        "params": "none",
    },
    {
        "group": "Core",
        "method": "GET",
        "path": "/api",
        "summary": "JSON service index with docs and endpoint catalog links.",
        "params": "none",
    },
    {
        "group": "Core",
        "method": "GET",
        "path": "/api/endpoints",
        "summary": "Machine-readable list of every public route.",
        "params": "none",
    },
    {
        "group": "Core",
        "method": "GET",
        "path": "/api/sample",
        "summary": "Static sample song response for frontend testing.",
        "params": "none",
    },
    {
        "group": "Song",
        "method": "GET, POST",
        "path": "/result/",
        "summary": "Original endpoint. Returns an array of song metadata.",
        "params": "url=<gaana-song-url>&lyrics=true",
    },
    {
        "group": "Song",
        "method": "GET, POST",
        "path": "/api/result",
        "summary": "Vercel-style alias for /result/.",
        "params": "url=<gaana-song-url>&lyrics=false",
    },
    {
        "group": "Song",
        "method": "GET, POST",
        "path": "/api/song",
        "summary": "Returns one song object instead of an array.",
        "params": "url=<gaana-song-url> or seokey=<song-seokey>",
    },
    {
        "group": "Song",
        "method": "GET",
        "path": "/api/song/<seokey>",
        "summary": "Fetch one song by Gaana seokey.",
        "params": "lyrics=true",
    },
    {
        "group": "Song",
        "method": "GET, POST",
        "path": "/api/lyrics",
        "summary": "Fetch lyrics for a song when Gaana exposes them.",
        "params": "url=<gaana-song-url> or seokey=<song-seokey>",
    },
    {
        "group": "Song",
        "method": "GET",
        "path": "/api/lyrics/<seokey>",
        "summary": "Fetch lyrics by song seokey.",
        "params": "none",
    },
    {
        "group": "Song",
        "method": "GET, POST",
        "path": "/api/artwork",
        "summary": "Return title and artwork for a song.",
        "params": "url=<gaana-song-url> or seokey=<song-seokey>",
    },
    {
        "group": "Song",
        "method": "GET, POST",
        "path": "/api/stream",
        "summary": "Return stream availability, bitrate, and link when decryptable.",
        "params": "url=<gaana-song-url> or seokey=<song-seokey>",
    },
    {
        "group": "Album",
        "method": "GET, POST",
        "path": "/api/album",
        "summary": "Return album metadata and track list.",
        "params": "url=<gaana-album-url> or seokey=<album-seokey>",
    },
    {
        "group": "Album",
        "method": "GET",
        "path": "/api/album/<seokey>",
        "summary": "Fetch album metadata and tracks by seokey.",
        "params": "lyrics=true",
    },
    {
        "group": "Discovery",
        "method": "GET",
        "path": "/api/search",
        "summary": "Search Gaana and return normalized results.",
        "params": "q=<query>&type=all|song|album|artist|playlist&limit=10",
    },
    {
        "group": "Utility",
        "method": "GET, POST",
        "path": "/api/resolve",
        "summary": "Resolve a Gaana URL into type, seokey, path, and host.",
        "params": "url=<gaana-url> or path=/song/<seokey>",
    },
]


def _json_error(message, status_code=400, detail=None):
    payload = {
        "status": False,
        "service": SERVICE_NAME,
        "error": message,
    }
    if detail:
        payload["detail"] = str(detail)
    return jsonify(payload), status_code


def _truthy(value):
    if value is None:
        return False
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}


def _request_value(name, default=None):
    body = request.get_json(silent=True) or {}
    return request.args.get(name) or request.form.get(name) or body.get(name, default)


def _request_limit(default=10):
    try:
        return max(1, min(int(_request_value("limit", default)), 50))
    except (TypeError, ValueError):
        return default


def _valid_http_url(value):
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _link_or_error(kind):
    link = _request_value("url")
    seokey = _request_value("seokey") or _request_value("id")

    if link:
        if not _valid_http_url(link):
            return None, _json_error("The url parameter must be a valid http(s) URL")
        return link, None

    if seokey:
        try:
            return gaana.build_gaana_url(kind, seokey), None
        except ValueError as exc:
            return None, _json_error(str(exc))

    return None, _json_error("Missing required parameter: url or seokey")


def _song_payload(link, lyrics=False):
    try:
        song = gaana.get_song(link, lyrics)
    except Exception as exc:
        app.logger.exception("Failed to fetch Gaana song data")
        return None, _json_error("Unable to fetch song data from Gaana", 502, exc)

    if not song:
        return None, _json_error("No song data found for the provided URL", 404)

    return song, None


@app.after_request
def add_api_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    return response


@app.route("/")
@app.route("/docs")
def home():
    return render_template(
        "index.html",
        service_name=SERVICE_NAME,
        api_version=API_VERSION,
        endpoints=ENDPOINTS,
        sample_url=SAMPLE_URL,
    )


@app.route("/styles.css")
def styles():
    return send_from_directory(
        os.path.join(app.root_path, "public"),
        "styles.css",
        mimetype="text/css",
    )


@app.route("/health")
@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": True,
            "service": SERVICE_NAME,
            "version": API_VERSION,
            "runtime": "flask",
        }
    )


@app.route("/api")
def api_index():
    return jsonify(
        {
            "status": True,
            "service": SERVICE_NAME,
            "version": API_VERSION,
            "docs": "/docs",
            "health": "/health",
            "endpoints_url": "/api/endpoints",
            "endpoint_count": len(ENDPOINTS),
        }
    )


@app.route("/api/endpoints")
def api_endpoints():
    return jsonify(
        {
            "status": True,
            "service": SERVICE_NAME,
            "version": API_VERSION,
            "count": len(ENDPOINTS),
            "endpoints": ENDPOINTS,
        }
    )


@app.route("/api/sample")
def api_sample():
    return jsonify(
        {
            "status": True,
            "service": SERVICE_NAME,
            "song": gaana.sample_song(),
        }
    )


@app.route("/result/", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/result", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/result/", methods=["GET", "POST", "OPTIONS"])
def result():
    if request.method == "OPTIONS":
        return "", 204

    link, error = _link_or_error("song")
    if error:
        return error

    lyrics = _truthy(_request_value("lyrics", False))
    try:
        data = gaana.downloadAndParsePage(link, lyrics)
    except Exception as exc:
        app.logger.exception("Failed to fetch Gaana data")
        return _json_error("Unable to fetch song data from Gaana", 502, exc)

    if not data:
        return _json_error("No song data found for the provided URL", 404)

    return jsonify(data)


@app.route("/api/song", methods=["GET", "POST", "OPTIONS"])
def api_song():
    if request.method == "OPTIONS":
        return "", 204

    link, error = _link_or_error("song")
    if error:
        return error

    song, error = _song_payload(link, _truthy(_request_value("lyrics", False)))
    if error:
        return error
    return jsonify(song)


@app.route("/api/song/<path:seokey>")
def api_song_by_seokey(seokey):
    song, error = _song_payload(
        gaana.build_gaana_url("song", seokey),
        _truthy(_request_value("lyrics", False)),
    )
    if error:
        return error
    return jsonify(song)


@app.route("/api/lyrics", methods=["GET", "POST", "OPTIONS"])
def api_lyrics():
    if request.method == "OPTIONS":
        return "", 204

    link, error = _link_or_error("song")
    if error:
        return error

    return _lyrics_response(link)


@app.route("/api/lyrics/<path:seokey>")
def api_lyrics_by_seokey(seokey):
    return _lyrics_response(gaana.build_gaana_url("song", seokey))


def _lyrics_response(link):
    try:
        lyrics = gaana.get_lyrics(link)
    except Exception as exc:
        app.logger.exception("Failed to fetch lyrics")
        return _json_error("Unable to fetch lyrics from Gaana", 502, exc)

    if lyrics is None:
        return _json_error("Lyrics not found for the provided song", 404)

    return jsonify(
        {
            "status": True,
            "gaana_url": link,
            "lyrics": lyrics,
        }
    )


@app.route("/api/artwork", methods=["GET", "POST", "OPTIONS"])
def api_artwork():
    if request.method == "OPTIONS":
        return "", 204

    link, error = _link_or_error("song")
    if error:
        return error

    song, error = _song_payload(link, False)
    if error:
        return error

    return jsonify(
        {
            "status": True,
            "title": song.get("title"),
            "album": song.get("album"),
            "artist": song.get("artist"),
            "thumb": song.get("thumb"),
            "gaana_url": song.get("gaana_url"),
        }
    )


@app.route("/api/stream", methods=["GET", "POST", "OPTIONS"])
def api_stream():
    if request.method == "OPTIONS":
        return "", 204

    link, error = _link_or_error("song")
    if error:
        return error

    song, error = _song_payload(link, False)
    if error:
        return error

    stream_link = song.get("link")
    return jsonify(
        {
            "status": True,
            "available": bool(stream_link),
            "title": song.get("title"),
            "bitrate": song.get("bitrate"),
            "link": stream_link,
            "gaana_url": song.get("gaana_url"),
            "note": None if stream_link else "Gaana did not expose a decryptable stream link for this request.",
        }
    )


@app.route("/api/album", methods=["GET", "POST", "OPTIONS"])
def api_album():
    if request.method == "OPTIONS":
        return "", 204

    link, error = _link_or_error("album")
    if error:
        return error

    return _album_response(link)


@app.route("/api/album/<path:seokey>")
def api_album_by_seokey(seokey):
    return _album_response(gaana.build_gaana_url("album", seokey))


def _album_response(link):
    try:
        album = gaana.get_album(link, _truthy(_request_value("lyrics", False)))
    except Exception as exc:
        app.logger.exception("Failed to fetch Gaana album data")
        return _json_error("Unable to fetch album data from Gaana", 502, exc)

    if not album:
        return _json_error("No album data found for the provided URL", 404)

    return jsonify(album)


@app.route("/api/search")
def api_search():
    query = _request_value("q") or _request_value("query")
    if not query:
        return _json_error("Missing required parameter: q")

    try:
        payload = gaana.search(
            query,
            _request_value("type", "all"),
            _request_limit(10),
        )
    except Exception as exc:
        app.logger.exception("Failed to search Gaana")
        return _json_error("Unable to search Gaana", 502, exc)

    return jsonify(payload)


@app.route("/api/resolve", methods=["GET", "POST", "OPTIONS"])
def api_resolve():
    if request.method == "OPTIONS":
        return "", 204

    value = _request_value("url") or _request_value("path")
    if not value:
        return _json_error("Missing required parameter: url or path")

    value = str(value).strip()
    if value.startswith("/"):
        value = "https://gaana.com"+value
    elif not _valid_http_url(value):
        return _json_error("The url parameter must be a valid http(s) URL or Gaana path")

    return jsonify(gaana.resolve_url_info(value))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5555"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
