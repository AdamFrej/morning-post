import unittest
from unittest.mock import patch, Mock
import os
import tempfile
import json
from morning import MorningPaperGenerator

class TestMorningPaperGenerator(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.test_dir.name, "config.json")
        self.output_dir = os.path.join(self.test_dir.name, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        # Create a test config
        test_config = {
            "rss_feeds": [
                {"name": "Test Feed", "url": "https://example.com/feed.xml", "max_articles": 2}
            ],
            "hacker_news": {
                "include": True,
                "max_articles": 2,
                "only_self_posts": True,
                "api_endpoints": {
                    "top_stories": "https://hacker-news.firebaseio.com/v0/topstories.json",
                    "item": "https://hacker-news.firebaseio.com/v0/item/{}.json",
                    "discussion_url": "https://news.ycombinator.com/item?id={}"
                }
            },
            "output_directory": self.output_dir,
            "templates": {
                "directory": os.path.join(self.test_dir.name, "templates"),
                "main_template": "paper_template.html"
            }
        }

        with open(self.config_path, 'w') as f:
            json.dump(test_config, f)

        # Create a test template directory
        template_dir = os.path.join(self.test_dir.name, "templates")
        os.makedirs(template_dir, exist_ok=True)

        # Create a test template
        with open(os.path.join(template_dir, "paper_template.html"), 'w') as f:
            f.write("<html><body>{{ articles|length }} articles</body></html>")

    def tearDown(self):
        self.test_dir.cleanup()

    @patch('morning.fetchers.rss.RSSFetcher.fetch_articles')
    @patch('morning.fetchers.hackernews.HackerNewsFetcher.fetch_articles')
    @patch('morning.rendering.DocumentRenderer.generate_pdf')
    def test_run_successful(self, mock_generate_pdf, mock_hn_fetch, mock_rss_fetch):
        # Mock fetchers to return test articles
        mock_rss_fetch.return_value = [
            {
                "title": "RSS Article",
                "source": "Test Feed",
                "link": "https://example.com/article",
                "published": "2023-01-01",
                "content": "<p>Test content</p>"
            }
        ]

        mock_hn_fetch.return_value = [
            {
                "title": "HN Article",
                "source": "Hacker News",
                "link": "https://news.ycombinator.com/item?id=123",
                "published": "2023-01-01",
                "content": "<p>Test content</p>"
            }
        ]

        # Mock PDF generation
        pdf_path = os.path.join(self.output_dir, "morning_paper_test.pdf")
        mock_generate_pdf.return_value = pdf_path

        # Create and run the generator
        generator = MorningPaperGenerator(config_path=self.config_path)
        result = generator.run()

        # Verify fetchers were called
        mock_rss_fetch.assert_called_once()
        mock_hn_fetch.assert_called_once()

        # Verify PDF was generated
        mock_generate_pdf.assert_called_once()
        self.assertEqual(result, pdf_path)

        # Verify articles were combined
        self.assertEqual(len(generator.articles), 2)

    @patch('morning.fetchers.rss.RSSFetcher.fetch_articles')
    @patch('morning.fetchers.hackernews.HackerNewsFetcher.fetch_articles')
    def test_run_no_articles(self, mock_hn_fetch, mock_rss_fetch):
        # Mock fetchers to return no articles
        mock_rss_fetch.return_value = []
        mock_hn_fetch.return_value = []

        # Create and run the generator
        generator = MorningPaperGenerator(config_path=self.config_path)
        result = generator.run()

        # Verify no PDF was generated
        self.assertIsNone(result)
        # Verify fetchers were called
        mock_rss_fetch.assert_called_once()
        mock_hn_fetch.assert_called_once()
