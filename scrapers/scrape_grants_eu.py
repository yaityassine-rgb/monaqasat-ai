"""
Grant scraper for EU TED (Tenders Electronic Daily).
Source: https://api.ted.europa.eu/v3/notices/search

Focuses on grant/subsidy notices and EU Neighbourhood (ENI) funding
for MENA countries via the TED Europa POST API.

TED country codes (ISO 3166 alpha-3):
  MAR, TUN, DZA, EGY, JOR, LBN, SAU, ARE, KWT, QAT, BHR, OMN, IRQ, LBY

Also searches for ENI (European Neighbourhood Instrument) and NDICI
(Neighbourhood, Development and International Cooperation Instrument)
grant opportunities.
"""

import re
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

logger = logging.getLogger("grants_eu")

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

# TED API headers
TED_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# MENA countries: TED ISO-3 code → our ISO-2 code
MENA_TED_CODES: dict[str, str] = {
    "MAR": "MA",
    "TUN": "TN",
    "DZA": "DZ",
    "EGY": "EG",
    "JOR": "JO",
    "LBN": "LB",
    "SAU": "SA",
    "ARE": "AE",
    "KWT": "KW",
    "QAT": "QA",
    "BHR": "BH",
    "OMN": "OM",
    "IRQ": "IQ",
    "LBY": "LY",
}

# Grant-related notice type keywords in TED
GRANT_KEYWORDS = [
    "grant", "subsidy", "subvention", "aide", "donation",
    "call for proposals", "appel à propositions",
    "neighbourhood", "ENI", "NDICI", "EuropeAid",
    "development cooperation", "technical assistance",
]

# EU funding programme keywords (to identify grant vs. procurement)
EU_PROGRAMME_KEYWORDS = [
    "ENI", "ENPI", "NDICI", "Global Europe", "EuropeAid",
    "Neighbourhood", "IPA", "DCI", "EIDHR", "ECHO",
    "Horizon", "ERASMUS", "LIFE", "Interreg",
]


