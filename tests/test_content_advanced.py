import unittest
from unittest.mock import patch, Mock
from bs4 import BeautifulSoup

from morning.content import ContentExtractor
from morning.config_models import AppConfig
from morning.utils import TimeoutException

class TestContentExtractionHeuristics(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
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
            timeout={"request": 5, "extraction": 10},
            include_images=True,
            fallback_selectors=["article", "main", ".content", "#article-body"],
            elements_to_remove=["script", "style", "iframe"],
            class_selectors_to_remove=[".ad", ".comments", ".sidebar"]
        )
        self.extractor = ContentExtractor(self.config)

    def test_text_density_calculation(self):
        """Test calculation of text density for HTML elements."""
        # Create a test element with known text ratio
        html = """
        <div id="high-density">This is a div with a lot of text content and relatively little HTML markup.</div>
        <div id="low-density"><span>T</span><span>h</span><span>i</span><span>s</span> <span>h</span><span>a</span><span>s</span> <span>l</span><span>o</span><span>w</span> <span>d</span><span>e</span><span>n</span><span>s</span><span>i</span><span>t</span><span>y</span></div>
        """
        soup = BeautifulSoup(html, "html.parser")

        high_density = soup.find(id="high-density")
        low_density = soup.find(id="low-density")

        # Calculate densities
        high_density_score = self.extractor._get_text_density(high_density)
        low_density_score = self.extractor._get_text_density(low_density)

        # High density should have a higher score
        self.assertGreater(high_density_score, low_density_score)

        # Check reasonable values (should be between 0 and 1)
        self.assertTrue(0 < high_density_score < 1)
        self.assertTrue(0 < low_density_score < 1)

    def test_find_content_by_density(self):
        """Test finding the highest density content element."""
        # Create HTML with content in different elements
        html = """
        <html>
        <body>
            <header class="header">
                <h1>Website Title</h1>
                <nav>Menu items here</nav>
            </header>
            <main>
                <aside class="sidebar">
                    This is a sidebar with some links and stuff.
                    <ul>
                        <li>Link 1</li>
                        <li>Link 2</li>
                    </ul>
                </aside>
                <article class="content">
                    <h2>Article Title</h2>
                    <p>This is the main content of the article. It should have the highest density of text.</p>
                    <p>It contains multiple paragraphs with substantial text content.</p>
                    <p>The text density should be higher here than in navigation or sidebar areas.</p>
                    <p>This is precisely what we're looking for when extracting content.</p>
                </article>
                <div class="comments">
                    <div class="comment">Comment 1 text here</div>
                    <div class="comment">Comment 2 text here</div>
                </div>
            </main>
            <footer>
                Copyright information and site links
            </footer>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        # Find the content
        content_element = self.extractor._find_content_by_density(soup)

        # Should find the article element
        self.assertEqual(content_element.name, "article")
        self.assertIn("content", content_element.get("class", []))

        # Verify content text was found
        self.assertIn("main content of the article", content_element.get_text())

    def test_get_content_using_heuristics(self):
        """Test the combined heuristic content detection."""
        # Case 1: Single article tag (most semantic)
        html1 = """
        <html><body>
            <header>Header content</header>
            <article>This is the article content we want to extract.</article>
            <footer>Footer content</footer>
        </body></html>
        """
        soup1 = BeautifulSoup(html1, "html.parser")
        content1 = self.extractor._get_content_using_heuristics(soup1)
        self.assertEqual(content1.name, "article")

        # Case 2: No article tag, but has main tag
        html2 = """
        <html><body>
            <header>Header content</header>
            <main>This is the main content we want to extract.</main>
            <footer>Footer content</footer>
        </body></html>
        """
        soup2 = BeautifulSoup(html2, "html.parser")
        content2 = self.extractor._get_content_using_heuristics(soup2)
        self.assertEqual(content2.name, "main")

        # Case 3: Elements with article-indicating classes
        html3 = """
        <html><body>
            <header>Header content</header>
            <div class="entry-content">This is the content with a special class.</div>
            <footer>Footer content</footer>
        </body></html>
        """
        soup3 = BeautifulSoup(html3, "html.parser")
        content3 = self.extractor._get_content_using_heuristics(soup3)
        self.assertEqual(content3.get("class", [])[0], "entry-content")

    def test_image_processing(self):
        """Test processing of images in extracted content."""
        # HTML with both absolute and relative image URLs
        html = """
        <html><body><article>
            <p>Article with images</p>
            <img src="https://example.com/absolute.jpg" alt="Absolute">
            <img src="/relative.jpg" alt="Relative">
            <img src="data:image/png;base64,abc" alt="Data URL">
        </article></body></html>
        """

        # Mock the requests.get to return this HTML
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = html.encode('utf-8')
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Set include_images=True
            self.config.include_images = True
            content = self.extractor.extract_article_content("https://example.com/article")

            # Parse the result to check image processing
            result_soup = BeautifulSoup(content, "html.parser")

            # Should have two images (the data URL image should be preserved)
            images = result_soup.find_all("img")

            # Check absolute URL is preserved
            absolute_img = next((img for img in images if "absolute.jpg" in img.get("src", "")), None)
            self.assertIsNotNone(absolute_img)

            # Check relative URL is converted to absolute
            relative_img = next((img for img in images if "example.com/relative.jpg" in img.get("src", "")), None)
            self.assertIsNotNone(relative_img)

            # Now test with include_images=False
            self.config.include_images = False
            content = self.extractor.extract_article_content("https://example.com/article")

            # Parse the result
            result_soup = BeautifulSoup(content, "html.parser")

            # Should have no images
            images = result_soup.find_all("img")
            self.assertEqual(len(images), 0)

    def test_element_removal(self):
        """Test removal of specified elements."""
        html = """
        <html><body><article>
            <p>Article content</p>
            <script>alert('script')</script>
            <div class="ad">Advertisement</div>
            <div class="comments">
                <div>Comment 1</div>
                <div>Comment 2</div>
            </div>
        </article></body></html>
        """

        # Mock the requests.get to return this HTML
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = html.encode('utf-8')
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            content = self.extractor.extract_article_content("https://example.com/article")

            # Parse the result
            result_soup = BeautifulSoup(content, "html.parser")

            # Should have removed scripts
            scripts = result_soup.find_all("script")
            self.assertEqual(len(scripts), 0)

            # Should have removed ads
            ads = result_soup.find_all(class_="ad")
            self.assertEqual(len(ads), 0)

            # Should have removed comments
            comments = result_soup.find_all(class_="comments")
            self.assertEqual(len(comments), 0)

            # Should have kept content
            self.assertIn("Article content", result_soup.get_text())

    @patch('requests.get')
    def test_malformed_html_handling(self, mock_get):
        """Test handling of malformed HTML."""
        # Malformed HTML with unclosed tags
        malformed_html = """
        <html><body>
            <div>
                <p>This paragraph is not closed.
                <p>Another unclosed paragraph.
            <article>
                <h1>Article with unclosed tags
                <p>Content
            </article>
        </body></html>
        """

        mock_response = Mock()
        mock_response.content = malformed_html.encode('utf-8')
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Should not raise an exception
        content = self.extractor.extract_article_content("https://example.com/malformed")

        # Should have extracted some content
        self.assertIsNotNone(content)
        self.assertIn("Article with unclosed tags", content)

    @patch('requests.get')
    def test_garbage_collection(self, mock_get):
        """Test garbage collection during extraction."""
        # Create a large HTML document to simulate memory pressure
        large_html = "<html><body>" + "<p>Repeated content</p>" * 10000 + "</body></html>"

        mock_response = Mock()
        mock_response.content = large_html.encode('utf-8')
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Mock gc.collect() to check if it was called
        with patch('gc.collect') as mock_gc:
            content = self.extractor.extract_article_content("https://example.com/large")

            # Verify gc.collect() was called
            mock_gc.assert_called()
