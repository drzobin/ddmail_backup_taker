import configparser
import os
import shutil
import logging
import glob
import sys

config = configparser.ConfigParser()
conf_file = sys.argv[1]

# Check that conf_file is a file.
if os.path.isfile(conf_file) == False:
    print("Error: can not open config file")
    sys.exit(1)

# Import configuration file from cmd arg.
config.read(conf_file)

# Working folder.
tmp_folder = config["DEFAULT"]["tmp_folder"]

# Backups will be saved to this folder.
save_backups_to = config["DEFAULT"]["save_backups_to"]

# Configure logging.
logging.basicConfig(filename=config["logging"]["logfile"], format='%(asctime)s: %(levelname)s: %(message)s', level=logging.INFO)

# Check if save_backups_to is a folder.
if not os.path.exists(save_backups_to): 
    logging.error("can not find folder where backups are saved")

# Get list of all files only in the given directory
list_of_files = filter(os.path.isfile, glob.glob(save_backups_to + '/*.zip'))

# Sort list of files based on last modification time in ascending order
list_of_files = sorted(list_of_files, key = os.path.getmtime)

# If we have less or equal of 7 backups then exit.
if len(list_of_files) <= 7:
    logging.info("we have less then or equals to 7 backups saved, exit without doing anything")
    sys.exit(0)

list_of_files.reverse()
count = 0

# Only save 7 days of backups, remove other.
for file in list_of_files:
    count = count + 1
    if count <= 7:
        continue
    else:
        os.remove(save_backups_to + "/" + file)
        logging.info("removing: " + save_backups_to + "/" + file)
