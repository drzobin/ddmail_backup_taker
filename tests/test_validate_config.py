import os
import pytest
import uuid
import gnupg
from ddmail_backup_taker.validate_config import check_main_vars, check_data_vars, check_mariadb_vars, check_gpg_vars, check_backup_receiver_vars, check_config

def test_check_main_vars(logger,toml_config):
    """Test the check_main_vars function with valid configuration."""
    result = check_main_vars(logger,toml_config)

    assert result["is_working"]
    assert result["msg"] == "Configurations file main variable is valid."


def test_check_main_vars_save_backups_to_none(logger, toml_config, monkeypatch):
    """Test check_main_vars with SAVE_BACKUPS_TO set to None."""
    # Create a copy of the config to modify
    config_copy = toml_config.copy()
    # Set SAVE_BACKUPS_TO to None
    monkeypatch.setitem(config_copy, "SAVE_BACKUPS_TO", None)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config SAVE_BACKUPS_TO is None"


def test_check_main_vars_save_backups_to_empty(logger, toml_config, monkeypatch):
    """Test check_main_vars with SAVE_BACKUPS_TO set to empty string."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "SAVE_BACKUPS_TO", "")

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config SAVE_BACKUPS_TO is None"


def test_check_main_vars_save_backups_to_not_dir(logger, toml_config, monkeypatch):
    """Test check_main_vars with SAVE_BACKUPS_TO pointing to non-existent directory that can't be created."""
    config_copy = toml_config.copy()
    save_backups_path = config_copy["SAVE_BACKUPS_TO"]

    # Store the original function to avoid recursion
    original_isdir = os.path.isdir

    # Create a scenario where isdir is False and makedirs fails
    def mock_isdir(path):
        if path == save_backups_path:
            return False
        return original_isdir(path)

    def mock_makedirs(path, *args, **kwargs):
        if path == save_backups_path:
            # Don't actually raise the exception, just don't create the directory
            return

    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    monkeypatch.setattr(os, "makedirs", mock_makedirs)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config SAVE_BACKUPS_TO do not exist"


def test_check_main_vars_save_backups_to_not_writable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_main_vars with SAVE_BACKUPS_TO pointing to non-writable directory."""
    # Skip on Windows or if running as root
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    try:
        if os.geteuid() == 0:  # Only works on Unix-like systems
            pytest.skip("Test not applicable when running as root")
    except AttributeError:
        pass

    config_copy = toml_config.copy()
    # Create a temp directory
    test_dir = tmp_path / "test_backups"
    test_dir.mkdir()
    # Set permissions to read-only
    test_dir.chmod(0o500)  # r-x------

    monkeypatch.setitem(config_copy, "SAVE_BACKUPS_TO", str(test_dir))

    try:
        result = check_main_vars(logger, config_copy)

        assert not result["is_working"]
        assert result["msg"] == "config SAVE_BACKUPS_TO is not writable"
    finally:
        # Restore permissions so we can delete it
        test_dir.chmod(0o700)


def test_check_main_vars_tmp_folder_none(logger, toml_config, monkeypatch):
    """Test check_main_vars with TMP_FOLDER set to None."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "TMP_FOLDER", None)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config TMP_FOLDER is None"


def test_check_main_vars_tmp_folder_not_dir(logger, toml_config, monkeypatch):
    """Test check_main_vars with TMP_FOLDER pointing to non-existent directory that can't be created."""
    config_copy = toml_config.copy()
    tmp_folder_path = config_copy["TMP_FOLDER"]

    # Store the original function to avoid recursion
    original_isdir = os.path.isdir

    # Create a state where SAVE_BACKUPS_TO exists but TMP_FOLDER can't be created
    def mock_isdir(path):
        if path == tmp_folder_path:
            return False
        return original_isdir(path)

    def mock_makedirs(path, *args, **kwargs):
        if path == tmp_folder_path:
            # Don't actually raise an exception, just don't create the directory
            return

    # We need to patch os.path.isdir to pretend SAVE_BACKUPS_TO exists (or is created)
    # but TMP_FOLDER doesn't exist even after makedirs
    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    monkeypatch.setattr(os, "makedirs", mock_makedirs)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config TMP_FOLDER do not exist"


