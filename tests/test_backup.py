import pytest
import logging
import os
import tempfile
import hashlib
from ddmail_backup_taker.backup import sha256_of_file, backup_mariadb, clear_backups, create_backup, tar_data, send_to_backup_receiver, secure_delete

@pytest.fixture
def testfile():
    path = "tests/test_file.txt"
    name = "test_file.txt"
    sha256checksum = "4677942dfa3e74b5dea7484661a2485bb73ba422eb72d311fdb39372c019c615"

    # Read testfile from disc.
    f = open(path, "r")
    data = f.read()

    return {"path": path, "name": name, "sha256checksum": sha256checksum, "data": data}


@pytest.fixture
def logger():
    # Setup logging.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "{asctime} testing ddmail_backup_taker {levelname} in {module} {funcName} {lineno}: {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def test_sha256_of_file_create_sha256(logger,testfile):
    """Test sha256_of_file() checksum is correct."""
    sha256 = sha256_of_file(logger, testfile["path"])

    assert sha256["is_working"] is True
    assert sha256["checksum"] == testfile["sha256checksum"]


def test_sha256_of_no_file(logger):
    """Test sha256_of_file() with a file that does not exist."""
    file_path = "/tmp/nofile"
    sha256 = sha256_of_file(logger,file_path)

    assert sha256["is_working"] is False
    assert sha256["msg"] == "file does not exist"


def test_sha256_of_file_empty_str(logger):
    """Test sha256_of_file() with an empty string path."""
    sha256 = sha256_of_file(logger,"")

    assert sha256["is_working"] is False
    assert sha256["msg"] == "file does not exist"


def test_sha256_of_empty_file(logger):
    """Test sha256_of_file() with an empty file."""
    # Create a temporary empty file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        # Compute expected checksum for empty file
        expected_checksum = hashlib.sha256(b"").hexdigest()
        
        # Test the function
        sha256 = sha256_of_file(logger, temp_path)
        
        assert sha256["is_working"] is True
        assert sha256["checksum"] == expected_checksum
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_sha256_of_binary_file(logger):
    """Test sha256_of_file() with a binary file."""
    # Create a temporary binary file
    binary_data = bytes([0x00, 0xFF, 0xAA, 0x55, 0x12, 0x34, 0x56, 0x78])
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
        temp_file.write(binary_data)
        temp_path = temp_file.name

    try:
        # Compute expected checksum
        expected_checksum = hashlib.sha256(binary_data).hexdigest()
        
        # Test the function
        sha256 = sha256_of_file(logger, temp_path)
        
        assert sha256["is_working"] is True
        assert sha256["checksum"] == expected_checksum
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_sha256_of_large_file(logger):
    """Test sha256_of_file() with a file larger than the buffer size (65536 bytes)."""
    # Create a temporary large file (100KB)
    large_data = b'x' * 100000
    with tempfile.NamedTemporaryFile(delete=False, mode='wb') as temp_file:
        temp_file.write(large_data)
        temp_path = temp_file.name

    try:
        # Compute expected checksum
        expected_checksum = hashlib.sha256(large_data).hexdigest()
        
        # Test the function
        sha256 = sha256_of_file(logger, temp_path)
        
        assert sha256["is_working"] is True
        assert sha256["checksum"] == expected_checksum
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_sha256_of_unreadable_file(logger):
    """Test sha256_of_file() with a file that cannot be read due to permissions."""
    # This test may not work on all platforms/environments where the test is run with elevated privileges
    # Skip on Windows or if running as root/admin
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")
    
    # Skip if running as root on Unix-like systems
    try:
        if os.geteuid() == 0:  # Only works on Unix-like systems
            pytest.skip("Test not applicable when running as root")
    except AttributeError:
        # geteuid not available on this platform
        pass

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"test content")
        temp_path = temp_file.name
    
    try:
        # Remove read permissions
        os.chmod(temp_path, 0o000)
        
        # The current implementation of sha256_of_file doesn't handle permission errors
        # It will raise a PermissionError when it tries to open the file
        with pytest.raises(PermissionError):
            sha256_of_file(logger, temp_path)
    finally:
        # Restore permissions so we can delete it
        os.chmod(temp_path, 0o600)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
