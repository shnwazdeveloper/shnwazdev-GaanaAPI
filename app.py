import os
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_from_directory

import gaana


SERVICE_NAME = "shnwazdev-GaanaAPI"
API_VERSION = "1.0.0"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gaanaapi-local-dev-key")


DOC_ENDPOINTS = [
    {
        "method": "GET",
        "path": "/result/",
        "summary": "Fetch song metadata from a Gaana song URL.",
        "params": "url=<gaana-song-url>&lyrics=true",
    },
    {
        "method": "GET",
        "path": "/api/result",
        "summary": "Alias for Vercel-style API clients.",
        "params": "url=<gaana-song-url>&lyrics=false",
    },
    {
        "method": "GET",
        "path": "/health",
        "summary": "Lightweight service health check.",
        "params": "none",
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


def _valid_http_url(value):
    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


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
        endpoints=DOC_ENDPOINTS,
        sample_url="https://gaana.com/song/alone-1435",
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
            "endpoints": DOC_ENDPOINTS,
        }
    )


@app.route("/result/", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/result", methods=["GET", "POST", "OPTIONS"])
@app.route("/api/result/", methods=["GET", "POST", "OPTIONS"])
def result():
    if request.method == "OPTIONS":
        return "", 204

    link = _request_value("url")
    lyrics = _truthy(_request_value("lyrics", False))

    if not link:
        return _json_error("Missing required parameter: url")

    if not _valid_http_url(link):
        return _json_error("The url parameter must be a valid http(s) URL")

    try:
        data = gaana.downloadAndParsePage(link, lyrics)
    except Exception as exc:
        app.logger.exception("Failed to fetch Gaana data")
        return _json_error("Unable to fetch song data from Gaana", 502, exc)

    if not data:
        return _json_error("No song data found for the provided URL", 404)

    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5555"))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
