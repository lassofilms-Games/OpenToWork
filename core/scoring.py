import re
from datetime import datetime

DEFAULT_PROFILE_KEYWORDS = {
    "comfyui": 20,
    "stable diffusion": 15,
    "generative ai": 15,
    "genai": 15,
    "ai video": 15,
    "video generation": 15,
    "blender": 12,
    "unity": 12,
    "unreal": 12,
    "3d": 10,
    "vfx": 10,
    "motion": 8,
    "lead": 10,
    "senior": 10,
    "remote": 10,
    "barcelona": 12,
    "spain": 8,
}

EXCLUDE_KEYWORDS = [
    "customer support", "call center", "sales representative", "account executive",
    "data analyst", "qa rater", "medical", "administrative assistant", "bookkeeper",
    "nurse", "driver", "teacher", "real estate", "crypto trader"
]


def normalize_text(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def freshness_bonus(published, now=None):
    """Prima la actualidad de la oferta: +10 si tiene una semana o menos,
    0 hasta 30 días, -10 si es más antigua. Fechas ilegibles no puntúan."""
    try:
        if isinstance(published, (int, float)):
            dt = datetime.fromtimestamp(published)
        else:
            dt = datetime.fromisoformat(str(published)[:10])
    except (ValueError, OSError, OverflowError):
        return 0
    age_days = ((now or datetime.now()) - dt).days
    if age_days < 0:
        return 0
    if age_days <= 7:
        return 10
    if age_days <= 30:
        return 0
    return -10


def all_words_match(text, phrase):
    # Todas las palabras de la frase presentes como palabras enteras,
    # en cualquier orden ("ai creative director" cuenta para "creative ai").
    words = phrase.split()
    return bool(words) and all(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def phrase_in_text(text, phrase):
    # Frase presente como palabras enteras ("ai" no coincide dentro de "email").
    phrase = (phrase or "").strip()
    if not phrase:
        return False
    return bool(re.search(r"\b" + re.escape(phrase) + r"\b", text))


def score_job(title, description, company, location, profile_keywords=None, active_roles=None, is_search_link=False):
    text = f"{title} {description} {company} {location}".lower()
    title_l = (title or "").lower()
    profile_keywords = profile_keywords or DEFAULT_PROFILE_KEYWORDS
    active_roles = active_roles or []
    score = 0
    found = []
    # Prioridad alta a la categoría real seleccionada
    role_hit = False
    for role in active_roles:
        role_l = role.lower()
        if not role_l:
            continue
        if role_l in title_l:
            score += 50
            found.append(f"role_title:{role_l}")
            role_hit = True
        elif all_words_match(title_l, role_l):
            score += 40
            found.append(f"role_title_words:{role_l}")
            role_hit = True
        elif role_l in text:
            score += 25
            found.append(f"role_text:{role_l}")
            role_hit = True
        elif all_words_match(text, role_l):
            score += 15
            found.append(f"role_text_words:{role_l}")
            role_hit = True
    for k, pts in profile_keywords.items():
        if phrase_in_text(text, k) or all_words_match(text, k):
            score += pts
            found.append(k)
    for bad in EXCLUDE_KEYWORDS:
        if phrase_in_text(text, bad):
            score -= 35
            found.append(f"exclude:{bad}")
    if active_roles and not role_hit and not is_search_link:
        score -= 25
        found.append("penalty:no_active_category")
    return max(0, min(100, score)), found
