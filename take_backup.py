import configparser
import os

# Import configuration file.
config = configparser.ConfigParser()
config.read('config.ini')

# Working folder.
tmp_folder = config["DEFAULT"]["tmp_folder"]

# Backups will be saved to this folder.
save_backups_to = config["DEFAULT"]["save_backups_to"]

# The folder to take backups on.
folders_to_backup = str.split(config["DEFAULT"]["folders_to_backup"])

# Create working folder.
if not os.path.exists(tmp_folder): 
    os.makedirs(tmp_folder) 

# Create folder to save backups to
if not os.path.exists(save_backups_to): 
    os.makedirs(save_backups_to) 
