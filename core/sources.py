import re
import urllib.parse
from datetime import datetime

from constants import APP_NAME, APP_VERSION
from core.scoring import normalize_text, score_job
from i18n import t

try:
    import requests
except ImportError:
    requests = None

SOURCE_DOMAINS = {
    "LinkedIn Jobs": "linkedin.com/jobs",
    "Wellfound": "wellfound.com/jobs",
    "Work With Indies": "workwithindies.com",
    "Hitmarker": "hitmarker.net/jobs",
    "Creativepool Jobs": "creativepool.com/jobs",
    "InfoJobs": "infojobs.net",
    "Glassdoor Jobs": "glassdoor.es/Job",
    "ArtStation Jobs": "artstation.com/jobs",
}


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
                if src in ["RemoteOK API", "Remotive API"]:
                    continue
                domain = domains.get(src, "")
                direct = build_source_url(src, role, loc, domains)
                google = build_google_url(role, loc, domain) if domain else direct
                title = t(lang, "search_link_title", role=role)
                desc = t(lang, "search_link_description", src=src, role=role, loc=loc)
                score, found = score_job(title, desc, src, loc, profile_keywords, roles, is_search_link=True)
                jobs.append({
                    "match": score,
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
                    "skills_found": ", ".join(found),
                    "type": "search_link"
                })
    return jobs


def _matches_role_terms(text, role_terms):
    # Frase completa del rol, o alguna de sus palabras como palabra entera
    # (con \b para que "ai" no coincida dentro de "email" o "available").
    for term in role_terms:
        if term in text:
            return True
        for word in term.split():
            if re.search(r"\b" + re.escape(word) + r"\b", text):
                return True
    return False


def fetch_remoteok(roles, profile_keywords=None, limit=40, lang="es"):
    results = []
    url = "https://remoteok.com/api"
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    response = _handle_requests_call("RemoteOK API", url, headers=headers)
    try:
        data = response.json()
    except ValueError as error:
        raise SourceFetchError("RemoteOK API", "invalid_response", "RemoteOK API: la respuesta JSON no es valida.") from error
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
        q = urllib.parse.quote_plus(role)
        url = f"https://remotive.com/api/remote-jobs?search={q}"
        response = _handle_requests_call("Remotive API", url)
        try:
            data = response.json().get("jobs", [])
        except ValueError as error:
            raise SourceFetchError("Remotive API", "invalid_response", "Remotive API: la respuesta JSON no es valida.") from error
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


def dedupe_jobs(jobs):
    seen = set(); out = []
    for j in jobs:
        key = (j.get("title","" ).lower(), j.get("company","").lower(), j.get("apply_url","").lower())
        if key not in seen:
            seen.add(key); out.append(j)
    # El match (relevancia respecto al rol) manda; el tipo de resultado solo desempata.
    return sorted(out, key=lambda x: (x.get("match", 0), x.get("type") == "api_result", str(x.get("published_date",""))), reverse=True)
