"""Morning Paper Generator package."""
import logging
from .config import ConfigManager
from .content import ContentExtractor
from .templates import TemplateManager
from .rendering import DocumentRenderer
from .fetchers.rss import RSSFetcher
from .fetchers.hackernews import HackerNewsFetcher

logger = logging.getLogger(__name__)  # Add this line to define logger

class MorningPaperGenerator:
    def __init__(self, config_path="config.json"):
        """Initialize the paper generator with configuration."""
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config  # Now a Pydantic model
        self.content_extractor = ContentExtractor(self.config)
        self.template_manager = TemplateManager(self.config)
        self.rss_fetcher = RSSFetcher(self.config, self.content_extractor)
        self.hackernews_fetcher = HackerNewsFetcher(self.config, self.content_extractor)
        self.renderer = DocumentRenderer(self.config, self.template_manager)
        self.articles = []

    def run(self):
        """Run the morning paper generation process.

        Returns:
            str: Path to the generated PDF file or None if generation failed
        """
        try:
            # Step 1: Fetch articles from RSS feeds
            rss_articles = self.rss_fetcher.fetch_articles()

            # Step 2: Fetch articles from Hacker News if enabled
            hn_articles = self.hackernews_fetcher.fetch_articles() if self.config.hacker_news.include else []

            # Step 3: Combine articles from different sources
            self.articles = rss_articles + hn_articles

            # Step 4: Generate the PDF document
            if not self.articles:
                logger.warning("No articles fetched. Cannot generate paper.")
                return None

            pdf_path = self.renderer.generate_pdf(self.articles)
            return pdf_path
        except Exception as e:
            logger.error(f"Error generating morning paper: {e}")
            return None
