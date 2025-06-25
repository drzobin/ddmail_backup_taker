import argparse
import logging
import logging.handlers
import os
import toml
import datetime
import platform
import shutil
import sys
from ddmail_backup_taker.take_backup import create_backup, send_to_backup_receiver, clear_backups

def main():
    # Get arguments from args.
    parser = argparse.ArgumentParser(description="Backup files and mariadb databases")
    parser.add_argument('--config-file', type=str, help='Full path to config file.', required=True)
    args = parser.parse_args()

    # Check that config file exists and is a file.
    if not os.path.isfile(args.config_file):
        print("ERROR: config file does not exist or is not a file.")
        sys.exit(1)

    # Parse toml config file.
    with open(args.config_file, 'r') as f:
        toml_config = toml.load(f)

    # Setup logging.
    logger = logging.getLogger(__name__)

    formatter = logging.Formatter(
        "{asctime} ddmail_backup_taker {levelname} in {module} {funcName} {lineno}: {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        )

    if toml_config["LOGGING"]["LOG_TO_CONSOLE"] == True:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if toml_config["LOGGING"]["LOG_TO_FILE"] == True:
        file_handler = logging.FileHandler(toml_config["LOGGING"]["LOGFILE"], mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if toml_config["LOGGING"]["LOG_TO_SYSLOG"] == True:
        syslog_handler = logging.handlers.SysLogHandler(address = toml_config["LOGGING"]["SYSLOG_SERVER"])
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    # Set loglevel.
    if toml_config["LOGGING"]["LOGLEVEL"] == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif toml_config["LOGGING"]["LOGLEVEL"] == "INFO":
        logger.setLevel(logging.INFO)
    elif toml_config["LOGGING"]["LOGLEVEL"] == "WARNING":
        logger.setLevel(logging.WARNING)
    elif toml_config["LOGGING"]["LOGLEVEL"] == "ERROR":
        logger.setLevel(logging.ERROR)

    logger.info("starting backup job")

    # Create backup file.
    result_create_backup = create_backup(logger, toml_config)
    if not result_create_backup["is_working"]:
        logger.error("create_backup failed: " + result_create_backup["msg"])

    # Send backup to ddmail_backup_receiver.
    if toml_config["BACKUP_RECEIVER"]["USE"] == True:
        url = toml_config["BACKUP_RECEIVER"]["URL"]
        password = toml_config["BACKUP_RECEIVER"]["PASSWORD"]

        result_send_to_backup_receiver = send_to_backup_receiver(logger, result_create_backup["backup_file"], result_create_backup["backup_filename"], url, password)
        if not result_send_to_backup_receiver["is_working"]:
            logger.error("send_to_backup_receiver failed: " + result_send_to_backup_receiver["msg"])
            # Continue execution even if sending to backup receiver fails

    # Clear/remove backups if there is to many.
    return_clear_backups = clear_backups(logger, toml_config["SAVE_BACKUPS_TO"], toml_config["BACKUPS_TO_SAVE_LOCAL"])

    logger.info("backup job finished succesfully")

if __name__ == "__main__":
    main()
