import configparser
import os
import subprocess
from datetime import date

# Import configuration file.
config = configparser.ConfigParser()
config.read('config.ini')

# Working folder.
tmp_folder = config["DEFAULT"]["tmp_folder"]

# Backups will be saved to this folder.
save_backups_to = config["DEFAULT"]["save_backups_to"]

# The folder to take backups on.
folders_to_backup = str.split(config["DEFAULT"]["folders_to_backup"])

# Tar bin location.
tar_bin = config["DEFAULT"]["tar_bin"]

# Mariadb-dump bin location.
mariadbdump_bin = config["DEFAULT"]["mariadbdump_bin"]

mariadb_root_password = config["mariadb"]["root_password"]

# Create working folder.
if not os.path.exists(tmp_folder): 
    os.makedirs(tmp_folder) 

# Create folder to save backups to.
if not os.path.exists(save_backups_to): 
    os.makedirs(save_backups_to)

# Create working folder for todays date.
today = str(date.today())
if not os.path.exists(tmp_folder + "/" + today): 
    os.makedirs(tmp_folder + "/" + today)
tmp_folder_date = tmp_folder + "/" + today

# Take backup of folders in folders_to_backup.
for folder in folders_to_backup:
    # Create tar archive name.
    backup_name = folder.replace("/","_") + ".tar.gz"
    try:
        output = subprocess.run([tar_bin,"-czf",tmp_folder_date + "/" + backup_name,folder], check=True)
        if output.returncode != 0:
            print("error: returncode of cmd tar is non zero")
    except subprocess.CalledProcessError as e:
        print("error: returncode of cmd tar is non zero")
    except:
        print("error: unkonwn exception running subprocess with tar")

# Take backup of mariadb databases.
if config["mariadb"].getboolean("take_backup") == True:
    try:
        f = open(tmp_folder_date + "/" + "full_db_dump.sql","w")
        output = subprocess.run([mariadbdump_bin,"-h","localhost","--all-databases","-uroot","-p" + mariadb_root_password], check=True, stdout = f)
        if output.returncode != 0:
            print("error: returncode of cmd mysqldump is non zero")
    except subprocess.CalledProcessError as e:
        print("error: returncode of cmd mysqldump is non zero")
    except:
        print("error: unknown exception running subprocess with mysqldump")
