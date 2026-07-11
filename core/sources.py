import re
import time
import urllib.parse
from datetime import datetime

from constants import APP_NAME, APP_VERSION
from core.scoring import normalize_text, score_job, all_words_match, freshness_bonus
from i18n import t

# Caché en memoria de las respuestas de las APIs: RemoteOK devuelve su feed
# completo en cada llamada y Remotive consulta una URL por rol; repetir una
# búsqueda a los pocos minutos no debería volver a descargarlo todo.
_CACHE_TTL_SECONDS = 15 * 60
_api_cache = {}


def _cache_get(key):
    entry = _api_cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _cache_set(key, value):
    _api_cache[key] = (time.time(), value)

try:
    import requests
except ImportError:
    requests = None

SOURCE_DOMAINS = {
    # Empleo público
    "Empléate": "empleate.gob.es",
    "Infoempleo": "infoempleo.com",
    "EURES": "eures.europa.eu",
    "Feina Activa": "feinaactiva.gencat.cat",
    "SAE Empleo": "saempleo.es",
    "Lanbide": "lanbide.euskadi.eus",
    # Generalistas
    "InfoJobs": "infojobs.net",
    "LinkedIn Jobs": "linkedin.com/jobs",
    "Google Empleos": "google.com",
    "JobToday": "jobtoday.com",
    "Job&Talent": "jobandtalent.es",
    "Adzuna": "adzuna.es",
    "Jooble España": "es.jooble.org",
    # Especializados
    "TuriJobs": "turijobs.com",
    "Tecnoempleo": "tecnoempleo.com",
    "Domestika Jobs": "domestika.org/es/jobs",
    "Jobgether": "jobgether.com",
    "Malt": "malt.es",
    "JobFluent": "jobfluent.com",
    "Work With Indies": "workwithindies.com",
    "Hitmarker": "hitmarker.net/jobs",
    "Creativepool Jobs": "creativepool.com/jobs",
    "ArtStation Jobs": "artstation.com/jobs",
    # Internacional
    "Indeed": "indeed.com",
    "AnyWorkAnywhere": "anyworkanywhere.com",
    "Glassdoor Jobs": "glassdoor.es/Job",
    "Workaway": "workaway.info",
    "Relocate.me": "relocate.me",
    "Go Overseas": "gooverseas.com",
    # Trabajo remoto
    "FlexJobs": "flexjobs.com",
    "Jobspresso": "jobspresso.co",
    "Remote.co": "remote.co",
    "Wellfound": "wellfound.com/jobs",
    "Working Nomads": "workingnomads.com",
    "PeoplePerHour": "peopleperhour.com",
}

# Fuentes que devuelven ofertas reales vía API (no generan enlaces de búsqueda).
API_SOURCES = ("RemoteOK API", "Remotive API", "Arbeitnow API", "Jobicy API")


class SourceFetchError(Exception):
    def __init__(self, source, kind, message):
        super().__init__(message)
        self.source = source
        self.kind = kind
        self.message = message


def _classify_requests_error(source, error):
    if isinstance(error, requests.exceptions.Timeout):
        return SourceFetchError(source, "timeout", f"{source}: time out al consultar la fuente.")
    if isinstance(error, requests.exceptions.ConnectionError):
        return SourceFetchError(source, "connection", f"{source}: no se pudo establecer conexión con el servidor.")
    if isinstance(error, requests.exceptions.HTTPError):
        status = getattr(getattr(error, "response", None), "status_code", "desconocido")
        return SourceFetchError(source, "api", f"{source}: la API devolvio un error HTTP {status}.")
    if isinstance(error, ValueError):
        return SourceFetchError(source, "invalid_response", f"{source}: la respuesta recibida no tiene un formato valido.")
    return SourceFetchError(source, "api", f"{source}: fallo al consultar la fuente.")


def _handle_requests_call(source, url, timeout=18, headers=None):
    if requests is None:
        raise SourceFetchError(source, "dependency", f"{source}: falta la dependencia 'requests'.")
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as error:
        raise _classify_requests_error(source, error) from error


