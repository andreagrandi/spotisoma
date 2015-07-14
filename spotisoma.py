import os
import requests
import urllib
import spotify
import threading
import logging


IMPORTIO_API_INDIEPOP_URL = ('https://api.import.io/store/data/'
    'c3914ba4-3da3-4fee-8120-fcb6bfb66d3f/_query?input/webpage/'
    'url=http%3A%2F%2Fsomafm.com%2Findiepop%2Fsonghistory.html'
    '&_user=cc187fb6-b6e3-4d38-8b82-3e67399bafbc&_apikey=')
IMPORTIO_API_KEY = os.environ.get('IMPORTIO_API_KEY')
SPOTIFY_USERNAME = os.environ.get('SPOTIFY_USERNAME')
SPOTIFY_PASSWORD = os.environ.get('SPOTIFY_PASSWORD')
SPOTIFY_PLAYLIST_NAME = 'SomaFM - Indie Pop Rock'
SPOTIFY_PLAYLIST_MAXLENGTH = 300

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('spotisoma.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Setup Spotify Session
session = spotify.Session()
logged_in_event = threading.Event()


def connection_state_listener(session):
    if session.connection.state is spotify.ConnectionState.LOGGED_IN:
        logged_in_event.set()

def login_to_spotify():
    loop = spotify.EventLoop(session)
    loop.start()

    session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED,
        connection_state_listener)

    session.login(SPOTIFY_USERNAME, SPOTIFY_PASSWORD)
    logged_in_event.wait()

def get_songs_history():
    response = requests.get('{0}{1}'.format(
        IMPORTIO_API_INDIEPOP_URL, IMPORTIO_API_KEY))

    if response.ok:
        logger.info('Received songs history from SomaFM')
        results = response.json()['results']
        return [(s['song_value'], s['artist_link/_text']) for s in results]

def get_or_create_spotify_playlist(name):
    container = session.playlist_container
    container.load()

    for pl in container:
        pl.load()

        if pl.name == name:
            logger.info('Found playlist')
            return pl

    logger.info('Created new playlist')
    return container.add_new_playlist(name)

def search_song(title, artist):
    search = session.search('{0} {1}'.format(title, artist))
    search.load()

    if len(search.tracks) > 0:
        logger.info('Found track {0} - {1}'.format(title, artist))
        return search.tracks[0]
    else:
        logger.warning('Track not found: {0} - {1}'.format(title, artist))
        return None

def is_song_in_playlist(song, playlist):
    for track in playlist.tracks:
        if song == track:
            logger.debug('Track already in playlist: {0}'.format(song.name))
            return True
    return False

if __name__ == "__main__":
    # Get songs list from SomaFM
    songs_history = get_songs_history()

    # Login to Spotify
    login_to_spotify()

    # Get or create the Spotify playlist for SomaFM:
    playlist = get_or_create_spotify_playlist(SPOTIFY_PLAYLIST_NAME)

    # Search each song in Spotify catalog
    for s in songs_history:
        logger.info('Searching song: {0}'.format(s))
        song = search_song(s[0], s[1])

        if song:
            song.load()

            # Add song to the playlist if it's not already there
            if not is_song_in_playlist(song, playlist):
                logger.info('Adding track: {0}'.format(song.name.encode("utf8")))
                playlist.add_tracks(song, 0)

    # Removes old tracks if the playlist length is > SPOTIFY_PLAYLIST_MAXLENGTH
    if len(playlist.tracks) > SPOTIFY_PLAYLIST_MAXLENGTH:
        logger.info('Removing older tracks from the playlist')
        indexes_to_remove = [x for x in range(SPOTIFY_PLAYLIST_MAXLENGTH,
            len(playlist.tracks))]
        try:
            playlist.remove_tracks(indexes_to_remove)
            logger.info('Removed last {0} tracks'.format(
                len(indexes_to_remove)))
        except Error as e:
            logger.error('Error occurred while removing tracks: {0}'.format(e))
