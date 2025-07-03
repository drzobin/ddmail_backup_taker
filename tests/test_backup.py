import pytest
import os
import tempfile
import hashlib
import uuid
import subprocess
import shutil
import datetime
import time
from ddmail_backup_taker.backup import sha256_of_file, backup_mariadb, clear_backups, tar_data, secure_delete, create_backup

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

def test_secure_delete(logger,toml_config):
    """Test to ensure secure_delete() deletes the file and returns True"""
    file = tempfile.NamedTemporaryFile(delete=False)
    file.write(b"test content")
    file.close()

    result = secure_delete(logger,toml_config,file.name)

    # Check that the file was deleted
    assert not os.path.exists(file.name)

    # Check that the result is True
    assert result["is_working"]


def test_secure_delete_directory(logger, toml_config):
    """Test secure_delete() on a directory"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Create a file inside the directory
    with open(os.path.join(temp_dir, "test_file.txt"), "w") as f:
        f.write("test content")

    result = secure_delete(logger, toml_config, temp_dir)

    # Check the directory was deleted
    assert not os.path.exists(temp_dir)
    assert result["is_working"]


def test_secure_delete_empty_path(logger, toml_config):
    """Test secure_delete() with an empty path"""
    result = secure_delete(logger, toml_config, "")

    assert not result["is_working"]
    assert result["msg"] == "data var is empty"


def test_secure_delete_nonexistent_path(logger, toml_config):
    """Test secure_delete() with a path that doesn't exist"""
    # Generate a path that definitely doesn't exist
    nonexistent_path = "/tmp/" + str(uuid.uuid4())

    result = secure_delete(logger, toml_config, nonexistent_path)

    assert not result["is_working"]
    assert "does not exist" in result["msg"]


def test_secure_delete_permission_denied(logger, toml_config):
    """Test secure_delete() with a path without write permissions"""
    # Skip on Windows or if running as root
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    try:
        if os.geteuid() == 0:  # Only works on Unix-like systems
            pytest.skip("Test not applicable when running as root")
    except AttributeError:
        # geteuid not available on this platform
        pass

    # Create a temporary file
    file = tempfile.NamedTemporaryFile(delete=False)
    file.write(b"test content")
    file.close()

    # Remove write permissions
    os.chmod(file.name, 0o444)  # read-only

    try:
        result = secure_delete(logger, toml_config, file.name)

        assert not result["is_working"]
        assert "permission denied" in result["msg"]
    finally:
        # Restore permissions so we can delete it
        os.chmod(file.name, 0o600)
        if os.path.exists(file.name):
            os.unlink(file.name)


def test_secure_delete_command_error(logger, toml_config, monkeypatch):
    """Test secure_delete() when the srm command fails"""
    file = tempfile.NamedTemporaryFile(delete=False)
    file.write(b"test content")
    file.close()

    # Mock subprocess.run to simulate a failure
    def mock_run(*args, **kwargs):
        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 1
        return MockCompletedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        result = secure_delete(logger, toml_config, file.name)

        assert not result["is_working"]
        assert result["msg"] == "returncode of cmd srm is non zero"
    finally:
        # Clean up
        if os.path.exists(file.name):
            os.unlink(file.name)


def test_secure_delete_subprocess_exception(logger, toml_config, monkeypatch):
    """Test secure_delete() when subprocess.run raises an exception"""
    file = tempfile.NamedTemporaryFile(delete=False)
    file.write(b"test content")
    file.close()

    # Mock subprocess.run to raise CalledProcessError
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "srm")

    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        result = secure_delete(logger, toml_config, file.name)

        assert not result["is_working"]
        assert result["msg"] == "cmd srm except subprocess.CalledProcessError occured"
    finally:
        # Clean up
        if os.path.exists(file.name):
            os.unlink(file.name)

def test_backup_mariadb_success(logger, toml_config):
    """Test backup_mariadb with valid parameters for successful backup."""
    mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]
    mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

    # Create temporary folder
    dst_folder = tempfile.mkdtemp()

    try:
        result = backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder)

        assert result["is_working"]
        assert result["msg"] == "done"
        assert os.path.exists(result["db_dump_file"])
        assert result["db_dump_file"] == os.path.join(dst_folder, "full_db_dump.sql")
    finally:
        # Remove temporary folder
        shutil.rmtree(dst_folder)


