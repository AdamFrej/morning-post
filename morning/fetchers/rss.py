"""RSS feed article fetcher."""
import logging
import feedparser
import time
import gc

logger = logging.getLogger(__name__)

class RSSFetcher:
    def __init__(self, config, content_extractor):
        """Initialize RSS fetcher."""
        self.config = config
        self.content_extractor = content_extractor

    def fetch_articles(self):
        """Fetch articles from configured RSS feeds."""
        articles = []
        for feed_config in self.config["rss_feeds"]:
            try:
                feed = feedparser.parse(feed_config["url"])
                logger.info(f"Fetched {len(feed.entries)} articles from {feed_config['name']}")

                for i, entry in enumerate(feed.entries):
                    if i >= feed_config["max_articles"]:
                        break

                    if not hasattr(entry, 'link') or not self.content_extractor._is_valid_url(entry.link):
                        logger.warning(f"Skipping entry with invalid URL: {getattr(entry, 'title', 'Unknown')}")
                        continue

                    article = {
                        "title": getattr(entry, 'title', 'No title'),
                        "source": feed_config["name"],
                        "link": entry.link,
                        "published": getattr(entry, 'published', 'Unknown date'),
                        "summary": getattr(entry, 'summary', '')
                    }

                    # Extract full content if configured
                    if self.config["extract_full_content"]:
                        try:
                            article["content"] = self.content_extractor.extract_article_content(entry.link)
                            # Add a short delay to avoid hammering servers
                            time.sleep(1)
                        except Exception as e:
                            logger.warning(f"Failed to extract full content for {article['title']}: {e}")
                            article["content"] = f"<p>{article['summary']}</p>"
                    else:
                        article["content"] = f"<p>{article['summary']}</p>"

                    articles.append(article)

                    # Force garbage collection to free memory
                    gc.collect()
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_config['name']}: {e}")

        logger.info(f"Successfully fetched {len(articles)} articles from RSS feeds")
        return articles
