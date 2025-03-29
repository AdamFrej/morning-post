"""Document rendering functionality for Morning Paper Generator."""
import os
import datetime
import tempfile
import logging
import gc

logger = logging.getLogger(__name__)

class DocumentRenderer:
    def __init__(self, config, template_manager):
        """Initialize the document renderer."""
        self.config = config
        self.template_manager = template_manager

    def generate_html(self, articles):
        """Generate HTML content from the fetched articles using Jinja2 templates."""
        if not articles:
            logger.warning("No articles to generate paper from")
            return None

        # Sort all articles by date, newest first
        # Try to parse published date, fall back to string comparison
        def get_article_date(article):
            published = article.get("published", "")
            try:
                # Try different date formats
                for fmt in ["%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"]:
                    try:
                        dt = datetime.datetime.strptime(published, fmt)
                        # Make sure the datetime is naive (no timezone info)
                        if dt.tzinfo is not None:
                            # Convert to UTC then remove timezone info
                            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                        return dt
                    except ValueError:
                        continue

                # If none of the formats match, try a simpler approach
                return datetime.datetime.strptime(published[:10], "%Y-%m-%d")
            except Exception as e:
                # Return current time minus random seconds for stable sorting
                # when dates can't be parsed
                logger.debug(f"Could not parse date '{published}': {e}")
                return datetime.datetime.now() - datetime.timedelta(seconds=hash(article.get("title", "")) % 86400)

        # Sort the articles, newest first
        sorted_articles = sorted(articles, key=get_article_date, reverse=True)

        # Filter out articles with insufficient content or file links
        filtered_articles = []
        for article in sorted_articles:
            content = article.get("content", "")
            title = article.get("title", "").lower()
            link = article.get("link", "").lower()

            # Skip PDF files based on title or link
            file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                             '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi',
                             '.mov', '.exe', '.dmg', '.apk', '.iso']

            # Check if title indicates a file
            if any(ext in title for ext in file_extensions):
                logger.info(f"Skipping file article based on title: {article.get('title', 'Unknown')}")
                continue

            # Check if link is a direct file download
            if any(link.endswith(ext) for ext in file_extensions):
                logger.info(f"Skipping file article based on URL: {article.get('title', 'Unknown')}")
                continue

            # Strip HTML tags and extra whitespace
            from bs4 import BeautifulSoup
            text_content = BeautifulSoup(content, "html.parser").get_text().strip()

            # Skip articles with very short content
            if len(text_content) < 150:
                logger.info(f"Skipping article with insufficient content: {article.get('title', 'Unknown')}")
                continue

            # Skip articles that mention file links
            file_link_phrases = [
                'This article links to a file that cannot be displayed',
                'links to a file',
                'download the file',
                'view the PDF',
                'download PDF',
                'View the original'
            ]

            skip = False
            for phrase in file_link_phrases:
                if phrase.lower() in text_content.lower():
                    logger.info(f"Skipping file link article: {article.get('title', 'Unknown')}")
                    skip = True
                    break

            if skip:
                continue

            # Skip articles that appear to have failed extraction
            error_phrases = [
                'Content extraction failed',
                'Content extraction timed out',
                'No text content available',
                'Failed to extract'
            ]

            for phrase in error_phrases:
                if phrase in text_content and len(text_content) < 200:
                    logger.info(f"Skipping article with extraction error: {article.get('title', 'Unknown')}")
                    skip = True
                    break

            if not skip:
                filtered_articles.append(article)

        # Check if we still have articles after filtering
        if not filtered_articles:
            logger.warning("No articles with sufficient content to generate paper")
            return None

        # Template variables - include both old and new format for compatibility
        template_vars = {
            "date": datetime.datetime.now().strftime("%A, %B %d, %Y"),
            "articles": filtered_articles,  # New format - single list of all articles
            "sources": {"Today's Articles": filtered_articles}  # Old format - for backward compatibility
        }

        # Get the main template name from config
        template_name = self.config.templates.main_template

        try:
            # Load and render the template
            template = self.template_manager.get_template(template_name)
            return template.render(**template_vars)
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return None

    def generate_pdf(self, articles):
        """Generate a PDF document from the articles using WeasyPrint."""
        html_content = self.generate_html(articles)
        if not html_content:
            return None

        # Create output directory if it doesn't exist
        os.makedirs(self.config.output_directory, exist_ok=True)

        # Generate PDF filename
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        pdf_path = os.path.join(self.config.output_directory, f"morning_paper_{today}.pdf")

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
