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


def backup_folders(logger, tar_bin, folders_to_backup, dst_folder):
    """Tar folders and save the compressed tar files on disc.

    Keyword arguments:
    tar_bin -- full location of the tar binary.
    folders_to_backup -- list with folders to backup.
    dst_folder -- save all tar files to this folder.
    """
    # Check if tar binary exist.
    if not os.path.exists(tar_bin):
        logger.error("tar binary location is wrong")
        return False

    # Check if dst_foler exist.
    if not os.path.exists(dst_folder):
        logger.error("dst_folder do not exist")
        return False

    # Take backup of folders in folders_to_backup.
    for folder in folders_to_backup:

        # Check if folder exist.
        if not os.path.exists(folder):
            logger.error("folder do not exist")
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
                logger.error("returncode of cmd tar is non zero")
        except subprocess.CalledProcessError:
            logger.error("returncode of cmd tar is non zero")
            return False

    # All worked as expected.
    return True


def backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, dst_folder):
    """Take a full dump of all databases in mariadb included with schema.

    Keyword arguments:
    mariadbdump_bin -- full location of the mariadbdump binary.
    mariadb_root_password -- mariadb password for user root.
    dst_folder -- save the database dumpt to this folder.
    """
    # Check if mariadbdump binary exist.
    if not os.path.exists(mariadbdump_bin):
        logger.error("mariadbdump binary location is wrong")
        return False

    # Check if dst_folder exist.
    if not os.path.exists(dst_folder):
        logger.error("dst_folder do not exist")
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
            logger.error("returncode of cmd mysqldump is none zero")
            return False
    except subprocess.CalledProcessError:
        logger.error("returncode of cmd mysqldump is none zero")
        return False

    # All worked as expected.
    return True


def clear_backups(logger, save_backups_to, days_to_save_backups):
    """Clear/remove old backups/files that is older then x amount of days.

    Keyword arguments:
    save_backups_to -- folder where backups is stored that will be removed.
    days_to_save_backups -- number of days before backups are removed.
    """
    # Check if save_backups_to is a folder.
    if not os.path.exists(save_backups_to):
        logger.error("can not find folder where backups are saved")

    # Get list of zip files in the given directory.
    list_of_files = filter(
            os.path.isfile,
            glob.glob(save_backups_to + '/backup*.zip*')
            )

    # Sort list of files based on last modification time in ascending order.
    list_of_files = sorted(list_of_files, key=os.path.getmtime)

    # If we have less or equal of 7 backups then exit.
    if len(list_of_files) <= days_to_save_backups:
        logger.info("too few backups for clearing old backups")
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
            logger.info("removing: " + save_backups_to + "/" + file)


def sha256_of_file(logger, file):
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


def gpg_encrypt(logger, pubkey_fingerprint, src_file, src_filename, dst_folder):
    """Encrypt file with gpg using a public key in the current users keyring.

    Keyword arguments:
    pubkey_fingerprint -- fingerprint for public key to use for encryption.
    src_file -- full path to file that should be encrypted.
    src_filename -- filename of file that should be encrypted.
    dst_folder -- full path to folder to save encrypted file in.
    """
    #
    if not os.path.exists(src_file):
        logger.error("can not find folder where backups are saved")
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
        logger.error("encryption failed with " + str(encrypted_data.status))
        return False

    encrypted_file = dst_folder + "/" + src_filename + ".gpg"

    with open(encrypted_file, "wb") as file:
        file.write(encrypted_data.data)

    logger.info("successfully encrypted backup")
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
    try:
        r = requests.post(url, files=files, data=data, timeout=10)

        # Log result.
        if str(r.status_code) == "200" and r.text == "done":
            logger.info("successfully sent backup to backup_receiver")
        else:
            logger.error("failed to sent backup to backup_receiver " +
                          "got http status code: " + str(r.status_code) +
                          " and message: " + r.text
                          )
    except requests.ConnectionError:
        logger.error("failed to sent backup to backup_receiver" +
                      " request exception ConncetionError"
                      )
