import logging
import os
import re
import gnupg

def check_main_vars(logger:logging.Logger,toml_config:dict) -> dict:
    # Check if SAVE_BACKUPS_TO is None.
    if not toml_config["SAVE_BACKUPS_TO"]:
        msg = "config SAVE_BACKUPS_TO is None"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if SAVE_BACKUPS_TO is a valid directory
    if not os.path.isdir(toml_config["SAVE_BACKUPS_TO"]):
        logger.info("config SAVE_BACKUPS_TO" + toml_config["SAVE_BACKUPS_TO"] + " do not exist, trying to create it")
        os.makedirs(toml_config["SAVE_BACKUPS_TO"])
        if not os.path.isdir(toml_config["SAVE_BACKUPS_TO"]):
            msg = "config SAVE_BACKUPS_TO do not exist"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

    # Check if SAVED_BACKUPS_TO is a writable directory
    if not os.access(toml_config["SAVE_BACKUPS_TO"], os.W_OK):
        msg = "config SAVE_BACKUPS_TO is not writable"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if TMP_FOLDER is None.
    if not toml_config["TMP_FOLDER"]:
        msg = "config TMP_FOLDER is None"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if TMP_FOLDER is a valid directory
    if not os.path.isdir(toml_config["TMP_FOLDER"]):
        logger.info("config TMP_FOLDER" + toml_config["TMP_FOLDER"] + " do not exist, trying to create it")
        os.makedirs(toml_config["TMP_FOLDER"])
        if not os.path.isdir(toml_config["TMP_FOLDER"]):
            msg = "config TMP_FOLDER do not exist"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

    # Check if TMP_FOLDER is writable
    if not os.access(toml_config["TMP_FOLDER"], os.W_OK):
        msg = "config TMP_FOLDER is not writable"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if TAR_BIN is None.
    if not toml_config["TAR_BIN"]:
        msg = "config TAR_BIN is None"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if TAR_BIN is a valid file
    if not os.path.isfile(toml_config["TAR_BIN"]):
        msg = "config TAR_BIN do not exist"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if TAR_BIN is executable
    if not os.access(toml_config["TAR_BIN"], os.X_OK):
        msg = "config TAR_BIN is not executable"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if BACKUPS_TO_SAVE_LOCAL is a positive int
    if not isinstance(toml_config["BACKUPS_TO_SAVE_LOCAL"], int) or toml_config["BACKUPS_TO_SAVE_LOCAL"] <= 0:
        msg = "config BACKUPS_TO_SAVE_LOCAL must be a positive integer"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if SRM_BIN is None.
    if toml_config["SRM_BIN"] is None:
        msg = "config SRM_BIN is None."
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if SRM_BIN is a file.
    if not os.path.isfile(toml_config["SRM_BIN"]):
        msg = "config SRM_BIN is not a file"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check if SRM_BIN is executable
    if not os.access(toml_config["SRM_BIN"], os.X_OK):
        msg = "config SRM_BIN is not executable"
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    return {"is_working": True, "msg": "Configurations file main variable is valid."}

def check_data_vars(logger:logging.Logger, toml_config:dict) -> dict:
    # Check if DATA.USE is True.
    if toml_config["DATA"]["USE"]:
        # Check if DATA.DATA_TO_BACKUP is a string
        if not isinstance(toml_config["DATA"]["DATA_TO_BACKUP"], str):
            msg = "config DATA.DATA_TO_BACKUP must be a string"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if each folder in DATA.DATA_TO_BACKUP exists
        for data in str(toml_config["DATA"]["DATA_TO_BACKUP"]).split(" "):
            if not os.path.isdir(data) and not os.path.isfile(data):
                msg = f"config DATA.DATA_TO_BACKUP contains non-existent path: {data}"
                logger.error(msg)
                return {"is_working": False, "msg": msg}

        # Check if each folder/file in DATA.DATA_TO_BACKUP is readable
        for data in str(toml_config["DATA"]["DATA_TO_BACKUP"]).split(" "):
            if not os.access(data, os.R_OK):
                msg = f"config DATA.DATA_TO_BACKUP contains unreadable path: {data}"
                logger.error(msg)
                return {"is_working": False, "msg": msg}

    return {"is_working": True, "msg": "Configurations file DATA section variables is valid."}

def check_mariadb_vars(logger:logging.Logger, toml_config:dict) -> dict:
    # Check if MARIADB.USE is True
    if toml_config["MARIADB"]["USE"]:
        # Check if MARIADBDUMP_BIN is not None
        if not toml_config["MARIADB"]["MARIADBDUMP_BIN"]:
            msg = "config MARIADB.MARIADBDUMP_BIN must be a valid path"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if MARIADB.MARIADBDUMP_BIN is a file.
        if not os.path.isfile(toml_config["MARIADB"]["MARIADBDUMP_BIN"]):
            msg = "config MARIADB.MARIADBDUMP_BIN must be a valid path"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if MARIADB.MARIADUMP_BIN is executable.
        if not os.access(toml_config["MARIADB"]["MARIADBDUMP_BIN"], os.X_OK):
            msg = "config MARIADB.MARIADBDUMP_BIN must be executable"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if MARIADB.ROOT_PASSWORD is not none
        if not toml_config["MARIADB"]["ROOT_PASSWORD"]:
            msg = "config MARIADB.ROOT_PASSWORD must be a string"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

    return {"is_working": True, "msg": "Configurations file MARIADB section variables is valid."}

