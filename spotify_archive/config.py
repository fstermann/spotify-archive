import inspect
import os
from dataclasses import dataclass
from typing import Dict

import yaml
from dotenv import dotenv_values


@dataclass
class PlaylistConfig:
    original_playlist: str
    all_time_playlist: str


@dataclass
class SpotifyConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    username: str
    refresh_token: str

    @classmethod
    def from_env(cls, env):
        return cls(
            **{
                k.lower(): v
                for k, v in env.items()
                if k.lower() in inspect.signature(cls).parameters
            }
        )


@dataclass
class Config:
    daily: Dict[str, PlaylistConfig]
    weekly: Dict[str, PlaylistConfig]
    spotify: SpotifyConfig


with open("conf/config.yaml", "r") as f:
    config_raw = yaml.safe_load(f)

config = Config(
    daily={name: PlaylistConfig(**pc) for name, pc in config_raw["daily"].items()},
    weekly={name: PlaylistConfig(**pc) for name, pc in config_raw["weekly"].items()},
    spotify=SpotifyConfig.from_env({**dotenv_values(".env"), **os.environ}),
)
