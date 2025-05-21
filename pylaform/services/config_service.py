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

    def save_linkedin_config(self, proxycurl_api_key):
        """
        Save LinkedIn configuration

        :param proxycurl_api_key: API key for Proxycurl
        :return: Success status
        """
        if 'linkedin' not in self.config:
            self.config['linkedin'] = {}

        self.config['linkedin']['proxycurl_api_key'] = proxycurl_api_key

        # Also set in environment for immediate use
        os.environ['PROXYCURL_API_KEY'] = proxycurl_api_key

        return self._save_config(self.config)

    def _get_default_config(self):
        """
        Get default configuration

        :return: Default configuration dictionary
        """
        return {
            "ai": {
                "enabled": True,
                "service_type": "AMAZON_Q",
                "amazon_q": {
                    "region": "us-east-1",
                    "application_id": ""
                }
            }
        }

    def get_ai_config(self):
        """
        Get AI service configuration

        :return: Dictionary with Amazon Q service configuration
        """
        return {
            'service_type': 'AMAZON_Q',
            'amazon_q': {
                'region': os.environ.get('AMAZON_Q_REGION',
                                         self.config.get('ai', {}).get('amazon_q', {}).get('region', 'us-east-1')),
                'application_id': os.environ.get('AMAZON_Q_APPLICATION_ID',
                                                 self.config.get('ai', {}).get('amazon_q', {}).get('application_id')),
            }
        }

    def save_ai_config(self, enabled, region, application_id):
        """
        Save Amazon Q configuration

        :param enabled: Whether AI features are enabled
        :param region: AWS region for Amazon Q
        :param application_id: Amazon Q application ID
        :return: Success status
        """
        self.config["ai"] = {
            "enabled": enabled,
            "service_type": "AMAZON_Q",
            "amazon_q": {
                "region": region,
                "application_id": application_id
            }
        }
        return self._save_config(self.config)

    # LinkedIn API settings
    LINKEDIN_CONFIG = {
        'CLIENT_ID': os.environ.get('LINKEDIN_CLIENT_ID', ''),
        'CLIENT_SECRET': os.environ.get('LINKEDIN_CLIENT_SECRET', ''),
        'REDIRECT_URI': os.environ.get('LINKEDIN_REDIRECT_URI', 'http://localhost:5000/auth/linkedin/callback'),
        'SCOPES': 'r_liteprofile r_emailaddress r_basicprofile'
    }

    @classmethod
    def get_linkedin_config(cls):
        """Get LinkedIn API configuration settings"""
        return cls.LINKEDIN_CONFIG