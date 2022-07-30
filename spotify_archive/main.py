import argparse
from typing import Dict, List

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

from spotify_archive.config import config
from spotify_archive.logger import logger

SCHEDULES = ["daily", "weekly"]


def main():
    schedule = parse_schedule()
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
        track_uris = parse_playlist(client, playlist.original_playlist)
        logger.info(f"Found {name} with {len(track_uris)} tracks")
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
) -> Spotify:
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
    client = Spotify(auth_manager=auth_manager)
    return client


def get_all_playlist_items(client: Spotify, playlist_id: str) -> List[Dict]:
    results = client.playlist_items(playlist_id)
    items = results["items"]
    while results["next"]:
        results = client.next(results)
        items.extend(results["items"])
    return items


def parse_playlist(client: Spotify, playlist_id: str) -> List[str]:
    playlist_items = get_all_playlist_items(client, playlist_id)
    track_uris = [item["track"]["uri"] for item in playlist_items]
    return track_uris


def add_to_all_time_playlist(
    client: Spotify, track_uris: List[str], all_time_playlist_id: str
) -> bool:
    all_tracks = get_all_playlist_items(client, all_time_playlist_id)
    logger.info(f"Found all time playlist with {len(all_tracks)} tracks")

    all_time_uris = [t["track"]["uri"] for t in all_tracks]
    uris_to_be_added = [uri for uri in track_uris if uri not in all_time_uris]

    if not uris_to_be_added:
        logger.info("All tracks are already included.")
        return False

    client.playlist_add_items(all_time_playlist_id, uris_to_be_added)
    logger.info(f"Archived {len(uris_to_be_added)} tracks.")
    return True


def parse_schedule() -> str:
    parser = argparse.ArgumentParser(description="Archive Playlist tracks")
    parser.add_argument("schedule", type=str, nargs="?", help="the schedule to be run")
    args = parser.parse_args()

    if args.schedule not in SCHEDULES:
        raise ValueError(f"Unknown schedule {args.schedule}")
    return args.schedule


if __name__ == "__main__":
    main()
