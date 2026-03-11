"""
Grant scraper for Asian Development Bank (ADB).
Sources:
  - ADB Data Library API: https://data.adb.org/
  - ADB Projects API: https://www.adb.org/projects
  - IATI Datastore (ADB org): XM-DAC-46004

ADB operates across Asia and the Pacific, with some MENA-adjacent
coverage through Central and West Asia operations (e.g., Pakistan,
Afghanistan). Filters for MENA countries where ADB has presence.

Currency: USD
"""

import requests
import logging
import time
from config import (
    HEADERS, MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_adb")

# ADB API endpoints
ADB_API = "https://www.adb.org/search/results"
ADB_PROJECTS_API = "https://data.adb.org/api/3/action/package_search"
IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"
ADB_ORG_ID = "XM-DAC-46004"

# ADB project listing (HTML scraping fallback)
ADB_PROJECTS_URL = "https://www.adb.org/projects"

# MENA countries that ADB may have crossover projects with
# ADB covers some MENA-adjacent regions
ADB_MENA_COUNTRIES = {
    "EG": "Egypt",
    "JO": "Jordan",
    "SA": "Saudi Arabia",
    "AE": "UAE",
    "KW": "Kuwait",
    "QA": "Qatar",
    "BH": "Bahrain",
    "OM": "Oman",
    "IQ": "Iraq",
    "LB": "Lebanon",
    "PS": "Palestine",
    "YE": "Yemen",
    "MA": "Morocco",
    "TN": "Tunisia",
    "DZ": "Algeria",
    "LY": "Libya",
    "SD": "Sudan",
    "MR": "Mauritania",
}

# ADB sometimes lists MENA countries with these alternate names
_ADB_COUNTRY_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _ADB_COUNTRY_TO_CODE[_name.lower()] = _code
_ADB_COUNTRY_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "egypt, arab republic of": "EG",
    "arab republic of egypt": "EG",
    "west bank and gaza": "PS",
    "republic of iraq": "IQ",
    "kingdom of saudi arabia": "SA",
    "hashemite kingdom of jordan": "JO",
    "republic of yemen": "YE",
    "republic of tunisia": "TN",
    "republic of sudan": "SD",
    "palestine": "PS",
})

# IATI activity status codes
STATUS_MAP = {
    "1": "open",    # Pipeline/identification
    "2": "open",    # Implementation
    "3": "open",    # Finalisation
    "4": "closed",  # Closed
    "5": "closed",  # Cancelled
}


def _resolve_country(name_raw: str) -> tuple[str, str]:
    """Resolve a country name to (iso2_code, country_name).

    Returns ("", "") if not a MENA country.
    """
    if not name_raw:
        return "", ""
    key = name_raw.strip().lower()
    code = _ADB_COUNTRY_TO_CODE.get(key, "")
    if code:
        return code, MENA_COUNTRIES[code]
    # Try partial match
    for pattern, c in _ADB_COUNTRY_TO_CODE.items():
        if pattern in key or key in pattern:
            return c, MENA_COUNTRIES[c]
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
    """Parse total budget from IATI budget field. Returns (amount_usd, currency)."""
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


def _parse_transaction_total(transactions) -> float:
    """Sum commitment transactions as an alternative budget source."""
    if not transactions:
        return 0.0

    if isinstance(transactions, dict):
        transactions = [transactions]

    total = 0.0
    for txn in transactions:
        txn_type = txn.get("transaction-type", {})
        if isinstance(txn_type, dict):
            type_code = txn_type.get("code", "")
        else:
            type_code = str(txn_type)

        # Code 2 = Commitment
        if type_code == "2":
            val = txn.get("value", {})
            if isinstance(val, dict):
                try:
                    amount = float(val.get("text", "0") or "0")
                except (ValueError, TypeError):
                    amount = 0.0
                total += amount

    return total


def _extract_dates(act: dict) -> tuple[str, str, str, str]:
    """Extract dates from IATI activity.

    Returns (planned_start, actual_start, planned_end, actual_end).
    """
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


