from dataclasses import dataclass
from typing import Dict

import toml


@dataclass
class PlaylistConfig:
    original_playlist: str
    all_time_playlist: str


@dataclass
class Config:
    playlists: Dict[str, PlaylistConfig]


config = Config(
    playlists={
        name: PlaylistConfig(**pc) for name, pc in toml.load("conf/config.toml").items()
    }
)