def build_google_url(role, location, domain):
    query = f'site:{domain} "{role}" "{location}" job apply'
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def build_source_url(source, role, location, source_domains=None):
    domains = SOURCE_DOMAINS if source_domains is None else source_domains
    q = urllib.parse.quote_plus(role)
    loc = urllib.parse.quote_plus(location)
    if source == "Google Empleos":
        # Panel nativo de empleo de Google (ibp=htl;jobs).
        return f"https://www.google.com/search?q={q}+{loc}&ibp=htl;jobs"
    if source == "Indeed":
        return f"https://es.indeed.com/jobs?q={q}&l={loc}"
    if source == "LinkedIn Jobs":
        return f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}"
    if source == "Wellfound":
        return f"https://wellfound.com/jobs?keywords={q}"
    if source == "Work With Indies":
        return f"https://www.workwithindies.com/jobs?search={q}"
    if source == "Hitmarker":
        return f"https://hitmarker.net/jobs?keyword={q}&location={loc}"
    if source == "Creativepool Jobs":
        return f"https://creativepool.com/jobs?keyword={q}"
    if source == "InfoJobs":
        return f"https://www.infojobs.net/jobsearch/search-results/list.xhtml?keyword={q}&province=Barcelona"
    if source == "Glassdoor Jobs":
        return f"https://www.glassdoor.es/Empleo/{loc}-{q}-empleos-SRCH_IL.0,9_IC2629524_KO10,{10+len(role)}.htm"
    if source == "ArtStation Jobs":
        return f"https://www.artstation.com/jobs?search={q}"
    return build_google_url(role, location, domains.get(source, ""))


def make_search_links(roles, locations, sources, profile_keywords=None, source_domains=None, lang="es"):
    domains = SOURCE_DOMAINS if source_domains is None else source_domains
    jobs = []
    for role in roles:
        for loc in locations:
            for src in sources:
                if src in API_SOURCES:
                    continue
                domain = domains.get(src, "")
                direct = build_source_url(src, role, loc, domains)
                google = build_google_url(role, loc, domain) if domain else direct
                title = t(lang, "search_link_title", role=role)
                desc = t(lang, "search_link_description", src=src, role=role, loc=loc)
                # Los enlaces de búsqueda no se puntúan: no son ofertas y su
                # propia descripción contiene el rol, lo que inflaba el match
                # a 100% y enterraba a las ofertas reales.
                jobs.append({
                    "match": 0,
                    "title": title,
                    "company": "-",
                    "location": loc,
                    "remote": "Remote" if "remote" in loc.lower() else "Hybrid/On-site possible",
                    "source": src,
                    "published_date": t(lang, "not_available"),
                    "detected_date": datetime.now().strftime("%Y-%m-%d"),
                    "apply_url": direct,
                    "fallback_url": google,
                    "description": desc,
                    "skills_found": "",
                    "type": "search_link"
                })
    return jobs


def _matches_role_terms(text, role_terms):
    # Relacionado al rol = frase completa, o TODAS sus palabras como
    # palabras enteras en cualquier orden. Lo que no cumple esto no
    # le interesa al usuario y se descarta directamente.
    for term in role_terms:
        if term in text or all_words_match(text, term):
            return True
    return False


