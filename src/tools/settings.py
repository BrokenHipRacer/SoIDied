import yaml
import os
from typing import Any, Dict, Optional


class Settings:
    """Configuration manager for SoIDied - loads and provides access to YAML config."""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize Settings by loading configuration from a YAML file.

        Args:
            config_path: Path to the config.yaml file (relative or absolute)

        Raises:
            FileNotFoundError: If a config file does not exist,
            yaml.YAMLError: If a config file is invalid YAML
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as file:
            self._config: Dict[str, Any] = yaml.safe_load(file)

        self.config_path = config_path

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a top-level configuration key with an optional default value.

        Args:
            key: Configuration key to retrieve
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def get_nested(self, *keys: str) -> Any:
        """
        Get a nested configuration value using dot notation or multiple arguments.

        Example:
            settings.get_nested('defences', 'check_in_interval')
            or via dict access: settings['defences']['check_in_interval']

        Args:
            *keys: Sequence of keys to traverse the config dict

        Returns:
            Configuration value at the nested path

        Raises:
            KeyError: If any key in the path does not exist
        """
        value = self._config
        for key in keys:
            value = value[key]
        return value

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access: settings['app']"""
        return self._config[key]

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in config: 'app' in settings"""
        return key in self._config

    @property
    def config(self) -> Dict[str, Any]:
        """Get the raw configuration dictionary."""
        return self._config
