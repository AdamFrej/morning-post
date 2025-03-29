"""Configuration management for Morning Paper Generator."""
import json
import logging
import os
from typing import Dict, Any, Optional

from .config_models import AppConfig

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        """Initialize configuration manager."""
        self.config_path = config_path
        self._raw_config = self._load_config_file()
        self.config = self._parse_config()

    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info(f"Config file not found at {self.config_path}, creating default config")
            default_config = self._get_default_config()
            os.makedirs(os.path.dirname(self.config_path) or '.', exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file: {e}")
            logger.info("Using default configuration")
            return self._get_default_config()

    def _parse_config(self) -> AppConfig:
        """Parse raw config into validated Pydantic model."""
        try:
            return AppConfig.model_validate(self._raw_config)  # V2 style using model_validate
        except Exception as e:
            logger.error(f"Error in configuration: {e}")
            logger.info("Using default configuration")
            return AppConfig.model_validate(self._get_default_config())  # V2 style using model_validate

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration settings."""
        return {
            "rss_feeds": [
                {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "max_articles": 5},
                {"name": "New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "max_articles": 5}
            ],
            "hacker_news": {
                "include": True,
                "max_articles": 5,
                "only_self_posts": True,
                "api_endpoints": {
                    "top_stories": "https://hacker-news.firebaseio.com/v0/topstories.json",
                    "item": "https://hacker-news.firebaseio.com/v0/item/{}.json",
                    "discussion_url": "https://news.ycombinator.com/item?id={}"
                }
            },
            "output_directory": "./papers",
            "templates": {
                "directory": "./templates",
                "main_template": "paper_template.html",
                "article_template": "article_template.html"
            },
            "extract_full_content": True,
            "include_images": False,
            "timeout": {
                "request": 10,
                "extraction": 15
            },
            "max_content_length": 50000,
            "site_specific_selectors": {
                "nytimes.com": "article[data-testid='article-container']",
                "bbc.com": "article[data-component='text-block']",
                "bbc.co.uk": "article[data-component='text-block']"
            },
            "fallback_selectors": [
                "article", "main", "div.content", "div.article", "div.post",
                ".entry-content", "#content", ".article__body", ".post-content"
            ],
            "elements_to_remove": [
                "script", "style", "iframe", "noscript", "video", "audio"
            ],
            "class_selectors_to_remove": [
                ".comments", ".social-share", ".related-articles",
                ".newsletter-signup", ".advertisement", ".ad", ".popup"
            ]
        }

    def save_config(self) -> None:
        """Save current configuration back to file."""
        try:
            # Convert Pydantic model to dict with handling of special types
            config_dict = self.config.model_dump(mode='json')  # V2 style using model_dump
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