def fetch_remoteok(roles, profile_keywords=None, limit=40, lang="es"):
    results = []
    data = _cache_get("remoteok")
    if data is None:
        url = "https://remoteok.com/api"
        headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
        response = _handle_requests_call("RemoteOK API", url, headers=headers)
        try:
            data = response.json()
        except ValueError as error:
            raise SourceFetchError("RemoteOK API", "invalid_response", "RemoteOK API: la respuesta JSON no es valida.") from error
        _cache_set("remoteok", data)
    role_terms = [x.lower() for x in roles]
    not_available = t(lang, "not_available")
    for item in data[1:]:
        title = normalize_text(item.get("position") or item.get("title"))
        company = normalize_text(item.get("company"))
        desc = normalize_text(item.get("description"))
        tags = " ".join(item.get("tags") or [])
        text = f"{title} {company} {desc} {tags}".lower()
        if not _matches_role_terms(text, role_terms):
            continue
        loc = normalize_text(item.get("location") or "Remote")
        apply = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id','')}"
        raw_published = item.get("date") or item.get("epoch")
        score, found = score_job(title, desc + " " + tags, company, loc, profile_keywords, roles)
        score = max(0, min(100, score + freshness_bonus(raw_published)))
        results.append({
            "match": score,
            "title": title,
            "company": company,
            "location": loc,
            "remote": "Remote",
            "source": "RemoteOK API",
            "published_date": str(raw_published)[:10] if raw_published else not_available,
            "detected_date": datetime.now().strftime("%Y-%m-%d"),
            "apply_url": apply,
            "fallback_url": apply,
            "description": desc[:3000],
            "skills_found": ", ".join(found),
            "type": "api_result"
        })
    return results[:limit]


def fetch_remotive(roles, profile_keywords=None, limit=40, lang="es"):
    results = []
    role_terms = [x.lower() for x in roles]
    not_available = t(lang, "not_available")
    for role in roles[:8]:
        data = _cache_get(("remotive", role.lower()))
        if data is None:
            q = urllib.parse.quote_plus(role)
            url = f"https://remotive.com/api/remote-jobs?search={q}"
            response = _handle_requests_call("Remotive API", url)
            try:
                data = response.json().get("jobs", [])
            except ValueError as error:
                raise SourceFetchError("Remotive API", "invalid_response", "Remotive API: la respuesta JSON no es valida.") from error
            _cache_set(("remotive", role.lower()), data)
        for item in data:
            title = normalize_text(item.get("title"))
            company = normalize_text(item.get("company_name"))
            desc = normalize_text(re.sub(r"<[^>]+>", " ", item.get("description") or ""))
            text = f"{title} {company} {desc}".lower()
            if not _matches_role_terms(text, role_terms):
                continue
            loc = normalize_text(item.get("candidate_required_location") or "Remote")
            apply = item.get("url") or ""
            raw_published = item.get("publication_date")
            score, found = score_job(title, desc, company, loc, profile_keywords, roles)
            score = max(0, min(100, score + freshness_bonus(raw_published)))
            results.append({
                "match": score,
                "title": title,
                "company": company,
                "location": loc,
                "remote": "Remote",
                "source": "Remotive API",
                "published_date": str(raw_published)[:10] if raw_published else not_available,
                "detected_date": datetime.now().strftime("%Y-%m-%d"),
                "apply_url": apply,
                "fallback_url": apply,
                "description": desc[:3000],
                "skills_found": ", ".join(found),
                "type": "api_result"
            })
    # dedupe
    seen = set()
    out = []
    for j in results:
        key = (j["title"].lower(), j["company"].lower(), j["source"])
        if key not in seen:
            seen.add(key); out.append(j)
    return out[:limit]


