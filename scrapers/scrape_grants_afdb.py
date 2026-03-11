"""
Grant scraper for African Development Bank (AfDB) via IATI Datastore.
Source: https://datastore.codeforiati.org/api/1/access/activity.json

AfDB IATI org ID: XM-DAC-46002.
Covers North African MENA countries: MA, TN, DZ, EG, LY, MR, SD.

Parses IATI activity records for:
  - Title narratives (en/fr/ar)
  - Budget amounts (XDR converted to USD at ~1.35)
  - Activity dates, sectors, status
  - Participating organisations
"""

import requests
import logging
import time
from config import (
    MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_afdb")

IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"
AFDB_ORG_ID = "XM-DAC-46002"

# North African MENA countries the AfDB covers
AFDB_MENA_COUNTRIES = {
    "MA": "Morocco",
    "TN": "Tunisia",
    "DZ": "Algeria",
    "EG": "Egypt",
    "LY": "Libya",
    "MR": "Mauritania",
    "SD": "Sudan",
}

# IATI activity status codes
STATUS_MAP = {
    "1": "open",    # Pipeline/identification
    "2": "open",    # Implementation
    "3": "open",    # Finalisation
    "4": "closed",  # Closed
    "5": "closed",  # Cancelled
}

# XDR (Special Drawing Rights) to USD approximate conversion rate
XDR_TO_USD = 1.35

# IATI DAC sector code categories (5-digit codes → readable sectors)
DAC_SECTOR_MAP = {
    "111": "education",
    "112": "education",
    "113": "education",
    "114": "education",
    "120": "healthcare",
    "121": "healthcare",
    "122": "healthcare",
    "130": "healthcare",
    "140": "water",
    "150": "finance",
    "160": "it",
    "210": "transport",
    "220": "telecom",
    "230": "energy",
    "240": "finance",
    "250": "finance",
    "310": "agriculture",
    "311": "agriculture",
    "312": "agriculture",
    "320": "mining",
    "321": "mining",
    "330": "construction",
    "331": "real_estate",
    "332": "tourism",
    "410": "water",
    "430": "water",
    "720": "emergency",
    "730": "emergency",
    "740": "emergency",
}


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

    # Try the requested language first
    for n in narratives:
        if isinstance(n, dict):
            n_lang = n.get("xml:lang", "") or n.get("lang", "")
            if n_lang.startswith(lang):
                return (n.get("text", "") or "").strip()

    # Fall back to first available narrative
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
            if cur == "XDR":
                amount *= XDR_TO_USD
                cur = "USD"
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
                cur = val.get("currency", "USD") or "USD"
                if cur == "XDR":
                    amount *= XDR_TO_USD
                total += amount

    return total


def _extract_sectors(act: dict) -> tuple[str, list[str]]:
    """Extract primary sector and all sectors from IATI activity."""
    sectors_raw = act.get("sector", [])
    if isinstance(sectors_raw, dict):
        sectors_raw = [sectors_raw]

    sector_texts: list[str] = []
    sector_codes: list[str] = []

    for s in sectors_raw:
        if not isinstance(s, dict):
            continue
        # Get narrative text
        text = _get_narrative(s, "en")
        if text:
            sector_texts.append(text)
        # Get DAC code
        code = str(s.get("code", ""))
        if code:
            sector_codes.append(code)

    # Classify each text
    classified = []
    for text in sector_texts:
        c = classify_sector(text)
        if c not in classified:
            classified.append(c)

    # Also map DAC codes
    for code in sector_codes:
        prefix = code[:3]
        mapped = DAC_SECTOR_MAP.get(prefix)
        if mapped and mapped not in classified:
            classified.append(mapped)

    primary = classified[0] if classified else classify_sector(
        " ".join(sector_texts) if sector_texts else ""
    )

    return primary, classified if classified else [primary]


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


def scrape() -> list[dict]:
    """Scrape AfDB grant projects from IATI Datastore for MENA countries."""
    grants: list[dict] = []
    seen_ids: set[str] = set()

    for country_code, country_name in AFDB_MENA_COUNTRIES.items():
        offset = 0
        page_size = 50
        country_count = 0

        while True:
            try:
                params = {
                    "reporting-org": AFDB_ORG_ID,
                    "recipient-country": country_code,
                    "limit": page_size,
                    "offset": offset,
                }

                resp = requests.get(IATI_API, params=params, timeout=30)
                if resp.status_code != 200:
                    logger.warning(
                        f"IATI AfDB {country_code}: HTTP {resp.status_code}"
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

                    # Title in multiple languages
                    title_en = _get_narrative(act.get("title", {}), "en")
                    title_fr = _get_narrative(act.get("title", {}), "fr")
                    title_ar = _get_narrative(act.get("title", {}), "ar")

                    if not title_en and not title_fr:
                        continue
                    if not title_en:
                        title_en = title_fr
                    if not title_fr:
                        title_fr = title_en

                    # Status — only include active/pipeline
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
                        desc_fr = _get_narrative(desc_data[0], "fr") if desc_data else ""
                        desc_ar = _get_narrative(desc_data[0], "ar") if desc_data else ""
                    else:
                        desc_en = _get_narrative(desc_data, "en")
                        desc_fr = _get_narrative(desc_data, "fr")
                        desc_ar = _get_narrative(desc_data, "ar")

                    # Budget
                    budget, currency = _parse_budget(act.get("budget"))
                    if budget == 0:
                        # Try transaction commitments as fallback
                        budget = _parse_transaction_total(act.get("transaction"))
                        if budget > 0:
                            currency = "USD"

                    # Dates
                    planned_start, actual_start, planned_end, actual_end = (
                        _extract_dates(act)
                    )
                    publish_date = actual_start or planned_start or ""
                    deadline = planned_end or actual_end or ""

                    # Skip ancient projects — only include 2020+
                    all_dates = [planned_start, actual_start, planned_end, actual_end]
                    most_recent_year = 0
                    for d in all_dates:
                        if d and len(d) >= 4:
                            try:
                                most_recent_year = max(most_recent_year, int(d[:4]))
                            except ValueError:
                                pass
                    if most_recent_year > 0 and most_recent_year < 2020:
                        continue

                    # Sectors
                    primary_sector, sectors_list = _extract_sectors(act)

                    # Grant type from description
                    combined_text = f"{title_en} {desc_en}"
                    grant_type = classify_grant_type(combined_text)

                    # Participating organisations
                    participating_orgs = _extract_participating_orgs(act)

                    # Tags
                    tags: list[str] = []
                    if "pipeline" in str(status_code):
                        tags.append("pipeline")
                    if budget > 50_000_000:
                        tags.append("large_project")
                    for org in participating_orgs:
                        if "afdb" in org.lower() or "african" in org.lower():
                            continue
                        tags.append(org[:30])

                    # Contact
                    contact_info = "; ".join(participating_orgs[:3])

                    grant = {
                        "id": generate_grant_id("afdb", iati_id),
                        "title": title_en,
                        "title_ar": title_ar or "",
                        "title_fr": title_fr or "",
                        "source": "afdb",
                        "source_ref": iati_id,
                        "source_url": (
                            f"https://projectsportal.afdb.org/dataportal/"
                            f"VProject/show/{iati_id}"
                            if iati_id else ""
                        ),
                        "funding_organization": "African Development Bank",
                        "funding_organization_ar": "البنك الأفريقي للتنمية",
                        "funding_organization_fr": "Banque africaine de développement",
                        "funding_amount": round(budget, 2),
                        "funding_amount_max": 0,
                        "currency": currency,
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": primary_sector,
                        "sectors": sectors_list,
                        "eligibility_criteria": "",
                        "eligibility_countries": [country_code],
                        "description": (desc_en or title_en)[:2000],
                        "description_ar": (desc_ar or "")[:2000],
                        "description_fr": (desc_fr or title_fr)[:2000],
                        "application_deadline": parse_date(deadline) or "",
                        "publish_date": parse_date(publish_date) or "",
                        "status": status,
                        "contact_info": contact_info,
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
                logger.error(f"IATI AfDB {country_code}: {e}")
                break

        logger.info(
            f"AfDB {country_code} ({country_name}): {country_count} active grants"
        )

    logger.info(f"AfDB total: {len(grants)} grants across MENA")
    return grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "afdb")
    print(f"Scraped {len(results)} grants from AfDB")
