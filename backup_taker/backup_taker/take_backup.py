"""Take backups of folders/files and mariadb databases."""
import configparser
import os
import subprocess
import shutil
import logging
import datetime
import sys
import argparse
import glob
import hashlib
import requests
import platform
import gnupg

# Configure logging.
logging.basicConfig(
        filename="/var/log/ddmail_backup_taker.log",
        format='%(asctime)s %(funcName)s %(levelname)s: %(message)s',
        level=logging.INFO
        )


def backup_folders(tar_bin, folders_to_backup, dst_folder):
    """Tar folders and save the compressed tar files on disc.

    Keyword arguments:
    tar_bin -- full location of the tar binary.
    folders_to_backup -- list with folders to backup.
    dst_folder -- save all tar files to this folder.
    """
    # Check if tar binary exist.
    if not os.path.exists(tar_bin):
        logging.error("tar binary location is wrong")
        return False

    # Check if dst_foler exist.
    if not os.path.exists(dst_folder):
        logging.error("dst_folder do not exist")
        return False

    # Take backup of folders in folders_to_backup.
    for folder in folders_to_backup:

        # Check if folder exist.
        if not os.path.exists(folder):
            logging.error("folder do not exist")
            return False

        # Create tar archive name.
        backup_name = folder.replace("/", "_") + ".tar.gz"

        try:
            output = subprocess.run(
                    [tar_bin,
                     "-czf",
                     dst_folder + "/" + backup_name,
                     folder],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                    )
            if output.returncode != 0:
                logging.error("returncode of cmd tar is non zero")
        except subprocess.CalledProcessError:
            logging.error("returncode of cmd tar is non zero")
            return False

    # All worked as expected.
    return True


def backup_mariadb(mariadbdump_bin, mariadb_root_password, dst_folder):
    """Take a full dump of all databases in mariadb included with schema.

    Keyword arguments:
    mariadbdump_bin -- full location of the mariadbdump binary.
    mariadb_root_password -- mariadb password for user root.
    dst_folder -- save the database dumpt to this folder.
    """
    # Check if mariadbdump binary exist.
    if not os.path.exists(mariadbdump_bin):
        logging.error("mariadbdump binary location is wrong")
        return False

    # Check if dst_folder exist.
    if not os.path.exists(dst_folder):
        logging.error("dst_folder do not exist")
        return False

    # Take backup of mariadb all databases.
    try:
        f = open(dst_folder + "/" + "full_db_dump.sql", "w")
        output = subprocess.run(
                [mariadbdump_bin,
                 "-h",
                 "localhost",
                 "--all-databases",
                 "-uroot",
                 "-p" + mariadb_root_password],
                check=True,
                stdout=f
                )
        if output.returncode != 0:
            logging.error("returncode of cmd mysqldump is none zero")
            return False
    except subprocess.CalledProcessError:
        logging.error("returncode of cmd mysqldump is none zero")
        return False

    # All worked as expected.
    return True


def clear_backups(save_backups_to, days_to_save_backups):
    """Clear/remove old backups/files that is older then x amount of days.

    Keyword arguments:
    save_backups_to -- folder where backups is stored that will be removed.
    days_to_save_backups -- number of days before backups are removed.
    """
    # Check if save_backups_to is a folder.
    if not os.path.exists(save_backups_to):
        logging.error("can not find folder where backups are saved")

    # Get list of zip files in the given directory.
    list_of_files = filter(
            os.path.isfile,
            glob.glob(save_backups_to + '/backup*.zip*')
            )

    # Sort list of files based on last modification time in ascending order.
    list_of_files = sorted(list_of_files, key=os.path.getmtime)

    # If we have less or equal of 7 backups then exit.
    if len(list_of_files) <= days_to_save_backups:
        logging.info("too few backups for clearing old backups")
        return

    list_of_files.reverse()
    count = 0

    # Only save days_to_save_backups days of backups, remove other.
    for file in list_of_files:
        count = count + 1
        if count <= days_to_save_backups:
            continue
        else:
            os.remove(file)
            logging.info("removing: " + save_backups_to + "/" + file)


