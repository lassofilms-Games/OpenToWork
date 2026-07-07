import os
from pathlib import Path

from constants import BASE_DIR

APP_FOLDER_NAME = "OPentowork_app"
LEGACY_APP_FOLDER_NAMES = ["JobFinderPro"]


def _candidate_dirs(folder_name):
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / folder_name)
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates.append(Path(localappdata) / folder_name)
    candidates.append(Path.home() / f".{folder_name}")
    return candidates


def get_user_data_dir():
    candidates = _candidate_dirs(APP_FOLDER_NAME)
    candidates.append(BASE_DIR / "user_data")
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    fallback = BASE_DIR / "user_data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def find_legacy_appdata_config():
    for legacy_name in LEGACY_APP_FOLDER_NAMES:
        for candidate in _candidate_dirs(legacy_name):
            config_path = candidate / "config.json"
            if config_path.exists():
                return config_path
    return None


DATA_DIR = get_user_data_dir()
RESULTS_DIR = DATA_DIR / "results"
LOGS_DIR = DATA_DIR / "logs"
CONFIG_FILE = DATA_DIR / "config.json"
LEGACY_CONFIG_FILE = BASE_DIR / "config.json"
for folder in (RESULTS_DIR, LOGS_DIR):
    folder.mkdir(parents=True, exist_ok=True)
