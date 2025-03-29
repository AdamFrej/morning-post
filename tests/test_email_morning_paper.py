"""
Unit tests for the email_morning_paper.py script.
"""
import unittest
import os
import tempfile
import argparse
from unittest.mock import patch, mock_open, MagicMock

# Import the functions directly from your script
from email_morning_paper import (
    find_latest_pdf,
    send_email,
    load_config_file,
    load_from_env,
    main
)

class TestEmailMorningPaper(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf_dir = self.temp_dir.name

        # Create a sample PDF file
        self.pdf_path = os.path.join(self.pdf_dir, "morning_paper_2023-05-01.pdf")
        with open(self.pdf_path, 'wb') as f:
            f.write(b'Test PDF content')

        # Touch the file to update its timestamp
        os.utime(self.pdf_path, None)

        # Create another PDF with an older timestamp
        self.old_pdf_path = os.path.join(self.pdf_dir, "morning_paper_2023-04-30.pdf")
        with open(self.old_pdf_path, 'wb') as f:
            f.write(b'Old PDF content')

        # Set the timestamp to be older
        old_time = os.path.getmtime(self.pdf_path) - 86400  # 1 day older
        os.utime(self.old_pdf_path, (old_time, old_time))

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    def test_find_latest_pdf(self):
        """Test finding the latest PDF in a directory."""
        # Test with valid directory containing PDFs
        latest = find_latest_pdf(self.pdf_dir)
        self.assertEqual(latest, self.pdf_path)

        # Test with empty directory
        empty_dir = tempfile.TemporaryDirectory()
        self.assertIsNone(find_latest_pdf(empty_dir.name))
        empty_dir.cleanup()

        # Test with non-existent directory
        non_existent = "/non/existent/directory"
        self.assertIsNone(find_latest_pdf(non_existent))

    @patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        """Test sending an email with attachment."""
        # Set up mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        # Test successful email sending
        result = send_email(
            pdf_path=self.pdf_path,
            recipient="recipient@example.com",
            sender="sender@example.com",
            subject="Test Subject",
            body="Test Body",
            smtp_server="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            use_tls=True
        )

        # Verify SMTP calls
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

        # Check result
        self.assertTrue(result)

        # Test without TLS
        mock_smtp.reset_mock()
        mock_server.reset_mock()

        result = send_email(
            pdf_path=self.pdf_path,
            recipient="recipient@example.com",
            sender="sender@example.com",
            subject="Test Subject",
            body="Test Body",
            smtp_server="smtp.example.com",
            smtp_port=25,
            username="user",
            password="pass",
            use_tls=False
        )

        mock_smtp.assert_called_once_with("smtp.example.com", 25)
        mock_server.starttls.assert_not_called()
        self.assertTrue(result)

        # Test with error
        mock_smtp.reset_mock()
        mock_server.send_message.side_effect = Exception("SMTP error")

        result = send_email(
            pdf_path=self.pdf_path,
            recipient="recipient@example.com",
            sender="sender@example.com",
            subject="Test Subject",
            body="Test Body",
            smtp_server="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass"
        )

        self.assertFalse(result)

    def test_load_config_file_key_value(self):
        """Test loading config from a KEY=VALUE formatted file."""
        config_content = """
        RECIPIENT=test@example.com
        SENDER=sender@example.com
        SMTP_SERVER=smtp.example.com
        SMTP_PORT=587
        USERNAME=username
        PASSWORD=password
        PDF_DIR=/path/to/pdfs
        USE_TLS=true
        """

        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(config_content)
            config_path = temp_file.name

        try:
            # Load config from the temporary file
            config = load_config_file(config_path)

            # Verify the config was loaded correctly
            self.assertEqual(config['recipient'], 'test@example.com')
            self.assertEqual(config['sender'], 'sender@example.com')
            self.assertEqual(config['smtp_server'], 'smtp.example.com')
            self.assertEqual(config['smtp_port'], 587)
            self.assertEqual(config['username'], 'username')
            self.assertEqual(config['password'], 'password')
            self.assertEqual(config['pdf_dir'], '/path/to/pdfs')
            self.assertTrue(config['use_tls'])
        finally:
            # Clean up the temporary file
            os.unlink(config_path)

    def test_load_config_file_ini_format(self):
        """Test loading config from an INI formatted file."""
        config_content = """
        [Email]
        RECIPIENT=test@example.com
        SENDER=sender@example.com
        SMTP_SERVER=smtp.example.com
        SMTP_PORT=587
        USERNAME=username
        PASSWORD=password
        PDF_DIR=/path/to/pdfs
        USE_TLS=false
        """

        # Create a temporary INI file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(config_content)
            config_path = temp_file.name

        try:
            # Load config from the temporary file
            config = load_config_file(config_path)

            # Verify the config was loaded correctly
            self.assertEqual(config['recipient'], 'test@example.com')
            self.assertEqual(config['sender'], 'sender@example.com')
            self.assertEqual(config['smtp_server'], 'smtp.example.com')
            self.assertEqual(config['smtp_port'], 587)
            self.assertEqual(config['username'], 'username')
            self.assertEqual(config['password'], 'password')
            self.assertEqual(config['pdf_dir'], '/path/to/pdfs')
            self.assertFalse(config['use_tls'])
        finally:
            # Clean up the temporary file
            os.unlink(config_path)

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            'MORNING_PAPER_RECIPIENT': 'env@example.com',
            'MORNING_PAPER_SENDER': 'env-sender@example.com',
            'MORNING_PAPER_SMTP_SERVER': 'env-smtp.example.com',
            'MORNING_PAPER_SMTP_PORT': '465',
            'MORNING_PAPER_USERNAME': 'env-user',
            'MORNING_PAPER_PASSWORD': 'env-pass',
            'MORNING_PAPER_PDF_DIR': '/env/path/to/pdfs',
            'MORNING_PAPER_USE_TLS': 'false'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = load_from_env()

        self.assertEqual(config['recipient'], 'env@example.com')
        self.assertEqual(config['sender'], 'env-sender@example.com')
        self.assertEqual(config['smtp_server'], 'env-smtp.example.com')
        self.assertEqual(config['smtp_port'], 465)
        self.assertEqual(config['username'], 'env-user')
        self.assertEqual(config['password'], 'env-pass')
        self.assertEqual(config['pdf_dir'], '/env/path/to/pdfs')
        self.assertFalse(config['use_tls'])

        # Test with missing variables
        with patch.dict(os.environ, {}, clear=True):
            config = load_from_env()

        self.assertIsNone(config['recipient'])
        self.assertIsNone(config['sender'])
        self.assertIsNone(config['smtp_server'])
        self.assertEqual(config['smtp_port'], 587)  # Default value
        self.assertEqual(config['pdf_dir'], './papers')  # Default value

    @patch('argparse.ArgumentParser.parse_args')
    @patch('email_morning_paper.send_email')
    @patch('email_morning_paper.find_latest_pdf')
    def test_main_with_direct_args(self, mock_find_pdf, mock_send_email, mock_parse_args):
        """Test main function with direct command line arguments."""
        # Set up mocks
        mock_args = argparse.Namespace(
            config=None,
            use_env=False,
            recipient='cmd@example.com',
            sender='cmd-sender@example.com',
            smtp_server='cmd-smtp.example.com',
            pdf_dir=self.pdf_dir,
            smtp_port=587,
            username='cmd-user',
            password='cmd-pass',
            subject=None,
            body=None,
            no_tls=False
        )
        mock_parse_args.return_value = mock_args

        mock_find_pdf.return_value = self.pdf_path
        mock_send_email.return_value = True

        # Run main function
        result = main()

        # Verify email was sent with correct parameters
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        self.assertEqual(call_args['pdf_path'], self.pdf_path)
        self.assertEqual(call_args['recipient'], 'cmd@example.com')
        self.assertEqual(call_args['sender'], 'cmd-sender@example.com')
        self.assertEqual(call_args['smtp_server'], 'cmd-smtp.example.com')
        self.assertEqual(call_args['smtp_port'], 587)
        self.assertEqual(call_args['username'], 'cmd-user')
        self.assertEqual(call_args['password'], 'cmd-pass')
        self.assertTrue(call_args['use_tls'])

        # Verify exit code
        self.assertEqual(result, 0)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('email_morning_paper.load_config_file')
    @patch('email_morning_paper.send_email')
    @patch('email_morning_paper.find_latest_pdf')
    def test_main_with_config_file(self, mock_find_pdf, mock_send_email, mock_load_config,
                                 mock_parse_args):
        """Test main function loading from config file."""
        # Set up mocks
        mock_args = argparse.Namespace(
            config='/path/to/config.conf',
            use_env=False,
            recipient=None,
            sender=None,
            smtp_server=None,
            pdf_dir=None,
            smtp_port=None,
            username=None,
            password=None,
            subject=None,
            body=None,
            no_tls=False
        )
        mock_parse_args.return_value = mock_args

        mock_find_pdf.return_value = self.pdf_path
        mock_send_email.return_value = True

        # Mock config loading
        mock_config = {
            'recipient': 'config@example.com',
            'sender': 'config-sender@example.com',
            'smtp_server': 'config-smtp.example.com',
            'smtp_port': 465,
            'username': 'config-user',
            'password': 'config-pass',
            'pdf_dir': self.pdf_dir,
            'use_tls': True
        }
        mock_load_config.return_value = mock_config

        # Mock that the config file exists
        with patch('os.path.exists', return_value=True):
            # Run main function
            result = main()

        # Verify config was loaded and email was sent
        mock_load_config.assert_called_once_with('/path/to/config.conf')
        mock_send_email.assert_called_once()

        # Verify parameters
        call_args = mock_send_email.call_args[1]
        self.assertEqual(call_args['recipient'], 'config@example.com')
        self.assertEqual(call_args['smtp_port'], 465)

        # Verify exit code
        self.assertEqual(result, 0)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('email_morning_paper.load_from_env')
    @patch('email_morning_paper.send_email')
    @patch('email_morning_paper.find_latest_pdf')
    def test_main_with_env_vars(self, mock_find_pdf, mock_send_email, mock_load_env,
                               mock_parse_args):
        """Test main function loading from environment variables."""
        # Set up mocks
        mock_args = argparse.Namespace(
            config=None,
            use_env=True,
            recipient=None,
            sender=None,
            smtp_server=None,
            pdf_dir=None,
            smtp_port=None,
            username=None,
            password=None,
            subject=None,
            body=None,
            no_tls=False
        )
        mock_parse_args.return_value = mock_args

        mock_find_pdf.return_value = self.pdf_path
        mock_send_email.return_value = True

        # Mock env var loading
        mock_env_config = {
            'recipient': 'env@example.com',
            'sender': 'env-sender@example.com',
            'smtp_server': 'env-smtp.example.com',
            'smtp_port': 587,
            'username': 'env-user',
            'password': 'env-pass',
            'pdf_dir': self.pdf_dir,
            'use_tls': True
        }
        mock_load_env.return_value = mock_env_config

        # Run main function
        result = main()

        # Verify env vars were loaded and email was sent
        mock_load_env.assert_called_once()
        mock_send_email.assert_called_once()

        # Verify parameters
        call_args = mock_send_email.call_args[1]
        self.assertEqual(call_args['recipient'], 'env@example.com')

        # Verify exit code
        self.assertEqual(result, 0)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('email_morning_paper.find_latest_pdf')
    def test_main_no_pdf_found(self, mock_find_pdf, mock_parse_args):
        """Test main function when no PDF is found."""
        # Set up mocks
        mock_args = argparse.Namespace(
            config=None,
            use_env=False,
            recipient='test@example.com',
            sender='sender@example.com',
            smtp_server='smtp.example.com',
            pdf_dir='/non/existent/dir',
            smtp_port=587,
            username='user',
            password='pass',
            subject=None,
            body=None,
            no_tls=False
        )
        mock_parse_args.return_value = mock_args

        # No PDF found
        mock_find_pdf.return_value = None

        # Run main function
        result = main()

        # Verify exit code indicates failure
        self.assertEqual(result, 1)

    @patch('argparse.ArgumentParser.parse_args')
    def test_main_missing_required_fields(self, mock_parse_args):
        """Test main function with missing required configuration."""
        # Set up mocks with missing required fields
        mock_args = argparse.Namespace(
            config=None,
            use_env=False,
            recipient=None,  # Missing required field
            sender='sender@example.com',
            smtp_server='smtp.example.com',
            pdf_dir=self.pdf_dir,
            smtp_port=587,
            username='user',
            password='pass',
            subject=None,
            body=None,
            no_tls=False
        )
        mock_parse_args.return_value = mock_args

        # Run main function
        result = main()

        # Verify exit code indicates failure
        self.assertEqual(result, 1)

if __name__ == '__main__':
    unittest.main()
