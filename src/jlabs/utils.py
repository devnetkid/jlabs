import json
import logging
import os
import platform
import time
from datetime import datetime
from pathlib import Path

import tomlkit

logger = logging.getLogger(__name__)


def setup_environment():
    # Define base directories
    base_dir = Path.home() / "jlabs"
    logs_dir = base_dir / "logs"
    labs_dir = base_dir / "labs"

    # Create folders if they don't exist
    logs_dir.mkdir(parents=True, exist_ok=True)
    labs_dir.mkdir(parents=True, exist_ok=True)

    # Dynamically create the log filename using current timestamp
    # logname = f"jlabs_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"
    log_file = "jlabs.log"

    # Check environment variables for log level, defaults to info if none provided
    log_level = getattr(logging, os.getenv("LABS_LOG_LEVEL", "info").upper(), None)
    if not isinstance(log_level, int):
        raise ValueError("Invalid log level")

    # Configure logging
    logging.basicConfig(
        filename=logs_dir / log_file,
        filemode="w",
        encoding="utf-8",
        level=log_level,
        format="%(asctime)s %(filename)20s:%(lineno)s %(levelname)11s > %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
    )


def get_state_file_path() -> Path:
    base_dir = Path.home() / "jlabs"
    """Returns the path to the hidden state file in the project root."""
    return base_dir / ".jlabs_state.json"


def load_state() -> dict:
    """Loads the state dictionary from the hidden JSON file."""
    state_file = get_state_file_path()
    if not state_file.exists():
        return {"last_lab_launched": None, "timestamp": None}

    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except Exception:
        # If the file is corrupted, return an empty tracking state
        return {"last_lab_launched": None, "timestamp": None}


def save_state(lab_name: str):
    """Updates the state file with the most recently launched lab."""
    state_file = get_state_file_path()
    state_data = {
        "last_lab_launched": lab_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=4)
        logger.info(f"State updated: last lab launched is '{lab_name}'")
    except Exception as e:
        logger.error(f"Failed to save state file: {e}")


def write_toml(filename, content):
    """
    Saves toml data to a file, prompting to overwrite if the file already exists.

    Args:
        filename (str): The file name.
        content (str): The toml data to write to the file.
    """
    config_path = Path.home() / "jlabs/labs/" / filename
    if config_path.exists():
        overwrite = input(f"File {filename} already exists. Overwrite? (y/n): ").lower()
        if overwrite != "y":
            print("File not saved.")
            return False
    try:
        with open(config_path, "w") as f:
            tomlkit.dump(content, f)
        print(f"File '{config_path}' saved successfully.")
        return True
    except IOError as err:
        print(f"Error saving file '{config_path}': {err}")


def load_toml(filename):
    """
    Loads toml data to memory.

    Args:
        filename (str): The file name to be loaded
    """
    config_path = Path.home() / "jlabs/labs/" / filename
    if not config_path.exists():
        print(f"File '{config_path}' does not exist.")
        return False
    try:
        with open(config_path, "r") as f:
            return tomlkit.load(f)
    except IOError as err:
        print(f"Error loading file '{config_path}': {err}")


def load_config(filename):
    """
    Loads a config file for use in eve-ng.

    Args:
        filename (str): The filename of the config to load.
    """
    config_path = Path.home() / "jlabs/labs/" / filename
    if not config_path.exists():
        print(f"File '{config_path}' does not exist.")
        return False
    try:
        with open(config_path, "r") as f:
            return f.readlines()
    except IOError as err:
        print(f"Error loading file '{config_path}': {err}")


def list_dir():
    """List the contents of a specified directory"""
    # Define base directories
    folders = []
    base_dir = Path.home() / "jlabs/labs"
    fullpath = [item for item in base_dir.iterdir() if item.is_dir()]
    for folder in fullpath:
        folders.append(folder.name)
    return folders


def colorme(msg, color):
    """
    Sets the terminal color requested, defaults to white

    Args:
        msg (str): The message to be displayed as color
        color (str): Sets the terminal color of msg
    """
    if color == "red":
        wrapper = "\033[91m"
    elif color == "blue":
        wrapper = "\033[94m"
    elif color == "green":
        wrapper = "\033[92m"
    else:
        # Defaults to white if invalid color is given
        wrapper = "\033[47m"
    return wrapper + msg + "\033[0m"


def clear_screen():
    """
    Runs the terminal clear screen command for the OS in use
    """
    if platform.system().lower() == "windows":
        cmd = "cls"
    else:
        cmd = "clear"
    os.system(cmd)


# https://www.asciiart.eu/text-to-ascii-art
menu_title = colorme(
    r"""
     _ _          _         
    | | |    __ _| |__  ___ 
 _  | | |   / _` | '_ \/ __|
| |_| | |__| (_| | |_) \__ \
 \___/|_____\__,_|_.__/|___/

""",
    "red",
)
