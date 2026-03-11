"""
Grant scraper for Inter-American Development Bank (IDB).
Sources:
  - IDB Procurement API: https://projectprocurement.iadb.org/
  - IDB Projects API: https://www.iadb.org/en/projects
  - IATI Datastore (IDB org): XM-DAC-46012

IDB primarily serves Latin America and the Caribbean, but some projects
have global components or partnerships with MENA institutions. This
scraper searches for MENA-relevant procurement and project opportunities.

Currency: USD
"""

import requests
import logging
import time
from bs4 import BeautifulSoup
from config import (
    HEADERS, MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_idb")

# IDB API endpoints
IDB_PROCUREMENT_URL = "https://projectprocurement.iadb.org/en/procurement-notices"
IDB_PROCUREMENT_API = "https://projectprocurement.iadb.org/api/procurement"
IDB_PROJECTS_API = "https://www.iadb.org/en/projects-search"
IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"
IDB_ORG_ID = "XM-DAC-46012"

# MENA country name -> code mapping
_IDB_COUNTRY_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _IDB_COUNTRY_TO_CODE[_name.lower()] = _code
_IDB_COUNTRY_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "egypt, arab republic of": "EG",
    "arab republic of egypt": "EG",
    "morocco": "MA",
    "kingdom of morocco": "MA",
    "tunisia": "TN",
    "jordan": "JO",
    "west bank and gaza": "PS",
    "palestine": "PS",
    "iraq": "IQ",
    "yemen": "YE",
    "saudi arabia": "SA",
    "algeria": "DZ",
    "libya": "LY",
    "lebanon": "LB",
    "sudan": "SD",
    "mauritania": "MR",
    "kuwait": "KW",
    "qatar": "QA",
    "bahrain": "BH",
    "oman": "OM",
})

# IATI activity status codes
STATUS_MAP = {
    "1": "open",
    "2": "open",
    "3": "open",
    "4": "closed",
    "5": "closed",
}

# MENA-related search keywords for IDB global programs
MENA_SEARCH_KEYWORDS = [
    "Middle East",
    "North Africa",
    "MENA",
    "Arab",
    "Morocco",
    "Tunisia",
    "Egypt",
    "Jordan",
    "South-South cooperation",
    "triangular cooperation",
]


def _resolve_country(name_raw: str) -> tuple[str, str]:
    """Resolve a country name to (iso2_code, country_name).

    Returns ("", "") if not a MENA country.
    """
    if not name_raw:
        return "", ""
    key = name_raw.strip().lower()
    code = _IDB_COUNTRY_TO_CODE.get(key, "")
    if code:
        return code, MENA_COUNTRIES[code]
    for pattern, c in _IDB_COUNTRY_TO_CODE.items():
        if pattern in key or key in pattern:
            return c, MENA_COUNTRIES[c]
    return "", ""


def _detect_mena_country(text: str) -> tuple[str, str]:
    """Detect a MENA country mention in free text."""
    text_lower = text.lower()
    for name, code in _IDB_COUNTRY_TO_CODE.items():
        if name in text_lower:
            return code, MENA_COUNTRIES.get(code, "")
    return "", ""


def _get_narrative(field, lang: str = "en") -> str:
    """Extract narrative text from IATI title/description field."""
    if isinstance(field, list):
        narratives = field
    elif isinstance(field, dict):
        narratives = field.get("narrative", [])
    else:
        return ""

    if isinstance(narratives, dict):
        narratives = [narratives]

    for n in narratives:
        if isinstance(n, dict):
            n_lang = n.get("xml:lang", "") or n.get("lang", "")
            if n_lang.startswith(lang):
                return (n.get("text", "") or "").strip()

    for n in narratives:
        if isinstance(n, dict) and n.get("text"):
            return n["text"].strip()

    return ""


def _parse_budget(budget_data) -> tuple[float, str]:
    """Parse total budget from IATI budget field."""
    if not budget_data:
        return 0.0, "USD"

    budgets = budget_data if isinstance(budget_data, list) else [budget_data]

    total = 0.0
    currency = "USD"

    for b in budgets:
        val = b.get("value", {})
        if isinstance(val, dict):
            try:
                amount = float(val.get("text", "0") or "0")
            except (ValueError, TypeError):
                amount = 0.0
            cur = val.get("currency", "USD") or "USD"
            total += amount
            currency = cur
        elif isinstance(val, (int, float)):
            total += float(val)

    return total, currency


