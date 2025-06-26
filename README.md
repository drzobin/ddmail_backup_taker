# What is ddmail_backup_taker
Application to handle backups for the DDMail project.

## Features
- Backups of folders/files and mariadb databases.
- Storing backups in encrypted form "at rest" using OpenPGP.
- Sending backups offsite using ddmail_backup_receiver.

## What is DDMail
DDMail is a e-mail system/service that prioritizes security. A current production example can be found at www.ddmail.se

## Operating system
Developt for and tested on debian 12.

## Installing using pip
`pip install ddmail-backup-taker`

## Building and installing from source using hatchling.
Step 1: clone github repo<br>
`git clone https://github.com/drzobin/ddmail_backup_taker [code path]`<br>
`cd [code path]`<br>
<br>
Step 2: Setup python virtual environments<br>
`python -m venv [venv path]`<br>
`source [venv path]/bin/activate`<br>
<br>
Step 3: Install package and required dependencies<br>
`pip install -e .[dev]`<br>
<br>
Step 4: Build package<br>
`python -m pip install --upgrade build`<br>
`python -m build`<br>
<br>
Packages is now located under dist folder<br>
<br>
Step 5: Install package<br>
`pip install dist/[package name].whl`<br>

## Running
`source [ddmail_backup_taker venv]/bin/activate`<br>
`ddmail_backup_taker --config-file [config file path]`<br>

## Testing
`cd [code path]`<br>
`pytest --cov=ddmail_backup_taker tests/ --config=[config file path]`

## Coding
Follow PEP8 and PEP257. Use Flake8 with flake8-docstrings for linting. Strive for 100% test coverage.
