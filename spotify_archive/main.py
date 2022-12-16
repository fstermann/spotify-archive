from __future__ import annotations

import argparse

from spotify_archive.config import config
from spotify_archive.logger import logger
from spotify_archive.utils import add_to_all_time_playlist
from spotify_archive.utils import deduplicate_playlist
from spotify_archive.utils import load_client_from_config
from spotify_archive.utils import parse_playlist
from spotify_archive.utils import update_playlist_description

SCHEDULES = ["daily", "weekly"]


def archive():
    schedule = parse_schedule()
    logger.info("Loading client")
    client = load_client_from_config(config.spotify)

    logger.info(f"Archiving {schedule} playlists")
    playlists = getattr(config, schedule)
    for name, playlist in playlists.items():
        track_uris = parse_playlist(client, playlist.original_playlist)
        logger.info(f"Found {name} with {len(track_uris)} tracks")
        logger.info("Adding to all time playlist")
        added_tracks = add_to_all_time_playlist(
            client,
            track_uris=track_uris,
            all_time_playlist_id=playlist.all_time_playlist,
        )
        update_playlist_description(
            client,
            n_tracks=len(added_tracks),
            playlist_id=playlist.all_time_playlist,
        )

    logger.info("Done archiving")


def deduplicate():
    schedule = parse_schedule()
    logger.info("Loading client")
    client = load_client_from_config(config.spotify)

    playlists = getattr(config, schedule)
    for name, playlist in playlists.items():
        logger.info(f"Deduplicating {name}")
        deduplicate_playlist(playlist.all_time_playlist, client)


def parse_schedule() -> str:
    parser = argparse.ArgumentParser(description="Archive Playlist tracks")
    parser.add_argument("schedule", type=str, nargs="?", help="The schedule to be run")
    args = parser.parse_args()

    if args.schedule not in SCHEDULES:
        raise ValueError(f"Unknown schedule {args.schedule}")
    return args.schedule


if __name__ == "__main__":
    deduplicate()
