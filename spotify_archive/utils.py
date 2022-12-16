from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Generator
from typing import NamedTuple

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

from spotify_archive.config import SpotifyConfig
from spotify_archive.logger import logger


class TrackInfo(NamedTuple):
    external_id: str | None
    uri: str
    position: int
    added_at: str


def load_client_from_config(config: SpotifyConfig) -> Spotify:
    return load_client(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        username=config.username,
        refresh_token=config.refresh_token,
    )


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


def get_all_playlist_items(client: Spotify, playlist_id: str) -> list[dict]:
    results = client.playlist_items(playlist_id)
    items = results["items"]
    while results["next"]:
        results = client.next(results)
        items.extend(results["items"])
    return items


def parse_playlist(client: Spotify, playlist_id: str) -> list[str]:
    playlist_items = get_all_playlist_items(client, playlist_id)
    track_uris = [item["track"]["uri"] for item in playlist_items]
    return track_uris


def add_to_all_time_playlist(
    client: Spotify,
    track_uris: list[str],
    all_time_playlist_id: str,
) -> list[str]:
    all_tracks = get_all_playlist_items(client, all_time_playlist_id)
    logger.info(f"Found all time playlist with {len(all_tracks)} tracks")

    all_time_uris = [t["track"]["uri"] for t in all_tracks]
    uris_to_be_added = [uri for uri in track_uris if uri not in all_time_uris]

    if not uris_to_be_added:
        logger.info("All tracks are already included.")
        return []

    client.playlist_add_items(all_time_playlist_id, uris_to_be_added)
    logger.info(f"Archived {len(uris_to_be_added)} tracks.")
    return uris_to_be_added


def update_playlist_description(client: Spotify, n_tracks: int, playlist_id: str):
    current_date = datetime.today().strftime("%d.%m.%Y")
    description = (
        "This playlist is continously updated by spotify-archive. "
        "Recently added: "
        f"{n_tracks} track{'' if n_tracks == 1 else 's'} ({current_date})"
    )
    logger.info(f"Changing playlist description to:\n{description}")
    client.playlist_change_details(playlist_id=playlist_id, description=description)


def find_duplicates_by_external_id(tracks: list) -> list[dict[str, str | list[int]]]:
    """Find duplicate tracks by external id.

    The position of the track in the playlist is 0-indexed, according to:
    http://web.archive.org/web/20201112020302/https://developer.spotify.com/documentation/web-api/reference/playlists/remove-tracks-playlist/

    Args:
        tracks (list): List of tracks.

    Returns:
        list[str]: List of track uris to be removed, with their positions.
    """
    tracks_info = [
        TrackInfo(
            external_id=t["track"].get("external_ids", {}).get("isrc"),
            uri=t["track"]["id"],
            position=pos,
            added_at=t["added_at"],
        )
        for pos, t in enumerate(tracks)
    ]

    seen: dict[str, list[TrackInfo]] = defaultdict(list)
    for t in tracks_info:
        if t.external_id is not None:
            seen[t.external_id].append(t)

    duplicates = [v for v in seen.values() if len(v) > 1]

    to_remove: list[dict[str, str | list[int]]] = []
    for d in duplicates:
        # Only keep the first occurrence of the track
        d.sort(key=lambda x: x.added_at)
        to_remove += [{"uri": t.uri, "positions": [t.position]} for t in d[1:]]
    return to_remove


def make_chunks(list_: list, n: int) -> Generator[list, None, None]:
    for i in range(0, len(list_), n):
        yield list_[i : i + n]


def deduplicate_playlist(playlist_id: str, client: Spotify):
    tracks = get_all_playlist_items(client, playlist_id)
    dups = find_duplicates_by_external_id(tracks)

    if not dups:
        logger.info(f"No duplicates found in {playlist_id}")
        return

    logger.info(f"Removing {len(dups)} duplicates from {playlist_id}")
    for chunk in make_chunks(dups, 100):
        client.playlist_remove_specific_occurrences_of_items(
            playlist_id=playlist_id,
            items=chunk,
        )
        logger.info(f"Removed {len(chunk)} duplicates from {playlist_id}")

    logger.info(f"Done removing duplicates from {playlist_id}")