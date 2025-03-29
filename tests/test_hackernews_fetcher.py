import unittest
from unittest.mock import patch, Mock
import json
from morning.fetchers.hackernews import HackerNewsFetcher
from morning.config_models import AppConfig, HackerNewsConfig, HackerNewsAPIEndpoints

class TestHackerNewsFetcher(unittest.TestCase):
    def setUp(self):
        # Create a minimal config
        hn_api_endpoints = HackerNewsAPIEndpoints(
            top_stories="https://hacker-news.firebaseio.com/v0/topstories.json",
            item="https://hacker-news.firebaseio.com/v0/item/{}.json",
            discussion_url="https://news.ycombinator.com/item?id={}"
        )

        hn_config = HackerNewsConfig(
            include=True,
            max_articles=2,
            only_self_posts=True,
            api_endpoints=hn_api_endpoints
        )

        self.config = AppConfig(
            rss_feeds=[],
            hacker_news=hn_config,
            timeout={"request": 5, "extraction": 10}
        )

        # Create a mock content extractor
        self.mock_extractor = Mock()
        self.mock_extractor.extract_article_content.return_value = "<p>Extracted content</p>"

        self.fetcher = HackerNewsFetcher(self.config, self.mock_extractor)

    @patch('requests.get')
    def test_fetch_articles(self, mock_get):
        # Mock top stories response
        top_stories_resp = Mock()
        top_stories_resp.status_code = 200
        top_stories_resp.json.return_value = [123, 456, 789]

        # Mock story responses
        story1_resp = Mock()
        story1_resp.status_code = 200
        story1_resp.json.return_value = {
            "id": 123,
            "title": "Ask HN: What are you working on?",
            "time": 1609459200,  # 2021-01-01
            "score": 100,
            "descendants": 50,
            "text": "<p>Share your projects!</p>"
        }

        story2_resp = Mock()
        story2_resp.status_code = 200
        story2_resp.json.return_value = {
            "id": 456,
            "title": "Regular article",
            "time": 1609545600,  # 2021-01-02
            "score": 200,
            "descendants": 100,
            "url": "https://example.com/article"
        }

        # Configure mock to return different responses
        def get_side_effect(url, timeout=None):
            if "topstories" in url:
                return top_stories_resp
            elif "item/123" in url:
                return story1_resp
            elif "item/456" in url:
                return story2_resp
            return Mock(status_code=404)

        mock_get.side_effect = get_side_effect

        # Fetch articles
        with patch('time.sleep'):  # Skip sleep delays
            articles = self.fetcher.fetch_articles()

        # Verify API calls
        self.assertEqual(mock_get.call_count, 3)  # top stories + 2 story details

        # Verify self-post filtering
        self.assertEqual(len(articles), 1)  # Only the Ask HN post
        self.assertEqual(articles[0]["title"], "Ask HN: What are you working on?")
        self.assertIn("Share your projects", articles[0]["content"])

    @patch('requests.get')
    def test_fetch_articles_include_all(self, mock_get):
        # Configure to include all posts, not just self posts
        self.config.hacker_news.only_self_posts = False

        # Mock responses
        top_stories_resp = Mock()
        top_stories_resp.status_code = 200
        top_stories_resp.json.return_value = [123, 456]

        story1_resp = Mock()
        story1_resp.status_code = 200
        story1_resp.json.return_value = {
            "id": 123,
            "title": "Ask HN: Question?",
            "time": 1609459200,
            "score": 100,
            "descendants": 50,
            "text": "<p>Self post text</p>"
        }

        story2_resp = Mock()
        story2_resp.status_code = 200
        story2_resp.json.return_value = {
            "id": 456,
            "title": "External article",
            "time": 1609545600,
            "score": 200,
            "descendants": 100,
            "url": "https://example.com/article"
        }

        def get_side_effect(url, timeout=None):
            if "topstories" in url:
                return top_stories_resp
            elif "item/123" in url:
                return story1_resp
            elif "item/456" in url:
                return story2_resp
            return Mock(status_code=404)

        mock_get.side_effect = get_side_effect

        # Fetch articles
        with patch('time.sleep'):  # Skip sleep delays
            articles = self.fetcher.fetch_articles()

        # Verify both types of posts were included
        self.assertEqual(len(articles), 2)
        titles = [a["title"] for a in articles]
        self.assertIn("Ask HN: Question?", titles)
        self.assertIn("External article", titles)

    @patch('requests.get')
    def test_fetch_articles(self, mock_get):
        # Mock top stories response
        top_stories_resp = Mock()
        top_stories_resp.status_code = 200
        top_stories_resp.json.return_value = [123, 456, 789]

        # Mock story responses
        story1_resp = Mock()
        story1_resp.status_code = 200
        story1_resp.json.return_value = {
            "id": 123,
            "title": "Ask HN: What are you working on?",
            "time": 1609459200,  # 2021-01-01
            "score": 100,
            "descendants": 50,
            "text": "<p>Share your projects!</p>"
        }

        story2_resp = Mock()
        story2_resp.status_code = 200
        story2_resp.json.return_value = {
            "id": 456,
            "title": "Regular article",
            "time": 1609545600,  # 2021-01-02
            "score": 200,
            "descendants": 100,
            "url": "https://example.com/article"
        }

        # Configure mock to return different responses
        def get_side_effect(url, timeout=None):
            if "topstories" in url:
                return top_stories_resp
            elif "item/123" in url:
                return story1_resp
            elif "item/456" in url:
                return story2_resp
            else:
                # Create a 404 response for story 789
                resp = Mock()
                resp.status_code = 404
                return resp

        mock_get.side_effect = get_side_effect

        # Fetch articles
        with patch('time.sleep'):  # Skip sleep delays
            articles = self.fetcher.fetch_articles()

        # Verify self-post filtering
        self.assertEqual(len(articles), 1)  # Only the Ask HN post
        self.assertEqual(articles[0]["title"], "Ask HN: What are you working on?")
        self.assertIn("Share your projects", articles[0]["content"])

        # Update expectation to include call for story 789 that returns 404
        self.assertEqual(mock_get.call_count, 4)  # top stories + 3 story details (including 404)
