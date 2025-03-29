"""Configuration management for Morning Paper Generator."""
import json
import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path="config.json"):
        """Initialize configuration manager."""
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
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

    def _get_default_config(self):
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
                "bbc.co.uk": "article[data-component='text-block']",
                "theverge.com": "div.duet--article--article-body-component",
                "washingtonpost.com": "div.article-body",
                "medium.com": "article",
                "towardsdatascience.com": "article",
                "techcrunch.com": "div.article-content"
            },
            "fallback_selectors": [
                "article", "main", "div.content", "div.article", "div.post",
                ".entry-content", "#content", ".article__body", ".post-content",
                ".story", ".story-body", "[itemprop='articleBody']"
            ],
            "elements_to_remove": [
                "script", "style", "iframe", "noscript", "video", "audio",
                "embed", "object", "canvas", "form", "button", "aside",
                "header", "footer", "nav"
            ],
            "class_selectors_to_remove": [
                ".comments", ".social-share", ".related-articles", ".recommendations",
                ".newsletter-signup", ".advertisement", ".ad", ".popup", ".modal",
                ".share", ".social", ".related", ".popular", ".trending",
                ".recommended", "#comments", ".comments", ".comment-section",
                ".advertisement", ".ad-container", ".sponsored", ".subscribe",
                ".newsletter", ".signup", ".sidebar", ".footer", ".header"
            ]
        }
