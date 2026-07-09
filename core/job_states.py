import json

from core.config_store import DATA_DIR

STATES_FILE = DATA_DIR / "job_states.json"


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
