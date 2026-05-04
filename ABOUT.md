# About shnwazdev-GaanaAPI

`shnwazdev-GaanaAPI` is an unofficial Flask API for reading public Gaana song and album metadata. It is designed to be easy to run locally, simple to deploy on Vercel, and useful for frontend projects that need clean JSON responses.

## What It Provides

- Song metadata from Gaana song URLs and seokeys
- Album metadata with normalized track lists
- Search results for songs, albums, artists, playlists, and mixed results
- Artwork, lyrics, stream-status, health, resolve, sample, and endpoint catalog routes
- Playable HLS audio URLs when Gaana provides valid stream metadata
- A clean documentation website served by the same Flask app

## Main Use Cases

- Build music metadata demos
- Test frontend API integrations
- Create small Flask/Vercel API examples
- Query public Gaana page data in JSON format

## Deployment Target

The project is prepared for:

- Localhost: `http://localhost:5555`
- Vercel Python/Flask deployment
- GitHub public repository distribution

## Important Note

This is an unofficial API wrapper around public Gaana web pages. Gaana can change its page structure or encrypted stream payload at any time. This build supports the current encrypted HLS stream format, but expired, blocked, or missing stream metadata can still return `null`.

## Credit

Modernized by `shnwazdeveloper`.

Original project: `cyberboysumanjay/GaanaAPI`