def test_check_main_vars_tmp_folder_not_writable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_main_vars with TMP_FOLDER pointing to non-writable directory."""
    # Skip on Windows or if running as root
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    try:
        if os.geteuid() == 0:  # Only works on Unix-like systems
            pytest.skip("Test not applicable when running as root")
    except AttributeError:
        pass

    config_copy = toml_config.copy()
    # Create a temp directory
    test_dir = tmp_path / "test_tmp"
    test_dir.mkdir()
    # Set permissions to read-only
    test_dir.chmod(0o500)  # r-x------

    monkeypatch.setitem(config_copy, "TMP_FOLDER", str(test_dir))

    try:
        result = check_main_vars(logger, config_copy)

        assert not result["is_working"]
        assert result["msg"] == "config TMP_FOLDER is not writable"
    finally:
        # Restore permissions so we can delete it
        test_dir.chmod(0o700)


def test_check_main_vars_tar_bin_none(logger, toml_config, monkeypatch):
    """Test check_main_vars with TAR_BIN set to None."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "TAR_BIN", None)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config TAR_BIN is None"


def test_check_main_vars_tar_bin_not_file(logger, toml_config, monkeypatch):
    """Test check_main_vars with TAR_BIN pointing to non-existent file."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "TAR_BIN", "/path/to/nonexistent/tar")

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config TAR_BIN do not exist"


def test_check_main_vars_tar_bin_not_executable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_main_vars with TAR_BIN pointing to non-executable file."""
    # Skip on Windows
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    config_copy = toml_config.copy()
    # Create a non-executable file
    test_file = tmp_path / "fake_tar"
    test_file.write_text("#!/bin/sh\necho 'fake tar'")
    test_file.chmod(0o600)  # rw-------

    monkeypatch.setitem(config_copy, "TAR_BIN", str(test_file))

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config TAR_BIN is not executable"


def test_check_main_vars_backups_to_save_local_not_int(logger, toml_config, monkeypatch):
    """Test check_main_vars with BACKUPS_TO_SAVE_LOCAL not an integer."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "BACKUPS_TO_SAVE_LOCAL", "3")

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUPS_TO_SAVE_LOCAL must be a positive integer"


def test_check_main_vars_backups_to_save_local_zero(logger, toml_config, monkeypatch):
    """Test check_main_vars with BACKUPS_TO_SAVE_LOCAL set to zero."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "BACKUPS_TO_SAVE_LOCAL", 0)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUPS_TO_SAVE_LOCAL must be a positive integer"


def test_check_main_vars_backups_to_save_local_negative(logger, toml_config, monkeypatch):
    """Test check_main_vars with BACKUPS_TO_SAVE_LOCAL set to negative value."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "BACKUPS_TO_SAVE_LOCAL", -1)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUPS_TO_SAVE_LOCAL must be a positive integer"


def test_check_main_vars_srm_bin_none(logger, toml_config, monkeypatch):
    """Test check_main_vars with SRM_BIN set to None."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "SRM_BIN", None)

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config SRM_BIN is None."


def test_check_main_vars_srm_bin_not_file(logger, toml_config, monkeypatch):
    """Test check_main_vars with SRM_BIN pointing to non-existent file."""
    config_copy = toml_config.copy()
    monkeypatch.setitem(config_copy, "SRM_BIN", "/path/to/nonexistent/srm")

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config SRM_BIN is not a file"


