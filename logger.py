# Your software must produce a log file stored in the location named
# in the environment bariable $LOG_FILE and using the verbosity level
# indicated in the environment variable $LOG_LEVEL
# 0 means silent
# 1 means informational messags
# 2 means debug messages
# Default log verbosity is 0
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# read env vars once
LOG_FILE = os.environ.get("LOG_FILE")
LOG_LEVEL = int(os.environ.get("LOG_LEVEL", 0))  # default to 0

# Validate LOG_FILE early and narrow its type for type checkers
if not LOG_FILE:
    # Missing or empty path - cannot proceed
    sys.exit(1)
if not os.path.isfile(LOG_FILE):
    # If the file doesn't exist, try to create the containing directory then create the file
    dirpath = os.path.dirname(LOG_FILE) or "."
    try:
        os.makedirs(dirpath, exist_ok=True)
        open(LOG_FILE, "w").close()
    except Exception:
        sys.exit(1)

# At this point LOG_FILE is a non-empty path string; narrow for mypy
assert LOG_FILE is not None
LOG_FILE_PATH: str = LOG_FILE

# Start with a blank log file each time (ensure writable)
open(LOG_FILE_PATH, "w").close()

# Then open file in append mode and write message
# LOG_LEVEL 1 informational messages


def info(msg: str):
    if LOG_LEVEL >= 1:
        with open(LOG_FILE_PATH, "a") as log_file:
            log_file.write("Info:" + msg + "\n")

# LOG_LEVEL 2 debug messages
# This will include info and debug messages


def debug(msg: str):
    if LOG_LEVEL == 2:
        with open(LOG_FILE_PATH, "a") as log_file:
            log_file.write("Debug:" + msg + "\n")
