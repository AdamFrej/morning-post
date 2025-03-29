import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, Mock
import jinja2

from morning.templates import TemplateManager
from morning.config_models import AppConfig, TemplatesConfig

class TestTemplateManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary directories."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.templates_dir = os.path.join(self.test_dir.name, "templates")
        os.makedirs(self.templates_dir, exist_ok=True)

        # Create a minimal config for testing
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
            templates=TemplatesConfig(
                directory=self.templates_dir,
                main_template="paper_template.html",
                article_template="article_template.html"
            )
        )

    def tearDown(self):
        """Clean up the temporary directory."""
        self.test_dir.cleanup()

    def test_setup_templates_creates_directory(self):
        """Test that template directory is created if it doesn't exist."""
        # Remove the templates directory
        shutil.rmtree(self.templates_dir)

        # Initialize template manager, which should create the directory
        template_manager = TemplateManager(self.config)

        # Check that the directory was created
        self.assertTrue(os.path.exists(self.templates_dir))

    def test_default_templates_creation(self):
        """Test that default templates are created when missing."""
        # Initialize template manager with empty templates directory
        template_manager = TemplateManager(self.config)

        # Check that default templates were created
        main_template_path = os.path.join(self.templates_dir, "paper_template.html")
        article_template_path = os.path.join(self.templates_dir, "article_template.html")

        self.assertTrue(os.path.exists(main_template_path))
        self.assertTrue(os.path.exists(article_template_path))

    def test_get_template(self):
        """Test getting a template by name."""
        # Create a test template file
        test_template_content = "<html><body>{{ test_var }}</body></html>"
        test_template_path = os.path.join(self.templates_dir, "test_template.html")

        with open(test_template_path, "w") as f:
            f.write(test_template_content)

        # Initialize template manager
        template_manager = TemplateManager(self.config)

        # Get the template
        template = template_manager.get_template("test_template.html")

        # Verify it's a Jinja2 template
        self.assertIsInstance(template, jinja2.Template)

        # Render the template and verify content
        rendered = template.render(test_var="Test Value")
        self.assertEqual(rendered, "<html><body>Test Value</body></html>")

    @patch('os.path.exists')
    @patch('morning.templates.shutil.copy2')
    @patch('os.makedirs')
    def test_default_templates_from_package(self, mock_makedirs, mock_copy, mock_exists):
        """Test copying default templates from package."""
        # Mock paths to exist
        mock_exists.return_value = True

        # Mock the copy operation to actually create a file
        def side_effect_copy(src, dst):
            # Create the destination file
            with open(dst, 'w') as f:
                f.write("Mock template content")
            return True

        mock_copy.side_effect = side_effect_copy

        # Create config with a different templates directory (but use a real path)
        test_templates_dir = os.path.join(self.test_dir.name, "custom_templates")
        os.makedirs(test_templates_dir, exist_ok=True)

        config = AppConfig(
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
            templates=TemplatesConfig(
                directory=test_templates_dir,
                main_template="custom_main.html",
                article_template="custom_article.html"
            )
        )

        # Initialize template manager, which should try to copy default templates
        template_manager = TemplateManager(config)

        # Verify templates were created
        self.assertTrue(os.path.exists(os.path.join(test_templates_dir, "custom_main.html")))
        self.assertTrue(os.path.exists(os.path.join(test_templates_dir, "custom_article.html")))

    def test_template_error_handling(self):
        """Test error handling when template has syntax errors."""
        # Create a template with Jinja2 syntax error
        bad_template_content = "<html><body>{{ unclosed }</body></html>"
        bad_template_path = os.path.join(self.templates_dir, "bad_template.html")

        with open(bad_template_path, "w") as f:
            f.write(bad_template_content)

        # Initialize template manager
        template_manager = TemplateManager(self.config)

        # Verify that getting the template raises an error
        with self.assertRaises(Exception):
            template = template_manager.get_template("bad_template.html")