def test_check_main_vars_srm_bin_not_executable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_main_vars with SRM_BIN pointing to non-executable file."""
    # Skip on Windows
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    config_copy = toml_config.copy()
    # Create a non-executable file
    test_file = tmp_path / "fake_srm"
    test_file.write_text("#!/bin/sh\necho 'fake srm'")
    test_file.chmod(0o600)  # rw-------

    monkeypatch.setitem(config_copy, "SRM_BIN", str(test_file))

    result = check_main_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config SRM_BIN is not executable"


# Test cases for check_data_vars function

def test_check_data_vars_valid(logger, toml_config):
    """Test check_data_vars with valid configuration."""
    result = check_data_vars(logger, toml_config)

    assert result["is_working"]
    assert result["msg"] == "Configurations file DATA section variables is valid."


def test_check_data_vars_use_false(logger, toml_config, monkeypatch):
    """Test check_data_vars with DATA.USE set to False."""
    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    data_copy["USE"] = False
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    result = check_data_vars(logger, config_copy)

    assert result["is_working"]
    assert result["msg"] == "Configurations file DATA section variables is valid."


def test_check_data_vars_data_to_backup_not_string(logger, toml_config, monkeypatch):
    """Test check_data_vars with DATA.DATA_TO_BACKUP not a string."""
    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    data_copy["DATA_TO_BACKUP"] = ["path1", "path2"]  # List instead of string
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    result = check_data_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config DATA.DATA_TO_BACKUP must be a string"


def test_check_data_vars_nonexistent_path(logger, toml_config, monkeypatch):
    """Test check_data_vars with non-existent path in DATA.DATA_TO_BACKUP."""
    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    # Use a path that definitely doesn't exist
    nonexistent_path = "/path/that/definitely/does/not/exist/" + str(uuid.uuid4())
    data_copy["DATA_TO_BACKUP"] = nonexistent_path
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    # Store the original function to avoid recursion
    original_isdir = os.path.isdir
    original_isfile = os.path.isfile

    # Mock isdir and isfile to always return False for our nonexistent path
    def mock_isdir(path):
        if path == nonexistent_path:
            return False
        return original_isdir(path)

    def mock_isfile(path):
        if path == nonexistent_path:
            return False
        return original_isfile(path)

    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    monkeypatch.setattr(os.path, "isfile", mock_isfile)

    result = check_data_vars(logger, config_copy)

    assert not result["is_working"]
    assert f"config DATA.DATA_TO_BACKUP contains non-existent path: {nonexistent_path}" == result["msg"]


def test_check_data_vars_multiple_paths_one_nonexistent(logger, toml_config, monkeypatch, tmp_path):
    """Test check_data_vars with multiple paths, one of which doesn't exist."""
    # Create a temporary directory that does exist
    existing_dir = tmp_path / "existing_dir"
    existing_dir.mkdir()

    # Path that doesn't exist
    nonexistent_path = str(tmp_path / "nonexistent_dir")

    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    data_copy["DATA_TO_BACKUP"] = f"{existing_dir} {nonexistent_path}"
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    result = check_data_vars(logger, config_copy)

    assert not result["is_working"]
    assert f"config DATA.DATA_TO_BACKUP contains non-existent path: {nonexistent_path}" == result["msg"]


def test_check_data_vars_unreadable_path(logger, toml_config, monkeypatch, tmp_path):
    """Test check_data_vars with unreadable path in DATA.DATA_TO_BACKUP."""
    # Skip on Windows or if running as root
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    try:
        if os.geteuid() == 0:  # Only works on Unix-like systems
            pytest.skip("Test not applicable when running as root")
    except AttributeError:
        pass

    # Create a temporary directory with no read permissions
    unreadable_dir = tmp_path / "unreadable_dir"
    unreadable_dir.mkdir()
    unreadable_dir.chmod(0o000)  # No permissions

    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    data_copy["DATA_TO_BACKUP"] = str(unreadable_dir)
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    try:
        result = check_data_vars(logger, config_copy)

        assert not result["is_working"]
        assert f"config DATA.DATA_TO_BACKUP contains unreadable path: {unreadable_dir}" == result["msg"]
    finally:
        # Restore permissions so we can delete it
        unreadable_dir.chmod(0o700)


