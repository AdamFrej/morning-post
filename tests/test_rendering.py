import unittest
from unittest.mock import patch, Mock, MagicMock
import os
import tempfile
from morning.rendering import DocumentRenderer
from morning.config_models import AppConfig, TemplatesConfig

class TestDocumentRenderer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for output
        self.test_dir = tempfile.TemporaryDirectory()

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
            output_directory=self.test_dir.name,
            templates=TemplatesConfig(
                directory="./templates",
                main_template="paper_template.html"
            )
        )

        # Mock template manager
        self.mock_template_manager = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html><body><h1>Test Paper</h1></body></html>"
        self.mock_template_manager.get_template.return_value = mock_template

        self.renderer = DocumentRenderer(self.config, self.mock_template_manager)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_generate_html(self):
        # Test articles with enough content to pass filtering
        articles = [
            {
                "title": "Test Article 1",
                "source": "Test Source",
                "link": "https://example.com/article1",
                "published": "2023-01-01 12:00:00",
                "content": "<p>Test content 1 with sufficient length to pass filtering</p>" * 10
            }
        ]

        # Generate HTML
        html = self.renderer.generate_html(articles)

        # Verify template was used
        self.mock_template_manager.get_template.assert_called_once_with("paper_template.html")
        # Verify HTML was generated
        self.assertIsNotNone(html)

    @patch('weasyprint.HTML')
    def test_generate_pdf(self, mock_html):
        # Mock WeasyPrint
        mock_weasy = Mock()
        mock_html.return_value = mock_weasy

        # Test articles with enough content to pass filtering
        articles = [
            {
                "title": "Test Article",
                "source": "Test Source",
                "link": "https://example.com/article",
                "published": "2023-01-01 12:00:00",
                "content": "<p>Test content with sufficient length to pass filtering</p>" * 10
            }
        ]

        # Generate PDF
        pdf_path = self.renderer.generate_pdf(articles)

        # Verify PDF path is correct
        self.assertIsNotNone(pdf_path)
        self.assertTrue(pdf_path.startswith(self.test_dir.name))
        self.assertTrue("morning_paper_" in pdf_path)
        self.assertTrue(pdf_path.endswith(".pdf"))

        # Verify WeasyPrint was called
        mock_html.assert_called_once()
        mock_weasy.write_pdf.assert_called_once()

    def test_filter_articles(self):
        # Articles with various issues
        articles = [
            {
                "title": "Good Article",
                "source": "Test Source",
                "link": "https://example.com/good",
                "published": "2023-01-01",
                "content": "<p>This is good content with sufficient length to be included</p>" * 10
            },
            {
                "title": "PDF Article",
                "source": "Test Source",
                "link": "https://example.com/file.pdf",
                "published": "2023-01-01",
                "content": "<p>This article links to a file that cannot be displayed</p>"
            },
            {
                "title": "Short Article",
                "source": "Test Source",
                "link": "https://example.com/short",
                "published": "2023-01-01",
                "content": "<p>Too short</p>"
            },
            {
                "title": "Failed Article",
                "source": "Test Source",
                "link": "https://example.com/failed",
                "published": "2023-01-01",
                "content": "<p>Content extraction failed</p>"
            }
        ]

        # Generate HTML (which filters articles)
        html = self.renderer.generate_html(articles)

        # Verify template was called with filtered articles
        template_args = self.mock_template_manager.get_template().render.call_args[1]

        # Only the good article should remain
        self.assertEqual(len(template_args["articles"]), 1)
        self.assertEqual(template_args["articles"][0]["title"], "Good Article")