def check_gpg_vars(logger:logging.Logger,toml_config:dict) -> dict:

    # Check if GPG_ENCRYPTION.USE is True.
    if toml_config["GPG_ENCRYPTION"]["USE"]:
        # Check if GPG_ENCRYPTION.GPG_BIN is a string
        if not isinstance(toml_config["GPG_ENCRYPTION"]["GPG_BIN"], str):
            msg = "config GPG_ENCRYPTION.GPG_BIN must be a string"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if GPG_ENCRYPTION.GPG_BIN is a file
        if not os.path.isfile(toml_config["GPG_ENCRYPTION"]["GPG_BIN"]):
            msg = "config GPG_ENCRYPTION.GPG_BIN must be a valid path"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if GPG_ENCRYPTION.GPG_BIN is executable
        if not os.access(toml_config["GPG_ENCRYPTION"]["GPG_BIN"], os.X_OK):
            msg = "config GPG_ENCRYPTION.GPG_BIN must be executable"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if GPG_ENCRYPTION.FINGERPRINT is a string.
        if not isinstance(toml_config["GPG_ENCRYPTION"]["PUBKEY_FINGERPRINT"], str):
            msg = "config GPG_ENCRYPTION.PUBKEY_FINGERPRINT must be a string"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if GPG_ENCRYPTION.FINGERPRINT is a valid fingerprint.
        if not re.match(r"^[A-Fa-f0-9]{40}$", toml_config["GPG_ENCRYPTION"]["PUBKEY_FINGERPRINT"]):
            msg = "config GPG_ENCRYPTION.PUBKEY_FINGERPRINT must be a valid fingerprint"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if GPG_ENCRYPTION.FINGERPRINT key exist in keystore
        gpg = gnupg.GPG(gpgbinary=toml_config["GPG_ENCRYPTION"]["GPG_BIN"])
        gpg.encoding = 'utf-8'

        if not gpg.list_keys(secret=False, keys=toml_config["GPG_ENCRYPTION"]["PUBKEY_FINGERPRINT"]):
            msg = "config GPG_ENCRYPTION.PUBKEY_FINGERPRINT " + toml_config["GPG_ENCRYPTION"]["PUBKEY_FINGERPRINT"] +" key is not in keystore"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

    return {"is_working": True, "msg": "Configurations file GPG section variables is valid."}

def check_backup_receiver_vars(logger:logging.Logger,toml_config:dict) -> dict:
    # Check if BACKUP_RECEIVER.USE is True
    if toml_config["BACKUP_RECEIVER"]["USE"]:
        # Check if BACKUP_RECEIVER.URL is a string.
        if not isinstance(toml_config["BACKUP_RECEIVER"]["URL"], str):
            msg = "config BACKUP_RECEIVER.URL must be a string"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if BACKUP_RECEIVER.URL is a valid URL.
        if not re.match(r"^https?://", toml_config["BACKUP_RECEIVER"]["URL"]):
            msg = "config BACKUP_RECEIVER.URL must be a valid URL"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

        # Check if BACKUP_RECEIVER.PASSWORD is a string.
        if not isinstance(toml_config["BACKUP_RECEIVER"]["PASSWORD"], str):
            msg = "config BACKUP_RECEIVER.PASSWORD must be a string"
            logger.error(msg)
            return {"is_working": False, "msg": msg}

    return {"is_working": True, "msg": "Configurations file BACKUP_RECEIVER section variables is valid."}

def check_config(logger:logging.Logger, toml_config:dict) -> dict:
    """Check if the configuration is valid."""
    # Check if toml_config is None.
    if not toml_config:
        msg = "No configuration provided."
        logger.error(msg)
        return {"is_working": False, "msg": msg}

    # Check the main variables in toml_config.
    results_check_main_vars = check_main_vars(logger, toml_config)
    if not results_check_main_vars["is_working"]:
        return results_check_main_vars

    # Check DATA sektion vars in toml_config.
    results_check_data_vars = check_data_vars(logger, toml_config)
    if not results_check_data_vars["is_working"]:
        return results_check_data_vars


    # Check MARIADB sektion vars in toml_config.
    results_check_mariadb_vars = check_mariadb_vars(logger, toml_config)
    if not results_check_mariadb_vars["is_working"]:
        return results_check_mariadb_vars


    # Check GPG_ENCRYPTION sektion vars in toml_config.
    results_check_gpg_vars = check_gpg_vars(logger, toml_config)
    if not results_check_gpg_vars["is_working"]:
        return results_check_gpg_vars


    # Check BACKUP_RECEIVER sektion vars in toml_config.
    results_check_backup_receiver_vars = check_backup_receiver_vars(logger, toml_config)
    if not results_check_backup_receiver_vars["is_working"]:
        return results_check_backup_receiver_vars

    return {"is_working": True, "msg": "Configuration is valid"}
