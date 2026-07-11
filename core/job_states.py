import json
from datetime import datetime, timedelta

from core.config_store import DATA_DIR

STATES_FILE = DATA_DIR / "job_states.json"
SEEN_FILE = DATA_DIR / "seen_jobs.json"
# Una oferta desaparece del histórico de "vistas" pasados 90 días: si vuelve a
# publicarse después de tanto tiempo, merece marcarse como nueva otra vez.
SEEN_MAX_AGE_DAYS = 90


def job_key(job):
    # La URL de aplicar es el identificador más estable de una oferta:
    # sobrevive a nuevas búsquedas y es la clave del dedupe.
    return (job.get("apply_url") or "").strip().lower()


def load_states():
    try:
        if STATES_FILE.exists():
            data = json.loads(STATES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_states(states):
    STATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATES_FILE, "w", encoding="utf-8") as f:
        json.dump(states, f, indent=2, ensure_ascii=False)


def load_seen():
    """Histórico {job_key: fecha ISO de primera vez vista} para marcar nuevas."""
    try:
        if SEEN_FILE.exists():
            data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_seen(seen):
    cutoff = datetime.now() - timedelta(days=SEEN_MAX_AGE_DAYS)
    pruned = {}
    for key, date_str in seen.items():
        try:
            if datetime.fromisoformat(str(date_str)) >= cutoff:
                pruned[key] = date_str
        except ValueError:
            continue
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(pruned, f, indent=2, ensure_ascii=False)