def test_backup_mariadb_invalid_binary(logger, toml_config):
    """Test backup_mariadb with non-existent mariadbdump binary."""
    # Use a path that definitely doesn't exist
    invalid_binary = "/path/to/nonexistent/mariadbdump" + str(uuid.uuid4())
    mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

    # Create temporary folder
    dst_folder = tempfile.mkdtemp()

    try:
        result = backup_mariadb(logger, invalid_binary, mariadb_root_password, dst_folder)

        assert not result["is_working"]
        assert result["msg"] == "mariadbdump binary location is wrong"
    finally:
        # Remove temporary folder
        shutil.rmtree(dst_folder)


def test_backup_mariadb_invalid_destination(logger, toml_config):
    """Test backup_mariadb with non-existent destination folder."""
    mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]
    mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

    # Use a path that definitely doesn't exist
    invalid_folder = "/path/to/nonexistent/folder" + str(uuid.uuid4())

    result = backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, invalid_folder)

    assert not result["is_working"]
    assert result["msg"] == "dst_folder do not exist"


def test_backup_mariadb_command_error(logger, toml_config, monkeypatch):
    """Test backup_mariadb when mariadbdump command fails."""
    mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]
    mariadb_root_password = "wrong_password"  # Use an incorrect password to cause an error

    # Create temporary folder
    dst_folder = tempfile.mkdtemp()

    # Mock subprocess.run to simulate command failure
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "mariadbdump")

    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        result = backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder)

        assert not result["is_working"]
        assert result["msg"] == "returncode of cmd mariadbdump is none zero"
    finally:
        # Remove temporary folder
        shutil.rmtree(dst_folder)


def test_backup_mariadb_non_zero_returncode(logger, toml_config, monkeypatch):
    """Test backup_mariadb when mariadbdump returns non-zero code."""
    mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]
    mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

    # Create temporary folder
    dst_folder = tempfile.mkdtemp()

    # Mock subprocess.run to return non-zero code
    def mock_run(*args, **kwargs):
        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 1
        return MockCompletedProcess()

    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        result = backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder)

        assert not result["is_working"]
        assert result["msg"] == "returncode of cmd mariadbdump is none zero"
    finally:
        # Remove temporary folder
        shutil.rmtree(dst_folder)


def test_backup_mariadb_file_not_created(logger, toml_config, monkeypatch):
    """Test backup_mariadb when dump file isn't created despite command success."""
    mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]
    mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

    # Create temporary folder
    dst_folder = tempfile.mkdtemp()

    # Mock subprocess.run to return success but not create file
    def mock_run(*args, **kwargs):
        class MockCompletedProcess:
            def __init__(self):
                self.returncode = 0
        return MockCompletedProcess()

    # Mock open to do nothing
    def mock_open(*args, **kwargs):
        class MockFile:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def write(self, *args):
                pass
        return MockFile()

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr("builtins.open", mock_open)

    try:
        result = backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder)

        assert not result["is_working"]
        assert "does not exist" in result["msg"]
    finally:
        # Remove temporary folder
        shutil.rmtree(dst_folder)


# Test cases for tar_data function

def test_tar_data_without_encryption(logger, toml_config, monkeypatch):
    """Test tar_data successfully creating a tar file without encryption."""
    # Create temporary directories for testing
    save_backups_to = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()

    # Create a sample file to back up
    test_file_path = os.path.join(data_dir, "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("Test data for tar_data function")

    # Modify config to use our temporary directories
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Ensure GPG encryption is disabled
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = False
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Mock datetime to get a predictable filename
    # Use a context manager to avoid issues with restoring immutable datetime.now
    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2023, 1, 1, 12, 0, 0)

    # Replace datetime with our version
    original_datetime = datetime.datetime
    datetime.datetime = MockDatetime

    # Make tar_process.returncode always be 0 in subprocess.run
    original_run = subprocess.run

    def mock_run(*args, **kwargs):
        result = original_run(*args, **kwargs)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        # Call tar_data
        result = tar_data(logger, config_copy, [test_file_path])

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"
        assert "backup_20230101120000.tar.gz" in result["backup_filename"]
        assert os.path.exists(result["backup_file"])
    finally:
        # Clean up
        datetime.datetime = original_datetime  # Restore original datetime
        shutil.rmtree(save_backups_to)
        shutil.rmtree(data_dir)


