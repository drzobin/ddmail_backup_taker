from backup_taker.take_backup import sha256_of_file

# Testfile used in many testcases.
TESTFILE_PATH = "tests/test_file.txt"
TESTFILE_NAME = "test_file.txt"
SHA256 = "4677942dfa3e74b5dea7484661a2485bb73ba422eb72d311fdb39372c019c615"
f = open(TESTFILE_PATH, "r")
TESTFILE_DATA = f.read()

# Test that sha256 checksum is correct. 
def test_sha256_of_file_test1():
    sha256 = sha256_of_file(TESTFILE_PATH)

    assert sha256 == SHA256

# Test to open a file that do not exist.
def test_sha256_of_file_test2():
    file_path = "/tmp/nofile"
    sha256 = sha256_of_file(file_path)

    assert sha256 is None
