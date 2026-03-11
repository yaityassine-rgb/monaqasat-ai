"""
Grant scraper for Arab Fund for Economic and Social Development (AFESD).
Sources:
  - AFESD website: https://www.arabfund.org/
  - Projects/operations pages: https://www.arabfund.org/Default.aspx?pageId=355
  - Annual reports: https://www.arabfund.org/Default.aspx?pageId=25

The Arab Fund specifically targets Arab countries and all projects are
MENA-relevant. It provides soft loans, grants, and technical assistance
to member Arab countries for economic and social development.

Member countries: All 22 Arab League members (covering all MENA countries).

Currency: KWD (Kuwaiti Dinar) primary, with some USD amounts.
"""

import re
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

logger = logging.getLogger("grants_afesd")

# AFESD endpoints
AFESD_BASE_URL = "https://www.arabfund.org"
AFESD_PROJECTS_URL = "https://www.arabfund.org/Default.aspx?pageId=355"
AFESD_LOANS_URL = "https://www.arabfund.org/Default.aspx?pageId=357"
AFESD_GRANTS_URL = "https://www.arabfund.org/Default.aspx?pageId=356"

# Country name -> code mapping (Arabic and English)
_AFESD_COUNTRY_TO_CODE: dict[str, str] = {}
for _code, _name in MENA_COUNTRIES.items():
    _AFESD_COUNTRY_TO_CODE[_name.lower()] = _code
_AFESD_COUNTRY_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "egypt, arab republic of": "EG",
    "arab republic of egypt": "EG",
    "morocco": "MA",
    "kingdom of morocco": "MA",
    "republic of tunisia": "TN",
    "hashemite kingdom of jordan": "JO",
    "jordan": "JO",
    "west bank and gaza": "PS",
    "palestine": "PS",
    "state of palestine": "PS",
    "republic of iraq": "IQ",
    "republic of yemen": "YE",
    "kingdom of saudi arabia": "SA",
    "republic of sudan": "SD",
    "algeria": "DZ",
    "mauritania": "MR",
    "lebanon": "LB",
    "libya": "LY",
    "kuwait": "KW",
    "qatar": "QA",
    "bahrain": "BH",
    "oman": "OM",
    "somalia": "",  # Not in our MENA list but AFESD member
    "djibouti": "",
    "comoros": "",
    "syrian arab republic": "",  # Syria not in our current MENA list
    "syria": "",
})

# Arabic country name to code
_AFESD_AR_TO_CODE: dict[str, str] = {}
for _code, _name_ar in MENA_COUNTRIES_AR.items():
    _AFESD_AR_TO_CODE[_name_ar] = _code
# Additional Arabic spellings
_AFESD_AR_TO_CODE.update({
    "\u0627\u0644\u0645\u063a\u0631\u0628": "MA",
    "\u0645\u0635\u0631": "EG",
    "\u0627\u0644\u0623\u0631\u062f\u0646": "JO",
    "\u062a\u0648\u0646\u0633": "TN",
    "\u0627\u0644\u062c\u0632\u0627\u0626\u0631": "DZ",
    "\u0627\u0644\u0639\u0631\u0627\u0642": "IQ",
    "\u0644\u0628\u0646\u0627\u0646": "LB",
    "\u0641\u0644\u0633\u0637\u064a\u0646": "PS",
    "\u0627\u0644\u0633\u0648\u062f\u0627\u0646": "SD",
    "\u0627\u0644\u064a\u0645\u0646": "YE",
    "\u0644\u064a\u0628\u064a\u0627": "LY",
    "\u0645\u0648\u0631\u064a\u062a\u0627\u0646\u064a\u0627": "MR",
    "\u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629": "SA",
    "\u0627\u0644\u0643\u0648\u064a\u062a": "KW",
    "\u0642\u0637\u0631": "QA",
    "\u0627\u0644\u0628\u062d\u0631\u064a\u0646": "BH",
    "\u0639\u0645\u0627\u0646": "OM",
    "\u0627\u0644\u0625\u0645\u0627\u0631\u0627\u062a": "AE",
})

# KWD to USD approximate conversion rate
KWD_TO_USD = 3.26

# Browser headers
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}


def _resolve_country(name_raw: str) -> tuple[str, str]:
    """Resolve a country name to (iso2_code, country_name).

    Returns ("", "") if not a MENA country.
    """
    if not name_raw:
        return "", ""
    key = name_raw.strip().lower()
    code = _AFESD_COUNTRY_TO_CODE.get(key, "")
    if code:
        return code, MENA_COUNTRIES[code]
    # Try partial match
    for pattern, c in _AFESD_COUNTRY_TO_CODE.items():
        if c and (pattern in key or key in pattern):
            return c, MENA_COUNTRIES[c]
    return "", ""


