import pytest
import logging
import toml

def pytest_addoption(parser):
    parser.addoption(
        "--config",
        action="store",
        default=None,
        help="Config file to use during test.",
    )

@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    # Get config file option but we don't need to do anything with it here
    # The actual file loading happens in the fixtures
    session.config.getoption("--config")

@pytest.fixture(scope="session")
def config_file(request):
    """Fixture to retrieve config file"""
    return request.config.getoption("--config")

@pytest.fixture
def toml_config(config_file) -> dict:
    """Fixture to retrieve toml config"""
    if not config_file:
        pytest.skip("No config file provided with --config option")
    return toml.load(config_file)

@pytest.fixture
def testfile() -> dict:
    path = "tests/test_file.txt"
    name = "test_file.txt"
    sha256checksum = "4677942dfa3e74b5dea7484661a2485bb73ba422eb72d311fdb39372c019c615"

    # Read testfile from disc.
    f = open(path, "r")
    data = f.read()

    return {"path": path, "name": name, "sha256checksum": sha256checksum, "data": data}

@pytest.fixture
def logger() -> logging.Logger:
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