def _extract_participating_orgs(act: dict) -> list[str]:
    """Extract participating organisations from IATI activity."""
    orgs_raw = act.get("participating-org", [])
    if isinstance(orgs_raw, dict):
        orgs_raw = [orgs_raw]

    orgs = []
    for org in orgs_raw:
        if not isinstance(org, dict):
            continue
        name = _get_narrative(org, "en")
        if not name:
            name = org.get("ref", "")
        if name and name not in orgs:
            orgs.append(name)

    return orgs


def _scrape_iati_adb() -> list[dict]:
    """Scrape ADB grants from IATI Datastore for MENA countries."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    for country_code, country_name in ADB_MENA_COUNTRIES.items():
        offset = 0
        page_size = 50
        country_count = 0

        while True:
            try:
                params = {
                    "reporting-org": ADB_ORG_ID,
                    "recipient-country": country_code,
                    "limit": page_size,
                    "offset": offset,
                }

                resp = requests.get(IATI_API, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.warning(
                        f"IATI ADB {country_code}: HTTP {resp.status_code}"
                    )
                    break

                data = resp.json()
                total_count = data.get("total-count", 0)
                activities = data.get("iati-activities", [])

                if not activities:
                    break

                for entry in activities:
                    act = entry.get("iati-activity", entry)

                    # IATI identifier
                    iati_id = act.get("iati-identifier", "")
                    if not iati_id:
                        continue
                    if iati_id in seen_ids:
                        continue

                    # Title
                    title_en = _get_narrative(act.get("title", {}), "en")
                    title_fr = _get_narrative(act.get("title", {}), "fr")
                    title_ar = _get_narrative(act.get("title", {}), "ar")

                    if not title_en and not title_fr:
                        continue
                    if not title_en:
                        title_en = title_fr

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
                        desc_ar = _get_narrative(desc_data[0], "ar") if desc_data else ""
                    else:
                        desc_en = _get_narrative(desc_data, "en")
                        desc_ar = _get_narrative(desc_data, "ar")

                    # Budget
                    budget, currency = _parse_budget(act.get("budget"))
                    if budget == 0:
                        budget = _parse_transaction_total(act.get("transaction"))
                        if budget > 0:
                            currency = "USD"

                    # Dates
                    planned_start, actual_start, planned_end, actual_end = (
                        _extract_dates(act)
                    )
                    publish_date = actual_start or planned_start or ""
                    deadline = planned_end or actual_end or ""

                    # Sector
                    combined_text = f"{title_en} {desc_en}"
                    sector = classify_sector(combined_text)
                    grant_type = classify_grant_type(combined_text)

                    # Participating organisations
                    participating_orgs = _extract_participating_orgs(act)

                    # Tags
                    tags: list[str] = ["ADB"]
                    if budget > 50_000_000:
                        tags.append("large_project")

                    grant = {
                        "id": generate_grant_id("adb", iati_id),
                        "title": title_en,
                        "title_ar": title_ar or "",
                        "title_fr": title_fr or "",
                        "source": "adb",
                        "source_ref": iati_id,
                        "source_url": f"https://www.adb.org/projects/{iati_id.split('-')[-1]}" if iati_id else "",
                        "funding_organization": "Asian Development Bank",
                        "funding_organization_ar": "بنك التنمية الآسيوي",
                        "funding_organization_fr": "Banque asiatique de d\u00e9veloppement",
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
                        "description_ar": (desc_ar or "")[:2000],
                        "description_fr": "",
                        "application_deadline": parse_date(deadline) or "",
                        "publish_date": parse_date(publish_date) or "",
                        "status": status,
                        "contact_info": "; ".join(participating_orgs[:3]),
                        "documents_url": "",
                        "tags": tags[:10],
                        "metadata": {
                            "iati_id": iati_id,
                            "activity_status_code": str(status_code),
                            "planned_start": planned_start,
                            "actual_start": actual_start,
                            "planned_end": planned_end,
                            "actual_end": actual_end,
                            "participating_orgs": participating_orgs,
                        },
                    }
                    grants.append(grant)
                    country_count += 1

                offset += page_size
                if offset >= total_count:
                    break

                time.sleep(0.3)

            except Exception as e:
                logger.error(f"IATI ADB {country_code}: {e}")
                break

        if country_count > 0:
            logger.info(
                f"ADB {country_code} ({country_name}): {country_count} active grants"
            )

    logger.info(f"ADB IATI total: {len(grants)} grants across MENA")
    return grants


def _scrape_adb_api() -> list[dict]:
    """Scrape ADB projects via their direct API for MENA-relevant projects."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    # ADB API for sovereign projects
    api_url = "https://www.adb.org/api/views/project_list"

    for country_code, country_name in ADB_MENA_COUNTRIES.items():
        try:
            params = {
                "country": country_name,
                "status": "Active",
                "_format": "json",
                "limit": 100,
                "offset": 0,
            }

            resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                continue

            try:
                data = resp.json()
            except Exception:
                continue

            if not isinstance(data, list):
                data = data.get("results", []) if isinstance(data, dict) else []

            for proj in data:
                if not isinstance(proj, dict):
                    continue

                project_id = str(proj.get("project_number", proj.get("id", "")))
                if not project_id or project_id in seen_ids:
                    continue

                title = proj.get("project_name", proj.get("title", ""))
                if not title:
                    continue

                seen_ids.add(project_id)

                # Extract fields
                amount = parse_amount(proj.get("total_project_cost", proj.get("amount", 0)))
                approval_date = parse_date(str(proj.get("approval_date", "")))
                closing_date = parse_date(str(proj.get("closing_date", "")))
                sector_raw = proj.get("sector", proj.get("primary_sector", ""))
                description = proj.get("description", proj.get("project_abstract", title))
                status_raw = proj.get("status", "Active")
                project_url = proj.get("url", f"https://www.adb.org/projects/{project_id}")

                # Classify
                combined_text = f"{title} {description} {sector_raw}"
                sector = classify_sector(combined_text)
                grant_type = classify_grant_type(combined_text)

                status = "open"
                if status_raw and "close" in status_raw.lower():
                    status = "closed"
                elif status_raw and "complet" in status_raw.lower():
                    status = "closed"

                grant = {
                    "id": generate_grant_id("adb_api", project_id),
                    "title": title,
                    "title_ar": "",
                    "title_fr": "",
                    "source": "adb",
                    "source_ref": project_id,
                    "source_url": project_url,
                    "funding_organization": "Asian Development Bank",
                    "funding_organization_ar": "بنك التنمية الآسيوي",
                    "funding_organization_fr": "Banque asiatique de d\u00e9veloppement",
                    "funding_amount": amount,
                    "funding_amount_max": 0,
                    "currency": "USD",
                    "grant_type": grant_type,
                    "country": country_name,
                    "country_code": country_code,
                    "region": "MENA",
                    "sector": sector,
                    "sectors": [sector],
                    "eligibility_criteria": "",
                    "eligibility_countries": [country_code],
                    "description": (description or title)[:2000],
                    "description_ar": "",
                    "description_fr": "",
                    "application_deadline": closing_date or "",
                    "publish_date": approval_date or "",
                    "status": status,
                    "contact_info": "",
                    "documents_url": project_url,
                    "tags": ["ADB"],
                    "metadata": {
                        "sector_raw": sector_raw,
                        "status_raw": status_raw,
                    },
                }
                grants.append(grant)

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"ADB API {country_code}: {e}")
            continue

    logger.info(f"ADB API total: {len(grants)} grants")
    return grants


def scrape() -> list[dict]:
    """Scrape Asian Development Bank for MENA grant opportunities."""
    logger.info("Starting ADB grants scraper...")

    # Phase 1: IATI Datastore (most reliable)
    iati_grants = _scrape_iati_adb()
    logger.info(f"Phase 1 -- IATI: {len(iati_grants)} grants")

    # Phase 2: ADB direct API
    api_grants = _scrape_adb_api()
    logger.info(f"Phase 2 -- ADB API: {len(api_grants)} grants")

    # Merge and deduplicate by source_ref
    all_grants = iati_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in api_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"ADB total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "adb")
    print(f"Scraped {len(results)} grants from ADB")
