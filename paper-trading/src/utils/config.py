"""Configuration management with YAML loading and dotted-key access."""

import os
import yaml
from dotenv import load_dotenv


class Config:
    """Singleton configuration manager."""

    _instance = None

    def __init__(self, config_path="config.yaml"):
        load_dotenv()
        self._config_path = config_path
        self._data = {}
        self._load()

    def _load(self):
        with open(self._config_path, "r") as f:
            self._data = yaml.safe_load(f) or {}

    @classmethod
    def get_instance(cls, config_path=None):
        if cls._instance is None:
            if config_path is None:
                config_path = "config.yaml"
            cls._instance = cls(config_path)
        return cls._instance

    def get(self, dotted_key, default=None):
        """Access nested config values: config.get('trading.pairs')."""
        keys = dotted_key.split(".")
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default

        # Check for environment variable override
        env_key = "TRADING_" + dotted_key.upper().replace(".", "_")
        env_val = os.environ.get(env_key)
        if env_val is not None:
            # Try to cast to the same type as the config value
            if isinstance(value, bool):
                return env_val.lower() in ("true", "1", "yes")
            elif isinstance(value, int):
                return int(env_val)
            elif isinstance(value, float):
                return float(env_val)
            return env_val

        return value

    def reload(self):
        """Reload config from disk."""
        self._load()
