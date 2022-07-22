from datetime import datetime
from typing import List, Tuple

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from spotify_archive.config import config
from spotify_archive.logger import logger


def main(schedule: str):
    logger.info("Loading client")
    client = load_client(
        client_id=config.spotify.client_id,
        client_secret=config.spotify.client_secret,
        redirect_uri=config.spotify.redirect_uri,
        username=config.spotify.username,
        refresh_token=config.spotify.refresh_token,
    )

    logger.info(f"Archiving {schedule} playlists")
    playlists = getattr(config, schedule)
    for name, playlist in playlists.items():
        playlist_date, track_uris = parse_playlist(client, playlist.original_playlist)
        logger.info(f"Found {name} for {playlist_date}")
        logger.info("Adding to all time playlist")
        add_to_all_time_playlist(client, track_uris, playlist.all_time_playlist)

    logger.info("Done archiving")


def main_daily():
    main("daily")


def main_weekly():
    main("weekly")


def load_client(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    username: str,
    refresh_token: str,
) -> spotipy.Spotify:
    scopes = ["playlist-read-private", "playlist-modify-private"]
    # Authenticate
    auth_manager = SpotifyOAuth(
        scope=scopes,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        username=username,
    )
    auth_manager.refresh_access_token(refresh_token)
    client = spotipy.Spotify(auth_manager=auth_manager)
    return client


def parse_playlist(client: spotipy.Spotify, playlist_id: str) -> Tuple[str, List[str]]:
    playlist_items = client.playlist_items(playlist_id)
    playlist_created = datetime.strptime(
        playlist_items["items"][0]["added_at"], "%Y-%m-%dT%H:%M:%S%z"
    )
    playlist_date = playlist_created.strftime("%Y-%m-%d")

    track_uris = [item["track"]["uri"] for item in playlist_items["items"]]
    return playlist_date, track_uris


def add_to_all_time_playlist(
    client: spotipy.Spotify, track_uris: List[str], all_time_playlist_id: str
) -> bool:
    all_tracks = client.playlist_items(all_time_playlist_id)

    all_time_uris = [t["track"]["uri"] for t in all_tracks["items"]]
    uris_to_be_added = [uri for uri in track_uris if uri not in all_time_uris]

    if not uris_to_be_added:
        logger.info("All tracks are already included.")
        return False

    client.playlist_add_items(all_time_playlist_id, uris_to_be_added)
    logger.info(f"Archived {len(uris_to_be_added)} tracks.")
    return True
