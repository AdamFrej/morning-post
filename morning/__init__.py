"""Morning Paper Generator package."""
from .config import ConfigManager
from .content import ContentExtractor
from .templates import TemplateManager
from .rendering import DocumentRenderer
from .fetchers.rss import RSSFetcher
from .fetchers.hackernews import HackerNewsFetcher

class MorningPaperGenerator:
    def __init__(self, config_path="config.json"):
        """Initialize the paper generator with configuration."""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config
        self.content_extractor = ContentExtractor(self.config)
        self.template_manager = TemplateManager(self.config)
        self.rss_fetcher = RSSFetcher(self.config, self.content_extractor)
        self.hackernews_fetcher = HackerNewsFetcher(self.config, self.content_extractor)
        self.renderer = DocumentRenderer(self.config, self.template_manager)
        self.articles = []

    def run(self):
        """Run the complete paper generation process."""
        import logging
        import gc

        logger = logging.getLogger(__name__)
        logger.info("Starting paper generation process")

        try:
            # Fetch articles from RSS feeds
            rss_articles = self.rss_fetcher.fetch_articles()
            self.articles.extend(rss_articles)
            gc.collect()  # Free memory after RSS processing

            # Fetch articles from Hacker News
            hn_articles = self.hackernews_fetcher.fetch_articles()
            self.articles.extend(hn_articles)
            gc.collect()  # Free memory after Hacker News processing

            # Generate PDF
            return self.renderer.generate_pdf(self.articles)
        except Exception as e:
            logger.error(f"Error in paper generation process: {e}")
            return None
