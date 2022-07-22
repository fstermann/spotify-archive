from dataclasses import dataclass
from typing import Dict

import toml


@dataclass
class PlaylistConfig:
    original_playlist: str
    all_time_playlist: str


@dataclass
class Config:
    daily: Dict[str, PlaylistConfig]
    weekly: Dict[str, PlaylistConfig]


config_raw = toml.load("conf/config.toml")
config = Config(
    daily={name: PlaylistConfig(**pc) for name, pc in config_raw["daily"].items()},
    weekly={name: PlaylistConfig(**pc) for name, pc in config_raw["weekly"].items()},
)