def test_check_data_vars_multiple_paths_one_unreadable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_data_vars with multiple paths, one of which is unreadable."""
    # Skip on Windows or if running as root
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    try:
        if os.geteuid() == 0:  # Only works on Unix-like systems
            pytest.skip("Test not applicable when running as root")
    except AttributeError:
        pass

    # Create a readable directory
    readable_dir = tmp_path / "readable_dir"
    readable_dir.mkdir()

    # Create an unreadable directory
    unreadable_dir = tmp_path / "unreadable_dir"
    unreadable_dir.mkdir()
    unreadable_dir.chmod(0o000)  # No permissions

    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    data_copy["DATA_TO_BACKUP"] = f"{readable_dir} {unreadable_dir}"
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    try:
        result = check_data_vars(logger, config_copy)

        assert not result["is_working"]
        assert f"config DATA.DATA_TO_BACKUP contains unreadable path: {unreadable_dir}" == result["msg"]
    finally:
        # Restore permissions so we can delete it
        unreadable_dir.chmod(0o700)


def test_check_data_vars_with_file(logger, toml_config, monkeypatch, tmp_path):
    """Test check_data_vars with a file in DATA.DATA_TO_BACKUP."""
    # Create a temporary file
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test content")

    config_copy = toml_config.copy()
    data_copy = config_copy["DATA"].copy()
    data_copy["DATA_TO_BACKUP"] = str(test_file)
    monkeypatch.setitem(config_copy, "DATA", data_copy)

    result = check_data_vars(logger, config_copy)

    assert result["is_working"]
    assert result["msg"] == "Configurations file DATA section variables is valid."


# Test cases for check_mariadb_vars function

def test_check_mariadb_vars_valid(logger, toml_config):
    """Test check_mariadb_vars with valid configuration."""
    result = check_mariadb_vars(logger, toml_config)

    assert result["is_working"]
    assert result["msg"] == "Configurations file MARIADB section variables is valid."


def test_check_mariadb_vars_use_false(logger, toml_config, monkeypatch):
    """Test check_mariadb_vars with MARIADB.USE set to False."""
    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    mariadb_copy["USE"] = False
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    result = check_mariadb_vars(logger, config_copy)

    assert result["is_working"]
    assert result["msg"] == "Configurations file MARIADB section variables is valid."


def test_check_mariadb_vars_mariadbdump_bin_none(logger, toml_config, monkeypatch):
    """Test check_mariadb_vars with MARIADBDUMP_BIN set to None."""
    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    mariadb_copy["MARIADBDUMP_BIN"] = None
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    result = check_mariadb_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config MARIADB.MARIADBDUMP_BIN must be a valid path"


def test_check_mariadb_vars_mariadbdump_bin_empty(logger, toml_config, monkeypatch):
    """Test check_mariadb_vars with MARIADBDUMP_BIN set to empty string."""
    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    mariadb_copy["MARIADBDUMP_BIN"] = ""
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    result = check_mariadb_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config MARIADB.MARIADBDUMP_BIN must be a valid path"


def test_check_mariadb_vars_mariadbdump_bin_not_file(logger, toml_config, monkeypatch):
    """Test check_mariadb_vars with MARIADBDUMP_BIN pointing to non-existent file."""
    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    nonexistent_path = "/path/to/nonexistent/mariadb-dump" + str(uuid.uuid4())
    mariadb_copy["MARIADBDUMP_BIN"] = nonexistent_path
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    # Store the original function to avoid recursion
    original_isfile = os.path.isfile

    # Mock isfile to return False for our nonexistent path
    def mock_isfile(path):
        if path == nonexistent_path:
            return False
        return original_isfile(path)

    monkeypatch.setattr(os.path, "isfile", mock_isfile)

    result = check_mariadb_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config MARIADB.MARIADBDUMP_BIN must be a valid path"


def test_check_mariadb_vars_mariadbdump_bin_not_executable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_mariadb_vars with MARIADBDUMP_BIN pointing to non-executable file."""
    # Skip on Windows
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    # Create a non-executable file
    test_file = tmp_path / "fake_mariadbdump"
    test_file.write_text("#!/bin/sh\necho 'fake mariadbdump'")
    test_file.chmod(0o600)  # rw-------

    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    mariadb_copy["MARIADBDUMP_BIN"] = str(test_file)
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    result = check_mariadb_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config MARIADB.MARIADBDUMP_BIN must be executable"


