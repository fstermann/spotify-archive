from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from itertools import zip_longest
from typing import Generator
from typing import NamedTuple

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

from spotify_archive.config import SpotifyConfig
from spotify_archive.logger import logger

MAX_SEEDS = 5


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
    """Load a Spotify client from config

    Args:
        client_id (str): The client id
        client_secret (str): The client secret
        redirect_uri (str): The redirect uri
        username (str): The username
        refresh_token (str): The refresh token

    Returns:
        Spotify: The Spotify client
    """
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
    """Get all items (tracks) from a playlist.

    Args:
        client (Spotify): The Spotify client
        playlist_id (str): The playlist id

    Returns:
        list[dict]: A list of all items (tracks) in the playlist
    """
    results = client.playlist_items(playlist_id)
    items = results["items"]
    while results["next"]:
        results = client.next(results)
        items.extend(results["items"])
    return items


def parse_playlist(client: Spotify, playlist_id: str) -> list[str]:
    """Parse a playlist and return a list of track uris.

    This return the raw track uris, not the ids with the spotify:track: prefix.

    Args:
        client (Spotify): The Spotify client
        playlist_id (str): The playlist id

    Returns:
        list[str]: A list of track uris
    """
    playlist_items = get_all_playlist_items(client, playlist_id)
    track_uris = [item["track"]["id"] for item in playlist_items]
    return track_uris


