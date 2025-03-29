# Morning Paper Generator

A Python application that automatically generates a newspaper-style PDF from various RSS feeds and Hacker News articles.

## Features

- Fetches articles from configurable RSS feeds
- Includes top stories from Hacker News
- Extracts full article content from webpages
- Generates a nicely formatted newspaper-style PDF
- Fully customizable templates and styling
- Handles images (optional)
- Site-specific content extraction for better quality
- Memory-efficient content processing

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/morning-paper-generator.git
   cd morning-paper-generator
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv

   # On Windows:
   venv\Scripts\activate

   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Configure your feeds and settings in `config.json` (a default configuration will be created if it doesn't exist)
2. Run the application:
   ```python
   from morning import MorningPaperGenerator

   generator = MorningPaperGenerator()
   pdf_path = generator.run()
   print(f"Generated PDF: {pdf_path}")
   ```

   Alternatively, create a script like `generate_paper.py`:
   ```python
   #!/usr/bin/env python3
   from morning import MorningPaperGenerator

   if __name__ == "__main__":
       generator = MorningPaperGenerator()
       pdf_path = generator.run()
       if pdf_path:
           print(f"Successfully generated paper at: {pdf_path}")
       else:
           print("Failed to generate paper")
   ```

3. Find your generated PDF in the `papers` directory (or your custom output directory specified in config)

## Configuration

The `config.json` file allows you to customize:

- RSS feeds and number of articles per feed
- Hacker News inclusion settings
- PDF formatting options
- Content extraction settings
- HTML templates
- Output directory
- Timeout settings
- Site-specific content selectors
- And more!

Example configuration:
```json
{
    "rss_feeds": [
        {"name": "BBC News", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "max_articles": 5},
        {"name": "New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "max_articles": 5}
    ],
    "hacker_news": {
        "include": true,
        "max_articles": 5,
        "only_self_posts": true
    },
    "output_directory": "./papers",
    "newspaper_title": "Morning Paper",
    "columns": 1,
    "extract_full_content": true,
    "include_images": false
}
```

## Templates

The application uses Jinja2 templates to generate the newspaper. You can customize the appearance by editing:

- `templates/paper_template.html` - overall newspaper layout
- `templates/article_template.html` - individual article formatting

Default templates are created automatically if they don't exist in the configured templates directory.

## Requirements

- Python 3.7+
- All dependencies listed in `requirements.txt`, including:
  - pydantic (v2+)
  - feedparser
  - requests
  - beautifulsoup4
  - markdownify
  - Jinja2
  - WeasyPrint
  - readability-lxml (optional but recommended)

## Testing

Run the test suite with pytest:

```
pytest tests/
```

For coverage information:

```
pytest --cov=morning tests/
```

## Troubleshooting

### WeasyPrint Dependencies

WeasyPrint requires additional system dependencies for PDF generation:

- **Ubuntu/Debian**:
  ```
  sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
  ```

- **macOS** (using Homebrew):
  ```
  brew install cairo pango gdk-pixbuf libffi
  ```

- **Windows**: Follow the [WeasyPrint Windows installation instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows)

See the [WeasyPrint installation documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) for more details.

### Memory Usage

For large feeds or many articles, you can:
- Reduce the `max_articles` per feed
- Decrease the number of feeds
- Set `extract_full_content` to `false` to use summaries instead
- Set `include_images` to `false` to skip image processing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [feedparser](https://github.com/kurtmckee/feedparser) for RSS parsing
- [readability-lxml](https://github.com/buriy/python-readability) for content extraction
- [WeasyPrint](https://weasyprint.org/) for HTML to PDF conversion
- [Hacker News API](https://github.com/HackerNews/API) for HN integration
