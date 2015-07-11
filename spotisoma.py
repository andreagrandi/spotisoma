import os
import requests
import urllib
import spotify
import threading


IMPORTIO_API_INDIEPOP_URL = ('https://api.import.io/store/data/'
    'c3914ba4-3da3-4fee-8120-fcb6bfb66d3f/_query?input/webpage/'
    'url=http%3A%2F%2Fsomafm.com%2Findiepop%2Fsonghistory.html'
    '&_user=cc187fb6-b6e3-4d38-8b82-3e67399bafbc&_apikey=')
IMPORTIO_API_KEY = os.environ.get('IMPORTIO_API_KEY')
SPOTIFY_USERNAME = os.environ.get('SPOTIFY_USERNAME')
SPOTIFY_PASSWORD = os.environ.get('SPOTIFY_PASSWORD')
SPOTIFY_PLAYLIST_NAME = 'SomaFM - Indie Pop Rock'
SPOTIFY_PLAYLIST_MAXLENGTH = 300

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
        results = response.json()['results']
        return [(s['song_value'], s['artist_link/_text']) for s in results]

def get_or_create_spotify_playlist(name):
    container = session.playlist_container
    container.load()

    for pl in container:
        pl.load()

        if pl.name == name:
            return pl

    return container.add_new_playlist(name)

def search_song(title, artist):
    search = session.search('{0} {1}'.format(title, artist))
    search.load()

    if len(search.tracks) > 0:
        return search.tracks[0]
    else:
        return None

def is_song_in_playlist(song, playlist):
    for track in playlist.tracks:
        if song == track:
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
        print 'Searching song: {0}'.format(s)
        song = search_song(s[0], s[1])

        if song:
            song.load()

            # Add song to the playlist if it's not already there
            if not is_song_in_playlist(song, playlist):
                print 'Adding track: {0} - {1}'.format(song.artists, song.name)
                playlist.add_tracks(song, 0)

    # Removes old tracks if the playlist length is > SPOTIFY_PLAYLIST_MAXLENGTH
    if len(playlist.tracks > SPOTIFY_PLAYLIST_MAXLENGTH):
        indexes_to_remove = [x for x in range(SPOTIFY_PLAYLIST_MAXLENGTH,
            len(playlist.tracks))]
        playlist.remove_tracks(indexes_to_remove)
