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

def create_backup(logger:logging.Logger, toml_config:dict) -> dict:
    # Working folder.
    tmp_folder = toml_config["TMP_FOLDER"]

    # Backups will be saved to this folder.
    save_backups_to = toml_config["SAVE_BACKUPS_TO"]

    # Tar binary location.
    tar_bin = toml_config["TAR_BIN"]

    # The folder and/or files to take backups on.
    data_to_backup = []

    # Create tmp folder.
    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

    # Create folder to save backups to.
    if not os.path.exists(save_backups_to):
        os.makedirs(save_backups_to)

    # Create tmp folder for todays date.
    today = str(datetime.date.today())
    tmp_folder_date = os.path.join(tmp_folder, today)
    if not os.path.exists(tmp_folder_date):
        os.makedirs(tmp_folder_date)

    if toml_config["MARIADB"]["USE"] == True:
        # Mariadb-dump binary location.
        mariadbdump_bin = toml_config["MARIADB"]["MARIADBDUMP_BIN"]

        # Mariadb root password.
        mariadb_root_password = toml_config["MARIADB"]["ROOT_PASSWORD"]

        result = backup_mariadb(logger, mariadbdump_bin, mariadb_root_password, tmp_folder_date)

        if not result["is_working"]:
            msg = "Failed to backup MariaDB: " + result["msg"]
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        data_to_backup.append(result["db_dump_file"])

    if toml_config["FOLDERS"]["USE"] == True:
        # The folder to take backups on.
        data_to_backup.extend(str.split(toml_config["FOLDERS"]["FOLDERS_TO_BACKUP"]))

    if toml_config["FOLDERS"]["USE"] == True or toml_config["MARIADB"]["USE"] == True:
        result = tar_data(logger, toml_config, data_to_backup)
        if not result["is_working"]:
            msg = "Failed to backup folders: " + result["msg"]
            logger.error(msg)
            return {"is_working": False, "msg": msg}


    # Remove temp folder
    shutil.rmtree(tmp_folder_date)

    # All worked as expected.
    msg = "Backup created successfully"
    logger.info(msg)
    return {"is_working": True, "msg": msg}

