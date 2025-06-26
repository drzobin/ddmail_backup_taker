import os
import shutil
import time
from ddmail_backup_taker.backup import sha256_of_file, backup_mariadb, clear_backups, create_backup, tar_data, send_to_backup_receiver, secure_delete


# Testfile used in many testcases.
TESTFILE_PATH = "tests/test_file.txt"
TESTFILE_NAME = "test_file.txt"
SHA256 = "4677942dfa3e74b5dea7484661a2485bb73ba422eb72d311fdb39372c019c615"
f = open(TESTFILE_PATH, "r")
TESTFILE_DATA = f.read()


def test_sha256_of_file_test1():
    """Test sha256_of_file() checksum is correct."""
    sha256 = sha256_of_file(TESTFILE_PATH)

    assert sha256 == SHA256


def test_sha256_of_file_test2():
    """Test sha256_go_file() open a file that do not exist."""
    file_path = "/tmp/nofile"
    sha256 = sha256_of_file(file_path)

    assert sha256 is None


def test_backup_mariadb_test1():
    """Test backup_mariadb() with mariadbdump binary location that do not exist."""

    mariadbdump_bin = "/usr/local/donotexist"
    mariadb_root_password = "1superGoodpasswordthatiswrong"
    dst_test_folder = "/tmp/mariadbdump"

    # Create empty dst_test_folder.
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
    if not os.path.exists(dst_test_folder):
        os.makedirs(dst_test_folder)

    worked = backup_mariadb(mariadbdump_bin, mariadb_root_password, dst_test_folder)

    assert worked is False

def test_backup_mariadb_test2():
    """Test backup_mariadb() with wrong db root password."""

    mariadbdump_bin = "/usr/bin/mariadb-dump"
    mariadb_root_password = "1superGoodpasswordthatiswrong"
    dst_test_folder = "/tmp/mariadbdump"

    # Create empty dst_test_folder.
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
    if not os.path.exists(dst_test_folder):
        os.makedirs(dst_test_folder)

    worked = backup_mariadb(mariadbdump_bin, mariadb_root_password, dst_test_folder)

    assert worked is False

def test_backup_mariadb_test3():
    """Test backup_mariadb() with dst_folder that do not exist."""

    mariadbdump_bin = "/usr/bin/mariadb-dump"
    mariadb_root_password = "1superGoodpasswordthatiswrong"
    dst_test_folder = "/tmp/mariadbdump"

    # Create empty dst_test_folder.
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)

    worked = backup_mariadb(mariadbdump_bin, mariadb_root_password, dst_test_folder)

    assert worked is False

def test_clear_backups_test1():
    """Test clear_backups() with empty folder."""

    folder = "/tmp/test_clear_backups"
    days_to_save_backups = 1

    if os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

    clear_backups(folder, days_to_save_backups)

def test_clear_backups_test2():
    """Test clear_backups() folder with 3 *.gpg files"""

    folder = "/tmp/test_clear_backups_test2"
    days_to_save_backups = 1

    if os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

    test_file1 = folder + "/backup.dev1.2024-08-01.zip.gpg"
    test_file2 = folder + "/backup.dev1.2024-08-02.zip.gpg"
    test_file3 = folder + "/backup.dev1.2024-08-03.zip.gpg"

    shutil.copyfile(TESTFILE_PATH, test_file1)
    time.sleep(1)
    shutil.copyfile(TESTFILE_PATH, test_file2)
    time.sleep(1)
    shutil.copyfile(TESTFILE_PATH, test_file3)

    clear_backups(folder, days_to_save_backups)

    assert os.path.exists(test_file1) is False
    assert os.path.exists(test_file2) is False
    assert os.path.exists(test_file3) is True

    if os.path.exists(folder):
        shutil.rmtree(folder)

def test_clear_backups_test3():
    """Test clear_backups() folder with 3 *.zip files"""

    folder = "/tmp/test_clear_backups_test3"
    days_to_save_backups = 2

    if os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

    test_file1 = folder + "/backup.dev1.2024-08-01.zip"
    test_file2 = folder + "/backup.dev1.2024-08-02.zip"
    test_file3 = folder + "/backup.dev1.2024-08-03.zip"

    shutil.copyfile(TESTFILE_PATH, test_file1)
    time.sleep(1)
    shutil.copyfile(TESTFILE_PATH, test_file2)
    time.sleep(1)
    shutil.copyfile(TESTFILE_PATH, test_file3)

    clear_backups(folder, days_to_save_backups)

    assert os.path.exists(test_file1) is False
    assert os.path.exists(test_file2) is True
    assert os.path.exists(test_file3) is True

    if os.path.exists(folder):
        shutil.rmtree(folder)

def test_clear_backups_test4():
    """Test clear_backups() folder with 3 *.zip files without deleting anything"""

    folder = "/tmp/test_clear_backups_test4"
    days_to_save_backups = 7

    if os.path.exists(folder):
        shutil.rmtree(folder)
    if not os.path.exists(folder):
        os.makedirs(folder)

    test_file1 = folder + "/backup.dev1.2024-08-01.zip"
    test_file2 = folder + "/backup.dev1.2024-08-02.zip"
    test_file3 = folder + "/backup.dev1.2024-08-03.zip"

    shutil.copyfile(TESTFILE_PATH, test_file1)
    time.sleep(1)
    shutil.copyfile(TESTFILE_PATH, test_file2)
    time.sleep(1)
    shutil.copyfile(TESTFILE_PATH, test_file3)

    clear_backups(folder, days_to_save_backups)

    assert os.path.exists(test_file1) is True
    assert os.path.exists(test_file2) is True
    assert os.path.exists(test_file3) is True

    if os.path.exists(folder):
        shutil.rmtree(folder)
