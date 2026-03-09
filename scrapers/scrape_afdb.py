"""
Scraper for African Development Bank (AfDB) via IATI Datastore API.
Source: https://datastore.codeforiati.org/api/1/access/activity.json

Free, unauthenticated JSON API. AfDB's IATI org ID: XM-DAC-46002.
Covers North African MENA countries with project-level data.
"""

import requests
import logging
import time
from config import MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("afdb")

IATI_API = "https://datastore.codeforiati.org/api/1/access/activity.json"
AFDB_ORG_ID = "XM-DAC-46002"

# North African MENA countries the AfDB covers
AFDB_COUNTRIES = {
    "MA": "Morocco",
    "TN": "Tunisia",
    "DZ": "Algeria",
    "EG": "Egypt",
    "LY": "Libya",
    "MR": "Mauritania",
    "SD": "Sudan",
}

# IATI activity status codes
_STATUS_MAP = {
    "1": "open",    # Pipeline/identification
    "2": "open",    # Implementation
    "3": "open",    # Finalisation
    "4": "closed",  # Closed
    "5": "closed",  # Cancelled
}

# XDR (SDR) to USD approximate rate
XDR_TO_USD = 1.35


def _get_narrative(field: dict | list, lang: str = "en") -> str:
    """Extract narrative text from IATI title/description field."""
    if isinstance(field, list):
        # Some responses return list of narrative dicts directly
        narratives = field
    elif isinstance(field, dict):
        narratives = field.get("narrative", [])
    else:
        return ""

    if isinstance(narratives, dict):
        narratives = [narratives]

    # Try to find the requested language
    for n in narratives:
        if isinstance(n, dict) and n.get("xml:lang", "").startswith(lang):
            return n.get("text", "")

    # Fall back to first available
    for n in narratives:
        if isinstance(n, dict) and n.get("text"):
            return n["text"]

    return ""


def _parse_budget(budget_data) -> tuple[float, str]:
    """Parse budget from IATI budget field."""
    if not budget_data:
        return 0, "USD"

    budgets = budget_data if isinstance(budget_data, list) else [budget_data]

    total = 0
    currency = "USD"
    for b in budgets:
        val = b.get("value", {})
        if isinstance(val, dict):
            try:
                amount = float(val.get("text", "0"))
            except (ValueError, TypeError):
                amount = 0
            cur = val.get("currency", "USD")
            if cur == "XDR":
                amount *= XDR_TO_USD
                cur = "USD"
            total += amount
            currency = cur

    return total, currency


def scrape() -> list[dict]:
    """Scrape AfDB projects from IATI Datastore for MENA countries."""
    tenders: list[dict] = []

    for country_code, country_name in AFDB_COUNTRIES.items():
        offset = 0
        page_size = 50

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
                    logger.warning(f"IATI AfDB {country_code}: {resp.status_code}")
                    break

                data = resp.json()
                total = data.get("total-count", 0)
                activities = data.get("iati-activities", [])

                if not activities:
                    break

                for entry in activities:
                    act = entry.get("iati-activity", entry)

                    # Title
                    title_en = _get_narrative(act.get("title", {}), "en")
                    title_fr = _get_narrative(act.get("title", {}), "fr")
                    if not title_en and not title_fr:
                        continue
                    if not title_en:
                        title_en = title_fr
                    if not title_fr:
                        title_fr = title_en

                    # Description
                    desc_data = act.get("description", {})
                    # description can be a list or dict
                    if isinstance(desc_data, list):
                        desc_en = _get_narrative(desc_data[0], "en") if desc_data else ""
                        desc_fr = _get_narrative(desc_data[0], "fr") if desc_data else ""
                    else:
                        desc_en = _get_narrative(desc_data, "en")
                        desc_fr = _get_narrative(desc_data, "fr")

                    # Budget
                    budget, currency = _parse_budget(act.get("budget"))

                    # Status
                    status_code = act.get("activity-status", {})
                    if isinstance(status_code, dict):
                        status_code = status_code.get("code", "2")
                    status = _STATUS_MAP.get(str(status_code), "open")

                    # Only include active/pipeline projects
                    if status == "closed":
                        continue

                    # Dates
                    dates = act.get("activity-date", [])
                    if isinstance(dates, dict):
                        dates = [dates]
                    pub_date = ""
                    end_date = ""
                    for d in dates:
                        dtype = str(d.get("type", ""))
                        iso = d.get("iso-date", "")
                        if dtype == "1" and not pub_date:  # Planned start
                            pub_date = iso
                        elif dtype == "2" and not pub_date:  # Actual start
                            pub_date = iso
                        elif dtype == "3" and not end_date:  # Planned end
                            end_date = iso
                        elif dtype == "4" and not end_date:  # Actual end
                            end_date = iso

                    # IATI identifier
                    iati_id = act.get("iati-identifier", "")

                    # Sector
                    sectors = act.get("sector", [])
                    if isinstance(sectors, dict):
                        sectors = [sectors]
                    sector_text = " ".join(
                        _get_narrative(s, "en") for s in sectors if isinstance(s, dict)
                    )

                    tender = {
                        "id": generate_id("afdb", iati_id or title_en[:80], ""),
                        "source": "AfDB",
                        "sourceRef": iati_id,
                        "sourceLanguage": "en",
                        "title": {
                            "en": title_en,
                            "ar": title_en,  # AfDB doesn't have Arabic
                            "fr": title_fr,
                        },
                        "organization": {
                            "en": "African Development Bank",
                            "ar": "البنك الأفريقي للتنمية",
                            "fr": "Banque africaine de développement",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(title_en + " " + sector_text),
                        "budget": round(budget, 2),
                        "currency": currency,
                        "deadline": end_date or "",
                        "publishDate": pub_date or "",
                        "status": status,
                        "description": {
                            "en": desc_en[:500] if desc_en else title_en,
                            "ar": desc_en[:500] if desc_en else title_en,
                            "fr": desc_fr[:500] if desc_fr else title_fr,
                        },
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": f"https://projectsportal.afdb.org/dataportal/VProject/show/{iati_id}" if iati_id else "",
                    }
                    tenders.append(tender)

                offset += page_size
                if offset >= total:
                    break

                time.sleep(0.3)

            except Exception as e:
                logger.error(f"IATI AfDB {country_code}: {e}")
                break

        logger.info(f"AfDB {country_code} ({country_name}): {len([t for t in tenders if t['countryCode'] == country_code])} projects")

    logger.info(f"AfDB total: {len(tenders)} projects")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "afdb")
    print(f"Scraped {len(results)} projects from AfDB")