def _search_ted(query: str, page: int = 1, limit: int = 100) -> dict:
    """Execute a TED API search query. Returns parsed JSON response."""
    payload = {
        "query": query,
        "fields": ["BT-01-notice"],
        "page": page,
        "limit": limit,
    }

    try:
        resp = requests.post(
            TED_SEARCH_URL,
            json=payload,
            headers=TED_HEADERS,
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning(f"TED API {resp.status_code} for query='{query}' page={page}")
            return {}
        return resp.json()
    except Exception as e:
        logger.error(f"TED API error: {e}")
        return {}


def _notice_to_grant(notice: dict, country_code: str, country_name: str,
                     is_grant_search: bool = False) -> dict | None:
    """Convert a TED notice to a grant record. Returns None if not relevant."""
    if not isinstance(notice, dict):
        return None

    pub_number = notice.get("publication-number", "")
    if not pub_number:
        return None

    # Extract available metadata from the notice
    # TED API v3 returns minimal data per notice in search results
    notice_links = notice.get("links", {})
    xml_link = ""
    html_link = ""
    if isinstance(notice_links, dict):
        xml_link = notice_links.get("xml", "")
        html_link = notice_links.get("html", "")

    # Notice title and details (may be limited in search results)
    title_parts = []
    for key in ["BT-01-notice", "title", "subject", "name"]:
        val = notice.get(key, "")
        if val and isinstance(val, str):
            title_parts.append(val)
            break
        elif val and isinstance(val, list):
            title_parts.extend([str(v) for v in val if v])
            break

    # Build title
    if title_parts:
        title = title_parts[0]
    else:
        title = f"EU Notice {pub_number} — {country_name}"

    # Check if this is grant-related
    combined_text = f"{title} {' '.join(str(v) for v in notice.values() if isinstance(v, str))}".lower()
    is_grant_notice = is_grant_search or any(
        kw.lower() in combined_text for kw in GRANT_KEYWORDS
    )
    is_eu_programme = any(
        kw.lower() in combined_text for kw in EU_PROGRAMME_KEYWORDS
    )

    # For non-grant-specific searches, only include if grant-related
    if not is_grant_search and not is_grant_notice and not is_eu_programme:
        return None

    # Sector classification
    sector = classify_sector(title + " " + combined_text)
    grant_type = classify_grant_type(combined_text)

    # Tags
    tags: list[str] = ["EU"]
    if is_eu_programme:
        for prog in EU_PROGRAMME_KEYWORDS:
            if prog.lower() in combined_text:
                tags.append(prog)
    if is_grant_notice:
        tags.append("grant")

    # Description
    desc_en = f"EU grant/funding notice {pub_number} for {country_name}. "
    if is_eu_programme:
        progs = [p for p in EU_PROGRAMME_KEYWORDS if p.lower() in combined_text]
        desc_en += f"Programme(s): {', '.join(progs)}. "
    desc_en += "View full details on TED Europa."

    desc_fr = f"Avis de subvention UE {pub_number} pour {MENA_COUNTRIES_FR.get(country_code, country_name)}. "
    desc_fr += "Consultez les détails complets sur TED Europa."

    desc_ar = f"إشعار منحة الاتحاد الأوروبي {pub_number} لـ {MENA_COUNTRIES_AR.get(country_code, country_name)}."

    source_url = (
        html_link
        or f"https://ted.europa.eu/en/notice/{pub_number}"
    )

    grant = {
        "id": generate_grant_id("eu_ted", pub_number),
        "title": title,
        "title_ar": f"إشعار منحة أوروبي {pub_number} — {MENA_COUNTRIES_AR.get(country_code, country_name)}",
        "title_fr": f"Avis subvention UE {pub_number} — {MENA_COUNTRIES_FR.get(country_code, country_name)}",
        "source": "eu_ted",
        "source_ref": pub_number,
        "source_url": source_url,
        "funding_organization": "European Union",
        "funding_organization_ar": "الاتحاد الأوروبي",
        "funding_organization_fr": "Union européenne",
        "funding_amount": 0,
        "funding_amount_max": 0,
        "currency": "EUR",
        "grant_type": grant_type,
        "country": country_name,
        "country_code": country_code,
        "region": "MENA",
        "sector": sector,
        "sectors": [sector],
        "eligibility_criteria": "",
        "eligibility_countries": [country_code],
        "description": desc_en,
        "description_ar": desc_ar,
        "description_fr": desc_fr,
        "application_deadline": "",
        "publish_date": "",
        "status": "open",
        "contact_info": "",
        "documents_url": source_url,
        "tags": tags[:10],
        "metadata": {
            "publication_number": pub_number,
            "xml_link": xml_link,
        },
    }
    return grant


def _scrape_country_grants(ted_code: str, iso2: str) -> list[dict]:
    """Scrape grant notices for a specific MENA country from TED."""
    grants: list[dict] = []
    country_name = MENA_COUNTRIES.get(iso2, "")
    seen_pubs: set[str] = set()

    # Search 1: Country-specific notices
    page = 1
    max_pages = 5

    while page <= max_pages:
        data = _search_ted(f"CY={ted_code}", page=page, limit=100)
        if not data:
            break

        notices = data.get("notices", [])
        total = data.get("totalNoticeCount", 0)

        if not notices:
            break

        for notice in notices:
            pub = notice.get("publication-number", "")
            if pub in seen_pubs:
                continue

            grant = _notice_to_grant(
                notice, iso2, country_name, is_grant_search=False
            )
            if grant:
                seen_pubs.add(pub)
                grants.append(grant)

        if page * 100 >= total or len(notices) < 100:
            break

        page += 1
        time.sleep(0.3)

    return grants


def _scrape_neighbourhood_grants() -> list[dict]:
    """Scrape EU Neighbourhood/ENI grant opportunities across MENA."""
    grants: list[dict] = []
    seen_pubs: set[str] = set()

    # Search for EU Neighbourhood / ENI / NDICI programmes
    neighbourhood_queries = [
        "neighbourhood AND (grant OR subvention)",
        "ENI AND (grant OR subvention OR call)",
        "NDICI AND (grant OR subvention OR cooperation)",
        "EuropeAid AND (grant OR subvention)",
    ]

    for query in neighbourhood_queries:
        page = 1

        while page <= 3:
            data = _search_ted(query, page=page, limit=100)
            if not data:
                break

            notices = data.get("notices", [])
            if not notices:
                break

            for notice in notices:
                pub = notice.get("publication-number", "")
                if pub in seen_pubs:
                    continue

                # Try to detect MENA country from notice content
                notice_text = " ".join(
                    str(v) for v in notice.values() if isinstance(v, str)
                ).lower()

                country_code = ""
                country_name = ""

                # Check against our MENA country names
                for code, name in MENA_COUNTRIES.items():
                    if name.lower() in notice_text:
                        country_code = code
                        country_name = name
                        break

                # Also check TED country codes in the notice
                if not country_code:
                    for ted3, iso2 in MENA_TED_CODES.items():
                        if ted3.lower() in notice_text:
                            country_code = iso2
                            country_name = MENA_COUNTRIES.get(iso2, "")
                            break

                if not country_code:
                    # Generic MENA-region grant
                    country_code = "XX"
                    country_name = "MENA Region"

                grant = _notice_to_grant(
                    notice, country_code, country_name, is_grant_search=True
                )
                if grant:
                    seen_pubs.add(pub)
                    # Update eligibility countries for neighbourhood grants
                    if country_code == "XX":
                        grant["eligibility_countries"] = list(
                            MENA_TED_CODES.values()
                        )
                    grants.append(grant)

            if len(notices) < 100:
                break
            page += 1
            time.sleep(0.3)

        time.sleep(0.5)

    return grants


def scrape() -> list[dict]:
    """Scrape EU TED for MENA grant opportunities."""
    logger.info("Starting EU TED grants scraper...")

    all_grants: list[dict] = []
    seen_refs: set[str] = set()

    # Phase 1: Country-specific grant searches
    for ted_code, iso2 in MENA_TED_CODES.items():
        country_grants = _scrape_country_grants(ted_code, iso2)
        for g in country_grants:
            if g["source_ref"] not in seen_refs:
                seen_refs.add(g["source_ref"])
                all_grants.append(g)

        logger.info(
            f"TED {ted_code} ({MENA_COUNTRIES.get(iso2, '')}): "
            f"{len(country_grants)} grant notices"
        )
        time.sleep(0.3)

    logger.info(f"Phase 1 — Country grants: {len(all_grants)}")

    # Phase 2: EU Neighbourhood programme grants
    neighbourhood = _scrape_neighbourhood_grants()
    new_neighbourhood = 0
    for g in neighbourhood:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)
            new_neighbourhood += 1

    logger.info(f"Phase 2 — Neighbourhood grants: {new_neighbourhood}")
    logger.info(f"EU TED total: {len(all_grants)} grant notices")

    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "eu_ted")
    print(f"Scraped {len(results)} grants from EU TED")
