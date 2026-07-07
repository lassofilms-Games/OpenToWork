from pathlib import Path

APP_NAME = "OPentowork_app"
APP_VERSION = "1.3.0"
APP_AUTHOR = "Diego Lasso"
BASE_DIR = Path(__file__).resolve().parent

DEFAULT_ROLES = [
    "AI Content Creator",
    "AI Filmmaker",
    "Generative AI Artist",
    "Creative Technologist",
    "Senior 3D Artist",
    "Lead 3D Artist",
    "Technical Artist",
    "VFX Artist",
    "Motion Designer",
]

DEFAULT_LOCATIONS = [
    "Barcelona",
    "Spain",
    "Remote Spain",
    "Remote Europe",
]

DEFAULT_SOURCES = {
    "LinkedIn Jobs": True,
    "Wellfound": True,
    "Work With Indies": True,
    "Hitmarker": True,
    "Creativepool Jobs": True,
    "InfoJobs": True,
    "Glassdoor Jobs": False,
    "ArtStation Jobs": False,
    "RemoteOK API": True,
    "Remotive API": True,
}
