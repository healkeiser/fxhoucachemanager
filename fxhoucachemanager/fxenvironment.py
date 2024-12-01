# Built in
import os
from pathlib import Path
import shutil


# Package and default
FXCACHEMANAGER_PACKAGE_DIR = Path(__file__).resolve().parent
FXCACHEMANAGER_DEFAULT_CONFIG_PATH = FXCACHEMANAGER_PACKAGE_DIR / "config.ini"

# User data
FXCACHEMANAGER_DATA_DIR = (
    Path(os.getenv("APPDATA")) / "fxcachemanager"
    if os.name == "nt"
    else Path.home() / ".fxcachemanager"
)
FXCACHEMANAGER_LOG_DIR = FXCACHEMANAGER_DATA_DIR / "logs"
FXCACHEMANAGER_USER_CONFIG_PATH = FXCACHEMANAGER_DATA_DIR / "config.ini"


def create_user_data() -> None:
    """Create the user data directories and files."""

    FXCACHEMANAGER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    FXCACHEMANAGER_LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Copy the default `config.ini` to the user data directory if it
    # doesn't exist already
    if not FXCACHEMANAGER_USER_CONFIG_PATH.exists():
        shutil.copy(
            FXCACHEMANAGER_DEFAULT_CONFIG_PATH, FXCACHEMANAGER_USER_CONFIG_PATH
        )
