from __future__ import annotations

import pytest

from spotify_archive.utils import find_duplicates_by_external_id


def track(isrc, uri, added_at):
    return {
        "track": {"external_ids": {"isrc": isrc}, "id": uri},
        "added_at": added_at,
    }


class TestDuplicates:
    @pytest.mark.parametrize(
        "tracks,expected",
        [
            # No duplicates
            (
                [
                    track("ABC123", "track1", "2022-01-01T00:00:00Z"),
                    track("DEF456", "track2", "2022-01-02T00:00:00Z"),
                ],
                [],
            ),
            # Two duplicates
            (
                [
                    track("ABC123", "track1", "2022-01-01T00:00:00Z"),
                    track("ABC123", "track2", "2022-01-02T00:00:00Z"),
                    track("DEF456", "track3", "2022-01-03T00:00:00Z"),
                ],
                [
                    {"uri": "track2", "positions": [1]},
                ],
            ),
            # Three duplicates, two with the same added_at
            (
                [
                    track("ABC123", "track1", "2022-01-01T00:00:00Z"),
                    track("ABC123", "track2", "2022-01-01T00:00:00Z"),
                    track("ABC123", "track3", "2022-01-03T00:00:00Z"),
                    track("DEF456", "track4", "2022-01-04T00:00:00Z"),
                ],
                [
                    {"uri": "track2", "positions": [1]},
                    {"uri": "track3", "positions": [2]},
                ],
            ),
            # Three duplicates, all with different added_at
            (
                [
                    track("ABC123", "track1", "2022-01-01T00:00:00Z"),
                    track("ABC123", "track2", "2022-01-02T00:00:00Z"),
                    track("ABC123", "track3", "2022-01-03T00:00:00Z"),
                    track("DEF456", "track4", "2022-01-04T00:00:00Z"),
                ],
                [
                    {"uri": "track2", "positions": [1]},
                    {"uri": "track3", "positions": [2]},
                ],
            ),
            # Three duplicates, different order
            (
                [
                    track("ABC123", "track3", "2022-01-03T00:00:00Z"),
                    track("ABC123", "track1", "2022-01-01T00:00:00Z"),
                    track("DEF456", "track4", "2022-01-04T00:00:00Z"),
                    track("ABC123", "track2", "2022-01-02T00:00:00Z"),
                ],
                [
                    {"uri": "track2", "positions": [3]},
                    {"uri": "track3", "positions": [0]},
                ],
            ),
            # Multiple tracks, multiple duplicates
            (
                [
                    track("ABC123", "track3", "2022-01-03T00:00:00Z"),
                    track("ABC123", "track1", "2022-01-01T00:00:00Z"),
                    track("DEF456", "track4", "2022-01-04T00:00:00Z"),
                    track("ABC123", "track2", "2022-01-02T00:00:00Z"),
                    track("DEF456", "track5", "2022-01-06T00:00:00Z"),
                    track("GHI789", "track7", "2022-01-04T00:00:00Z"),
                    track("GHI789", "track6", "2022-01-05T00:00:00Z"),
                ],
                [
                    {"uri": "track2", "positions": [3]},
                    {"uri": "track3", "positions": [0]},
                    {"uri": "track5", "positions": [4]},
                    {"uri": "track6", "positions": [6]},
                ],
            ),
        ],
    )
    def test_find_duplicates_by_external_id(self, tracks, expected):
        duplicates = find_duplicates_by_external_id(tracks)
        assert duplicates == expected