def _extract_dates(act: dict) -> tuple[str, str, str, str]:
    """Extract dates from IATI activity."""
    dates = act.get("activity-date", [])
    if isinstance(dates, dict):
        dates = [dates]

    planned_start = ""
    actual_start = ""
    planned_end = ""
    actual_end = ""

    for d in dates:
        if not isinstance(d, dict):
            continue
        dtype = str(d.get("type", ""))
        iso = d.get("iso-date", "")
        if dtype == "1":
            planned_start = iso
        elif dtype == "2":
            actual_start = iso
        elif dtype == "3":
            planned_end = iso
        elif dtype == "4":
            actual_end = iso

    return planned_start, actual_start, planned_end, actual_end


def _scrape_idb_procurement() -> list[dict]:
    """Scrape IDB procurement page for MENA-relevant opportunities."""
    grants: list[dict] = []
    seen_refs: set[str] = set()

    browser_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    for keyword in MENA_SEARCH_KEYWORDS:
        try:
            # Try IDB procurement search API
            params = {
                "search": keyword,
                "status": "active",
                "page": 1,
                "limit": 50,
            }

            resp = requests.get(
                IDB_PROCUREMENT_API,
                params=params,
                headers=browser_headers,
                timeout=30,
            )

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("results", data.get("data", []))

                    for item in items:
                        if not isinstance(item, dict):
                            continue

                        title = item.get("title", item.get("name", ""))
                        if not title:
                            continue

                        ref = str(item.get("id", item.get("procurement_number", "")))
                        if not ref or ref in seen_refs:
                            continue

                        # Check MENA relevance
                        combined = f"{title} {item.get('description', '')} {item.get('country', '')}"
                        country_code, country_name = _detect_mena_country(combined)
                        if not country_code:
                            # If searching with country keyword, assign it
                            country_code, country_name = _detect_mena_country(keyword)
                        if not country_code:
                            country_code = "XX"
                            country_name = "MENA Region"

                        seen_refs.add(ref)

                        description = item.get("description", title)
                        deadline = parse_date(str(item.get("deadline", item.get("closing_date", ""))))
                        pub_date = parse_date(str(item.get("publication_date", item.get("published", ""))))
                        amount = parse_amount(item.get("amount", item.get("estimated_cost", 0)))

                        sector = classify_sector(combined)
                        grant_type = classify_grant_type(combined)

                        grant = {
                            "id": generate_grant_id("idb", ref),
                            "title": title,
                            "title_ar": "",
                            "title_fr": "",
                            "source": "idb",
                            "source_ref": ref,
                            "source_url": item.get("url", f"https://projectprocurement.iadb.org/en/procurement-notices/{ref}"),
                            "funding_organization": "Inter-American Development Bank",
                            "funding_organization_ar": "\u0628\u0646\u0643 \u0627\u0644\u062a\u0646\u0645\u064a\u0629 \u0644\u0644\u0628\u0644\u062f\u0627\u0646 \u0627\u0644\u0623\u0645\u0631\u064a\u0643\u064a\u0629",
                            "funding_organization_fr": "Banque interam\u00e9ricaine de d\u00e9veloppement",
                            "funding_amount": amount,
                            "funding_amount_max": 0,
                            "currency": "USD",
                            "grant_type": grant_type,
                            "country": country_name,
                            "country_code": country_code,
                            "region": "MENA",
                            "sector": sector,
                            "sectors": [sector],
                            "eligibility_criteria": item.get("eligibility", ""),
                            "eligibility_countries": [country_code] if country_code != "XX" else list(MENA_COUNTRIES.keys()),
                            "description": (description or title)[:2000],
                            "description_ar": "",
                            "description_fr": "",
                            "application_deadline": deadline or "",
                            "publish_date": pub_date or "",
                            "status": "open",
                            "contact_info": item.get("contact", ""),
                            "documents_url": item.get("documents_url", ""),
                            "tags": ["IDB", "procurement"],
                            "metadata": {
                                "search_keyword": keyword,
                                "procurement_type": item.get("type", ""),
                            },
                        }
                        grants.append(grant)

                except Exception:
                    pass

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"IDB procurement search '{keyword}': {e}")
            continue

    logger.info(f"IDB procurement: {len(grants)} MENA-relevant grants")
    return grants