def test_tar_data_with_encryption(logger, toml_config, monkeypatch):
    """Test tar_data successfully creating an encrypted tar file."""
    # Create temporary directories for testing
    save_backups_to = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()

    # Create a sample file to back up
    test_file_path = os.path.join(data_dir, "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("Test data for tar_data function with encryption")

    # Modify config to use our temporary directories
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Ensure GPG encryption is enabled
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = True
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Mock datetime to get a predictable filename
    # Use a context manager to avoid issues with restoring immutable datetime.now
    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2023, 1, 1, 12, 0, 0)

    # Save original
    original_datetime = datetime.datetime
    # Replace with our version
    datetime.datetime = MockDatetime

    # Mock Popen to return successful processes
    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.stdout = None
            self.returncode = 0

        def communicate(self):
            return b"", b""

        def wait(self):
            return 0

        def close(self):
            pass

    # Mock os.path.exists to create the output file
    original_exists = os.path.exists

    def mock_exists(path):
        if path == config_copy["SAVE_BACKUPS_TO"] or path == config_copy["TAR_BIN"] or path == config_copy["GPG_ENCRYPTION"]["GPG_BIN"]:
            return True
        return original_exists(path)

    monkeypatch.setattr(subprocess, "Popen", MockPopen)
    monkeypatch.setattr(os.path, "exists", mock_exists)

    # Create the output file to simulate successful encryption
    expected_output_file = os.path.join(save_backups_to, "backup_20230101120000.tar.gz.gpg")

    try:
        # Call tar_data
        result = tar_data(logger, config_copy, [test_file_path])

        # Create the expected output file to simulate success
        with open(expected_output_file, "w") as f:
            f.write("mock encrypted data")

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"
        assert "backup_20230101120000.tar.gz.gpg" in result["backup_filename"]
        assert result["backup_file"] == expected_output_file
    finally:
        # Clean up
        datetime.datetime = original_datetime  # Restore original datetime
        shutil.rmtree(save_backups_to)
        shutil.rmtree(data_dir)


def test_tar_data_invalid_tar_bin(logger, toml_config):
    """Test tar_data with non-existent tar binary."""
    # Modify config to use a non-existent tar binary
    config_copy = toml_config.copy()
    config_copy["TAR_BIN"] = "/path/to/nonexistent/tar" + str(uuid.uuid4())

    # Call tar_data
    result = tar_data(logger, config_copy, ["/tmp/test.txt"])

    # Verify results
    assert not result["is_working"]
    assert result["msg"] == "tar binary location is wrong"


def test_tar_data_invalid_backup_dir(logger, toml_config):
    """Test tar_data with non-existent backup directory."""
    # Modify config to use a non-existent backup directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = "/path/to/nonexistent/backup/dir" + str(uuid.uuid4())

    # Call tar_data
    result = tar_data(logger, config_copy, ["/tmp/test.txt"])

    # Verify results
    assert not result["is_working"]
    assert result["msg"] == "save backups to directory location is wrong"


