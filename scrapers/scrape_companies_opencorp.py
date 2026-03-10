"""
Scraper for OpenCorporates — global company registry.
Source: https://api.opencorporates.com/v0.4/companies/search

Free tier: 500 requests/month (no API key needed for basic access).
Searches by jurisdiction_code for MENA countries and filters for
construction/engineering/consulting companies.
"""

import os
import time
import logging
import requests
from typing import Optional

from config import MENA_COUNTRIES, HEADERS
from base_scraper import (
    generate_company_id,
    classify_sector,
    classify_company_size,
    save_companies,
)

logger = logging.getLogger("opencorporates")

API_BASE = "https://api.opencorporates.com/v0.4"
API_TOKEN = os.environ.get("OPENCORPORATES_API_TOKEN", "")

# OpenCorporates jurisdiction codes for MENA countries
JURISDICTION_MAP = {
    "SA": "sa",
    "AE": "ae",
    "EG": "eg",
    "MA": "ma",
    "KW": "kw",
    "QA": "qa",
    "BH": "bh",
    "OM": "om",
    "JO": "jo",
    "TN": "tn",
    "DZ": "dz",
    "LY": "ly",
    "IQ": "iq",
    "LB": "lb",
    "SD": "sd",
    "YE": "ye",
}

# Industry search terms to find construction/engineering/consulting companies
INDUSTRY_SEARCH_TERMS = [
    "construction",
    "engineering",
    "contracting",
    "building",
    "infrastructure",
    "consulting",
    "contractor",
    "civil engineering",
    "electrical engineering",
    "mechanical engineering",
    "architecture",
    "real estate development",
    "water treatment",
    "roads",
    "bridges",
    "oil and gas",
    "energy",
    "telecommunications",
    "transport",
    "industrial",
    "manufacturing",
    "steel",
    "cement",
    "mining",
    "facilities management",
]

# Rate limiting
REQUESTS_PER_MINUTE = 8  # Conservative for free tier
REQUEST_DELAY = 60.0 / REQUESTS_PER_MINUTE  # ~7.5 seconds between requests
MAX_PAGES_PER_SEARCH = 5  # OpenCorporates free tier limits results


def _build_params(
    query: str,
    jurisdiction: str,
    page: int = 1,
) -> dict:
    """Build query parameters for the OpenCorporates API."""
    params = {
        "q": query,
        "jurisdiction_code": jurisdiction,
        "page": page,
        "per_page": 30,
        "current_status": "Active",
        "order": "score",
    }
    if API_TOKEN:
        params["api_token"] = API_TOKEN
    return params


def _parse_company(item: dict, country_code: str) -> Optional[dict]:
    """Parse an OpenCorporates company result into our schema."""
    company_data = item.get("company", {})
    if not company_data:
        return None

    name = company_data.get("name", "").strip()
    if not name or len(name) < 3:
        return None

    company_number = company_data.get("company_number", "")
    jurisdiction = company_data.get("jurisdiction_code", "").upper()

    # Resolve country from jurisdiction or fallback
    resolved_code = jurisdiction[:2].upper() if jurisdiction else country_code
    country_name = MENA_COUNTRIES.get(resolved_code, "")
    if not country_name:
        resolved_code = country_code
        country_name = MENA_COUNTRIES.get(country_code, country_code)

    # Registered address
    reg_addr = company_data.get("registered_address_in_full", "") or ""
    registered_address = company_data.get("registered_address", {}) or {}
    city = ""
    if isinstance(registered_address, dict):
        city = registered_address.get("locality", "") or ""

    # Incorporation date -> founded year
    inc_date = company_data.get("incorporation_date", "") or ""
    founded_year = None
    if inc_date and len(inc_date) >= 4:
        try:
            founded_year = int(inc_date[:4])
        except (ValueError, TypeError):
            pass

    # Company type from OpenCorporates
    oc_type = company_data.get("company_type", "") or ""

    # Sector classification from name + type
    sector_text = f"{name} {oc_type}"
    sector = classify_sector(sector_text)

    # Determine company_type for our schema
    company_type = "contractor"  # default
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["consult", "advisory", "design", "architect"]):
        company_type = "consultant"
    elif any(kw in name_lower for kw in ["supply", "supplier", "trading", "import", "export"]):
        company_type = "supplier"
    elif any(kw in name_lower for kw in ["manufactur", "factory", "industrial", "steel", "cement"]):
        company_type = "manufacturer"
    elif any(kw in name_lower for kw in ["develop", "real estate", "property", "investment"]):
        company_type = "developer"

    # Source URL
    oc_url = company_data.get("opencorporates_url", "")
    source_url = oc_url if oc_url else f"https://opencorporates.com/companies/{jurisdiction}/{company_number}"

    # Build the unique ref
    ref = f"{jurisdiction}:{company_number}" if company_number else name

    return {
        "id": generate_company_id("opencorporates", ref),
        "name": name,
        "name_ar": "",
        "name_fr": "",
        "legal_name": name,
        "source": "opencorporates",
        "source_ref": ref,
        "source_url": source_url,
        "country": country_name,
        "country_code": resolved_code,
        "city": city,
        "address": reg_addr,
        "website": "",
        "email": "",
        "phone": "",
        "sector": sector,
        "sectors": [sector],
        "subsectors": [],
        "company_type": company_type,
        "company_size": classify_company_size(),
        "employee_count": None,
        "annual_revenue": None,
        "revenue_currency": "USD",
        "founded_year": founded_year,
        "registration_number": company_number,
        "certifications": [],
        "classifications": [],
        "prequalified_with": [],
        "notable_projects": [],
        "jv_experience": False,
        "international_presence": [resolved_code],
        "description": f"{name} — registered in {country_name} ({jurisdiction}). Type: {oc_type}.",
        "description_ar": "",
        "description_fr": "",
        "tags": ["opencorporates"],
        "metadata": {
            "opencorporates_url": oc_url,
            "company_type_raw": oc_type,
            "jurisdiction_code": jurisdiction,
            "current_status": company_data.get("current_status", ""),
            "incorporation_date": inc_date,
        },
        "verified": False,
        "active": True,
    }


