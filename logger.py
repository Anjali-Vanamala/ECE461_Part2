"""
Simple logging utility that writes messages to a file specified by the
environment variable LOG_FILE. Message verbosity is controlled by LOG_LEVEL:
0 = silent, 1 = info, 2 = debug.
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# read env vars once
LOG_FILE = os.environ.get("LOG_FILE")
LOG_LEVEL = int(os.environ.get("LOG_LEVEL", 0))  # default to 0
# Handle invalid LOG_FILE input
if LOG_FILE is None:
    sys.exit(1)

# Minimal fix: create the file if it doesn't exist
if not os.path.isfile(LOG_FILE):
    open(LOG_FILE, "w").close()
# At this point LOG_FILE is guaranteed to be a str, narrow type for mypy
assert LOG_FILE is not None
LOG_FILE_PATH: str = LOG_FILE

# Start with a blank log file each time
open(LOG_FILE_PATH, "w").close()
# Then open file in append mode and write message


def info(msg: str):
    """
    Log an informational message if LOG_LEVEL >= 1.

    Parameters
    ----------
    msg : str
        The message to write to the log file.
    """
    if LOG_LEVEL >= 1:
        with open(LOG_FILE_PATH, "a") as log_file:
            log_file.write("Info:" + msg + "\n")


def debug(msg: str):
    """
    Log a debug message if LOG_LEVEL == 2.

    Parameters
    ----------
    msg : str
        The debug message to write to the log file.
    """
    if LOG_LEVEL == 2:
        with open(LOG_FILE_PATH, "a") as log_file:
            log_file.write("Debug:" + msg + "\n")
