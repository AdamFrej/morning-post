import feedparser
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import shutil
try:
    from importlib.resources import files
except ImportError:
    # Fallback for older Python versions
    import pkg_resources
from markdownify import markdownify as md
import tempfile
import time
import logging
import gc
import signal
from urllib.parse import urlparse
from contextlib import contextmanager
import jinja2

# Set up main logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

fonttools_logger = logging.getLogger('fontTools')
fonttools_logger.setLevel(logging.ERROR)  # Only show errors, not warnings

# Set the specific font subsetting module to ERROR level
logging.getLogger('fontTools.subset').setLevel(logging.ERROR)
logging.getLogger('fontTools.ttLib').setLevel(logging.ERROR)

# Add this to silence the root logger for specific packages
for logger_name in ['fontTools', 'PIL', 'weasyprint', 'cssselect', 'cffi', 'html5lib']:
    package_logger = logging.getLogger(logger_name)
    package_logger.propagate = False  # Stop propagating to parent loggers
    package_logger.setLevel(logging.ERROR)

    # Add a null handler to prevent warnings about no handlers
    if not package_logger.handlers:
        package_logger.addHandler(logging.NullHandler())

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """Context manager for timeout"""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class MorningPaperGenerator:
    def __init__(self, config_path="config.json"):
        """Initialize the paper generator with configuration."""
        self.config = self._load_config(config_path)
        self.articles = []
        self.template_env = self._setup_templates()

    def _setup_templates(self):
        """Set up Jinja2 template environment."""
        template_dir = self.config.get("templates", {}).get("directory", "./templates")

        # Create template directory if it doesn't exist
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)

            # Create default templates if they don't exist
            self._create_default_templates(template_dir)

        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir)
        )

    def _create_default_templates(self, template_dir):
        """Create default template files if they don't exist."""
        # Get default templates from package
        default_templates_dir = os.path.join(os.path.dirname(__file__), 'default_templates')

        # If running from a different location, try to find the default templates
        if not os.path.exists(default_templates_dir):
            try:
                # Try to find templates relative to script location
                script_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(script_dir)
                default_templates_dir = os.path.join(parent_dir, 'default_templates')

                # If still not found, try with gazeta folder
                if not os.path.exists(default_templates_dir):
                    default_templates_dir = os.path.join(parent_dir, 'gazeta', 'default_templates')
            except:
                logger.warning("Could not locate default templates directory")

        # Copy main template
        main_template_name = self.config.get("templates", {}).get("main_template", "paper_template.html")
        main_template_path = os.path.join(template_dir, main_template_name)

        if not os.path.exists(main_template_path):
            try:
                # Try to copy from default templates
                if os.path.exists(default_templates_dir):
                    src_path = os.path.join(default_templates_dir, "paper_template.html")
                    if os.path.exists(src_path):
                        shutil.copy2(src_path, main_template_path)
                        logger.info(f"Copied default main template to {main_template_path}")
                    else:
                        self._create_empty_template(main_template_path, "Main template")
                else:
                    self._create_empty_template(main_template_path, "Main template")
            except Exception as e:
                logger.warning(f"Error creating main template: {e}")
                self._create_empty_template(main_template_path, "Main template")

        # Copy article template
        article_template_name = self.config.get("templates", {}).get("article_template", "article_template.html")
        article_template_path = os.path.join(template_dir, article_template_name)

        if not os.path.exists(article_template_path):
            try:
                # Try to copy from default templates
                if os.path.exists(default_templates_dir):
                    src_path = os.path.join(default_templates_dir, "article_template.html")
                    if os.path.exists(src_path):
                        shutil.copy2(src_path, article_template_path)
                        logger.info(f"Copied default article template to {article_template_path}")
                    else:
                        self._create_empty_template(article_template_path, "Article template")
                else:
                    self._create_empty_template(article_template_path, "Article template")
            except Exception as e:
                logger.warning(f"Error creating article template: {e}")
                self._create_empty_template(article_template_path, "Article template")

    def _create_empty_template(self, path, template_type):
        """Create an empty template with a note about missing the default template."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'''<!--
{template_type} file not found.
Please create your own template or check the documentation for example templates.
-->

<html>
<head><title>Template Missing</title></head>
<body>
    <h1>Template Missing</h1>
    <p>The default template could not be found. Please create your own template or check the documentation.</p>
</body>
</html>''')
        logger.warning(f"Created empty placeholder for {template_type} at {path}")

    def _load_config(self, config_path):
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info(f"Config file not found at {config_path}, creating default config")
            default_config = {
                "rss_feeds": [
                    {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "max_articles": 5},
                    {"name": "New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "max_articles": 5}
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
                "output_directory": "./papers",
                "templates": {
                    "directory": "./templates",
                    "main_template": "paper_template.html",
                    "article_template": "article_template.html"
                },
                "extract_full_content": True,
                "include_images": False,
                "timeout": {
                    "request": 10,
                    "extraction": 15
                },
                "max_content_length": 50000,
                "site_specific_selectors": {
                    "nytimes.com": "article[data-testid='article-container']",
                    "bbc.com": "article[data-component='text-block']",
                    "bbc.co.uk": "article[data-component='text-block']",
                    "theverge.com": "div.duet--article--article-body-component",
                    "washingtonpost.com": "div.article-body",
                    "medium.com": "article",
                    "towardsdatascience.com": "article",
                    "techcrunch.com": "div.article-content"
                },
                "fallback_selectors": [
                    "article", "main", "div.content", "div.article", "div.post",
                    ".entry-content", "#content", ".article__body", ".post-content",
                    ".story", ".story-body", "[itemprop='articleBody']"
                ],
                "elements_to_remove": [
                    "script", "style", "iframe", "noscript", "video", "audio",
                    "embed", "object", "canvas", "form", "button", "aside",
                    "header", "footer", "nav"
                ],
                "class_selectors_to_remove": [
                    ".comments", ".social-share", ".related-articles", ".recommendations",
                    ".newsletter-signup", ".advertisement", ".ad", ".popup", ".modal",
                    ".share", ".social", ".related", ".popular", ".trending",
                    ".recommended", "#comments", ".comments", ".comment-section",
                    ".advertisement", ".ad-container", ".sponsored", ".subscribe",
                    ".newsletter", ".signup", ".sidebar", ".footer", ".header"
                ]
            }
            os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def _is_valid_url(self, url):
        """Check if URL is valid and has an acceptable domain."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def fetch_rss_articles(self):
        """Fetch articles from configured RSS feeds."""
        for feed_config in self.config["rss_feeds"]:
            try:
                feed = feedparser.parse(feed_config["url"])
                logger.info(f"Fetched {len(feed.entries)} articles from {feed_config['name']}")

                for i, entry in enumerate(feed.entries):
                    if i >= feed_config["max_articles"]:
                        break

                    if not hasattr(entry, 'link') or not self._is_valid_url(entry.link):
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
                            article["content"] = self._extract_article_content(entry.link)
                            # Add a short delay to avoid hammering servers
                            time.sleep(1)
                        except Exception as e:
                            logger.warning(f"Failed to extract full content for {article['title']}: {e}")
                            article["content"] = f"<p>{article['summary']}</p>"
                    else:
                        article["content"] = f"<p>{article['summary']}</p>"

                    self.articles.append(article)

                    # Force garbage collection to free memory
                    gc.collect()
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_config['name']}: {e}")

    def fetch_hacker_news_articles(self):
        """Fetch self posts from Hacker News (Show HN, Ask HN, etc.)."""
        if not self.config["hacker_news"]["include"]:
            return

        try:
            # Get API endpoints from config or use defaults
            hn_config = self.config.get("hacker_news", {})
            api_endpoints = hn_config.get("api_endpoints", {
                "top_stories": "https://hacker-news.firebaseio.com/v0/topstories.json",
                "item": "https://hacker-news.firebaseio.com/v0/item/{}.json",
                "discussion_url": "https://news.ycombinator.com/item?id={}"
            })

            # Fetch top stories IDs
            timeout = self.config.get("timeout", {}).get("request", 10)
            response = requests.get(api_endpoints["top_stories"], timeout=timeout)
            if response.status_code != 200:
                logger.error(f"Failed to fetch Hacker News top stories: Status code {response.status_code}")
                return

            top_stories = response.json()
            if not top_stories or not isinstance(top_stories, list):
                logger.error("Invalid response from Hacker News API")
                return

            logger.info(f"Retrieved {len(top_stories)} top stories from Hacker News")

            count = 0
            max_articles = min(hn_config["max_articles"], 10)  # Cap at 10 to avoid memory issues
            only_self_posts = hn_config.get("only_self_posts", True)

            for i, story_id in enumerate(top_stories):
                if count >= max_articles:
                    break

                # Force garbage collection periodically
                if i % 5 == 0:
                    gc.collect()

                try:
                    # Fetch story details
                    story_url = api_endpoints["item"].format(story_id)
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
                    hn_url = api_endpoints["discussion_url"].format(story_id)
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
                    if self.config["extract_full_content"] and not text:
                        try:
                            article["content"] = self._extract_article_content(article_url)
                        except TimeoutException:
                            logger.warning(f"Content extraction timed out for {article['title']}")
                            article["content"] = f"<p>{article['summary']}</p><p><em>Content extraction timed out</em></p>"
                        except Exception as e:
                            logger.warning(f"Failed to extract content for {article['title']}: {str(e)[:100]}")
                            article["content"] = f"<p>{article['summary']}</p><p><em>Content extraction failed</em></p>"

                    self.articles.append(article)
                    count += 1

                    # Add a delay to avoid hammering servers
                    time.sleep(2)

                except Exception as e:
                    logger.warning(f"Error processing story {story_id}: {str(e)[:100]}")
                    continue

            logger.info(f"Successfully fetched {count} articles from Hacker News")
        except Exception as e:
            logger.error(f"Error fetching Hacker News articles: {str(e)[:100]}")

    def _extract_article_content(self, url):
        """Extract the main content from an article URL with improved quality."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        timeout = self.config.get("timeout", {}).get("request", 10)
        extraction_timeout = self.config.get("timeout", {}).get("extraction", 15)
        max_length = self.config.get("max_content_length", 50000)
        site_specific_selectors = self.config.get("site_specific_selectors", {})

        try:
            # Get the page with timeout
            response = requests.get(url, headers=headers, timeout=timeout)

            # Limit content size for memory management
            content = response.content[:500000]  # Limit to 500KB to avoid memory issues
            include_images = self.config.get("include_images", True)

            # Process the content with a timeout
            with time_limit(extraction_timeout):
                # First try with readability-lxml if available
                try:
                    from readability import Document
                    doc = Document(content)
                    article_html = doc.summary()
                    soup = BeautifulSoup(article_html, "html.parser")
                    logger.info(f"Successfully extracted content using readability-lxml for {url}")
                except ImportError:
                    # Fall back to BeautifulSoup if readability is not available
                    soup = BeautifulSoup(content, "html.parser")
                    logger.info("readability-lxml not available, using BeautifulSoup fallback")

                    # Try site-specific extraction based on domain
                    domain = urlparse(url).netloc
                    main_content = None

                    # Check if we have a specific selector for this domain in config
                    for site_domain, selector in site_specific_selectors.items():
                        if site_domain in domain:
                            main_content = soup.select_one(selector)
                            if main_content:
                                logger.info(f"Used site-specific selector for {domain}")
                                break

                    # Use generic fallback selectors if no site-specific selector matched
                    if not main_content:
                        # Use the fallback selectors from config or default ones
                        fallback_selectors = self.config.get("fallback_selectors", [
                            "article", "main", "div.content", "div.article", "div.post",
                            ".entry-content", "#content", ".article__body", ".post-content",
                            ".story", ".story-body", "[itemprop='articleBody']"
                        ])

                        for selector in fallback_selectors:
                            try:
                                if '.' in selector or '#' in selector or '[' in selector:
                                    main_content = soup.select_one(selector)
                                else:
                                    main_content = soup.find(selector)
                                if main_content:
                                    break
                            except Exception:
                                continue

                    if not main_content:
                        # Fallback: Get paragraphs from body
                        paragraphs = soup.find_all("p")
                        content_text = "".join(str(p) for p in paragraphs[:20])  # Limit to first 20 paragraphs
                        temp_soup = BeautifulSoup(f"<div>{content_text}</div>", "html.parser")
                        soup = temp_soup
                    else:
                        soup = BeautifulSoup(str(main_content), "html.parser")

                # Clean up common elements regardless of extraction method
                elements_to_remove = self.config.get("elements_to_remove", [
                    'script', 'style', 'iframe', 'noscript', 'video', 'audio',
                    'embed', 'object', 'canvas', 'form', 'button', 'aside',
                    'header', 'footer', 'nav'
                ])

                # Get class selectors to remove from config
                class_selectors_to_remove = self.config.get("class_selectors_to_remove", [
                    '.comments', '.social-share', '.related-articles', '.recommendations',
                    '.newsletter-signup', '.advertisement', '.ad', '.popup', '.modal',
                    '.share', '.social', '.related', '.popular', '.trending',
                    '.recommended', '#comments', '.comments', '.comment-section',
                    '.advertisement', '.ad-container', '.sponsored', '.subscribe',
                    '.newsletter', '.signup', '.sidebar', '.footer', '.header'
                ])

                # Remove elements by tag name
                for tag in soup(elements_to_remove):
                    tag.decompose()

                # Remove elements by class selectors
                for selector in class_selectors_to_remove:
                    for element in soup.select(selector):
                        element.decompose()

                # Process images
                if include_images:
                    for img in soup.find_all("img"):
                        try:
                            # Fix relative URLs
                            img_src = img.get('src', '')
                            if img_src.startswith('/'):
                                # Convert relative URLs to absolute
                                parsed_url = urlparse(url)
                                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                                img['src'] = base_url + img_src
                            elif not (img_src.startswith('http://') or img_src.startswith('https://')):
                                # Skip images with non-http sources to avoid file:/// errors
                                img.decompose()
                                continue
                        except Exception as e:
                            logger.debug(f"Error processing image: {e}")
                            img.decompose()  # Remove problematic images
                else:
                    # Remove images if not configured
                    for img in soup.find_all("img"):
                        img.decompose()

                # Clean up links - keep the text but remove the link
                for a in soup.find_all('a'):
                    try:
                        # If the link only contains an image, keep it
                        if a.find('img') and len(a.contents) == 1:
                            continue
                        # Otherwise replace with just the text
                        a.replace_with(a.get_text())
                    except Exception as e:
                        logger.debug(f"Error processing link: {e}")

                # Remove empty paragraphs and divs
                for p in soup.find_all(['p', 'div']):
                    if p.get_text(strip=True) == '':
                        p.decompose()

                content_text = str(soup)

                # Limit content length
                if len(content_text) > max_length:
                    content_text = content_text[:max_length] + "... [Content truncated due to length]"

                return content_text
        except requests.Timeout:
            logger.warning(f"Request timed out for {url}")
            raise TimeoutException(f"Request timed out for {url}")
        except TimeoutException:
            logger.warning(f"Content extraction timed out for {url}")
            raise
        except Exception as e:
            logger.warning(f"Error extracting content from {url}: {str(e)[:100]}")
            raise

    def generate_html(self):
        """Generate HTML content from the fetched articles using Jinja2 templates."""
        if not self.articles:
            logger.warning("No articles to generate paper from")
            return None

        # Group articles by source
        sources = {}
        for article in self.articles:
            source = article["source"]
            if source not in sources:
                sources[source] = []
            sources[source].append(article)

        # Template variables
        template_vars = {
            "date": datetime.datetime.now().strftime("%A, %B %d, %Y"),
            "sources": sources
        }

        # Get the main template name from config
        template_name = self.config.get("templates", {}).get("main_template", "paper_template.html")

        try:
            # Load and render the template
            template = self.template_env.get_template(template_name)
            return template.render(**template_vars)
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return None

    def generate_pdf(self):
        """Generate a PDF document from the articles using WeasyPrint."""
        html_content = self.generate_html()
        if not html_content:
            return None

        # Create output directory if it doesn't exist
        os.makedirs(self.config["output_directory"], exist_ok=True)

        # Generate PDF filename
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        pdf_path = os.path.join(self.config["output_directory"], f"morning_paper_{today}.pdf")

        try:
            # Create a temporary HTML file
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_html_path = f.name

            # Convert HTML to PDF using WeasyPrint with minimal settings
            logger.info(f"Generating PDF at {pdf_path}")

            # Import WeasyPrint only when needed to save memory earlier
            from weasyprint import HTML

            # Use a simpler font family that's likely available
            html = HTML(filename=temp_html_path)
            html.write_pdf(pdf_path)

            return pdf_path
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return None
        finally:
            # Clean up temporary file
            if 'temp_html_path' in locals():
                try:
                    os.unlink(temp_html_path)
                except:
                    pass

            # Force garbage collection
            gc.collect()

    def run(self):
        """Run the complete process."""
        logger.info("Starting paper generation process")
        try:
            self.fetch_rss_articles()
            gc.collect()  # Free memory after RSS processing

            self.fetch_hacker_news_articles()
            gc.collect()  # Free memory after Hacker News processing

            return self.generate_pdf()
        except Exception as e:
            logger.error(f"Error in paper generation process: {e}")
            return None

if __name__ == "__main__":
    try:
        generator = MorningPaperGenerator()
        pdf_path = generator.run()
        if pdf_path:
            logger.info(f"Morning paper successfully generated at: {pdf_path}")
        else:
            logger.error("Failed to generate morning paper")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
