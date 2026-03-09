"""
Scraper for World Bank Projects API.
Source: https://search.worldbank.org/api/v2/projects
Gets active projects with procurement opportunities in MENA.
Different from procnotices — this gives projects which have procurement.
"""

import requests
import logging
import time
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("wb_projects")

API_BASE = "https://search.worldbank.org/api/v2/projects"


def scrape() -> list[dict]:
    """Scrape World Bank active projects for MENA."""
    tenders = []

    for country_code in MENA_COUNTRIES.keys():
        offset = 0
        page_size = 100

        while offset < 300:
            try:
                params = {
                    "format": "json",
                    "countrycode_exact": country_code,
                    "rows": page_size,
                    "os": offset,
                    "status_exact": "Active",
                    "srt": "boardapprovaldate",
                    "order": "desc",
                    "fl": "id,project_name,boardapprovaldate,closingdate,totalamt,countryname,sector1,theme1,lendinginstr,status,url,borrower",
                }

                resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                total = int(data.get("total", 0))
                projects = data.get("projects", {})

                if isinstance(projects, dict):
                    project_list = [v for v in projects.values() if isinstance(v, dict)]
                else:
                    break

                if not project_list:
                    break

                for proj in project_list:
                    name = proj.get("project_name", "")
                    if not name:
                        continue

                    # Verify response country matches request
                    raw_cn = proj.get("countryname", "")
                    if isinstance(raw_cn, list):
                        resp_country = " ".join(raw_cn).lower()
                    else:
                        resp_country = (raw_cn or "").lower()
                    expected_name = MENA_COUNTRIES.get(country_code, "").lower()
                    if resp_country and expected_name and expected_name not in resp_country and resp_country not in expected_name:
                        logger.debug(f"WB Projects: skipping {name[:50]} — response country '{resp_country}' != '{expected_name}'")
                        continue

                    sector = proj.get("sector1", "")
                    theme = proj.get("theme1", "")
                    amount = proj.get("totalamt", 0)
                    borrower = proj.get("borrower", "")
                    approval_date = proj.get("boardapprovaldate", "")
                    closing_date = proj.get("closingdate", "")
                    proj_url = proj.get("url", "")
                    country_name = MENA_COUNTRIES.get(country_code, proj.get("countryname", ""))

                    try:
                        budget = float(str(amount).replace(",", "")) if amount else 0
                    except (ValueError, TypeError):
                        budget = 0

                    tender = {
                        "id": generate_id("wbp", proj.get("id", name[:80]), ""),
                        "source": "World Bank Projects",
                        "sourceRef": proj.get("id", ""),
                        "sourceLanguage": "en",
                        "title": {
                            "en": f"{name} — Active Project with Procurement Opportunities",
                            "ar": f"{name} — مشروع نشط مع فرص مشتريات",
                            "fr": f"{name} — Projet actif avec opportunités d'approvisionnement",
                        },
                        "organization": {
                            "en": borrower or f"Government of {country_name}",
                            "ar": borrower or f"حكومة {country_name}",
                            "fr": borrower or f"Gouvernement de {country_name}",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(f"{name} {sector} {theme}"),
                        "budget": budget,
                        "currency": "USD",
                        "deadline": parse_date(str(closing_date)) or "",
                        "publishDate": parse_date(str(approval_date)) or "",
                        "status": "open",
                        "description": {
                            "en": f"World Bank active project: {name}. Sector: {sector}. Theme: {theme}. Total commitment: ${budget:,.0f}. Borrower: {borrower}.",
                            "ar": f"مشروع البنك الدولي النشط: {name}. القطاع: {sector}. الالتزام الكلي: ${budget:,.0f}.",
                            "fr": f"Projet actif Banque mondiale: {name}. Secteur: {sector}. Engagement total: ${budget:,.0f}.",
                        },
                        "requirements": [s for s in [sector, theme, proj.get("lendinginstr", "")] if s],
                        "matchScore": 0,
                        "sourceUrl": proj_url,
                    }
                    tenders.append(tender)

                offset += page_size
                if offset >= total:
                    break
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"WB Projects {country_code}: {e}")
                break

        logger.info(f"WB Projects {country_code}: fetched")

    logger.info(f"World Bank Projects total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "wb_projects")
    print(f"Scraped {len(results)} projects from World Bank")
