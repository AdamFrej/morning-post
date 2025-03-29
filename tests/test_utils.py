import unittest
import time
import signal
from unittest.mock import patch, Mock

from morning.utils import time_limit, TimeoutException

class TestTimeLimit(unittest.TestCase):
    def test_operation_within_time_limit(self):
        """Test operations that complete within the time limit."""
        # Using a short operation that should complete quickly
        with time_limit(5):
            result = 1 + 1
            self.assertEqual(result, 2)

    def test_operation_exceeds_time_limit(self):
        """Test operations that exceed the time limit."""
        # Should raise TimeoutException after 1 second
        with self.assertRaises(TimeoutException):
            with time_limit(1):
                time.sleep(3)  # Sleep longer than the timeout

    def test_nested_time_limits(self):
        """Test nested time_limit context managers."""
        # Outer limit is longer than inner
        with time_limit(5):
            # This should timeout first
            with self.assertRaises(TimeoutException):
                with time_limit(1):
                    time.sleep(3)

            # This should run fine after inner timeout
            result = 2 + 2
            self.assertEqual(result, 4)

    def test_cleanup_after_timeout(self):
        """Test alarm is reset after timeout."""
        # First cause a timeout
        try:
            with time_limit(1):
                time.sleep(3)
        except TimeoutException:
            pass

        # Now try a longer operation that should succeed
        # If alarm wasn't reset, this would fail
        start_time = time.time()
        with time_limit(5):
            time.sleep(2)
        elapsed = time.time() - start_time

        # Verify sleep wasn't interrupted (should be ~2 seconds)
        self.assertTrue(1.5 < elapsed < 3)

    @patch('signal.signal')
    @patch('signal.alarm')
    def test_signal_handling(self, mock_alarm, mock_signal):
        """Test signal handling setup and cleanup."""
        # Run with time_limit
        with time_limit(10):
            pass

        # Verify signal was set up correctly
        mock_signal.assert_called_with(signal.SIGALRM, unittest.mock.ANY)

        # Verify alarm was set and then cleared
        mock_alarm.assert_any_call(10)  # Set timeout
        mock_alarm.assert_any_call(0)   # Clear timeout
