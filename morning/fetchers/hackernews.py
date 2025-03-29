"""Hacker News article fetcher."""
import logging
import requests
import datetime
import time
import gc
from typing import List, Dict, Any
from urllib.parse import urlparse
from markdownify import markdownify as md

from ..utils import TimeoutException
from ..config_models import AppConfig

logger = logging.getLogger(__name__)

class HackerNewsFetcher:
    def __init__(self, config: AppConfig, content_extractor):
        """Initialize Hacker News fetcher.

        Args:
            config: Validated application configuration
            content_extractor: Content extraction service
        """
        self.config = config
        self.content_extractor = content_extractor

    def fetch_articles(self) -> List[Dict[str, Any]]:
        """Fetch self posts from Hacker News (Show HN, Ask HN, etc.).

        Returns:
            List of article dictionaries with extracted content
        """
        articles = []

        if not self.config.hacker_news.include:
            logger.info("Skipping Hacker News articles (disabled in config)")
            return articles

        try:
            # Get API endpoints from config
            hn_config = self.config.hacker_news
            api_endpoints = hn_config.api_endpoints

            # Fetch top stories IDs
            timeout = self.config.timeout.request

            # Convert Pydantic HttpUrl to string
            top_stories_url = str(api_endpoints.top_stories)
            response = requests.get(top_stories_url, timeout=timeout)

            if response.status_code != 200:
                logger.error(f"Failed to fetch Hacker News top stories: Status code {response.status_code}")
                return articles

            top_stories = response.json()
            if not top_stories or not isinstance(top_stories, list):
                logger.error("Invalid response from Hacker News API")
                return articles

            logger.info(f"Retrieved {len(top_stories)} top stories from Hacker News")

            count = 0
            max_articles = min(hn_config.max_articles, 10)  # Cap at 10 to avoid memory issues
            only_self_posts = hn_config.only_self_posts

            for i, story_id in enumerate(top_stories):
                if count >= max_articles:
                    break

                # Force garbage collection periodically
                if i % 5 == 0:
                    gc.collect()

                try:
                    # Fetch story details
                    story_url = api_endpoints.item.format(story_id)
                    story_response = requests.get(story_url, timeout=timeout)
                    if story_response.status_code != 200:
                        logger.warning(f"Failed to fetch story {story_id}: Status code {story_response.status_code}")
                        continue

                    story = story_response.json()

                    if not story or not isinstance(story, dict):
                        logger.warning(f"Invalid story data for ID {story_id}")
                        continue

                    # Check if this is a self post (Show HN, Ask HN, etc.)
                    title = story.get("title", "").strip()
                    is_self_post = (
                        title.startswith("Show HN:") or
                        title.startswith("Ask HN:") or
                        title.startswith("Tell HN:") or
                        "url" not in story or
                        story.get("url", "").startswith("item?id=")
                    )

                    # Skip if we only want self posts and this isn't one
                    if only_self_posts and not is_self_post:
                        logger.info(f"Skipping story {story_id} (not a self post)")
                        continue

                    # For self posts without URLs, use the HN discussion URL
                    hn_url = api_endpoints.discussion_url.format(story_id)
                    article_url = story.get("url", hn_url)

                    # For true self-posts, we want to get the text from the story itself
                    text = story.get("text", "")
                    if text:
                        # Convert HTML to more readable format
                        text_content = md(text)
                        content = f"<div class='hn-text'>{text}</div>"
                    else:
                        content = "<p><em>No text content available</em></p>"

                    article = {
                        "title": title,
                        "source": "Hacker News",
                        "link": article_url,
                        "published": datetime.datetime.fromtimestamp(story.get("time", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                        "summary": f"Points: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}",
                        "content": content
                    }

                    # Extract full content only if it's not a true self-post (has URL to external site)
                    if self.config.extract_full_content and not text:
                        try:
                            article["content"] = self.content_extractor.extract_article_content(article_url)
                        except TimeoutException:
                            logger.warning(f"Content extraction timed out for {article['title']}")
                            article["content"] = f"<p>{article['summary']}</p><p><em>Content extraction timed out</em></p>"
                        except Exception as e:
                            logger.warning(f"Failed to extract content for {article['title']}: {str(e)[:100]}")
                            article["content"] = f"<p>{article['summary']}</p><p><em>Content extraction failed</em></p>"

                    articles.append(article)
                    count += 1

                    # Add a delay to avoid hammering servers
                    time.sleep(2)

                except Exception as e:
                    logger.warning(f"Error processing story {story_id}: {str(e)[:100]}")
                    continue

            logger.info(f"Successfully fetched {count} articles from Hacker News")
        except Exception as e:
            logger.error(f"Error fetching Hacker News articles: {str(e)[:100]}")

        return articles
