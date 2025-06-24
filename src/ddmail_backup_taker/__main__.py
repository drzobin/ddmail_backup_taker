import argparse
import logging
import logging.handlers
import os
import toml
import datetime
import platform
import shutil
from ddmail_backup_taker.take_backup import backup_folders, backup_mariadb, gpg_encrypt, clear_backups

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

    # Working folder.
    tmp_folder = toml_config["TMP_FOLDER"]

    # Backups will be saved to this folder.
    save_backups_to = toml_config["SAVE_BACKUPS_TO"]

    # The folder to take backups on.
    folders_to_backup = str.split(toml_config["FOLDERS"]["FOLDERS_TO_BACKUP"])

    # Tar binary location.
    tar_bin = toml_config["TAR_BIN"]

    # Mariadb-dump binary location.
    mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]

    # Mariadb root password.
    mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

    # Number of days to save backups.
    days_to_save_backups = int(toml_config["BACKUPS_TO_SAVE_LOCAL"])

    # Create tmp folder.
    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

    # Create folder to save backups to.
    if not os.path.exists(save_backups_to):
        os.makedirs(save_backups_to)

    # Create tmp folder for todays date.
    today = str(datetime.date.today())
    if not os.path.exists(tmp_folder + "/" + today):
        os.makedirs(tmp_folder + "/" + today)
    tmp_folder_date = tmp_folder + "/" + today

    # Take backup of folders.
    if toml_config["FOLDERS"]["USE"] == True:
        worked = backup_folders(tar_bin, folders_to_backup, tmp_folder_date)

        # Check if backup_folders succeded.
        if worked is True:
            logger.info("backup_folders finished succesfully")
        else:
            logger.error("backup_folders failed")
            sys.exit(1)

    # Take backup of mariadb all databases.
    if toml_config["MARIADB"]["USE"] == True:
        backup_mariadb(mariadbdump_bin, mariadb_root_password, tmp_folder_date)

    # Compress all files with zip.
    hostname = platform.uname().node
    backup_filename = "backup." + hostname + "." + today + ".zip"
    backup_path = save_backups_to + "/" + backup_filename
    shutil.make_archive(
            backup_path.replace(".zip", ""),
            'zip',
            tmp_folder_date
            )

    # Change premissions on backup file.
    os.chmod(backup_path, 0o640)

    # Remove content in tmp folder.
    shutil.rmtree(tmp_folder_date)

    # Encrypt backup with openPGP public key.
    if toml_config["GPG_ENCRYPTION"]["USE"] == True:
        pubkey_fingerprint = toml_config["GPG_ENCRYPTION"]["PUBKEY_FINGERPRINT"]

        status = gpg_encrypt(
                pubkey_fingerprint,
                backup_path,
                backup_filename,
                save_backups_to
                )

        # If encryption fails program will exit with 1.
        if status is not True:
            logging.error("gpg encryption failed")
            sys.exit(1)

        # Remove unencrypted backup.
        os.remove(backup_path)

        # Set names and path to match the encryptes backup file.
        backup_filename = backup_filename + ".gpg"
        backup_path = save_backups_to + "/" + backup_filename

    # Send backups to backup_receiver.
    if toml_config["BACKUP_RECEIVER"]["USE"] == True:
        url = toml_config["BACKUP_RECEIVER"]["URL"]
        password = toml_config["BACKUP_RECEIVER"]["PASSWORD"]

        send_to_backup_receiver(backup_path, backup_filename, url, password)

    # Remove old backups.
    clear_backups(save_backups_to, days_to_save_backups)
    logger.info("backup job finished succesfully")

if __name__ == "__main__":
    main()
