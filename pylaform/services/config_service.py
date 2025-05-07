import json
import os
from pathlib import Path


class ConfigService:
    """Service to manage application configuration"""

    def __init__(self, config_file="config.json"):
        """
        Initialize the configuration service

        :param config_file: Path to the configuration file
        """
        # Get the directory where the app is running
        app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        data_dir = app_dir.parent.parent / "data"

        # Create data directory if it doesn't exist
        if not data_dir.exists():
            data_dir.mkdir(parents=True)

        self.config_path = data_dir / config_file
        self.config = self._load_config()

    def _load_config(self):
        """
        Load configuration from file or create default config

        :return: Configuration dictionary
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # Return default config if file is invalid
                return self._get_default_config()
        else:
            # Create default config
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config

    def _save_config(self, config):
        """
        Save configuration to file

        :param config: Configuration dictionary to save
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
                return True
        except IOError:
            return False

    def _get_default_config(self):
        """
        Get default configuration

        :return: Default configuration dictionary
        """
        return {
            "ai": {
                "enabled": False,
                "ollama": {
                    "host": "localhost",
                    "port": "11434",
                    "model": "gemma3:1b"
                }
            }
        }

    def get_ai_config(self):
        """
        Get AI configuration

        :return: AI configuration dictionary
        """
        return self.config.get("ai", self._get_default_config()["ai"])

    def save_ai_config(self, enabled, host, port, model):
        """
        Save AI configuration

        :param enabled: Whether AI features are enabled
        :param host: Ollama server host
        :param port: Ollama server port
        :param model: Ollama model to use
        :return: Success status
        """
        self.config["ai"] = {
            "enabled": enabled,
            "ollama": {
                "host": host,
                "port": port,
                "model": model
            }
        }
        return self._save_config(self.config)