# Morning Post Generator

A Python application that automatically generates a newspaper-style PDF from various RSS feeds and Hacker News articles.

## Features

- Fetches articles from configurable RSS feeds
- Includes top stories from Hacker News
- Extracts full article content from webpages
- Generates a nicely formatted newspaper-style PDF
- Fully customizable templates and styling
- Handles images (optional)
- Site-specific content extraction for better quality

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/morning-post-generator.git
   cd morning-post-generator
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

1. Configure your feeds and settings in `config.json`
2. Run the script:
   ```
   python morning.py
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
- And more!

## Templates

The application uses Jinja2 templates to generate the newspaper. You can customize the appearance by editing:

- `templates/paper_template.html` - overall newspaper layout
- `templates/article_template.html` - individual article formatting

## Requirements

- Python 3.7+
- All dependencies listed in `requirements.txt`, including:
  - feedparser
  - requests
  - beautifulsoup4
  - markdownify
  - Jinja2
  - WeasyPrint
  - readability-lxml

## Troubleshooting

### WeasyPrint Dependencies

WeasyPrint may require additional system dependencies. See the [WeasyPrint installation documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) for details.

### Memory Usage

For large feeds or many articles, you may need to adjust the number of articles or feeds to avoid memory issues.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
