import unittest
from unittest.mock import patch, Mock, MagicMock
import os
import tempfile
import datetime
from bs4 import BeautifulSoup

from morning.rendering import DocumentRenderer
from morning.config_models import AppConfig, TemplatesConfig

class TestDocumentRendererAdvanced(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
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
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_date_sorting(self):
        """Test sorting articles by date."""
        # Create a mock template that preserves the kwargs for inspection
        mock_template = MagicMock()

        # Setup the render method to store the kwargs but still return a value
        captured_kwargs = {}

        def side_effect(**kwargs):
            nonlocal captured_kwargs
            captured_kwargs.update(kwargs)
            return "<html>Rendered template</html>"

        # Use side_effect instead of just assigning the function
        mock_template.render.side_effect = side_effect
        self.mock_template_manager.get_template.return_value = mock_template

        # Create articles with different date formats
        # Make sure they all have sufficient content that passes filtering
        articles = [
            {
                "title": "Article 1",
                "source": "Test Source",
                "link": "https://example.com/article1",
                "published": "2023-01-03 12:00:00",  # ISO format
                "content": "<p>This is good content with sufficient length to be included</p>" * 10
            },
            {
                "title": "Article 2",
                "source": "Test Source",
                "link": "https://example.com/article2",
                "published": "Tue, 02 Jan 2023 12:00:00 +0000",  # RFC format
                "content": "<p>This is good content with sufficient length to be included</p>" * 10
            },
            {
                "title": "Article 3",
                "source": "Test Source",
                "link": "https://example.com/article3",
                "published": "2023-01-01T12:00:00+00:00",  # ISO with timezone
                "content": "<p>This is good content with sufficient length to be included</p>" * 10
            },
            {
                "title": "Article 4",
                "source": "Test Source",
                "link": "https://example.com/article4",
                "published": "Invalid date format",  # Should be handled gracefully
                "content": "<p>This is good content with sufficient length to be included</p>" * 10
            }
        ]

        # Generate HTML to trigger sorting
        self.renderer.generate_html(articles)

        # Verify we have the articles in captured_kwargs
        self.assertIn("articles", captured_kwargs)
        sorted_articles = captured_kwargs["articles"]

        # Since Article 4 has an invalid date, it uses current time - hash, which can place it anywhere
        # So we just check the relative positions of Articles 1, 2, and 3

        # Find the indices of our first three articles
        idx1 = next(i for i, a in enumerate(sorted_articles) if a["title"] == "Article 1")
        idx2 = next(i for i, a in enumerate(sorted_articles) if a["title"] == "Article 2")
        idx3 = next(i for i, a in enumerate(sorted_articles) if a["title"] == "Article 3")

        # Verify relative positions - Article 1 should be before Article 2, and Article 2 before Article 3
        self.assertLess(idx1, idx2, "Article 1 (Jan 3) should be before Article 2 (Jan 2)")
        self.assertLess(idx2, idx3, "Article 2 (Jan 2) should be before Article 3 (Jan 1)")

        # Ensure Article 4 is included
        self.assertTrue(any(a["title"] == "Article 4" for a in sorted_articles))

    def test_comprehensive_article_filtering(self):
        """Test comprehensive article filtering with various edge cases."""
        # Create a diverse set of articles to test filtering logic
        articles = [
            # Good article with sufficient content
            {
                "title": "Good Article",
                "source": "Test Source",
                "link": "https://example.com/good",
                "published": "2023-01-01",
                "content": "<p>This is good content with sufficient length to be included</p>" * 10
            },
            # PDF file link in title
            {
                "title": "Download my PDF file",
                "source": "Test Source",
                "link": "https://example.com/download",
                "published": "2023-01-01",
                "content": "<p>This has a PDF mentioned in the title</p>" * 10
            },
            # PDF file link in URL
            {
                "title": "Research Paper",
                "source": "Test Source",
                "link": "https://example.com/paper.pdf",
                "published": "2023-01-01",
                "content": "<p>This links to a PDF file</p>" * 10
            },
            # Very short content
            {
                "title": "Short Article",
                "source": "Test Source",
                "link": "https://example.com/short",
                "published": "2023-01-01",
                "content": "<p>Too short</p>"
            },
            # Article mentioning downloading files
            {
                "title": "Download Article",
                "source": "Test Source",
                "link": "https://example.com/download-article",
                "published": "2023-01-01",
                "content": "<p>This article links to a file that cannot be displayed in the paper.</p>" * 10
            },
            # Article with extraction failure message
            {
                "title": "Failed Article",
                "source": "Test Source",
                "link": "https://example.com/failed",
                "published": "2023-01-01",
                "content": "<p>Content extraction failed. Please view the original article.</p>"
            }
        ]

        # Generate HTML (which filters articles)
        html = self.renderer.generate_html(articles)

        # Verify template was called with filtered articles
        template_args = self.mock_template_manager.get_template().render.call_args[1]
        filtered_articles = template_args["articles"]

        # Only the good article should remain
        self.assertEqual(len(filtered_articles), 1)
        self.assertEqual(filtered_articles[0]["title"], "Good Article")

    def test_html_format(self):
        """Test HTML content formatting."""
        # Create a mock template that returns the articles as JSON
        mock_template = Mock()
        mock_template.render.return_value = """
        <html>
        <head><title>Test Paper</title></head>
        <body>
            <h1>Morning Paper</h1>
            <div class="articles">
                {% for article in articles %}
                <article>
                    <h2>{{ article.title }}</h2>
                    <p class="source">{{ article.source }}</p>
                    <div class="content">{{ article.content }}</div>
                </article>
                {% endfor %}
            </div>
        </body>
        </html>
        """
        self.mock_template_manager.get_template.return_value = mock_template

        # Test articles
        articles = [
            {
                "title": "Test Article",
                "source": "Test Source",
                "link": "https://example.com/article",
                "published": "2023-01-01",
                "content": "<p>Test content with sufficient length</p>" * 10
            }
        ]

        # Generate HTML
        html = self.renderer.generate_html(articles)

        # Verify HTML structure
        self.assertIn("<html>", html)
        self.assertIn("<head>", html)
        self.assertIn("<body>", html)
        self.assertIn("<title>Test Paper</title>", html)

    @patch('weasyprint.HTML')
    def test_pdf_generation_error_handling(self, mock_html):
        """Test error handling during PDF generation."""
        # Mock WeasyPrint to raise an exception
        mock_weasy = Mock()
        mock_weasy.write_pdf.side_effect = Exception("PDF generation failed")
        mock_html.return_value = mock_weasy

        # Create test articles
        articles = [
            {
                "title": "Test Article",
                "source": "Test Source",
                "link": "https://example.com/article",
                "published": "2023-01-01",
                "content": "<p>Test content with sufficient length</p>" * 10
            }
        ]

        # Generate PDF, which should handle the exception
        with patch('tempfile.NamedTemporaryFile') as mock_temp:
            # Mock the temporary file
            mock_file = Mock()
            mock_file.name = "/tmp/test.html"
            mock_temp.return_value.__enter__.return_value = mock_file

            # Try to generate PDF
            pdf_path = self.renderer.generate_pdf(articles)

            # Verify PDF generation failed
            self.assertIsNone(pdf_path)

    def test_garbage_collection_during_pdf_generation(self):
        """Test garbage collection is called during PDF generation."""
        # Create test articles
        articles = [
            {
                "title": "Test Article",
                "source": "Test Source",
                "link": "https://example.com/article",
                "published": "2023-01-01",
                "content": "<p>Test content with sufficient length</p>" * 10
            }
        ]

        # Mock HTML generation
        with patch.object(self.renderer, 'generate_html', return_value="<html><body>Test</body></html>"):
            # Mock WeasyPrint
            with patch('weasyprint.HTML'):
                # Mock garbage collection
                with patch('gc.collect') as mock_gc:
                    # Generate PDF
                    self.renderer.generate_pdf(articles)

                    # Verify garbage collection was called
                    mock_gc.assert_called()
                    mock_gc.assert_called()
