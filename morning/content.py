"""Content extraction functionality."""
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import gc

from .utils import time_limit, TimeoutException
from .config_models import AppConfig

logger = logging.getLogger(__name__)

class ContentExtractor:
    def __init__(self, config: AppConfig):
        """Initialize the content extractor.

        Args:
            config: Validated application configuration
        """
        self.config = config

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and has an acceptable domain.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _is_web_page_url(self, url: str) -> bool:
        """Check if URL points to a webpage rather than a file download.

        Args:
            url: The URL to check

        Returns:
            True if the URL appears to be a web page, False if likely a file
        """
        file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                           '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi',
                           '.mov', '.exe', '.dmg', '.apk', '.iso']

        parsed_url = urlparse(url)
        path = parsed_url.path.lower()

        # Check for file extensions in the path
        for ext in file_extensions:
            if path.endswith(ext):
                logger.info(f"Skipping file URL: {url}")
                return False

        return True

    def extract_article_content(self, url: str) -> str:
        """Extract the main content from an article URL with improved quality.

        Args:
            url: The article URL to extract content from

        Returns:
            HTML content as string

        Raises:
            TimeoutException: If extraction takes too long
            requests.RequestException: On request failure
        """
        if not self._is_web_page_url(url):
            return f"<p><em>This article links to a file that cannot be displayed in the paper. View the original at:</em> {url}</p>"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        timeout = self.config.timeout.request
        extraction_timeout = self.config.timeout.extraction
        max_length = self.config.max_content_length
        site_specific_selectors = self.config.site_specific_selectors

        try:
            # Get the page with timeout
            response = requests.get(url, headers=headers, timeout=timeout)

            # Limit content size for memory management
            content = response.content[:500000]  # Limit to 500KB to avoid memory issues
            include_images = self.config.include_images

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
                        # Use the fallback selectors from config
                        fallback_selectors = self.config.fallback_selectors

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
                elements_to_remove = self.config.elements_to_remove

                # Get class selectors to remove from config
                class_selectors_to_remove = self.config.class_selectors_to_remove

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
        finally:
            # Force garbage collection to free memory
            gc.collect()
