from bs4 import BeautifulSoup
import requests
import lxml
from Crypto.Cipher import AES
import re
from json import JSONDecoder
from traceback import print_exc
import base64
import json
from urllib.parse import quote, urlparse


def unpad(s): return s[0:-ord(s[-1])]


REGEX = re.compile('> ({[^<]*}) <')
JSONDEC = JSONDecoder()
DOWN_FOLDER = '.'
REQUEST_TIMEOUT = 12
PRELOADED_STATE = 'window.__PRELOADED_STATE__ = '
GAANA_BASE_URL = 'https://gaana.com'
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:49.0) Gecko/20100101 Firefox/49.0'
}


def fetch_text(link):
    return requests.get(link, headers=headers, timeout=REQUEST_TIMEOUT).text


def build_gaana_url(kind, value):
    if not value:
        raise ValueError('A URL or seokey is required')

    value = str(value).strip()
    if value.startswith(('http://', 'https://')):
        return value

    value = value.strip('/')
    if kind == 'lyrics':
        kind = 'song'
    return GAANA_BASE_URL+'/'+kind+'/'+value


def resolve_url_info(link):
    parsed = urlparse(link or '')
    parts = [part for part in parsed.path.split('/') if part]
    kind = parts[0] if parts else 'home'
    if kind == 'lyrics':
        kind = 'song'

    return {
        'status': True,
        'type': kind,
        'url': link,
        'seokey': parts[1] if len(parts) > 1 else '',
        'path': parsed.path or '/',
        'host': parsed.netloc,
    }


def fate_proxy():
    resp = requests.get(
        'https://raw.githubusercontent.com/fate0/proxylist/master/proxy.list',
        timeout=REQUEST_TIMEOUT)
    a = ((resp.text).split('\n'))
    p_list = []

    for i in a:
        try:
            p_list.append(json.loads(i))
        except Exception as e:
            # print("Test",e)
            continue
    # print(len(p_list))
    np_list = []
    for i in p_list:
        if i['country'] == 'IN':
            np_list.append(i)
    proxy = []
    for i in np_list:
        proxy.append((str(i['host'])+':'+str(i['port'])))
    return(proxy)


def fix_share_url(s):
    if not s:
        return ''
    s = s.replace("\\", '')
    if s.startswith('http://') or s.startswith('https://'):
        return s
    if not s.startswith('/'):
        s = '/'+s
    s = 'https://gaana.com'+s
    return (s)


def fix_album_art(url):
    if not url:
        return ''
    url = url.replace("175x175", "640x640")
    return url


def decryptLink(message):
    IV = 'asd!@#!@#@!12312'.encode('utf-8')
    KEY = 'g@1n!(f1#r.0$)&%'.encode('utf-8')
    aes = AES.new(KEY, AES.MODE_CBC, IV)
    # message=message.encode('utf-8')
    message = message + ('=' * (-len(message) % 4))
    return unpad((aes.decrypt(base64.b64decode(message))).decode('utf-8'))


def fix_artist_name(t):
    t = t.split(',')
    l = []
    for i in t:
        i = i.split('#')[0]
        l.append(i)

    singers = ''
    for i in l:
        singers = singers+i+', '
    singers = singers[:len(singers)-2]
    return singers


