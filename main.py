#!/usr/bin/env python3
"""
Morning Paper Generator
A tool to fetch articles from various sources and create a daily reading digest in PDF format.
"""
import logging
import argparse
import sys
from morning import MorningPaperGenerator

def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Silence third-party loggers
    for logger_name in ['fontTools', 'PIL', 'weasyprint', 'cssselect', 'cffi', 'html5lib']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False

        # Add a null handler to prevent warnings about no handlers
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Generate a morning news PDF")
    parser.add_argument("-c", "--config", default="config.json",
                        help="Path to config file (default: config.json)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")
    args = parser.parse_args()

    # Set up logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Create and run the generator
    generator = MorningPaperGenerator(config_path=args.config)
    pdf_path = generator.run()

    if pdf_path:
        print(f"Morning paper successfully generated at: {pdf_path}")
        return 0
    else:
        print("Failed to generate morning paper")
        return 1

if __name__ == "__main__":
    sys.exit(main())