def test_check_mariadb_vars_root_password_none(logger, toml_config, monkeypatch, tmp_path):
    """Test check_mariadb_vars with ROOT_PASSWORD set to None."""
    # Create an executable file for mariadbdump
    test_file = tmp_path / "fake_mariadbdump"
    test_file.write_text("#!/bin/sh\necho 'fake mariadbdump'")
    test_file.chmod(0o700)  # rwx------

    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    mariadb_copy["MARIADBDUMP_BIN"] = str(test_file)
    mariadb_copy["ROOT_PASSWORD"] = None
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    result = check_mariadb_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config MARIADB.ROOT_PASSWORD must be a string"


def test_check_mariadb_vars_root_password_empty(logger, toml_config, monkeypatch, tmp_path):
    """Test check_mariadb_vars with ROOT_PASSWORD set to empty string."""
    # Create an executable file for mariadbdump
    test_file = tmp_path / "fake_mariadbdump"
    test_file.write_text("#!/bin/sh\necho 'fake mariadbdump'")
    test_file.chmod(0o700)  # rwx------

    config_copy = toml_config.copy()
    mariadb_copy = config_copy["MARIADB"].copy()
    mariadb_copy["MARIADBDUMP_BIN"] = str(test_file)
    mariadb_copy["ROOT_PASSWORD"] = ""
    monkeypatch.setitem(config_copy, "MARIADB", mariadb_copy)

    result = check_mariadb_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config MARIADB.ROOT_PASSWORD must be a string"


# Test cases for check_gpg_vars function

def test_check_gpg_vars_valid(logger, toml_config):
    """Test check_gpg_vars with valid configuration."""
    # This test assumes the config provided has valid GPG settings
    # If this test fails, you may need to adjust your test config
    result = check_gpg_vars(logger, toml_config)

    assert result["is_working"]
    assert result["msg"] == "Configurations file GPG section variables is valid."


def test_check_gpg_vars_use_false(logger, toml_config, monkeypatch):
    """Test check_gpg_vars with GPG_ENCRYPTION.USE set to False."""
    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["USE"] = False
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    result = check_gpg_vars(logger, config_copy)

    assert result["is_working"]
    assert result["msg"] == "Configurations file GPG section variables is valid."


def test_check_gpg_vars_gpg_bin_not_string(logger, toml_config, monkeypatch):
    """Test check_gpg_vars with GPG_BIN not a string."""
    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["GPG_BIN"] = 123  # Not a string
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    result = check_gpg_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config GPG_ENCRYPTION.GPG_BIN must be a string"


def test_check_gpg_vars_gpg_bin_not_file(logger, toml_config, monkeypatch):
    """Test check_gpg_vars with GPG_BIN pointing to non-existent file."""
    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    nonexistent_path = "/path/to/nonexistent/gpg" + str(uuid.uuid4())
    gpg_copy["GPG_BIN"] = nonexistent_path
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Store the original function to avoid recursion
    original_isfile = os.path.isfile

    # Mock isfile to return False for our nonexistent path
    def mock_isfile(path):
        if path == nonexistent_path:
            return False
        return original_isfile(path)

    monkeypatch.setattr(os.path, "isfile", mock_isfile)

    result = check_gpg_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config GPG_ENCRYPTION.GPG_BIN must be a valid path"