def _detect_mena_country(text: str) -> tuple[str, str]:
    """Detect a MENA country mention in text (English or Arabic)."""
    text_lower = text.lower()
    # Check English names
    for name, code in _AFESD_COUNTRY_TO_CODE.items():
        if code and name in text_lower:
            return code, MENA_COUNTRIES.get(code, "")
    # Check Arabic names
    for name_ar, code in _AFESD_AR_TO_CODE.items():
        if code and name_ar in text:
            return code, MENA_COUNTRIES.get(code, "")
    return "", ""


def _detect_multiple_countries(text: str) -> list[str]:
    """Detect all MENA countries mentioned in text."""
    countries = []
    text_lower = text.lower()
    for name, code in _AFESD_COUNTRY_TO_CODE.items():
        if code and name in text_lower and code not in countries:
            countries.append(code)
    for name_ar, code in _AFESD_AR_TO_CODE.items():
        if code and name_ar in text and code not in countries:
            countries.append(code)
    return countries


def _parse_kwd_amount(text: str) -> tuple[float, str]:
    """Parse an amount that might be in KWD or USD."""
    if not text:
        return 0.0, "USD"

    text = text.strip()
    currency = "USD"

    # Detect KWD
    if "KD" in text.upper() or "KWD" in text.upper() or "\u062f\u064a\u0646\u0627\u0631" in text:
        currency = "KWD"
        text = re.sub(r"[KkDd]{2,3}", "", text)
        text = text.replace("\u062f\u064a\u0646\u0627\u0631", "").replace("\u0643\u0648\u064a\u062a\u064a", "")
    elif "$" in text or "USD" in text.upper():
        currency = "USD"

    amount = parse_amount(text)

    return amount, currency


