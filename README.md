# What is ddmail_backup_taker
Application to handle backups for the ddmail project. 

## Features
- Backups of folders/files and mariadb databases. 
- Storing backups in encrypted form "at rest" using OpenPGP.
- Store backups local and/or offsite using ddmail_backup_receiver.

## What is ddmail
DDMail is a e-mail system/service and e-mail provider with strong focus on security, privacy and anonymity. A current production example can be found at www.ddmail.se

## Operating system
Developt for and tested on debian 12.

## Coding
Follow PEP8 and PEP257. Use Flake8 with flake8-docstrings for linting. Strive for 100% test coverage.
