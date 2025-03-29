"""Utility functions for Morning Paper Generator."""
import logging
import signal
from contextlib import contextmanager

# Set up main logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure loggers for noisy libraries
for logger_name in ['fontTools', 'PIL', 'weasyprint', 'cssselect', 'cffi', 'html5lib']:
    package_logger = logging.getLogger(logger_name)
    package_logger.propagate = False  # Stop propagating to parent loggers
    package_logger.setLevel(logging.ERROR)

    # Add a null handler to prevent warnings about no handlers
    if not package_logger.handlers:
        package_logger.addHandler(logging.NullHandler())

class TimeoutException(Exception):
    """Exception raised when an operation times out."""
    pass

@contextmanager
def time_limit(seconds):
    """Context manager for timeout."""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