def test_check_gpg_vars_gpg_bin_not_executable(logger, toml_config, monkeypatch, tmp_path):
    """Test check_gpg_vars with GPG_BIN pointing to non-executable file."""
    # Skip on Windows
    if os.name == 'nt':
        pytest.skip("Test not applicable on Windows")

    # Create a non-executable file
    test_file = tmp_path / "fake_gpg"
    test_file.write_text("#!/bin/sh\necho 'fake gpg'")
    test_file.chmod(0o600)  # rw-------

    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["GPG_BIN"] = str(test_file)
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    result = check_gpg_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config GPG_ENCRYPTION.GPG_BIN must be executable"


def test_check_gpg_vars_pubkey_fingerprint_not_string(logger, toml_config, monkeypatch, tmp_path):
    """Test check_gpg_vars with PUBKEY_FINGERPRINT not a string."""
    # Create an executable file for gpg
    test_file = tmp_path / "fake_gpg"
    test_file.write_text("#!/bin/sh\necho 'fake gpg'")
    test_file.chmod(0o700)  # rwx------

    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["GPG_BIN"] = str(test_file)
    gpg_copy["PUBKEY_FINGERPRINT"] = 123  # Not a string
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    result = check_gpg_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config GPG_ENCRYPTION.PUBKEY_FINGERPRINT must be a string"


def test_check_gpg_vars_pubkey_fingerprint_invalid_format(logger, toml_config, monkeypatch, tmp_path):
    """Test check_gpg_vars with PUBKEY_FINGERPRINT in invalid format."""
    # Create an executable file for gpg
    test_file = tmp_path / "fake_gpg"
    test_file.write_text("#!/bin/sh\necho 'fake gpg'")
    test_file.chmod(0o700)  # rwx------

    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["GPG_BIN"] = str(test_file)
    gpg_copy["PUBKEY_FINGERPRINT"] = "invalid-fingerprint"  # Invalid format
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    result = check_gpg_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config GPG_ENCRYPTION.PUBKEY_FINGERPRINT must be a valid fingerprint"


def test_check_gpg_vars_pubkey_fingerprint_not_in_keystore(logger, toml_config, monkeypatch, tmp_path):
    """Test check_gpg_vars with PUBKEY_FINGERPRINT not in keystore."""
    # Create an executable file for gpg
    test_file = tmp_path / "fake_gpg"
    test_file.write_text("#!/bin/sh\necho 'fake gpg'")
    test_file.chmod(0o700)  # rwx------

    # Valid fingerprint format but not in keystore
    valid_fingerprint = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"

    config_copy = toml_config.copy()
    gpg_copy = config_copy["GPG_ENCRYPTION"].copy()
    gpg_copy["GPG_BIN"] = str(test_file)
    gpg_copy["PUBKEY_FINGERPRINT"] = valid_fingerprint
    monkeypatch.setitem(config_copy, "GPG_ENCRYPTION", gpg_copy)

    # Mock gnupg.GPG to return empty list for list_keys
    class MockGPG:
        def __init__(self, gpgbinary=None):
            self.encoding = None

        def list_keys(self, secret=False, keys=None):
            return []

    # Patch the gnupg.GPG class
    monkeypatch.setattr(gnupg, "GPG", MockGPG)

    result = check_gpg_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == f"config GPG_ENCRYPTION.PUBKEY_FINGERPRINT {valid_fingerprint} key is not in keystore"


# Test cases for check_backup_receiver_vars function

def test_check_backup_receiver_vars_valid(logger, toml_config):
    """Test check_backup_receiver_vars with valid configuration."""
    result = check_backup_receiver_vars(logger, toml_config)

    assert result["is_working"]
    assert result["msg"] == "Configurations file BACKUP_RECEIVER section variables is valid."


def test_check_backup_receiver_vars_use_false(logger, toml_config, monkeypatch):
    """Test check_backup_receiver_vars with BACKUP_RECEIVER.USE set to False."""
    config_copy = toml_config.copy()
    backup_receiver_copy = config_copy["BACKUP_RECEIVER"].copy()
    backup_receiver_copy["USE"] = False
    monkeypatch.setitem(config_copy, "BACKUP_RECEIVER", backup_receiver_copy)

    result = check_backup_receiver_vars(logger, config_copy)

    assert result["is_working"]
    assert result["msg"] == "Configurations file BACKUP_RECEIVER section variables is valid."