def _scrape_iati_idb() -> list[dict]:
    """Scrape IDB grants from IATI Datastore for MENA countries."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    for country_code, country_name in MENA_COUNTRIES.items():
        offset = 0
        page_size = 50
        country_count = 0

        while True:
            try:
                params = {
                    "reporting-org": IDB_ORG_ID,
                    "recipient-country": country_code,
                    "limit": page_size,
                    "offset": offset,
                }

                resp = requests.get(IATI_API, params=params, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                total_count = data.get("total-count", 0)
                activities = data.get("iati-activities", [])

                if not activities:
                    break

                for entry in activities:
                    act = entry.get("iati-activity", entry)

                    iati_id = act.get("iati-identifier", "")
                    if not iati_id or iati_id in seen_ids:
                        continue

                    title_en = _get_narrative(act.get("title", {}), "en")
                    title_es = _get_narrative(act.get("title", {}), "es")

                    if not title_en:
                        title_en = title_es or ""
                    if not title_en:
                        continue

                    # Status
                    status_field = act.get("activity-status", {})
                    if isinstance(status_field, dict):
                        status_code = status_field.get("code", "2")
                    else:
                        status_code = str(status_field)
                    status = STATUS_MAP.get(str(status_code), "open")

                    if status == "closed":
                        continue

                    seen_ids.add(iati_id)

                    # Description
                    desc_data = act.get("description", {})
                    if isinstance(desc_data, list):
                        desc_en = _get_narrative(desc_data[0], "en") if desc_data else ""
                    else:
                        desc_en = _get_narrative(desc_data, "en")

                    # Budget
                    budget, currency = _parse_budget(act.get("budget"))

                    # Dates
                    planned_start, actual_start, planned_end, actual_end = (
                        _extract_dates(act)
                    )
                    publish_date = actual_start or planned_start or ""
                    deadline = planned_end or actual_end or ""

                    # Classify
                    combined_text = f"{title_en} {desc_en}"
                    sector = classify_sector(combined_text)
                    grant_type = classify_grant_type(combined_text)

                    # Participating organisations
                    orgs_raw = act.get("participating-org", [])
                    if isinstance(orgs_raw, dict):
                        orgs_raw = [orgs_raw]
                    orgs = []
                    for org in orgs_raw:
                        if isinstance(org, dict):
                            name = _get_narrative(org, "en")
                            if name and name not in orgs:
                                orgs.append(name)

                    grant = {
                        "id": generate_grant_id("idb", iati_id),
                        "title": title_en,
                        "title_ar": "",
                        "title_fr": "",
                        "source": "idb",
                        "source_ref": iati_id,
                        "source_url": f"https://www.iadb.org/en/project/{iati_id}" if iati_id else "",
                        "funding_organization": "Inter-American Development Bank",
                        "funding_organization_ar": "\u0628\u0646\u0643 \u0627\u0644\u062a\u0646\u0645\u064a\u0629 \u0644\u0644\u0628\u0644\u062f\u0627\u0646 \u0627\u0644\u0623\u0645\u0631\u064a\u0643\u064a\u0629",
                        "funding_organization_fr": "Banque interam\u00e9ricaine de d\u00e9veloppement",
                        "funding_amount": round(budget, 2),
                        "funding_amount_max": 0,
                        "currency": currency,
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": sector,
                        "sectors": [sector],
                        "eligibility_criteria": "",
                        "eligibility_countries": [country_code],
                        "description": (desc_en or title_en)[:2000],
                        "description_ar": "",
                        "description_fr": "",
                        "application_deadline": parse_date(deadline) or "",
                        "publish_date": parse_date(publish_date) or "",
                        "status": status,
                        "contact_info": "; ".join(orgs[:3]),
                        "documents_url": "",
                        "tags": ["IDB", "IATI"],
                        "metadata": {
                            "iati_id": iati_id,
                            "activity_status_code": str(status_code),
                        },
                    }
                    grants.append(grant)
                    country_count += 1

                offset += page_size
                if offset >= total_count:
                    break

                time.sleep(0.3)

            except Exception as e:
                logger.error(f"IATI IDB {country_code}: {e}")
                break

        if country_count > 0:
            logger.info(
                f"IDB IATI {country_code} ({country_name}): {country_count} grants"
            )

    logger.info(f"IDB IATI total: {len(grants)} grants")
    return grants


def scrape() -> list[dict]:
    """Scrape Inter-American Development Bank for MENA grant opportunities."""
    logger.info("Starting IDB grants scraper...")

    # Phase 1: IDB procurement portal
    proc_grants = _scrape_idb_procurement()
    logger.info(f"Phase 1 -- Procurement: {len(proc_grants)} grants")

    # Phase 2: IATI Datastore
    iati_grants = _scrape_iati_idb()
    logger.info(f"Phase 2 -- IATI: {len(iati_grants)} grants")

    # Merge and deduplicate by source_ref
    all_grants = proc_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in iati_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"IDB total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "idb")
    print(f"Scraped {len(results)} grants from IDB")
