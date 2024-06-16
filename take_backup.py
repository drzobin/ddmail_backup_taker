import configparser
import os
import subprocess
import shutil
import logging
import datetime
import sys
import argparse

# Get arguments from args.
parser = argparse.ArgumentParser(description="Backup for ddmail")
parser.add_argument('--config-file', type=str, help='Full path to config file.', required=True)
args = parser.parse_args()

# Check that config file exsist and is a file.
if os.path.isfile(args.config_file) != True:
    print("config file do not exist or is not a file.")
    sys.exit(1)

# Import config file.
config = configparser.ConfigParser()
conf_file = args.config_file
config.read(conf_file)
    
# Configure logging.
logging.basicConfig(filename=config["logging"]["logfile"], format='%(asctime)s: %(levelname)s: %(message)s', level=logging.ERROR)

# Take backup of folders.
def backup_folders(tar_bin, folders_to_backup, tmp_folder_date):
    # Take backup of folders in folders_to_backup.
    for folder in folders_to_backup:
        # Create tar archive name.
        backup_name = folder.replace("/","_") + ".tar.gz"

        try:
            output = subprocess.run([tar_bin,"-czf", tmp_folder_date + "/" + backup_name, folder], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if output.returncode != 0:
                logging.error("returncode of cmd tar is non zero")
        except subprocess.CalledProcessError as e:
            logging.error("returncode of cmd tar is non zero")
        except:
            logging.error("unkonwn exception running subprocess with tar")

# Take backup of mariadb databases.
def backup_mariadb(mariadbdump_bin, mariadb_root_password, tmp_folder_date):
    try:
        f = open(tmp_folder_date + "/" + "full_db_dump.sql","w")
        output = subprocess.run([mariadbdump_bin,"-h","localhost","--all-databases","-uroot","-p" + mariadb_root_password], check=True, stdout = f)
        if output.returncode != 0:
            logging.error("returncode of cmd mysqldump is none zero")
    except subprocess.CalledProcessError as e:
        logging.error("returncode of cmd mysqldump is none zero")
    except:
        logging.error("unknown exception running subprocess with mysqldump")

if __name__ == "__main__":
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

    # Take backup og folers.
    backup_folders(tar_bin, folders_to_backup, tmp_folder_date)
    
    # Take backup of mariadb all databases.
    if config["mariadb"].getboolean("take_backup") == True:
        backup_mariadb(mariadbdump_bin, mariadb_root_password, tmp_folder_date)

    # Compress all files with zip.
    shutil.make_archive(save_backups_to + "/" + "backup." + today, 'zip', tmp_folder_date)

    # Change premissions on backupsfile.
    os.chmod(save_backups_to + "/" + "backup." + today + ".zip", 0o640)

    # Remove content in tmp folder.
    shutil.rmtree(tmp_folder_date)