def test_check_backup_receiver_vars_url_not_string(logger, toml_config, monkeypatch):
    """Test check_backup_receiver_vars with URL not a string."""
    config_copy = toml_config.copy()
    backup_receiver_copy = config_copy["BACKUP_RECEIVER"].copy()
    backup_receiver_copy["URL"] = 123  # Not a string
    monkeypatch.setitem(config_copy, "BACKUP_RECEIVER", backup_receiver_copy)

    result = check_backup_receiver_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUP_RECEIVER.URL must be a string"


def test_check_backup_receiver_vars_url_invalid_format(logger, toml_config, monkeypatch):
    """Test check_backup_receiver_vars with URL in invalid format."""
    config_copy = toml_config.copy()
    backup_receiver_copy = config_copy["BACKUP_RECEIVER"].copy()
    backup_receiver_copy["URL"] = "ftp://example.com"  # Not http or https
    monkeypatch.setitem(config_copy, "BACKUP_RECEIVER", backup_receiver_copy)

    result = check_backup_receiver_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUP_RECEIVER.URL must be a valid URL"


def test_check_backup_receiver_vars_url_no_protocol(logger, toml_config, monkeypatch):
    """Test check_backup_receiver_vars with URL missing protocol."""
    config_copy = toml_config.copy()
    backup_receiver_copy = config_copy["BACKUP_RECEIVER"].copy()
    backup_receiver_copy["URL"] = "example.com/receive_backup"  # No protocol
    monkeypatch.setitem(config_copy, "BACKUP_RECEIVER", backup_receiver_copy)

    result = check_backup_receiver_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUP_RECEIVER.URL must be a valid URL"


