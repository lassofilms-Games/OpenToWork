import csv
from datetime import datetime
from html import escape

from constants import APP_NAME, APP_VERSION, APP_AUTHOR
from i18n import t


def now_stamp():
    return datetime.now().strftime("%Y_%m_%d_%H_%M")


def export_txt(jobs, path, lang="es"):
    not_available = t(lang, "not_available")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{APP_NAME} v{APP_VERSION}\n")
        f.write(t(lang, "export_created_by", author=APP_AUTHOR) + "\n")
        f.write(t(lang, "export_exported_on", date=datetime.now().strftime('%Y-%m-%d %H:%M')) + "\n")
        f.write("="*90 + "\n\n")
        for i, j in enumerate(jobs, 1):
            f.write(f"#{i} | MATCH: {j.get('match','-')}%\n")
            f.write(f"{t(lang, 'export_field_title')}: {j.get('title','-')}\n")
            f.write(f"{t(lang, 'export_field_company')}: {j.get('company','-')}\n")
            f.write(f"{t(lang, 'export_field_location')}: {j.get('location','-')}\n")
            f.write(f"{t(lang, 'export_field_mode')}: {j.get('remote','-')}\n")
            f.write(f"{t(lang, 'export_field_source')}: {j.get('source','-')}\n")
            f.write(f"{t(lang, 'export_field_published')}: {j.get('published_date', not_available)}\n")
            f.write(f"{t(lang, 'export_field_detected')}: {j.get('detected_date','-')}\n")
            f.write(f"{t(lang, 'export_field_url')}: {j.get('apply_url','-')}\n")
            if j.get("fallback_url") and j.get("fallback_url") != j.get("apply_url"):
                f.write(f"{t(lang, 'export_field_fallback')}: {j.get('fallback_url')}\n")
            f.write(f"{t(lang, 'export_field_skills')}: {j.get('skills_found','-')}\n")
            f.write(t(lang, "export_description_label") + "\n")
            f.write(j.get("description", "-") + "\n")
            f.write("-"*90 + "\n\n")


def export_csv(jobs, path):
    fields = ["match","published_date","detected_date","title","company","location","remote","source","apply_url","fallback_url","skills_found","description","type"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for j in jobs:
            writer.writerow({k: j.get(k, "") for k in fields})


def export_html(jobs, path, lang="es"):
    rows = []
    for j in jobs:
        rows.append(f"""
        <tr>
          <td>{escape(str(j.get('match','')))}%</td>
          <td>{escape(j.get('published_date',''))}</td>
          <td>{escape(j.get('title',''))}</td>
          <td>{escape(j.get('company',''))}</td>
          <td>{escape(j.get('location',''))}</td>
          <td>{escape(j.get('source',''))}</td>
          <td><a href="{escape(j.get('apply_url',''))}" target="_blank">{t(lang, 'export_html_link')}</a></td>
          <td><a href="{escape(j.get('fallback_url',''))}" target="_blank">{t(lang, 'export_html_google')}</a></td>
        </tr>""")
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>{APP_NAME}</title>
    <style>body{{font-family:Arial;margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px}}th{{background:#111;color:white}}tr:nth-child(even){{background:#f5f5f5}}</style></head>
    <body><h1>{APP_NAME}</h1><p>{t(lang, 'export_created_by', author=APP_AUTHOR)} · {t(lang, 'export_exported_on', date=datetime.now().strftime('%Y-%m-%d %H:%M'))}</p>
    <table><thead><tr><th>{t(lang, 'col_match')}</th><th>{t(lang, 'col_published')}</th><th>{t(lang, 'col_title')}</th><th>{t(lang, 'col_company')}</th><th>{t(lang, 'col_location')}</th><th>{t(lang, 'col_source')}</th><th>{t(lang, 'export_html_link')}</th><th>{t(lang, 'export_html_google')}</th></tr></thead><tbody>{''.join(rows)}</tbody></table></body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