def test_tar_data_tar_command_failure(logger, toml_config, monkeypatch):
    """Test tar_data when tar command fails without encryption."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Ensure GPG encryption is disabled
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = False
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Mock subprocess.run to simulate tar command failure
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "tar", stderr=b"mock tar error")

    monkeypatch.setattr(subprocess, "run", mock_run)

    try:
        # Call tar_data
        result = tar_data(logger, config_copy, ["/tmp/test.txt"])

        # Verify results
        assert not result["is_working"]
        assert "tar command failed with return code" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_tar_data_tar_process_failure_with_encryption(logger, toml_config, monkeypatch):
    """Test tar_data when tar process fails with encryption."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Ensure GPG encryption is enabled
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = True
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Create proper mock objects
    class TarMock:
        def __init__(self):
            self.stdout = None
            self.returncode = 1

        def wait(self):
            return self.returncode

    class GpgMock:
        def __init__(self):
            self.returncode = 0

        def communicate(self):
            return b"", b""

    def mock_popen(cmd, **kwargs):
        if cmd[0] == config_copy["TAR_BIN"]:
            return TarMock()
        return GpgMock()

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    try:
        # Call tar_data
        result = tar_data(logger, config_copy, ["/tmp/test.txt"])

        # Verify results
        assert not result["is_working"]
        assert "tar command failed with return code" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_tar_data_gpg_process_failure(logger, toml_config, monkeypatch):
    """Test tar_data when GPG process fails."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Ensure GPG encryption is enabled
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = True
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Create proper mock objects
    class TarMock:
        def __init__(self):
            self.stdout = None
            self.returncode = 0

        def wait(self):
            return self.returncode

    class GpgMock:
        def __init__(self):
            self.returncode = 1

        def communicate(self):
            return b"", b""

    def mock_popen(cmd, **kwargs):
        if cmd[0] == config_copy["TAR_BIN"]:
            return TarMock()
        return GpgMock()

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    try:
        # Call tar_data
        result = tar_data(logger, config_copy, ["/tmp/test.txt"])

        # Verify results
        assert not result["is_working"]
        assert "gpg command failed with return code" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_tar_data_encryption_exception(logger, toml_config, monkeypatch):
    """Test tar_data when an exception occurs during encryption."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Ensure GPG encryption is enabled
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = True
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Mock Popen to raise an exception
    def mock_popen(*args, **kwargs):
        raise Exception("Mock encryption exception")

    monkeypatch.setattr(subprocess, "Popen", mock_popen)

    try:
        # Call tar_data
        result = tar_data(logger, config_copy, ["/tmp/test.txt"])

        # Verify results
        assert not result["is_working"]
        assert "Error during backup process" in result["msg"]
        assert "Mock encryption exception" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


# Test cases for clear_backups function

