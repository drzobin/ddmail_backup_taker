"""Test for take_bacup module."""
from backup_taker.take_backup import sha256_of_file, backup_folders
import os
import shutil

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


def test_backup_folders_test1():
    """Test backup_folders()."""
    test_folders = ["/tmp/test1", "/tmp/test2"]
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Check if test folder exist, if they exist remove and recreate them.
    dst_test_folder = "/tmp/test3"
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
    if not os.path.exists(dst_test_folder):
        os.makedirs(dst_test_folder)

    tar_bin = "/usr/bin/tar"
    folders_to_backup = test_folders
    dst_folder = dst_test_folder

    worked = backup_folders(tar_bin, folders_to_backup, dst_folder)

    assert worked is True
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test1.tar.gz") is True
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test2.tar.gz") is True

    # Remove test folders and tar file.
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)


def test_backup_folders_test2():
    """Test backup_folders() with tar binary location that do not exist."""
    test_folders = ["/tmp/test1", "/tmp/test2"]
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Check if test folder exist, if they exist remove and recreate them.
    dst_test_folder = "/tmp/test3"
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
    if not os.path.exists(dst_test_folder):
        os.makedirs(dst_test_folder)

    tar_bin = "/usr/bin/donotexist"
    folders_to_backup = test_folders
    dst_folder = dst_test_folder

    worked = backup_folders(tar_bin, folders_to_backup, dst_folder)

    assert worked is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test1.tar.gz") is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test2.tar.gz") is False

    # Remove test folders and tar file.
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)


def test_backup_folders_test3():
    """Test backup_folders() with tar binary location that is not tar."""
    test_folders = ["/tmp/test1", "/tmp/test2"]
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Check if test folder exist, if they exist remove and recreate them.
    dst_test_folder = "/tmp/test3"
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
    if not os.path.exists(dst_test_folder):
        os.makedirs(dst_test_folder)

    tar_bin = "/usr/bin/ls"
    folders_to_backup = test_folders
    dst_folder = dst_test_folder

    worked = backup_folders(tar_bin, folders_to_backup, dst_folder)

    assert worked is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test1.tar.gz") is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test2.tar.gz") is False

    # Remove test folders and tar file.
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)


def test_backup_folders_test4():
    """Test backup_folders() with dst_folder location that do not exist."""
    test_folders = ["/tmp/test1", "/tmp/test2"]
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Check if test folder exist, if they exist remove and recreate them.
    dst_test_folder = "/tmp/test3"
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)

    tar_bin = "/usr/bin/tar"
    folders_to_backup = test_folders
    dst_folder = dst_test_folder

    worked = backup_folders(tar_bin, folders_to_backup, dst_folder)

    assert worked is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test1.tar.gz") is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test2.tar.gz") is False


def test_backup_folders_test5():
    """Test backup_folders() with folders_to_backup that do not exist."""
    test_folders = ["/tmp/test1", "/tmp/test2"]
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # Check if test folder exist, if they exist remove and recreate them.
    dst_test_folder = "/tmp/test3"
    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
    if not os.path.exists(dst_test_folder):
        os.makedirs(dst_test_folder)

    tar_bin = "/usr/bin/tar"
    folders_to_backup = test_folders
    dst_folder = dst_test_folder

    worked = backup_folders(tar_bin, folders_to_backup, dst_folder)

    assert worked is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test1.tar.gz") is False
    assert os.path.exists(dst_test_folder + "/" + "_tmp_test2.tar.gz") is False

    # Remove test folders and tar file.
    for folder in test_folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    if os.path.exists(dst_test_folder):
        shutil.rmtree(dst_test_folder)