def tar_data(logger:logging.Logger, toml_config:dict, data_to_backup:list[str])->dict:
    """Tar data and save the compressed tar file on disc.

    Keyword arguments:
    logger -- logger object.
    toml_config -- toml config dict.
    data_to_backup -- list of folders to backup.
    """

    tar_bin = toml_config["TAR_BIN"]
    save_backups_to = toml_config["SAVE_BACKUPS_TO"]

    # Check if tar binary exist.
    if not os.path.exists(tar_bin):
        msg = "tar binary location is wrong"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if save backups to directory exist.
    if not os.path.exists(save_backups_to):
        msg = "save backups to directory location is wrong"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Create backup file name.
    backup_filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.tar.gz"
    backup_file = os.path.join(save_backups_to, backup_filename)

    # Should the tar archive be encrypted.
    if toml_config["GPG_ENCRYPTION"]["USE"] == True:
        gpg_bin = toml_config["GPG_ENCRYPTION"]["GPG_BIN"]
        gpg_pubkey_fingerprint = toml_config["GPG_ENCRYPTION"]["PUBKEY_FINGERPRINT"]
        backup_file = backup_file + ".gpg"
        backup_filename = backup_filename + ".gpg"

        try:
            # Create tar process
            tar_process = subprocess.Popen(
                [tar_bin, "-czf", "-"] + data_to_backup,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Create gpg process that takes tar output as input
            gpg_process = subprocess.Popen(
                [gpg_bin, "-e", "-r", gpg_pubkey_fingerprint, "--trust-model", "always", "-o", backup_file],
                stdin=tar_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Allow tar_process to receive a SIGPIPE if gpg_process exits
            if tar_process.stdout:
                tar_process.stdout.close()

            # Wait for completion and check return codes
            gpg_stdout, gpg_stderr = gpg_process.communicate()
            tar_process.wait()

            if tar_process.returncode != 0:
                msg = f"tar command failed with return code {tar_process.returncode}"
                logger.error(msg)
                return {"is_working": False, "msg": msg}

            if gpg_process.returncode != 0:
                msg = f"gpg command failed with return code {gpg_process.returncode}"
                logger.error(msg)
                return {"is_working": False, "msg": msg}

        except Exception as e:
            msg = f"Error during backup process: {str(e)}"
            logger.error(msg)
            return {"is_working": False, "msg": msg}
    else:
        # Create regular tar file without encryption
        try:
            # Create standard tar command
            result = subprocess.run(
                [tar_bin, "-czf", backup_file] + data_to_backup,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

        except subprocess.CalledProcessError as e:
            msg = f"tar command failed with return code {e.returncode}: {e.stderr.decode('utf-8')}"
            logger.error(msg)
            return {"is_working": False, "msg": msg}
        except Exception as e:
            msg = f"Error during backup process: {str(e)}"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

    # All worked as expected.
    msg = "Successfully backed up data"
    logger.info(msg)
    return {"is_working": True, "msg": msg,"backup_file": backup_file, "backup_filename": backup_filename}

def backup_mariadb(logger: logging.Logger, mariadbdump_bin: str, mariadb_root_password: str, dst_folder: str) -> dict:
    """Take a full dump of all databases in mariadb included with schema.

    Keyword arguments:
    logger -- logger object.
    mariadbdump_bin -- full location of the mariadbdump binary.
    mariadb_root_password -- mariadb password for user root.
    dst_folder -- save the database dumpt to this folder.
    """
    # Check if mariadbdump binary exist.
    if not os.path.exists(mariadbdump_bin):
        msg = "mariadbdump binary location is wrong"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if dst_folder exist.
    if not os.path.exists(dst_folder):
        msg = "dst_folder do not exist"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    db_dump_file = dst_folder + "/" + "full_db_dump.sql"

    # Take backup of mariadb all databases.
    try:
        f = open(db_dump_file, "w")
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
            msg = "returncode of cmd mariadbdump is none zero"
            logger.error(msg)
            return {"is_working": False, "msg": msg}
    except subprocess.CalledProcessError:
        msg = "returncode of cmd mariadbdump is none zero"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check that sql dump file has been created.
    if not os.path.isfile(db_dump_file) == True:
        msg = "mariadb database dump file " + db_dump_file + " does not exist"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # All worked as expected.
    return {"is_working": True, "msg": "done", "db_dump_file": db_dump_file}


def clear_backups(logger:logging.Logger, save_backups_to:str, days_to_save_backups:int) -> dict:
    """Clear/remove old backups/files that is older then x amount of days.

    Keyword arguments:
    save_backups_to -- folder where backups is stored that will be removed.
    days_to_save_backups -- number of days before backups are removed.
    """
    # Check if save_backups_to is a folder.
    if not os.path.exists(save_backups_to):
        msg = "can not find folder where backups are saved"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Get list of zip files in the given directory.
    list_of_files = filter(
            os.path.isfile,
            glob.glob(save_backups_to + '/backup*.zip*')
            )

    # Sort list of files based on last modification time in ascending order.
    list_of_files = sorted(list_of_files, key=os.path.getmtime)

    # If we have less or equal of 7 backups then exit.
    if len(list_of_files) <= days_to_save_backups:
        msg = "too few backups for clearing old backups"
        logger.info(msg)
        return {"is_working": True, "msg": msg}

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

    msg = "Successfully cleared old backups"
    logger.info(msg)
    return {"is_working": True, "msg": msg}


def sha256_of_file(logger:logging.Logger, file:str) -> dict:
    """Take sha256 checksum of file on disc.

    Keyword arguments:
    file -- full path to file that we should take the sha256 checksum of.
    """
    # 65kb
    buf_size = 65536

    sha256 = hashlib.sha256()

    # Check if file exist.
    if os.path.exists(file) is not True:
        msg = "File does not exist"
        logger.error(msg)
        return {"is_working": False, "msg": msg, "checksum": None}

    with open(file, 'rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)

    checksum = sha256.hexdigest()
    msg = "Successfully generated SHA256 checksum"
    logger.info(msg)
    return {"is_working": True, "msg": msg, "checksum": checksum}

def send_to_backup_receiver(logger:logging.Logger, backup_path:str, filename:str, url:str, password:str) -> dict:
    """Send backups to remote ddmail_backup_receiver for offsite storage.

    Keyword arguments:
    backup_path -- full location of file to send.
    filename -- filename of file to send.
    url -- url to ddmail_backup_receiver.
    password -- password to ddmail_backup_receiver.
    """
    # Get the sha256 checksum of file.
    sha256_result = sha256_of_file(logger, backup_path)

    if not sha256_result["is_working"]:
        msg = "Failed to calculate SHA256 checksum: " + sha256_result["msg"]
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    sha256 = sha256_result["checksum"]

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
            msg = "successfully sent backup to backup_receiver"
            logger.info(msg)
            return {"is_working": True, "msg": msg}
        else:
            msg = "failed to sent backup to backup_receiver " + \
                  "got http status code: " + str(r.status_code) + \
                  " and message: " + r.text
            logger.error(msg)
            return {"is_working": False, "msg": msg}
    except requests.ConnectionError:
        msg = "failed to sent backup to backup_receiver request exception ConnectionError"
        logger.error(msg)
        return {"is_working": False, "msg": msg}
