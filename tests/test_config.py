import os
import json
import tempfile
import unittest
from morning.config import ConfigManager
from morning.config_models import AppConfig

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.test_dir.name, "config.json")

    def tearDown(self):
        # Clean up the temporary directory
        self.test_dir.cleanup()

    def test_load_valid_config(self):
        # Create a valid config file
        test_config = {
            "rss_feeds": [
                {"name": "Test Feed", "url": "https://example.com/feed.xml", "max_articles": 5}
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
            "output_directory": "./test_output"
        }

        with open(self.config_path, 'w') as f:
            json.dump(test_config, f)

        # Load the config
        cm = ConfigManager(self.config_path)

        # Verify the config was loaded correctly
        self.assertEqual(cm.config.rss_feeds[0].name, "Test Feed")
        self.assertEqual(cm.config.output_directory, "./test_output")

    def test_default_config_creation(self):
        # Test with a non-existent config file
        non_existent_path = os.path.join(self.test_dir.name, "nonexistent.json")
        cm = ConfigManager(non_existent_path)

        # Verify a default config was created
        self.assertTrue(os.path.exists(non_existent_path))
        self.assertIsInstance(cm.config, AppConfig)

    def test_invalid_config_fallback(self):
        # Create an invalid config file
        with open(self.config_path, 'w') as f:
            f.write("This is not valid JSON")

        # Load the config
        cm = ConfigManager(self.config_path)

        # Verify it fell back to default config
        self.assertIsInstance(cm.config, AppConfig)

    def test_save_config(self):
        # Initialize with default config
        cm = ConfigManager(self.config_path)

        # Modify the config
        cm.config.newspaper_title = "Test Newspaper"

        # Save the config
        cm.save_config()

        # Load the config again
        cm2 = ConfigManager(self.config_path)

        # Verify the change was saved
        self.assertEqual(cm2.config.newspaper_title, "Test Newspaper")