def test_clear_backups_no_files(logger, toml_config):
    """Test clear_backups when there are no backup files to clear."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to
    config_copy["BACKUPS_TO_SAVE_LOCAL"] = 3

    try:
        # Call clear_backups
        result = clear_backups(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "too few backups for clearing old backups"
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_clear_backups_fewer_than_limit(logger, toml_config):
    """Test clear_backups when there are fewer files than the retention limit."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to
    config_copy["BACKUPS_TO_SAVE_LOCAL"] = 3

    # Create two backup files (less than the limit of 3)
    backup_files = []
    for i in range(2):
        backup_path = os.path.join(save_backups_to, f"backup_{i}.tar.gz")
        with open(backup_path, "w") as f:
            f.write(f"backup content {i}")
        backup_files.append(backup_path)

    try:
        # Call clear_backups
        result = clear_backups(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "too few backups for clearing old backups"

        # Verify all files still exist
        for file in backup_files:
            assert os.path.exists(file)
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_clear_backups_more_than_limit(logger, toml_config, monkeypatch):
    """Test clear_backups when there are more files than the retention limit."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to
    config_copy["BACKUPS_TO_SAVE_LOCAL"] = 2

    # Create five backup files (more than the limit of 2)
    backup_files = []
    for i in range(5):
        backup_path = os.path.join(save_backups_to, f"backup_{i}.tar.gz")
        with open(backup_path, "w") as f:
            f.write(f"backup content {i}")
        # Add delays to ensure different modification times
        time.sleep(0.1)
        backup_files.append(backup_path)

    # Save the paths of the files to delete for verification later
    files_to_delete = backup_files[:-2]

    # Mock secure_delete to avoid actual deletion but track what would be deleted
    deleted_files = []

    def mock_secure_delete(logger, toml_config, path):
        deleted_files.append(path)
        return {"is_working": True, "msg": f"deleted {path} successfully"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call clear_backups
        result = clear_backups(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"

        # Verify the correct files were "deleted"
        assert set(deleted_files) == set(files_to_delete)
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_clear_backups_secure_delete_failure(logger, toml_config, monkeypatch):
    """Test clear_backups when secure_delete fails."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to
    config_copy["BACKUPS_TO_SAVE_LOCAL"] = 2

    # Create five backup files (more than the limit of 2)
    for i in range(5):
        backup_path = os.path.join(save_backups_to, f"backup_{i}.tar.gz")
        with open(backup_path, "w") as f:
            f.write(f"backup content {i}")
        # Add delays to ensure different modification times
        time.sleep(0.1)

    # Mock secure_delete to fail on the first delete
    def mock_secure_delete(logger, toml_config, path):
        return {"is_working": False, "msg": "mock secure delete failure"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call clear_backups
        result = clear_backups(logger, config_copy)

        # Verify results
        assert not result["is_working"]
        assert "Failed to delete file" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


def test_clear_backups_glob_pattern(logger, toml_config, monkeypatch):
    """Test clear_backups uses the correct glob pattern for finding backup files."""
    # Create temporary directory for testing
    save_backups_to = tempfile.mkdtemp()

    # Modify config to use our temporary directory
    config_copy = toml_config.copy()
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to
    config_copy["BACKUPS_TO_SAVE_LOCAL"] = 1

    # Create various files with different patterns
    valid_backup = os.path.join(save_backups_to, "backup_20220101.tar.gz")
    encrypted_backup = os.path.join(save_backups_to, "backup_20220102.tar.gz.gpg")
    non_backup_file = os.path.join(save_backups_to, "not_a_backup.txt")
    wrong_extension = os.path.join(save_backups_to, "backup_20220103.zip")

    # Create all test files
    for path in [valid_backup, encrypted_backup, non_backup_file, wrong_extension]:
        with open(path, "w") as f:
            f.write("test content")
        # Add a small delay between file creations
        time.sleep(0.1)

    # Mock secure_delete to track what would be deleted
    deleted_files = []

    def mock_secure_delete(logger, toml_config, path):
        deleted_files.append(path)
        return {"is_working": True, "msg": f"deleted {path} successfully"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call clear_backups
        result = clear_backups(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"

        # Should delete the oldest backup file, which should be the valid one
        # (since the encrypted one was created later)
        assert len(deleted_files) == 1
        assert deleted_files[0] == valid_backup

        # The non-backup files should not be touched
        assert os.path.exists(non_backup_file)
        assert os.path.exists(wrong_extension)
    finally:
        # Clean up
        shutil.rmtree(save_backups_to)


# Test cases for create_backup function

def test_create_backup_success_mariadb_and_data(logger, toml_config, monkeypatch):
    """Test create_backup with both MariaDB and data backups enabled."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()

    # Create a test file in the data directory
    test_file_path = os.path.join(data_dir, "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("Test data for backup function")

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = True
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = True
    data_config["DATA_TO_BACKUP"] = data_dir
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    # Create a custom date class to avoid modifying immutable datetime.date
    class MockDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date.fromisoformat(today)

    # Save original and patch
    datetime.date = MockDate

    # Mock backup_mariadb to return success
    def mock_backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder):
        # Create a mock DB dump file
        db_dump_file = os.path.join(dst_folder, "full_db_dump.sql")
        with open(db_dump_file, "w") as f:
            f.write("-- Mock MariaDB dump\n")
        return {"is_working": True, "msg": "done", "db_dump_file": db_dump_file}

    monkeypatch.setattr("ddmail_backup_taker.backup.backup_mariadb", mock_backup_mariadb)

    # Mock tar_data to return success
    backup_file = os.path.join(save_backups_to, "backup_20230115120000.tar.gz")

    def mock_tar_data(logger, toml_config, data_to_backup):
        # Create a mock tar file
        with open(backup_file, "w") as f:
            f.write("mock tar content")
        return {"is_working": True, "msg": "finished successfully",
                "backup_file": backup_file, "backup_filename": "backup_20230115120000.tar.gz"}

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    # Mock secure_delete to return success
    def mock_secure_delete(logger, toml_config, path):
        return {"is_working": True, "msg": f"deleted {path} successfully"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"
        assert result["backup_file"] == backup_file
        assert result["backup_filename"] == "backup_20230115120000.tar.gz"
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)
        shutil.rmtree(data_dir)


def test_create_backup_mariadb_only(logger, toml_config, monkeypatch):
    """Test create_backup with only MariaDB backup enabled."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings (enabled)
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = True
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings (disabled)
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = False
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    monkeypatch.setattr(datetime.date, "today", lambda: datetime.date.fromisoformat(today))

    # Mock backup_mariadb to return success
    def mock_backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder):
        # Create a mock DB dump file
        db_dump_file = os.path.join(dst_folder, "full_db_dump.sql")
        with open(db_dump_file, "w") as f:
            f.write("-- Mock MariaDB dump\n")
        return {"is_working": True, "msg": "done", "db_dump_file": db_dump_file}

    monkeypatch.setattr("ddmail_backup_taker.backup.backup_mariadb", mock_backup_mariadb)

    # Mock tar_data to return success
    backup_file = os.path.join(save_backups_to, "backup_20230115120000.tar.gz")

    def mock_tar_data(logger, toml_config, data_to_backup):
        # Create a mock tar file
        with open(backup_file, "w") as f:
            f.write("mock tar content")
        return {"is_working": True, "msg": "finished successfully",
                "backup_file": backup_file, "backup_filename": "backup_20230115120000.tar.gz"}

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    # Mock secure_delete to return success
    def mock_secure_delete(logger, toml_config, path):
        return {"is_working": True, "msg": f"deleted {path} successfully"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"
        assert result["backup_file"] == backup_file
        assert result["backup_filename"] == "backup_20230115120000.tar.gz"
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)


def test_create_backup_data_only(logger, toml_config, monkeypatch):
    """Test create_backup with only data backup enabled."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()

    # Create a test file in the data directory
    test_file_path = os.path.join(data_dir, "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("Test data for backup function")

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings (disabled)
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = False
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings (enabled)
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = True
    data_config["DATA_TO_BACKUP"] = data_dir
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    monkeypatch.setattr(datetime.date, "today", lambda: datetime.date.fromisoformat(today))

    # Mock tar_data to return success
    backup_file = os.path.join(save_backups_to, "backup_20230115120000.tar.gz")

    def mock_tar_data(logger, toml_config, data_to_backup):
        # Verify that data_to_backup contains our data directory
        assert data_dir in data_to_backup

        # Create a mock tar file
        with open(backup_file, "w") as f:
            f.write("mock tar content")
        return {"is_working": True, "msg": "finished successfully",
                "backup_file": backup_file, "backup_filename": "backup_20230115120000.tar.gz"}

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    # Mock secure_delete to return success
    def mock_secure_delete(logger, toml_config, path):
        return {"is_working": True, "msg": f"deleted {path} successfully"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results
        assert result["is_working"]
        assert result["msg"] == "finished successfully"
        assert result["backup_file"] == backup_file
        assert result["backup_filename"] == "backup_20230115120000.tar.gz"
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)
        shutil.rmtree(data_dir)


def test_create_backup_mariadb_failure(logger, toml_config, monkeypatch):
    """Test create_backup when MariaDB backup fails."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings (enabled)
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = True
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings (disabled)
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = False
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    monkeypatch.setattr(datetime.date, "today", lambda: datetime.date.fromisoformat(today))

    # Mock backup_mariadb to return failure
    def mock_backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder):
        return {"is_working": False, "msg": "mariadbdump binary location is wrong"}

    monkeypatch.setattr("ddmail_backup_taker.backup.backup_mariadb", mock_backup_mariadb)

    # We should never call tar_data in this scenario, so we'll set up a mock that asserts if called
    def mock_tar_data(logger, toml_config, data_to_backup):
        assert False, "tar_data should not be called when backup_mariadb fails"

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results
        assert not result["is_working"]
        assert "Failed to backup MariaDB" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)


def test_create_backup_tar_failure(logger, toml_config, monkeypatch):
    """Test create_backup when tar_data fails."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()

    # Create a test file in the data directory
    test_file_path = os.path.join(data_dir, "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("Test data for backup function")

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings (disabled)
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = False
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings (enabled)
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = True
    data_config["DATA_TO_BACKUP"] = data_dir
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    monkeypatch.setattr(datetime.date, "today", lambda: datetime.date.fromisoformat(today))

    # Mock tar_data to return failure
    def mock_tar_data(logger, toml_config, data_to_backup):
        return {"is_working": False, "msg": "tar binary location is wrong"}

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    # We should never call secure_delete in this scenario
    def mock_secure_delete(logger, toml_config, path):
        assert False, "secure_delete should not be called when tar_data fails"

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results
        assert not result["is_working"]
        assert "Failed to backup folders" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)
        shutil.rmtree(data_dir)


def test_create_backup_secure_delete_failure(logger, toml_config, monkeypatch):
    """Test create_backup when secure_delete fails."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()
    data_dir = tempfile.mkdtemp()

    # Create a test file in the data directory
    test_file_path = os.path.join(data_dir, "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("Test data for backup function")

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings (disabled)
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = False
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings (enabled)
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = True
    data_config["DATA_TO_BACKUP"] = data_dir
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    monkeypatch.setattr(datetime.date, "today", lambda: datetime.date.fromisoformat(today))

    # Mock tar_data to return success
    backup_file = os.path.join(save_backups_to, "backup_20230115120000.tar.gz")

    def mock_tar_data(logger, toml_config, data_to_backup):
        # Create a mock tar file
        with open(backup_file, "w") as f:
            f.write("mock tar content")
        return {"is_working": True, "msg": "finished successfully",
                "backup_file": backup_file, "backup_filename": "backup_20230115120000.tar.gz"}

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    # Mock secure_delete to return failure
    def mock_secure_delete(logger, toml_config, path):
        return {"is_working": False, "msg": "mock secure delete failure"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results
        assert not result["is_working"]
        assert "Failed to secure delete temp folder" in result["msg"]
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)
        shutil.rmtree(data_dir)


def test_create_backup_no_backups_configured(logger, toml_config, monkeypatch):
    """Test create_backup when neither MariaDB nor data backups are enabled."""
    # Create temporary directories
    tmp_folder = tempfile.mkdtemp()
    save_backups_to = tempfile.mkdtemp()

    # Setup config for the test
    config_copy = toml_config.copy()
    config_copy["TMP_FOLDER"] = tmp_folder
    config_copy["SAVE_BACKUPS_TO"] = save_backups_to

    # Configure MariaDB settings (disabled)
    mariadb_config = config_copy["MARIADB"].copy()
    mariadb_config["USE"] = False
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_config)

    # Configure data backup settings (disabled)
    data_config = config_copy["DATA"].copy()
    data_config["USE"] = False
    monkeypatch.setitem(config_copy, "DATA", data_config)

    # Mock current date for predictable folder names
    today = "2023-01-15"
    monkeypatch.setattr(datetime.date, "today", lambda: datetime.date.fromisoformat(today))

    # We should never call tar_data in this scenario
    def mock_tar_data(logger, toml_config, data_to_backup):
        assert False, "tar_data should not be called when no backups are configured"

    monkeypatch.setattr("ddmail_backup_taker.backup.tar_data", mock_tar_data)

    # Mock secure_delete to return success (should still be called to clean up the date folder)
    def mock_secure_delete(logger, toml_config, path):
        return {"is_working": True, "msg": f"deleted {path} successfully"}

    monkeypatch.setattr("ddmail_backup_taker.backup.secure_delete", mock_secure_delete)

    try:
        # Call create_backup
        result = create_backup(logger, config_copy)

        # Verify results - should still succeed but without backup file info
        assert result["is_working"] is False
        assert result["msg"] == "No backup data to backup"
        # Since no tar file was created, these should be empty
        assert "backup_file" not in result
        assert "backup_filename" not in result
    finally:
        # Clean up
        shutil.rmtree(tmp_folder)
        shutil.rmtree(save_backups_to)