def _scrape_afesd_projects() -> list[dict]:
    """Scrape AFESD projects from the website."""
    grants: list[dict] = []
    seen_refs: set[str] = set()

    # Pages to scrape: projects, loans, grants/TA
    pages_to_scrape = [
        (AFESD_PROJECTS_URL, "project"),
        (AFESD_LOANS_URL, "loan"),
        (AFESD_GRANTS_URL, "grant"),
    ]

    for page_url, page_type in pages_to_scrape:
        try:
            resp = requests.get(
                page_url,
                headers=BROWSER_HEADERS,
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning(f"AFESD {page_type} page HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for project tables
            tables = soup.select("table")
            for table in tables:
                rows = table.select("tr")
                header_row = rows[0] if rows else None

                # Get column indices from header
                if header_row:
                    headers = [th.get_text(strip=True).lower() for th in header_row.select("th, td")]
                else:
                    headers = []

                for row in rows[1:]:
                    cells = row.select("td")
                    if len(cells) < 2:
                        continue

                    # Try to extract data from cells
                    cell_texts = [c.get_text(strip=True) for c in cells]
                    row_text = " ".join(cell_texts)

                    # Find title (usually longest meaningful cell)
                    title = ""
                    for ct in cell_texts:
                        if len(ct) > len(title) and len(ct) > 15:
                            title = ct

                    if not title:
                        continue

                    # Detect country
                    country_code, country_name = _detect_mena_country(row_text)
                    if not country_code:
                        continue

                    # Try to find amount
                    amount = 0.0
                    currency = "KWD"
                    for ct in cell_texts:
                        if any(c.isdigit() for c in ct) and len(ct) < 50:
                            amt, cur = _parse_kwd_amount(ct)
                            if amt > 0:
                                amount = amt
                                currency = cur
                                break

                    # Try to find date
                    pub_date = ""
                    for ct in cell_texts:
                        d = parse_date(ct)
                        if d:
                            pub_date = d
                            break

                    # Generate ref from title
                    ref = re.sub(r"[^a-zA-Z0-9]", "_", title[:60]).strip("_")
                    if ref in seen_refs:
                        continue
                    seen_refs.add(ref)

                    # Get link if any
                    link = row.select_one("a")
                    href = link.get("href", "") if link else ""
                    source_url = href
                    if href and not href.startswith("http"):
                        source_url = f"{AFESD_BASE_URL}/{href.lstrip('/')}"

                    # Classify
                    sector = classify_sector(title)
                    grant_type = classify_grant_type(title)
                    if page_type == "grant":
                        grant_type = "technical_assistance"
                    elif page_type == "loan":
                        grant_type = "project_grant"

                    eligibility_countries = _detect_multiple_countries(row_text)
                    if country_code not in eligibility_countries:
                        eligibility_countries.insert(0, country_code)

                    grant = {
                        "id": generate_grant_id("afesd", ref),
                        "title": title,
                        "title_ar": "",
                        "title_fr": "",
                        "source": "afesd",
                        "source_ref": ref,
                        "source_url": source_url or AFESD_PROJECTS_URL,
                        "funding_organization": "Arab Fund for Economic and Social Development",
                        "funding_organization_ar": "\u0627\u0644\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0639\u0631\u0628\u064a \u0644\u0644\u0625\u0646\u0645\u0627\u0621 \u0627\u0644\u0627\u0642\u062a\u0635\u0627\u062f\u064a \u0648\u0627\u0644\u0627\u062c\u062a\u0645\u0627\u0639\u064a",
                        "funding_organization_fr": "Fonds arabe pour le d\u00e9veloppement \u00e9conomique et social",
                        "funding_amount": round(amount, 2),
                        "funding_amount_max": 0,
                        "currency": currency,
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": sector,
                        "sectors": [sector],
                        "eligibility_criteria": f"AFESD {page_type} for Arab member countries",
                        "eligibility_countries": eligibility_countries,
                        "description": title[:2000],
                        "description_ar": "",
                        "description_fr": "",
                        "application_deadline": "",
                        "publish_date": pub_date or "",
                        "status": "open",
                        "contact_info": "Arab Fund for Economic and Social Development, Kuwait",
                        "documents_url": source_url or "",
                        "tags": ["AFESD", page_type],
                        "metadata": {
                            "project_type": page_type,
                            "amount_currency": currency,
                        },
                    }
                    grants.append(grant)

            # Also look for list items, divs, etc.
            items = (
                soup.select(".project-item")
                or soup.select(".list-item")
                or soup.select("article")
                or soup.select("[class*='project']")
            )

            for item in items:
                title_el = (
                    item.select_one("h3")
                    or item.select_one("h2")
                    or item.select_one("h4")
                    or item.select_one(".title")
                    or item.select_one("a")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 10:
                    continue

                item_text = item.get_text(strip=True)
                country_code, country_name = _detect_mena_country(item_text)
                if not country_code:
                    continue

                ref = re.sub(r"[^a-zA-Z0-9]", "_", title[:60]).strip("_")
                if ref in seen_refs:
                    continue
                seen_refs.add(ref)

                link = item.select_one("a")
                href = link.get("href", "") if link else ""
                source_url = href
                if href and not href.startswith("http"):
                    source_url = f"{AFESD_BASE_URL}/{href.lstrip('/')}"

                desc_el = item.select_one("p") or item.select_one(".description")
                description = desc_el.get_text(strip=True) if desc_el else title

                sector = classify_sector(f"{title} {description}")
                grant_type = classify_grant_type(f"{title} {description}")

                grant = {
                    "id": generate_grant_id("afesd", ref),
                    "title": title,
                    "title_ar": "",
                    "title_fr": "",
                    "source": "afesd",
                    "source_ref": ref,
                    "source_url": source_url or AFESD_PROJECTS_URL,
                    "funding_organization": "Arab Fund for Economic and Social Development",
                    "funding_organization_ar": "\u0627\u0644\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0639\u0631\u0628\u064a \u0644\u0644\u0625\u0646\u0645\u0627\u0621 \u0627\u0644\u0627\u0642\u062a\u0635\u0627\u062f\u064a \u0648\u0627\u0644\u0627\u062c\u062a\u0645\u0627\u0639\u064a",
                    "funding_organization_fr": "Fonds arabe pour le d\u00e9veloppement \u00e9conomique et social",
                    "funding_amount": 0,
                    "funding_amount_max": 0,
                    "currency": "KWD",
                    "grant_type": grant_type,
                    "country": country_name,
                    "country_code": country_code,
                    "region": "MENA",
                    "sector": sector,
                    "sectors": [sector],
                    "eligibility_criteria": "AFESD project for Arab member countries",
                    "eligibility_countries": [country_code],
                    "description": (description or title)[:2000],
                    "description_ar": "",
                    "description_fr": "",
                    "application_deadline": "",
                    "publish_date": "",
                    "status": "open",
                    "contact_info": "Arab Fund for Economic and Social Development, Kuwait",
                    "documents_url": source_url or "",
                    "tags": ["AFESD", page_type],
                    "metadata": {
                        "project_type": page_type,
                    },
                }
                grants.append(grant)

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"AFESD {page_type} page: {e}")
            continue

    logger.info(f"AFESD website: {len(grants)} projects")
    return grants


def _scrape_afesd_arabic() -> list[dict]:
    """Scrape AFESD Arabic pages for additional project data."""
    grants: list[dict] = []
    seen_refs: set[str] = set()

    # Arabic version of the site
    ar_urls = [
        f"{AFESD_BASE_URL}/Default.aspx?pageId=355&lang=ar",
        f"{AFESD_BASE_URL}/Default.aspx?pageId=356&lang=ar",
        f"{AFESD_BASE_URL}/Default.aspx?pageId=357&lang=ar",
    ]

    ar_headers = BROWSER_HEADERS.copy()
    ar_headers["Accept-Language"] = "ar,en;q=0.5"

    for ar_url in ar_urls:
        try:
            resp = requests.get(ar_url, headers=ar_headers, timeout=30)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for tables with Arabic content
            tables = soup.select("table")
            for table in tables:
                rows = table.select("tr")
                for row in rows[1:]:
                    cells = row.select("td")
                    if len(cells) < 2:
                        continue

                    cell_texts = [c.get_text(strip=True) for c in cells]
                    row_text = " ".join(cell_texts)

                    # Find Arabic title
                    title_ar = ""
                    for ct in cell_texts:
                        if len(ct) > len(title_ar) and len(ct) > 10:
                            title_ar = ct

                    if not title_ar:
                        continue

                    # Detect country from Arabic
                    country_code, country_name = _detect_mena_country(row_text)
                    if not country_code:
                        continue

                    ref = re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]", "_", title_ar[:60]).strip("_")
                    if ref in seen_refs:
                        continue
                    seen_refs.add(ref)

                    # Parse amount
                    amount = 0.0
                    currency = "KWD"
                    for ct in cell_texts:
                        if any(c.isdigit() for c in ct) and len(ct) < 50:
                            amt, cur = _parse_kwd_amount(ct)
                            if amt > 0:
                                amount = amt
                                currency = cur
                                break

                    sector = classify_sector(title_ar)
                    grant_type = classify_grant_type(title_ar)

                    grant = {
                        "id": generate_grant_id("afesd_ar", ref),
                        "title": title_ar,
                        "title_ar": title_ar,
                        "title_fr": "",
                        "source": "afesd",
                        "source_ref": ref,
                        "source_url": AFESD_PROJECTS_URL,
                        "funding_organization": "Arab Fund for Economic and Social Development",
                        "funding_organization_ar": "\u0627\u0644\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0639\u0631\u0628\u064a \u0644\u0644\u0625\u0646\u0645\u0627\u0621 \u0627\u0644\u0627\u0642\u062a\u0635\u0627\u062f\u064a \u0648\u0627\u0644\u0627\u062c\u062a\u0645\u0627\u0639\u064a",
                        "funding_organization_fr": "Fonds arabe pour le d\u00e9veloppement \u00e9conomique et social",
                        "funding_amount": round(amount, 2),
                        "funding_amount_max": 0,
                        "currency": currency,
                        "grant_type": grant_type,
                        "country": country_name,
                        "country_code": country_code,
                        "region": "MENA",
                        "sector": sector,
                        "sectors": [sector],
                        "eligibility_criteria": "\u0645\u0634\u0631\u0648\u0639 \u0627\u0644\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0639\u0631\u0628\u064a \u0644\u0644\u062f\u0648\u0644 \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0623\u0639\u0636\u0627\u0621",
                        "eligibility_countries": [country_code],
                        "description": title_ar[:2000],
                        "description_ar": title_ar[:2000],
                        "description_fr": "",
                        "application_deadline": "",
                        "publish_date": "",
                        "status": "open",
                        "contact_info": "\u0627\u0644\u0635\u0646\u062f\u0648\u0642 \u0627\u0644\u0639\u0631\u0628\u064a \u0644\u0644\u0625\u0646\u0645\u0627\u0621 \u0627\u0644\u0627\u0642\u062a\u0635\u0627\u062f\u064a \u0648\u0627\u0644\u0627\u062c\u062a\u0645\u0627\u0639\u064a\u060c \u0627\u0644\u0643\u0648\u064a\u062a",
                        "documents_url": "",
                        "tags": ["AFESD", "arabic"],
                        "metadata": {},
                    }
                    grants.append(grant)

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"AFESD Arabic page: {e}")
            continue

    logger.info(f"AFESD Arabic: {len(grants)} projects")
    return grants


def scrape() -> list[dict]:
    """Scrape Arab Fund for Economic and Social Development for MENA grants."""
    logger.info("Starting AFESD grants scraper...")

    # Phase 1: English website pages
    en_grants = _scrape_afesd_projects()
    logger.info(f"Phase 1 -- English: {len(en_grants)} grants")

    # Phase 2: Arabic website pages
    ar_grants = _scrape_afesd_arabic()
    logger.info(f"Phase 2 -- Arabic: {len(ar_grants)} grants")

    # Merge and deduplicate by source_ref
    all_grants = en_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in ar_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"AFESD total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "afesd")
    print(f"Scraped {len(results)} grants from AFESD")