def test_check_backup_receiver_vars_password_not_string(logger, toml_config, monkeypatch):
    """Test check_backup_receiver_vars with PASSWORD not a string."""
    config_copy = toml_config.copy()
    backup_receiver_copy = config_copy["BACKUP_RECEIVER"].copy()
    backup_receiver_copy["PASSWORD"] = 123  # Not a string
    monkeypatch.setitem(config_copy, "BACKUP_RECEIVER", backup_receiver_copy)

    result = check_backup_receiver_vars(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "config BACKUP_RECEIVER.PASSWORD must be a string"


def test_check_backup_receiver_vars_complex_url(logger, toml_config, monkeypatch):
    """Test check_backup_receiver_vars with a complex URL including credentials, port, and path."""
    config_copy = toml_config.copy()
    backup_receiver_copy = config_copy["BACKUP_RECEIVER"].copy()
    backup_receiver_copy["URL"] = "https://user:pass@example.com:8080/path/to/receiver?param=value#fragment"
    monkeypatch.setitem(config_copy, "BACKUP_RECEIVER", backup_receiver_copy)

    result = check_backup_receiver_vars(logger, config_copy)

    assert result["is_working"]
    assert result["msg"] == "Configurations file BACKUP_RECEIVER section variables is valid."


# Test cases for check_config function

def test_check_config_valid(logger, toml_config):
    """Test check_config with valid configuration."""
    result = check_config(logger, toml_config)

    assert result["is_working"]
    assert result["msg"] == "Configuration is valid"


def test_check_config_none(logger):
    """Test check_config with None configuration."""
    # Use an empty dict instead of None to match the function signature
    # The function will still treat this as an empty configuration
    result = check_config(logger, {})

    assert not result["is_working"]
    assert result["msg"] == "No configuration provided."


def test_check_config_minimal_invalid(logger):
    """Test check_config with minimal but invalid configuration."""
    # Create a minimal configuration that will fail main_vars check
    minimal_config = {
        "SAVE_BACKUPS_TO": "",  # Empty string will fail validation
        "TMP_FOLDER": "",
        "TAR_BIN": "",
        "BACKUPS_TO_SAVE_LOCAL": 0,  # Invalid value
        "SRM_BIN": "",
        "DATA": {"USE": False},
        "MARIADB": {"USE": False},
        "GPG_ENCRYPTION": {"USE": False},
        "BACKUP_RECEIVER": {"USE": False}
    }

    result = check_config(logger, minimal_config)

    assert not result["is_working"]
    # We don't check the exact message as it depends on which validation fails first


def test_check_config_main_vars_fail(logger, toml_config, monkeypatch):
    """Test check_config when check_main_vars fails."""
    config_copy = toml_config.copy()

    # Mock check_main_vars to fail
    def mock_check_main_vars(logger, config):
        return {"is_working": False, "msg": "Main vars check failed"}

    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_main_vars", mock_check_main_vars)

    result = check_config(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "Main vars check failed"


def test_check_config_data_vars_fail(logger, toml_config, monkeypatch):
    """Test check_config when check_data_vars fails."""
    config_copy = toml_config.copy()

    # Mock check_main_vars to succeed and check_data_vars to fail
    def mock_check_main_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file main variable is valid."}

    def mock_check_data_vars(logger, config):
        return {"is_working": False, "msg": "Data vars check failed"}

    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_main_vars", mock_check_main_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_data_vars", mock_check_data_vars)

    result = check_config(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "Data vars check failed"


def test_check_config_mariadb_vars_fail(logger, toml_config, monkeypatch):
    """Test check_config when check_mariadb_vars fails."""
    config_copy = toml_config.copy()

    # Mock earlier checks to succeed and check_mariadb_vars to fail
    def mock_check_main_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file main variable is valid."}

    def mock_check_data_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file DATA section variables is valid."}

    def mock_check_mariadb_vars(logger, config):
        return {"is_working": False, "msg": "Mariadb vars check failed"}

    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_main_vars", mock_check_main_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_data_vars", mock_check_data_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_mariadb_vars", mock_check_mariadb_vars)

    result = check_config(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "Mariadb vars check failed"


def test_check_config_gpg_vars_fail(logger, toml_config, monkeypatch):
    """Test check_config when check_gpg_vars fails."""
    config_copy = toml_config.copy()

    # Mock earlier checks to succeed and check_gpg_vars to fail
    def mock_check_main_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file main variable is valid."}

    def mock_check_data_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file DATA section variables is valid."}

    def mock_check_mariadb_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file MARIADB section variables is valid."}

    def mock_check_gpg_vars(logger, config):
        return {"is_working": False, "msg": "GPG vars check failed"}

    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_main_vars", mock_check_main_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_data_vars", mock_check_data_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_mariadb_vars", mock_check_mariadb_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_gpg_vars", mock_check_gpg_vars)

    result = check_config(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "GPG vars check failed"


def test_check_config_backup_receiver_vars_fail(logger, toml_config, monkeypatch):
    """Test check_config when check_backup_receiver_vars fails."""
    config_copy = toml_config.copy()

    # Mock all earlier checks to succeed and check_backup_receiver_vars to fail
    def mock_check_main_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file main variable is valid."}

    def mock_check_data_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file DATA section variables is valid."}

    def mock_check_mariadb_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file MARIADB section variables is valid."}

    def mock_check_gpg_vars(logger, config):
        return {"is_working": True, "msg": "Configurations file GPG section variables is valid."}

    def mock_check_backup_receiver_vars(logger, config):
        return {"is_working": False, "msg": "Backup receiver vars check failed"}

    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_main_vars", mock_check_main_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_data_vars", mock_check_data_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_mariadb_vars", mock_check_mariadb_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_gpg_vars", mock_check_gpg_vars)
    monkeypatch.setattr("ddmail_backup_taker.validate_config.check_backup_receiver_vars", mock_check_backup_receiver_vars)

    result = check_config(logger, config_copy)

    assert not result["is_working"]
    assert result["msg"] == "Backup receiver vars check failed"