def get_recommendations(
    client: Spotify,
    seed_tracks: list[str] | None = None,
    seed_genres: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get recommendations from Spotify.

    Args:
        client (Spotify): The Spotify client
        seed_tracks (list[str]): A list of seed tracks
        seed_genres (list[str], optional): A list of seed genres. Defaults to None.
        limit (int): The number of recommendations to return

    Returns:
        list[dict]: A list of recommendation tracks

    Raises:
        ValueError: If limit is greater than 100
        ValueError: If no seed tracks or genres are provided
        ValueError: If the total number of seeds is greater than 5 (MAX_SEEDS)
    """
    if limit > 100:
        raise ValueError("limit must be less than or equal to 100")
    if not seed_tracks and not seed_genres:
        raise ValueError("Must provide at least one seed track or genre")
    if len(seed_tracks or []) + len(seed_genres or []) > MAX_SEEDS:
        raise ValueError(
            f"Total number of seeds must be less than or equal to {MAX_SEEDS}",
        )

    logger.info("Getting recommendations...")
    logger.info(f"Seed tracks: {seed_tracks}")
    logger.info(f"Seed genres: {seed_genres}")
    recommendations = client.recommendations(
        seed_tracks=seed_tracks,
        seed_genres=seed_genres,
        limit=limit,
    )
    return recommendations["tracks"]


def add_recommendations_to_all_time_playlist(
    client: Spotify,
    all_time_playlist_id: str,
    limit: int = 5,
    seed_genres: list[str] | None = None,
    max_tries: int = 5,
) -> list[str]:
    """Add recommendations to the all time playlist.

    Args:
        client (Spotify): The Spotify clientc
        all_time_playlist_id (str): The all time playlist id
        limit (int): The number of recommendations to return
        max_tries (int): The number of times to try to get recommendations

    Returns:
        list[str]: A list of track uris that were added to the playlist
    """
    all_tracks = get_all_playlist_items(client, all_time_playlist_id)
    all_uris = [t["track"]["id"] for t in all_tracks]
    all_uris.reverse()

    all_candidates = set()
    tries = 0
    seed_uris = make_chunks(all_uris, MAX_SEEDS - len(seed_genres or []))

    for s_uris, s_genres in zip_longest(seed_uris, [seed_genres] * max_tries):
        tries += 1
        logger.info(f"Trying to get recommendations {tries}/{max_tries}...")

        recommendations = get_recommendations(
            client,
            seed_tracks=s_uris,
            seed_genres=s_genres,
            limit=100,
        )
        logger.info(f"Got {len(recommendations)} recommendations.")

        candidates = filter_out_duplicates(
            tracks=all_tracks,
            new_tracks=recommendations,
        )
        logger.info(f"After filtering: {len(candidates)} candidates.")

        all_candidates.update({c["id"] for c in candidates})

        if len(all_candidates) >= limit or tries >= max_tries:
            break

    if not all_candidates:
        logger.info("Could not find any new tracks.")
        return []

    logger.info(f"Found {len(all_candidates)} new tracks.")
    uris_to_be_added = list(all_candidates)[:limit]
    logger.info(f"Adding {len(uris_to_be_added)} new tracks.")
    client.playlist_add_items(all_time_playlist_id, uris_to_be_added)
    logger.info(f"Added {len(uris_to_be_added)} new tracks.")
    return uris_to_be_added


def add_to_all_time_playlist(
    client: Spotify,
    tracks: list[dict],
    all_time_playlist_id: str,
) -> list[str]:
    """Add tracks to a given all time playlist.

    This function will only add tracks that are not already in the playlist.

    Args:
        client (Spotify): The Spotify client
        track_uris (list[str]): A list of track uris
        all_time_playlist_id (str): The all time playlist id

    Returns:
        list[str]: A list of track uris that were added to the playlist
    """
    all_tracks = get_all_playlist_items(client, all_time_playlist_id)
    logger.info(f"Found all time playlist with {len(all_tracks)} tracks")

    tracks_to_be_added = filter_out_duplicates(tracks=all_tracks, new_tracks=tracks)
    uris_to_be_added = [t["track"]["id"] for t in tracks_to_be_added]

    if not uris_to_be_added:
        logger.info("All tracks are already included.")
        return []

    client.playlist_add_items(all_time_playlist_id, uris_to_be_added)
    logger.info(f"Archived {len(uris_to_be_added)} tracks.")
    return uris_to_be_added


def update_playlist_description(client: Spotify, n_tracks: int, playlist_id: str):
    """Update the playlist description after adding tracks.

    Args:
        client (Spotify): The Spotify client
        n_tracks (int): The number of tracks that were added
        playlist_id (str): The id of the playlist to update
    """
    current_date = datetime.today().strftime("%d.%m.%Y")
    description = (
        "This playlist is continously updated by spotify-archive. "
        "Recently added: "
        f"{n_tracks} track{'' if n_tracks == 1 else 's'} ({current_date}). "
        "For more info visit github.com/fstermann/spotify-archive"
    )
    logger.info(f"Changing playlist description to:\n{description}")
    client.playlist_change_details(playlist_id=playlist_id, description=description)


def get_tracks_info(tracks: list) -> list[TrackInfo]:
    """Get track info from a list of tracks.

    Args:
        tracks (list): List of tracks.

    Returns:
        list[TrackInfo]: List of track info.
    """
    return [
        TrackInfo(
            external_id=t["track"].get("external_ids", {}).get("isrc"),
            uri=t["track"]["id"],
            position=pos,
            added_at=t["added_at"],
        )
        for pos, t in enumerate(tracks)
    ]


def filter_out_duplicates(tracks: list, new_tracks: list) -> list:
    """Filter out duplicate tracks.

    Args:
        tracks (list): List of tracks.
        new_tracks (list): List of new tracks.

    Returns:
        list: List of new tracks without tracks which are already in the list of tracks
    """
    tracks_info = get_tracks_info(tracks)

    # Remove duplicates by external id
    tracks_external_ids = {t.external_id for t in tracks_info}

    # Remove duplicates by uri, just to be sure
    tracks_uris = {t.uri for t in tracks_info}

    # Handle tracks from playlists or recommendations
    new_tracks = [t.get("track", t) for t in new_tracks]

    return [
        t
        for t in new_tracks
        if (
            t.get("external_ids", {}).get("isrc") not in tracks_external_ids
            and t["id"] not in tracks_uris
        )
    ]


def find_duplicates_by_external_id(tracks: list) -> list[dict[str, str | list[int]]]:
    """Find duplicate tracks by external id.

    The position of the track in the playlist is 0-indexed, according to:
    http://web.archive.org/web/20201112020302/https://developer.spotify.com/documentation/web-api/reference/playlists/remove-tracks-playlist/

    Args:
        tracks (list): List of tracks.

    Returns:
        list[str]: List of track uris to be removed, with their positions.
    """
    tracks_info = get_tracks_info(tracks)

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
    """Yield successive n-sized chunks from a list.

    Args:
        list_ (list): The list to split
        n (int): The chunk size

    Yields:
        Generator[list, None, None]: A generator of lists
    """
    for i in range(0, len(list_), n):
        yield list_[i : i + n]


def deduplicate_playlist(playlist_id: str, client: Spotify):
    """Remove duplicates from a playlist.

    This function will remove all duplicates from a playlist, based on the
    external id (ISRC). The external id links back to the original track, for
    example if a track was realeased on multiple albums.

    Args:
        playlist_id (str): The id of the playlist to deduplicate
        client (Spotify): The Spotify client
    """
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
