import unittest
from unittest.mock import patch, Mock
import requests
from morning.content import ContentExtractor
from morning.config_models import AppConfig

class TestContentExtractor(unittest.TestCase):
    def setUp(self):
        # Create a minimal config
        self.config = AppConfig(
            rss_feeds=[],
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
            timeout={"request": 5, "extraction": 10},
            max_content_length=5000,
            site_specific_selectors={"example.com": "article.main"},
            fallback_selectors=["article", "main", "div.content"],
            elements_to_remove=["script", "style"],
            class_selectors_to_remove=[".ad", ".comments"]
        )
        self.extractor = ContentExtractor(self.config)

    def test_is_valid_url(self):
        self.assertTrue(self.extractor._is_valid_url("https://example.com/article"))
        self.assertTrue(self.extractor._is_valid_url("http://news.com/story/123"))
        self.assertFalse(self.extractor._is_valid_url("not-a-url"))
        self.assertFalse(self.extractor._is_valid_url("file:///home/user/doc.txt"))

    def test_is_web_page_url(self):
        self.assertTrue(self.extractor._is_web_page_url("https://example.com/article"))
        self.assertTrue(self.extractor._is_web_page_url("https://example.com/article?id=123"))
        self.assertFalse(self.extractor._is_web_page_url("https://example.com/document.pdf"))
        self.assertFalse(self.extractor._is_web_page_url("https://example.com/download.zip"))

    @patch('requests.get')
    def test_extract_article_content_file_link(self, mock_get):
        url = "https://example.com/document.pdf"
        content = self.extractor.extract_article_content(url)

        # Should return a message about file links
        self.assertIn("This article links to a file", content)
        # Should not make a request
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_extract_article_content_with_readability(self, mock_get):
        # Mock the response
        mock_response = Mock()
        mock_response.content = b"<html><body><article><p>Test content</p></article></body></html>"
        mock_get.return_value = mock_response

        # Mock readability.Document
        with patch('readability.Document') as mock_document:
            mock_doc = Mock()
            mock_doc.summary.return_value = "<p>Extracted content</p>"
            mock_document.return_value = mock_doc

            content = self.extractor.extract_article_content("https://example.com/article")

            # Verify request was made
            mock_get.assert_called_once()
            # Verify readability was used
            mock_document.assert_called_once()
            # Check content
            self.assertEqual(content, "<p>Extracted content</p>")
