from bs4 import BeautifulSoup
import requests
import lxml
from Crypto.Cipher import AES
import re
from json import JSONDecoder
from traceback import print_exc
import base64
import json


def unpad(s): return s[0:-ord(s[-1])]


REGEX = re.compile('> ({[^<]*}) <')
JSONDEC = JSONDecoder()
DOWN_FOLDER = '.'
REQUEST_TIMEOUT = 12
PRELOADED_STATE = 'window.__PRELOADED_STATE__ = '
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:49.0) Gecko/20100101 Firefox/49.0'
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