def fetch_arbeitnow(roles, profile_keywords=None, limit=40, lang="es"):
    # Job board europeo (base en Alemania), API pública sin key. Devuelve el
    # feed completo paginado; con la primera página basta y se filtra por rol.
    results = []
    data = _cache_get("arbeitnow")
    if data is None:
        url = "https://www.arbeitnow.com/api/job-board-api"
        response = _handle_requests_call("Arbeitnow API", url)
        try:
            data = response.json().get("data", [])
        except ValueError as error:
            raise SourceFetchError("Arbeitnow API", "invalid_response", "Arbeitnow API: la respuesta JSON no es valida.") from error
        _cache_set("arbeitnow", data)
    role_terms = [x.lower() for x in roles]
    not_available = t(lang, "not_available")
    for item in data:
        title = normalize_text(item.get("title"))
        company = normalize_text(item.get("company_name"))
        desc = normalize_text(re.sub(r"<[^>]+>", " ", item.get("description") or ""))
        tags = " ".join((item.get("tags") or []) + (item.get("job_types") or []))
        text = f"{title} {company} {desc} {tags}".lower()
        if not _matches_role_terms(text, role_terms):
            continue
        is_remote = bool(item.get("remote"))
        loc = normalize_text(item.get("location")) or ("Remote" if is_remote else "-")
        apply = item.get("url") or ""
        raw_published = item.get("created_at")
        try:
            published = datetime.fromtimestamp(raw_published).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError, OverflowError):
            published = not_available
        score, found = score_job(title, desc + " " + tags, company, loc, profile_keywords, roles)
        score = max(0, min(100, score + freshness_bonus(raw_published)))
        results.append({
            "match": score,
            "title": title,
            "company": company,
            "location": loc,
            "remote": "Remote" if is_remote else "Hybrid/On-site possible",
            "source": "Arbeitnow API",
            "published_date": published,
            "detected_date": datetime.now().strftime("%Y-%m-%d"),
            "apply_url": apply,
            "fallback_url": apply,
            "description": desc[:3000],
            "skills_found": ", ".join(found),
            "type": "api_result"
        })
    return results[:limit]


def fetch_jobicy(roles, profile_keywords=None, limit=40, lang="es"):
    # Portal de empleo remoto con API pública sin key; admite un keyword por
    # consulta, así que se lanza una por rol (como Remotive).
    results = []
    role_terms = [x.lower() for x in roles]
    not_available = t(lang, "not_available")
    for role in roles[:8]:
        data = _cache_get(("jobicy", role.lower()))
        if data is None:
            q = urllib.parse.quote_plus(role)
            url = f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={q}"
            headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
            response = _handle_requests_call("Jobicy API", url, headers=headers)
            try:
                payload = response.json()
            except ValueError as error:
                raise SourceFetchError("Jobicy API", "invalid_response", "Jobicy API: la respuesta JSON no es valida.") from error
            data = payload.get("jobs") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                data = []
            _cache_set(("jobicy", role.lower()), data)
        for item in data:
            title = normalize_text(item.get("jobTitle"))
            company = normalize_text(item.get("companyName"))
            desc = normalize_text(re.sub(r"<[^>]+>", " ", item.get("jobDescription") or item.get("jobExcerpt") or ""))
            text = f"{title} {company} {desc}".lower()
            if not _matches_role_terms(text, role_terms):
                continue
            loc = normalize_text(item.get("jobGeo")) or "Remote"
            apply = item.get("url") or ""
            raw_published = item.get("pubDate")
            score, found = score_job(title, desc, company, loc, profile_keywords, roles)
            score = max(0, min(100, score + freshness_bonus(raw_published)))
            results.append({
                "match": score,
                "title": title,
                "company": company,
                "location": loc,
                "remote": "Remote",
                "source": "Jobicy API",
                "published_date": str(raw_published)[:10] if raw_published else not_available,
                "detected_date": datetime.now().strftime("%Y-%m-%d"),
                "apply_url": apply,
                "fallback_url": apply,
                "description": desc[:3000],
                "skills_found": ", ".join(found),
                "type": "api_result"
            })
    seen = set()
    out = []
    for j in results:
        key = (j["title"].lower(), j["company"].lower(), j["source"])
        if key not in seen:
            seen.add(key); out.append(j)
    return out[:limit]


def dedupe_jobs(jobs):
    seen = set(); out = []
    for j in jobs:
        key = (j.get("title","" ).lower(), j.get("company","").lower(), j.get("apply_url","").lower())
        if key not in seen:
            seen.add(key); out.append(j)
    # Las ofertas reales siempre por delante de los enlaces de búsqueda;
    # dentro de cada grupo manda el match y luego la fecha de publicación.
    return sorted(
        out,
        key=lambda x: (x.get("type") == "api_result", x.get("match", 0), str(x.get("published_date", ""))),
        reverse=True,
    )