def format_duration(duration):
    try:
        seconds = int(float(duration))
        return str(seconds//60)+"min " + str(seconds % 60) + "sec"
    except Exception:
        return duration or ''


def get_preloaded_state(response):
    start = response.find(PRELOADED_STATE)
    if start == -1:
        return None

    raw = response[start+len(PRELOADED_STATE):].lstrip()
    try:
        state, _ = JSONDEC.raw_decode(raw)
        return state
    except Exception as e:
        print(e)
        return None


def get_artist_names(artist):
    if isinstance(artist, list):
        names = []
        for item in artist:
            if isinstance(item, dict) and item.get('name'):
                names.append(item.get('name'))
            elif isinstance(item, str):
                names.append(item)
        return ', '.join(names)
    if isinstance(artist, str):
        return fix_artist_name(artist)
    return ''


def select_stream(streams):
    if not isinstance(streams, dict):
        return '', None

    first_bitrate = ''
    for quality in ('extreme', 'high', 'medium', 'normal', 'auto'):
        stream = streams.get(quality)
        if isinstance(stream, list):
            stream = stream[0] if stream else None
        if not isinstance(stream, dict):
            continue

        bitrate = stream.get('bitRate') or stream.get('bitrate') or ''
        if bitrate and not first_bitrate:
            first_bitrate = bitrate

        message = stream.get('message')
        if not message:
            continue

        try:
            return bitrate, decryptLink(message)
        except Exception:
            continue

    return first_bitrate, None


def current_song_url(track, fallback_link):
    if track.get('share_url'):
        return fix_share_url(track.get('share_url'))
    if track.get('seokey'):
        return 'https://gaana.com/song/'+track.get('seokey')
    return fallback_link


def current_track_to_song(track, fallback_link, lyrics):
    bitrate, playable_link = select_stream(track.get('urls') or track.get('path'))
    gaana_url = current_song_url(track, fallback_link)
    song = {
        'status': True,
        'title': track.get('track_title') or track.get('title') or track.get('name') or '',
        'album': track.get('album_title') or track.get('albumtitle') or track.get('album') or '',
        'thumb': track.get('artwork_large') or track.get('artwork_web') or track.get('artwork') or track.get('atw') or '',
        'language': track.get('language') or '',
        'gaana_url': gaana_url,
        'duration': format_duration(track.get('duration')),
        'artist': get_artist_names(track.get('artist')),
        'released': track.get('release_date') or track.get('released') or '',
        'bitrate': bitrate,
        'link': playable_link
    }
    if lyrics:
        song['lyrics'] = get_lyrics(gaana_url)
    return song


def parse_preloaded_songs(response, fallback_link, lyrics):
    state = get_preloaded_state(response)
    if not state:
        return []

    song_state = state.get('song') or {}
    for section in ('songDetail', 'songInfo', 'albumSongs'):
        data = song_state.get(section) or {}
        tracks = data.get('tracks') if isinstance(data, dict) else None
        if not tracks:
            continue
        songs = []
        seen = set()
        for track in tracks:
            if not isinstance(track, dict):
                continue
            key = track.get('track_id') or track.get('seokey') or track.get('track_title')
            if key in seen:
                continue
            seen.add(key)
            songs.append(current_track_to_song(track, fallback_link, lyrics))
        if songs:
            return songs

    return []


def get_song(link, lyrics=False):
    songs = downloadAndParsePage(link, lyrics)
    return songs[0] if songs else None


def get_song_by_seokey(seokey, lyrics=False):
    return get_song(build_gaana_url('song', seokey), lyrics)


def parse_preloaded_album(response, fallback_link, lyrics=False):
    state = get_preloaded_state(response)
    if not state:
        return None

    album_state = state.get('album') or {}
    song_state = state.get('song') or {}
    sections = (
        album_state.get('albumDetail') or {},
        song_state.get('albumSongs') or {},
    )

    for section in sections:
        tracks = section.get('tracks') if isinstance(section, dict) else None
        if not tracks:
            continue

        songs = []
        seen = set()
        for track in tracks:
            if not isinstance(track, dict):
                continue
            key = track.get('track_id') or track.get('seokey') or track.get('track_title')
            if key in seen:
                continue
            seen.add(key)
            songs.append(current_track_to_song(track, fallback_link, lyrics))

        if not songs:
            continue

        first_track = tracks[0]
        album_seokey = first_track.get('albumseokey') or ''
        return {
            'status': True,
            'type': 'album',
            'title': first_track.get('album_title') or songs[0].get('album') or '',
            'album_id': first_track.get('album_id') or '',
            'gaana_url': GAANA_BASE_URL+'/album/'+album_seokey if album_seokey else fallback_link,
            'thumb': first_track.get('artwork_large') or first_track.get('artwork_web') or first_track.get('artwork') or '',
            'language': first_track.get('language') or songs[0].get('language') or '',
            'artist': get_artist_names(first_track.get('artist')) or songs[0].get('artist') or '',
            'released': first_track.get('release_date') or songs[0].get('released') or '',
            'total_tracks': len(songs),
            'tracks': songs,
        }

    return None


def get_album(link, lyrics=False):
    response = fetch_text(link)
    album = parse_preloaded_album(response, link, lyrics)
    if album:
        return album

    songs = parse_preloaded_songs(response, link, lyrics)
    if songs:
        return {
            'status': True,
            'type': 'album',
            'title': songs[0].get('album') or '',
            'gaana_url': link,
            'thumb': songs[0].get('thumb') or '',
            'language': songs[0].get('language') or '',
            'artist': songs[0].get('artist') or '',
            'released': songs[0].get('released') or '',
            'total_tracks': len(songs),
            'tracks': songs,
        }

    return None


def get_album_by_seokey(seokey, lyrics=False):
    return get_album(build_gaana_url('album', seokey), lyrics)


def normalize_search_item(item):
    item_type = item.get('ty') or item.get('type') or ''
    seokey = item.get('seo') or item.get('seokey') or ''
    url_type = {
        'Track': 'song',
        'Song': 'song',
        'Album': 'album',
        'Artist': 'artist',
        'Playlist': 'playlist',
        'Podcast': 'podcast',
    }.get(item_type, item_type.lower() or 'item')

    return {
        'type': url_type,
        'id': str(item.get('iid') or item.get('id') or ''),
        'title': item.get('ti') or item.get('title') or item.get('name') or '',
        'subtitle': item.get('sti') or item.get('subtitle') or '',
        'artist': item.get('sti') or '',
        'language': item.get('language') or ', '.join(item.get('lang') or []),
        'thumb': item.get('aw') or item.get('artwork') or '',
        'gaana_url': GAANA_BASE_URL+'/'+url_type+'/'+seokey if seokey else '',
        'seokey': seokey,
        'tags': item.get('tags') or [],
    }


def search(query, item_type='all', limit=10):
    if not query:
        raise ValueError('Search query is required')

    limit = max(1, min(int(limit or 10), 50))
    link = GAANA_BASE_URL+'/search/'+quote(str(query).strip())
    state = get_preloaded_state(fetch_text(link))
    search_state = state.get('search') if state else {}
    groups = (((search_state or {}).get('searchAll') or {}).get('data') or {}).get('gr') or []

    requested_type = str(item_type or 'all').strip().lower()
    results = []
    seen = set()
    for group in groups:
        for item in group.get('gd') or []:
            if not isinstance(item, dict):
                continue
            result = normalize_search_item(item)
            if requested_type not in {'all', '', result['type'].lower()}:
                continue
            key = (result['type'], result['id'], result['seokey'])
            if key in seen:
                continue
            seen.add(key)
            results.append(result)
            if len(results) >= limit:
                return {
                    'status': True,
                    'query': query,
                    'type': requested_type or 'all',
                    'count': len(results),
                    'results': results,
                }

    return {
        'status': True,
        'query': query,
        'type': requested_type or 'all',
        'count': len(results),
        'results': results,
    }


def sample_song():
    return {
        'status': True,
        'title': 'Alone',
        'album': 'Alone',
        'thumb': 'https://a10.gaanacdn.com/gn_img/albums/DwPKOxB3qV/wPKOpPzk3q/size_l.jpg',
        'language': 'English',
        'gaana_url': 'https://gaana.com/song/alone-1435',
        'duration': '2min 39sec',
        'artist': 'Alan Walker',
        'released': '2016-12-02',
        'bitrate': '128',
        'link': None,
    }


def downloadAndParsePage(link, lyrics):
    if not link or not link.startswith(('http://', 'https://')):
        raise ValueError('A valid Gaana song URL is required')

    response = ''
    response = requests.get(link, headers=headers,
                            timeout=REQUEST_TIMEOUT).text
    raw_songs = list(set(REGEX.findall(response)))
    if len(raw_songs) == 0:
        songs = parse_preloaded_songs(response, link, lyrics)
        if songs:
            return songs

    if len(raw_songs) == 0:
        try:
            proxies = fate_proxy()
            for proxy in proxies:
                try:
                    response = requests.get(link, headers=headers, proxies={
                                            "http": proxy, "https": proxy},
                                            timeout=REQUEST_TIMEOUT).text
                    break
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)

    raw_songs = list(set(REGEX.findall(response)))
    if len(raw_songs) == 0:
        songs = parse_preloaded_songs(response, link, lyrics)
        if songs:
            return songs

    songs = []
    for raw_song in raw_songs:
        json_song = JSONDEC.decode(raw_song)

        try:
            bitrate, playable_link = select_stream(json_song.get('path'))
            song = {
                'status': True,
                'title': json_song['title'],
                'album': json_song['albumtitle'],
                'thumb': fix_album_art(json_song['albumartwork_large']),
                'language': json_song['language'],
                'gaana_url': fix_share_url(json_song['share_url']),
                'duration': format_duration(json_song['duration']),
                'artist': fix_artist_name(json_song['artist']),
                'released': json_song['release_date'],
                'bitrate': bitrate,
                'link': playable_link
            }
            if lyrics:
                song['lyrics'] = get_lyrics(song['gaana_url'])
            songs.append(song)
        except Exception as e:
            print(e)
    return songs


def get_lyrics(link):
    if '/song/' in link:
        link = link.replace('/song/', '/lyrics/')
    if '/lyrics/' in link:
        source = requests.get(link, headers=headers,
                              timeout=REQUEST_TIMEOUT).text
        state = get_preloaded_state(source)
        if state:
            song_lyrics = (state.get('lyrics') or {}).get('songLyrics') or {}
            if isinstance(song_lyrics, dict):
                for key in ('lyrics', 'lyric', 'content', 'text'):
                    if song_lyrics.get(key):
                        return str(song_lyrics.get(key)).strip()
        soup = BeautifulSoup(source, 'lxml')
        res = soup.find('div', class_='seelyrics')
        if res:
            return (res.get_text().strip())
    return None
