from __future__ import annotations

import pytest

from spotify_archive.utils import make_chunks


class TestUtils:
    @pytest.mark.parametrize(
        "list_, n, expected",
        [
            ([1, 2, 3, 4, 5], 2, [[1, 2], [3, 4], [5]]),
            ([1, 2, 3, 4, 5], 3, [[1, 2, 3], [4, 5]]),
            ([1, 2, 3, 4, 5], 4, [[1, 2, 3, 4], [5]]),
            ([1, 2, 3, 4, 5], 5, [[1, 2, 3, 4, 5]]),
            ([1, 2, 3, 4, 5], 6, [[1, 2, 3, 4, 5]]),
            ([1, 2, 3, 4, 5], 7, [[1, 2, 3, 4, 5]]),
            ([1, 2, 3, 4, 5], 8, [[1, 2, 3, 4, 5]]),
            ([1, 2, 3, 4, 5], 9, [[1, 2, 3, 4, 5]]),
            ([1, 2, 3, 4, 5], 10, [[1, 2, 3, 4, 5]]),
            ([], 2, []),
        ],
    )
    def test_make_chunks(self, list_, n, expected):
        assert list(make_chunks(list_, n)) == expected
