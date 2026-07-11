from pathlib import Path

APP_NAME = "OpenToWork"
APP_VERSION = "1.4.0"
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

# Fuentes agrupadas por categoría para que el sidebar no sea un muro de
# checkboxes: cada grupo se muestra plegado con un contador activas/total.
# La clave de grupo es una clave i18n; el bool es el estado por defecto
# (las fuentes históricas conservan su valor; las nuevas entran apagadas
# para no disparar decenas de enlaces de búsqueda de golpe).
DEFAULT_SOURCE_GROUPS = [
    ("source_group_public", {
        "Empléate": False,
        "Infoempleo": False,
        "EURES": False,
        "Feina Activa": False,
        "SAE Empleo": False,
        "Lanbide": False,
    }),
    ("source_group_general", {
        "InfoJobs": True,
        "LinkedIn Jobs": True,
        "Google Empleos": False,
        "JobToday": False,
        "Job&Talent": False,
        "Adzuna": False,
        "Jooble España": False,
    }),
    ("source_group_specialized", {
        "TuriJobs": False,
        "Tecnoempleo": False,
        "Domestika Jobs": False,
        "Jobgether": False,
        "Malt": False,
        "JobFluent": False,
        "Work With Indies": True,
        "Hitmarker": True,
        "Creativepool Jobs": True,
        "ArtStation Jobs": False,
    }),
    ("source_group_international", {
        "Indeed": False,
        "AnyWorkAnywhere": False,
        "Glassdoor Jobs": False,
        "Workaway": False,
        "Relocate.me": False,
        "Go Overseas": False,
    }),
    ("source_group_remote", {
        "FlexJobs": False,
        "Jobspresso": False,
        "Remote.co": False,
        "Wellfound": True,
        "Working Nomads": False,
        "PeoplePerHour": False,
    }),
    ("source_group_apis", {
        "RemoteOK API": True,
        "Remotive API": True,
        "Arbeitnow API": True,
        "Jobicy API": True,
    }),
]

# Vistas derivadas: dict plano nombre->activada (compatibilidad con la config
# guardada) y nombre->grupo (para colocar cada fila en su categoría de la UI).
DEFAULT_SOURCES = {name: enabled for _, group in DEFAULT_SOURCE_GROUPS for name, enabled in group.items()}
SOURCE_GROUP_OF = {name: key for key, group in DEFAULT_SOURCE_GROUPS for name in group}
SOURCE_GROUP_OTHER = "source_group_other"