def sha256_of_file(file):
    """Take sha256 checksum of file on disc.

    Keyword arguments:
    file -- full path to file that we should take the sha256 checksum of.
    """
    # 65kb
    buf_size = 65536

    sha256 = hashlib.sha256()

    # Check if file exist.
    if os.path.exists(file) is not True:
        return None

    with open(file, 'rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)

    return sha256.hexdigest()


def gpg_encrypt(pubkey_fingerprint, src_file, src_filename, dst_folder):
    """Encrypt file with gpg using a public key in the current users keyring.

    Keyword arguments:
    pubkey_fingerprint -- fingerprint for public key to use for encryption.
    src_file -- full path to file that should be encrypted.
    src_filename -- filename of file that should be encrypted.
    dst_folder -- full path to folder to save encrypted file in.
    """
    #
    if not os.path.exists(src_file):
        logging.error("can not find folder where backups are saved")
        return False

    gpg = gnupg.GPG()
    gpg.encoding = 'utf-8'

    stream = open(src_file, 'rb')
    encrypted_data = gpg.encrypt_file(
            stream,
            pubkey_fingerprint,
            armor=False,
            always_trust=True
            )

    # Encryption has failed.
    if encrypted_data.ok is not True:
        logging.error("encryption failed with " + str(encrypted_data.status))
        return False

    encrypted_file = dst_folder + "/" + src_filename + ".gpg"

    with open(encrypted_file, "wb") as file:
        file.write(encrypted_data.data)

    logging.info("successfully encrypted backup")
    return True


def send_to_backup_receiver(backup_path, filename, url, password):
    """Send backups to remote ddmail_backup_receiver for offsite storage.

    Keyword arguments:
    backup_path -- full location of file to send.
    filename -- filename of file to send.
    url -- url to ddmail_backup_receiver.
    password -- password to ddmail_backup_receiver.
    """
    # Get the sha256 checksum of file.
    sha256 = sha256_of_file(backup_path)

    files = {"file": open(backup_path, "rb")}
    data = {
            "filename": filename,
            "password": password,
            "sha256": sha256
            }

    # Send backup to backup_receiver
    r = requests.post(url, files=files, data=data, timeout=10)

    # Log result.
    if str(r.status_code) == "200" and r.text == "done":
        logging.info("successfully sent backup to backup_receiver")
    else:
        logging.error("failed to sent backup to backup_receiver")


if __name__ == "__main__":
    """Main function """

    logging.info("starting backup job")

    # Get arguments from args.
    parser = argparse.ArgumentParser(description="Backup for ddmail")
    parser.add_argument(
            '--config-file',
            type=str,
            help='Full path to config file.',
            required=True
            )

    args = parser.parse_args()

    # Check that config file exsist and is a file.
    if os.path.isfile(args.config_file) is False:
        print("config file do not exist or is not a file.")
        sys.exit(1)

    # Import config file.
    config = configparser.ConfigParser()
    conf_file = args.config_file
    config.read(conf_file)

    # Working folder.
    tmp_folder = config["DEFAULT"]["tmp_folder"]

    # Backups will be saved to this folder.
    save_backups_to = config["DEFAULT"]["save_backups_to"]

    # The folder to take backups on.
    folders_to_backup = str.split(config["DEFAULT"]["folders_to_backup"])

    # Tar binary location.
    tar_bin = config["DEFAULT"]["tar_bin"]

    # Mariadb-dump binary location.
    mariadbdump_bin = config["DEFAULT"]["mariadbdump_bin"]

    # Mariadb root password.
    mariadb_root_password = config["mariadb"]["root_password"]

    # Number of days to save backups.
    days_to_save_backups = int(config["DEFAULT"]["days_to_save_backups"])

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
    worked = backup_folders(tar_bin, folders_to_backup, tmp_folder_date)

    # Check if backup_folders succeded.
    if worked is True:
        logging.info("backup_folders finished succesfully")
    else:
        logging.error("backup_folders failed")
        sys.exit(1)

    # Take backup of mariadb all databases.
    if config["mariadb"]["use"] == "Yes":
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
    if config["gpg_encryption"]["use"] == "Yes":
        pubkey_fingerprint = config["gpg_encryption"]["pubkey_fingerprint"]

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
    if config["backup_receiver"]["use"] == "Yes":
        url = config["backup_receiver"]["url"]
        password = config["backup_receiver"]["password"]

        send_to_backup_receiver(backup_path, backup_filename, url, password)

    # Remove old backups.
    clear_backups(save_backups_to, days_to_save_backups)
    logging.info("backup job finished succesfully")
