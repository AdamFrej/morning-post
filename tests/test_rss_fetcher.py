import unittest
from unittest.mock import patch, Mock
import feedparser
from morning.fetchers.rss import RSSFetcher
from morning.config_models import AppConfig, RSSFeedConfig

class TestRSSFetcher(unittest.TestCase):
    def setUp(self):
        # Create a minimal config with mock RSS feeds
        self.config = AppConfig(
            rss_feeds=[
                RSSFeedConfig(name="Test Feed", url="https://example.com/feed.xml", max_articles=2)
            ],
            hacker_news={
                "include": False,
                "max_articles": 5,
                "only_self_posts": True,
                "api_endpoints": {
                    "top_stories": "https://hacker-news.firebaseio.com/v0/topstories.json",
                    "item": "https://hacker-news.firebaseio.com/v0/item/{}.json",
                    "discussion_url": "https://news.ycombinator.com/item?id={}"
                }
            },
            extract_full_content=True
        )

        # Create a mock content extractor
        self.mock_extractor = Mock()
        self.mock_extractor._is_valid_url.return_value = True
        self.mock_extractor.extract_article_content.return_value = "<p>Extracted content</p>"

        self.fetcher = RSSFetcher(self.config, self.mock_extractor)

    @patch('feedparser.parse')
    def test_fetch_articles(self, mock_parse):
        # Create a mock feed response
        mock_feed = Mock()
        mock_entry1 = Mock(title="Article 1", link="https://example.com/article1",
                          published="Mon, 01 Jan 2023 12:00:00 +0000", summary="Summary 1")
        mock_entry2 = Mock(title="Article 2", link="https://example.com/article2",
                          published="Mon, 02 Jan 2023 12:00:00 +0000", summary="Summary 2")

        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_parse.return_value = mock_feed

        # Fetch articles
        articles = self.fetcher.fetch_articles()

        # Verify feed was parsed
        mock_parse.assert_called_once()

        # Verify articles were extracted
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], "Article 1")
        self.assertEqual(articles[1]["title"], "Article 2")
        self.assertEqual(articles[0]["source"], "Test Feed")
        self.assertEqual(articles[0]["content"], "<p>Extracted content</p>")

        # Verify content extractor was called
        self.mock_extractor.extract_article_content.assert_called()

    @patch('feedparser.parse')
    def test_fetch_articles_max_limit(self, mock_parse):
        # Create a mock feed with more entries than the max_articles limit
        mock_feed = Mock()
        mock_entries = [
            Mock(title=f"Article {i}", link=f"https://example.com/article{i}",
                published=f"Mon, {i} Jan 2023 12:00:00 +0000", summary=f"Summary {i}")
            for i in range(1, 6)  # 5 articles, but max is 2
        ]

        mock_feed.entries = mock_entries
        mock_parse.return_value = mock_feed

        # Fetch articles
        articles = self.fetcher.fetch_articles()

        # Verify only max_articles were fetched
        self.assertEqual(len(articles), 2)

    @patch('feedparser.parse')
    def test_fetch_articles_invalid_url(self, mock_parse):
        # Mock an invalid URL in one of the entries
        mock_feed = Mock()
        mock_entry1 = Mock(title="Valid Article", link="https://example.com/valid",
                          published="Mon, 01 Jan 2023 12:00:00 +0000", summary="Valid summary")
        mock_entry2 = Mock(title="Invalid Article", link="invalid-url",
                          published="Mon, 02 Jan 2023 12:00:00 +0000", summary="Invalid summary")

        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_parse.return_value = mock_feed

        # Mock the content extractor to reject the invalid URL
        self.mock_extractor._is_valid_url = lambda url: url.startswith("http")

        # Fetch articles
        articles = self.fetcher.fetch_articles()

        # Verify only the valid article was fetched
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Valid Article")
