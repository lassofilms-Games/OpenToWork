import re

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


def score_job(title, description, company, location, profile_keywords=None, active_roles=None):
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
        if role_l and role_l in title_l:
            score += 50
            found.append(f"role_title:{role_l}")
            role_hit = True
        elif role_l and role_l in text:
            score += 25
            found.append(f"role_text:{role_l}")
            role_hit = True
    for k, pts in profile_keywords.items():
        if k in text:
            score += pts
            found.append(k)
    for bad in EXCLUDE_KEYWORDS:
        if bad in text:
            score -= 35
            found.append(f"exclude:{bad}")
    if active_roles and not role_hit and not title.lower().startswith("buscar:"):
        score -= 25
        found.append("penalty:no_active_category")
    return max(0, min(100, score)), found
