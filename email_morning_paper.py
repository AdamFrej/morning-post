#!/usr/bin/env python3
"""
Email the latest generated PDF from the morning paper generator.
"""
import os
import glob
import smtplib
import argparse
import logging
import configparser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("morning-paper-email")

def find_latest_pdf(directory):
    """Find the latest PDF file in the specified directory."""
    pdf_files = glob.glob(os.path.join(directory, "*.pdf"))
    if not pdf_files:
        return None

    # Get the most recently modified file
    latest_pdf = max(pdf_files, key=os.path.getmtime)
    return latest_pdf

def send_email(pdf_path, recipient, sender, subject, body, smtp_server, smtp_port, username, password, use_tls=True):
    """Send an email with the PDF attached."""
    # Create a multipart message
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject

    # Add body text
    msg.attach(MIMEText(body, 'plain'))

    # Add the PDF attachment
    with open(pdf_path, 'rb') as file:
        pdf_attachment = MIMEApplication(file.read(), _subtype='pdf')
        pdf_name = os.path.basename(pdf_path)
        pdf_attachment.add_header('Content-Disposition', f'attachment; filename={pdf_name}')
        msg.attach(pdf_attachment)

    # Connect to SMTP server and send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        if use_tls:
            server.starttls()

        if username and password:
            server.login(username, password)

        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent successfully to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def load_config_file(config_path):
    """Load settings from a configuration file."""
    config = configparser.ConfigParser()

    # For simple KEY=VALUE format without sections
    with open(config_path, 'r') as f:
        content = f.read()

    # Check if the file has sections (INI format)
    if '[' in content and ']' in content:
        # Standard INI format
        config.read(config_path)
        if 'Email' in config:
            return {
                'recipient': config.get('Email', 'RECIPIENT', fallback=None),
                'sender': config.get('Email', 'SENDER', fallback=None),
                'smtp_server': config.get('Email', 'SMTP_SERVER', fallback=None),
                'smtp_port': config.getint('Email', 'SMTP_PORT', fallback=587),
                'username': config.get('Email', 'USERNAME', fallback=None),
                'password': config.get('Email', 'PASSWORD', fallback=None),
                'pdf_dir': config.get('Email', 'PDF_DIR', fallback='./papers'),
                'use_tls': config.getboolean('Email', 'USE_TLS', fallback=True)
            }
    else:
        # Simple KEY=VALUE format
        settings = {}
        for line in content.splitlines():
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip().strip('"\'')

        return {
            'recipient': settings.get('RECIPIENT'),
            'sender': settings.get('SENDER'),
            'smtp_server': settings.get('SMTP_SERVER'),
            'smtp_port': int(settings.get('SMTP_PORT', '587')),
            'username': settings.get('USERNAME'),
            'password': settings.get('PASSWORD'),
            'pdf_dir': settings.get('PDF_DIR', './papers'),
            'use_tls': settings.get('USE_TLS', 'true').lower() != 'false'
        }

def load_from_env():
    """Load settings from environment variables."""
    return {
        'recipient': os.environ.get('MORNING_PAPER_RECIPIENT'),
        'sender': os.environ.get('MORNING_PAPER_SENDER'),
        'smtp_server': os.environ.get('MORNING_PAPER_SMTP_SERVER'),
        'smtp_port': int(os.environ.get('MORNING_PAPER_SMTP_PORT', '587')),
        'username': os.environ.get('MORNING_PAPER_USERNAME'),
        'password': os.environ.get('MORNING_PAPER_PASSWORD'),
        'pdf_dir': os.environ.get('MORNING_PAPER_PDF_DIR', './papers'),
        'use_tls': os.environ.get('MORNING_PAPER_USE_TLS', 'true').lower() != 'false'
    }

def main():
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(description="Email the latest morning paper PDF")

    # Configuration options
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument("--config", help="Path to configuration file")
    config_group.add_argument("--use-env", action="store_true",
                            help="Use environment variables for configuration")

    # Direct arguments
    direct_group = parser.add_argument_group('Direct Settings (alternative to config file)')
    direct_group.add_argument("--recipient", help="Email recipient address")
    direct_group.add_argument("--sender", help="Sender email address")
    direct_group.add_argument("--smtp-server", help="SMTP server address")
    direct_group.add_argument("--pdf-dir", default="./papers", help="Directory containing PDF files")
    direct_group.add_argument("--smtp-port", type=int, default=587, help="SMTP server port")
    direct_group.add_argument("--username", help="SMTP username (if required)")
    direct_group.add_argument("--password", help="SMTP password (if required)")
    direct_group.add_argument("--subject", help="Email subject (default: Morning Paper - YYYY-MM-DD)")
    direct_group.add_argument("--body", help="Email body text")
    direct_group.add_argument("--no-tls", action="store_true", help="Disable TLS encryption")

    args = parser.parse_args()

    # Load configuration based on provided options
    config = {}
    if args.config:
        if not os.path.exists(args.config):
            logger.error(f"Config file not found: {args.config}")
            return 1
        logger.info(f"Loading configuration from file: {args.config}")
        config = load_config_file(args.config)
    elif args.use_env:
        logger.info("Loading configuration from environment variables")
        config = load_from_env()

    # Override with any directly provided arguments
    # (Only if they're explicitly provided)
    for key in ['recipient', 'sender', 'smtp_server', 'smtp_port', 'username',
                'password', 'pdf_dir']:
        if hasattr(args, key) and getattr(args, key) is not None:
            config[key] = getattr(args, key)

    if args.no_tls:
        config['use_tls'] = False

    # Validate required fields
    required_fields = ['recipient', 'sender', 'smtp_server']
    missing_fields = [field for field in required_fields if not config.get(field)]

    if missing_fields:
        logger.error(f"Missing required configuration: {', '.join(missing_fields)}")
        logger.error("Please provide these values via config file, environment variables, or direct arguments")
        return 1

    # Find the latest PDF
    pdf_path = find_latest_pdf(config['pdf_dir'])
    if not pdf_path:
        logger.error(f"No PDF files found in {config['pdf_dir']}")
        return 1

    # Check if the PDF was generated today
    pdf_mtime = datetime.fromtimestamp(os.path.getmtime(pdf_path))
    today = datetime.now().date()

    if pdf_mtime.date() != today:
        logger.warning(f"Latest PDF ({os.path.basename(pdf_path)}) was not generated today. Sending anyway.")

    # Use default subject if not provided
    subject = args.subject
    if not subject:
        pdf_date = pdf_mtime.strftime("%Y-%m-%d")
        subject = f"Morning Paper - {pdf_date}"

    # Use default body if not provided
    body = args.body
    if not body:
        pdf_name = os.path.basename(pdf_path)
        body = f"Your morning paper digest is attached.\n\nFile: {pdf_name}\nGenerated: {pdf_mtime.strftime('%Y-%m-%d %H:%M:%S')}"

    # Send the email
    success = send_email(
        pdf_path=pdf_path,
        recipient=config['recipient'],
        sender=config['sender'],
        subject=subject,
        body=body,
        smtp_server=config['smtp_server'],
        smtp_port=config['smtp_port'],
        username=config.get('username'),
        password=config.get('password'),
        use_tls=config.get('use_tls', True)
    )

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