def _search_companies(
    session: requests.Session,
    query: str,
    jurisdiction: str,
    country_code: str,
    max_pages: int = MAX_PAGES_PER_SEARCH,
) -> list[dict]:
    """Search OpenCorporates for companies matching query in a jurisdiction."""
    results = []
    page = 1

    while page <= max_pages:
        params = _build_params(query, jurisdiction, page)
        try:
            resp = session.get(
                f"{API_BASE}/companies/search",
                params=params,
                timeout=30,
            )

            if resp.status_code == 403:
                logger.warning(f"OpenCorporates 403 for {jurisdiction}/{query} — rate limited or token required")
                break

            if resp.status_code == 429:
                logger.warning(f"OpenCorporates 429 rate limit for {jurisdiction}/{query} — backing off 60s")
                time.sleep(60)
                continue

            if resp.status_code != 200:
                logger.warning(f"OpenCorporates HTTP {resp.status_code} for {jurisdiction}/{query} page {page}")
                break

            data = resp.json()
            api_results = data.get("results", {})
            companies_list = api_results.get("companies", [])

            if not companies_list:
                logger.debug(f"No more results for {jurisdiction}/{query} page {page}")
                break

            for item in companies_list:
                parsed = _parse_company(item, country_code)
                if parsed:
                    results.append(parsed)

            total_count = api_results.get("total_count", 0)
            total_pages = api_results.get("total_pages", 1)

            logger.debug(
                f"  {jurisdiction}/{query} page {page}/{total_pages}: "
                f"{len(companies_list)} items (total: {total_count})"
            )

            if page >= total_pages:
                break

            page += 1
            time.sleep(REQUEST_DELAY)

        except requests.exceptions.Timeout:
            logger.warning(f"OpenCorporates timeout for {jurisdiction}/{query} page {page}")
            break

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"OpenCorporates connection error for {jurisdiction}/{query}: {e}")
            time.sleep(15)
            break

        except Exception as e:
            logger.error(f"OpenCorporates error for {jurisdiction}/{query} page {page}: {e}")
            break

    return results


def scrape() -> list[dict]:
    """Scrape company data from OpenCorporates for MENA countries.

    Searches across all MENA jurisdictions for construction, engineering,
    and consulting companies. Deduplicates by company registration number.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    all_companies: list[dict] = []
    seen_ids: set[str] = set()

    # Priority jurisdictions (larger construction markets first)
    priority_jurisdictions = ["SA", "AE", "EG", "QA", "KW", "MA", "OM", "BH", "JO"]
    other_jurisdictions = [k for k in JURISDICTION_MAP if k not in priority_jurisdictions]
    ordered_codes = priority_jurisdictions + other_jurisdictions

    # Priority search terms (most relevant first)
    priority_terms = [
        "construction",
        "contracting",
        "engineering",
        "building",
        "infrastructure",
        "consulting",
        "real estate",
    ]

    request_count = 0
    max_requests = 450 if API_TOKEN else 400  # Leave margin under 500 monthly limit

    for country_code in ordered_codes:
        jurisdiction = JURISDICTION_MAP.get(country_code)
        if not jurisdiction:
            continue

        country_name = MENA_COUNTRIES.get(country_code, country_code)
        logger.info(f"Searching OpenCorporates for {country_name} ({jurisdiction})...")

        for term in priority_terms:
            if request_count >= max_requests:
                logger.warning(
                    f"Approaching monthly request limit ({request_count}/{max_requests}) — stopping"
                )
                break

            companies = _search_companies(session, term, jurisdiction, country_code)
            request_count += len(companies) // 30 + 1  # Approximate page count

            new_count = 0
            for company in companies:
                cid = company["id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    all_companies.append(company)
                    new_count += 1

            if new_count > 0:
                logger.info(
                    f"  {country_name}/{term}: {new_count} new companies "
                    f"(total: {len(all_companies)})"
                )

            time.sleep(REQUEST_DELAY)

        if request_count >= max_requests:
            break

    logger.info(
        f"OpenCorporates total: {len(all_companies)} unique companies "
        f"(~{request_count} API requests used)"
    )
    return all_companies


if __name__ == "__main__":
    results = scrape()
    save_companies(results, "opencorporates")
    print(f"Scraped {len(results)} companies from OpenCorporates")
