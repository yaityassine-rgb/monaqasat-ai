"""
Scraper for government vendor/contractor registries across MENA.

Targets publicly accessible parts of:
- Etimad (Saudi Arabia) — contractor classification lists
- DEWA (Dubai) — approved vendor/contractor lists
- Ashghal (Qatar) — registered contractor lists
- Abu Dhabi DoT — public contractor lists
- Other MENA government procurement portals

Many of these portals require authentication or have limited public data.
The scraper logs warnings and continues when data is not accessible.
"""

import re
import time
import logging
import requests
from typing import Optional
from bs4 import BeautifulSoup

from config import HEADERS
from base_scraper import (
    generate_company_id,
    classify_sector,
    classify_company_size,
    save_companies,
)

logger = logging.getLogger("vendors")

# Rate limiting
REQUEST_DELAY = 4.0  # Seconds between requests
MAX_RETRIES = 2


def _create_session() -> requests.Session:
    """Create a session with browser-like headers."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    return s


def _safe_get(session: requests.Session, url: str, timeout: int = 30, **kwargs) -> Optional[requests.Response]:
    """Make a GET request with retries and error handling."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=timeout, **kwargs)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (403, 401):
                logger.warning(f"Access denied ({resp.status_code}) for {url}")
                return None
            if resp.status_code == 429:
                logger.warning(f"Rate limited (429) for {url} — backing off")
                time.sleep(30)
                continue
            logger.warning(f"HTTP {resp.status_code} for {url}")
            if attempt < MAX_RETRIES:
                time.sleep(5)
                continue
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {url} (attempt {attempt + 1}/{MAX_RETRIES + 1})")
            if attempt < MAX_RETRIES:
                time.sleep(5)
            continue
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error for {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(10)
            continue
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
    return None


def _extract_company_type(text: str) -> str:
    """Determine company type from classification/category text."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["consult", "advisory", "design", "architect", "supervision"]):
        return "consultant"
    if any(kw in text_lower for kw in ["supply", "supplier", "vendor", "trading", "distributor"]):
        return "supplier"
    if any(kw in text_lower for kw in ["manufactur", "factory", "fabricat", "production"]):
        return "manufacturer"
    if any(kw in text_lower for kw in ["develop", "investment", "property"]):
        return "developer"
    return "contractor"


# ---------------------------------------------------------------------------
# Portal 1: Etimad (Saudi Arabia)
# ---------------------------------------------------------------------------

def _scrape_etimad_contractors(session: requests.Session) -> list[dict]:
    """Scrape contractor classification data from Etimad's public pages.

    Etimad publishes some contractor classification lists publicly.
    The main contractor search at tenders.etimad.sa may require login,
    so we try multiple public-facing endpoints.
    """
    logger.info("Scraping Etimad (Saudi Arabia) contractor registry...")
    companies = []

    # Etimad's public contractor search page
    urls_to_try = [
        "https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync",
        "https://www.etimad.sa/en/contractors",
        "https://www.etimad.sa/en/approved-contractors",
        "https://tenders.etimad.sa/Contractor/ContractorClassificationForVisitor",
    ]

    for url in urls_to_try:
        resp = _safe_get(session, url)
        if not resp:
            continue

        content_type = resp.headers.get("content-type", "")

        # Try JSON response first (API endpoint)
        if "json" in content_type:
            try:
                data = resp.json()
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("data", data.get("items", data.get("contractors", [])))

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    name = (
                        item.get("contractorName", "")
                        or item.get("supplierName", "")
                        or item.get("name", "")
                    ).strip()
                    if not name or len(name) < 3:
                        continue

                    ref = (
                        item.get("contractorId", "")
                        or item.get("supplierId", "")
                        or item.get("crNumber", "")
                        or name
                    )
                    classification = item.get("classificationName", "") or item.get("classification", "")
                    category = item.get("categoryName", "") or item.get("category", "")
                    cr_number = item.get("crNumber", "") or item.get("commercialRegistration", "")

                    sector_text = f"{name} {classification} {category}"
                    sector = classify_sector(sector_text)

                    companies.append({
                        "id": generate_company_id("etimad_vendor", str(ref)),
                        "name": name,
                        "name_ar": item.get("contractorNameAr", "") or item.get("nameAr", ""),
                        "name_fr": "",
                        "legal_name": name,
                        "source": "etimad_vendor",
                        "source_ref": str(ref),
                        "source_url": "https://www.etimad.sa",
                        "country": "Saudi Arabia",
                        "country_code": "SA",
                        "city": item.get("city", "") or item.get("cityName", ""),
                        "address": item.get("address", ""),
                        "website": item.get("website", ""),
                        "email": item.get("email", ""),
                        "phone": item.get("phone", "") or item.get("mobile", ""),
                        "sector": sector,
                        "sectors": [sector],
                        "subsectors": [classification] if classification else [],
                        "company_type": _extract_company_type(f"{classification} {category}"),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "SAR",
                        "founded_year": None,
                        "registration_number": str(cr_number),
                        "certifications": [],
                        "classifications": [classification] if classification else [],
                        "prequalified_with": ["etimad"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["SA"],
                        "description": f"Etimad registered contractor. Classification: {classification}. Category: {category}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["etimad", "government_registered"],
                        "metadata": {
                            "classification": classification,
                            "category": category,
                            "cr_number": cr_number,
                            "portal": "etimad",
                        },
                        "verified": True,
                        "active": True,
                    })

                if companies:
                    logger.info(f"  Etimad: parsed {len(companies)} contractors from {url}")
                    break

            except (ValueError, KeyError) as e:
                logger.debug(f"  Etimad JSON parse error from {url}: {e}")
                continue

        # Try HTML response (scrape table)
        elif "html" in content_type:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for tables with contractor data
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue
                        name = cells[0].get_text(strip=True)
                        if not name or len(name) < 3:
                            continue
                        classification = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        city = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        phone = cells[3].get_text(strip=True) if len(cells) > 3 else ""

                        sector_text = f"{name} {classification}"
                        sector = classify_sector(sector_text)
                        ref = f"etimad-html-{name}"

                        companies.append({
                            "id": generate_company_id("etimad_vendor", ref),
                            "name": name,
                            "name_ar": "",
                            "name_fr": "",
                            "legal_name": name,
                            "source": "etimad_vendor",
                            "source_ref": ref,
                            "source_url": url,
                            "country": "Saudi Arabia",
                            "country_code": "SA",
                            "city": city,
                            "address": "",
                            "website": "",
                            "email": "",
                            "phone": phone,
                            "sector": sector,
                            "sectors": [sector],
                            "subsectors": [classification] if classification else [],
                            "company_type": _extract_company_type(classification),
                            "company_size": classify_company_size(),
                            "employee_count": None,
                            "annual_revenue": None,
                            "revenue_currency": "SAR",
                            "founded_year": None,
                            "registration_number": "",
                            "certifications": [],
                            "classifications": [classification] if classification else [],
                            "prequalified_with": ["etimad"],
                            "notable_projects": [],
                            "jv_experience": False,
                            "international_presence": ["SA"],
                            "description": f"Etimad registered contractor. Classification: {classification}.",
                            "description_ar": "",
                            "description_fr": "",
                            "tags": ["etimad", "government_registered"],
                            "metadata": {"classification": classification, "portal": "etimad"},
                            "verified": True,
                            "active": True,
                        })

                if companies:
                    logger.info(f"  Etimad: parsed {len(companies)} contractors from HTML at {url}")
                    break

            except Exception as e:
                logger.debug(f"  Etimad HTML parse error from {url}: {e}")
                continue

        time.sleep(REQUEST_DELAY)

    if not companies:
        logger.warning(
            "Etimad: no contractor data accessible publicly. "
            "Contractor classification lists may require authentication."
        )

    return companies


# ---------------------------------------------------------------------------
# Portal 2: DEWA (Dubai Electricity & Water Authority)
# ---------------------------------------------------------------------------

def _scrape_dewa_vendors(session: requests.Session) -> list[dict]:
    """Scrape approved vendor/contractor lists from DEWA's public pages."""
    logger.info("Scraping DEWA (Dubai) vendor registry...")
    companies = []

    urls_to_try = [
        "https://www.dewa.gov.ae/en/about-us/business-and-vendors",
        "https://www.dewa.gov.ae/en/about-us/business-and-vendors/registered-vendors",
        "https://www.dewa.gov.ae/en/about-us/business-and-vendors/approved-contractors",
        "https://www.dewa.gov.ae/en/about-us/business-and-vendors/vendor-registration",
    ]

    for url in urls_to_try:
        resp = _safe_get(session, url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for vendor/contractor lists in tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    specialization = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    contact = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    ref = f"dewa-{name}"

                    sector_text = f"{name} {specialization} energy water electricity"
                    sector = classify_sector(sector_text)

                    companies.append({
                        "id": generate_company_id("dewa_vendor", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "dewa_vendor",
                        "source_ref": ref,
                        "source_url": url,
                        "country": "UAE",
                        "country_code": "AE",
                        "city": "Dubai",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": contact if re.search(r'\d{7,}', contact) else "",
                        "sector": sector,
                        "sectors": [sector, "energy", "water"],
                        "subsectors": [specialization] if specialization else [],
                        "company_type": _extract_company_type(specialization),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "AED",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [specialization] if specialization else [],
                        "prequalified_with": ["dewa"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["AE"],
                        "description": f"DEWA approved vendor/contractor. Specialization: {specialization}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["dewa", "government_registered", "dubai"],
                        "metadata": {
                            "specialization": specialization,
                            "portal": "dewa",
                        },
                        "verified": True,
                        "active": True,
                    })

            # Also look for lists in divs/ul elements
            vendor_sections = soup.find_all(
                ["div", "section"],
                class_=re.compile(r"vendor|contractor|supplier|partner", re.I),
            )
            for section in vendor_sections:
                items = section.find_all("li")
                for li in items:
                    name = li.get_text(strip=True)
                    if not name or len(name) < 3 or len(name) > 200:
                        continue
                    ref = f"dewa-list-{name}"
                    sector = classify_sector(f"{name} energy water electricity")
                    companies.append({
                        "id": generate_company_id("dewa_vendor", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "dewa_vendor",
                        "source_ref": ref,
                        "source_url": url,
                        "country": "UAE",
                        "country_code": "AE",
                        "city": "Dubai",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector, "energy"],
                        "subsectors": [],
                        "company_type": "supplier",
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "AED",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [],
                        "prequalified_with": ["dewa"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["AE"],
                        "description": f"DEWA approved vendor.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["dewa", "government_registered", "dubai"],
                        "metadata": {"portal": "dewa"},
                        "verified": True,
                        "active": True,
                    })

            if companies:
                logger.info(f"  DEWA: parsed {len(companies)} vendors from {url}")
                break

        except Exception as e:
            logger.debug(f"  DEWA parse error for {url}: {e}")
            continue

        time.sleep(REQUEST_DELAY)

    if not companies:
        logger.warning(
            "DEWA: no vendor data accessible publicly. "
            "Vendor registration may require a DEWA account."
        )

    return companies


# ---------------------------------------------------------------------------
# Portal 3: Ashghal (Qatar Public Works Authority)
# ---------------------------------------------------------------------------

def _scrape_ashghal_contractors(session: requests.Session) -> list[dict]:
    """Scrape registered contractor lists from Ashghal's public pages."""
    logger.info("Scraping Ashghal (Qatar) contractor registry...")
    companies = []

    urls_to_try = [
        "https://www.ashghal.gov.qa/en/ContractorClassification",
        "https://www.ashghal.gov.qa/en/Pages/ContractorClassification.aspx",
        "https://www.ashghal.gov.qa/en/about-us/contractor-registration",
        "https://www.ashghal.gov.qa/en/business/contractors",
        "https://www.ashghal.gov.qa/en/registered-contractors",
    ]

    for url in urls_to_try:
        resp = _safe_get(session, url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for contractor classification tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    classification = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    grade = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    ref = f"ashghal-{name}"

                    sector_text = f"{name} {classification} construction infrastructure roads"
                    sector = classify_sector(sector_text)

                    companies.append({
                        "id": generate_company_id("ashghal_vendor", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "ashghal_vendor",
                        "source_ref": ref,
                        "source_url": url,
                        "country": "Qatar",
                        "country_code": "QA",
                        "city": "Doha",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector, "construction", "infrastructure"],
                        "subsectors": [classification] if classification else [],
                        "company_type": _extract_company_type(classification),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "QAR",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [f"Grade {grade}"] if grade else [],
                        "prequalified_with": ["ashghal"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["QA"],
                        "description": f"Ashghal registered contractor. Classification: {classification}. Grade: {grade}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["ashghal", "government_registered", "qatar"],
                        "metadata": {
                            "classification": classification,
                            "grade": grade,
                            "portal": "ashghal",
                        },
                        "verified": True,
                        "active": True,
                    })

            # Check for downloadable PDFs containing contractor lists
            pdf_links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
            for link in pdf_links:
                link_text = link.get_text(strip=True).lower()
                if any(kw in link_text for kw in ["contractor", "classification", "registered", "approved"]):
                    logger.info(f"  Ashghal: found contractor PDF link: {link.get('href')} — requires manual download")

            if companies:
                logger.info(f"  Ashghal: parsed {len(companies)} contractors from {url}")
                break

        except Exception as e:
            logger.debug(f"  Ashghal parse error for {url}: {e}")
            continue

        time.sleep(REQUEST_DELAY)

    if not companies:
        logger.warning(
            "Ashghal: no contractor data accessible publicly. "
            "Contractor classification lists may be in PDF format or require login."
        )

    return companies


# ---------------------------------------------------------------------------
# Portal 4: Abu Dhabi Department of Transport / Municipalities
# ---------------------------------------------------------------------------

def _scrape_abudhabi_contractors(session: requests.Session) -> list[dict]:
    """Scrape public contractor lists from Abu Dhabi government portals."""
    logger.info("Scraping Abu Dhabi government contractor registries...")
    companies = []

    urls_to_try = [
        "https://www.dot.abudhabi.ae/en/Contractors",
        "https://www.dot.abudhabi.ae/en/contractors-classification",
        "https://www.tamm.abudhabi/en/aspects-of-life/constructionandinfrastructure",
        "https://dmt.gov.ae/en/contractors",
        "https://www.abudhabi.ae/portal/public/en/business/construction-infrastructure",
    ]

    for url in urls_to_try:
        resp = _safe_get(session, url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for contractor lists in tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    classification = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    ref = f"abudhabi-{name}"

                    sector_text = f"{name} {classification} construction infrastructure"
                    sector = classify_sector(sector_text)

                    companies.append({
                        "id": generate_company_id("abudhabi_vendor", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "abudhabi_vendor",
                        "source_ref": ref,
                        "source_url": url,
                        "country": "UAE",
                        "country_code": "AE",
                        "city": "Abu Dhabi",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector, "construction"],
                        "subsectors": [classification] if classification else [],
                        "company_type": _extract_company_type(classification),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "AED",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [classification] if classification else [],
                        "prequalified_with": ["abu_dhabi_dot"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["AE"],
                        "description": f"Abu Dhabi government registered contractor. Classification: {classification}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["abudhabi", "government_registered", "uae"],
                        "metadata": {
                            "classification": classification,
                            "portal": "abu_dhabi",
                        },
                        "verified": True,
                        "active": True,
                    })

            # Also look for card/list layouts
            card_sections = soup.find_all(
                ["div", "li", "article"],
                class_=re.compile(r"contractor|vendor|company|partner|card", re.I),
            )
            for card in card_sections:
                name_el = card.find(["h2", "h3", "h4", "strong", "a"])
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if not name or len(name) < 3 or len(name) > 200:
                    continue

                desc_el = card.find("p")
                desc_text = desc_el.get_text(strip=True) if desc_el else ""
                ref = f"abudhabi-card-{name}"

                sector = classify_sector(f"{name} {desc_text} construction")

                companies.append({
                    "id": generate_company_id("abudhabi_vendor", ref),
                    "name": name,
                    "name_ar": "",
                    "name_fr": "",
                    "legal_name": name,
                    "source": "abudhabi_vendor",
                    "source_ref": ref,
                    "source_url": url,
                    "country": "UAE",
                    "country_code": "AE",
                    "city": "Abu Dhabi",
                    "address": "",
                    "website": "",
                    "email": "",
                    "phone": "",
                    "sector": sector,
                    "sectors": [sector],
                    "subsectors": [],
                    "company_type": "contractor",
                    "company_size": classify_company_size(),
                    "employee_count": None,
                    "annual_revenue": None,
                    "revenue_currency": "AED",
                    "founded_year": None,
                    "registration_number": "",
                    "certifications": [],
                    "classifications": [],
                    "prequalified_with": ["abu_dhabi_dot"],
                    "notable_projects": [],
                    "jv_experience": False,
                    "international_presence": ["AE"],
                    "description": desc_text or f"Abu Dhabi government registered company.",
                    "description_ar": "",
                    "description_fr": "",
                    "tags": ["abudhabi", "government_registered", "uae"],
                    "metadata": {"portal": "abu_dhabi"},
                    "verified": True,
                    "active": True,
                })

            if companies:
                logger.info(f"  Abu Dhabi: parsed {len(companies)} contractors from {url}")
                break

        except Exception as e:
            logger.debug(f"  Abu Dhabi parse error for {url}: {e}")
            continue

        time.sleep(REQUEST_DELAY)

    if not companies:
        logger.warning(
            "Abu Dhabi: no contractor data accessible publicly. "
            "Portal may require login or data is in downloadable documents."
        )

    return companies


# ---------------------------------------------------------------------------
# Portal 5: Kuwait Central Agency for Public Tenders (CAPT)
# ---------------------------------------------------------------------------

def _scrape_kuwait_vendors(session: requests.Session) -> list[dict]:
    """Scrape registered contractor/vendor lists from Kuwait CAPT."""
    logger.info("Scraping Kuwait CAPT vendor registry...")
    companies = []

    urls_to_try = [
        "https://www.capt.gov.kw/en/registered-companies",
        "https://www.capt.gov.kw/en/contractors",
        "https://www.capt.gov.kw/en/vendors",
    ]

    for url in urls_to_try:
        resp = _safe_get(session, url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    category = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    ref = f"kuwait-capt-{name}"
                    sector = classify_sector(f"{name} {category}")

                    companies.append({
                        "id": generate_company_id("kuwait_vendor", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "kuwait_vendor",
                        "source_ref": ref,
                        "source_url": url,
                        "country": "Kuwait",
                        "country_code": "KW",
                        "city": "Kuwait City",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector],
                        "subsectors": [category] if category else [],
                        "company_type": _extract_company_type(category),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "KWD",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [category] if category else [],
                        "prequalified_with": ["kuwait_capt"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["KW"],
                        "description": f"Kuwait CAPT registered vendor. Category: {category}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["kuwait", "government_registered"],
                        "metadata": {"category": category, "portal": "kuwait_capt"},
                        "verified": True,
                        "active": True,
                    })

            if companies:
                logger.info(f"  Kuwait CAPT: parsed {len(companies)} vendors from {url}")
                break

        except Exception as e:
            logger.debug(f"  Kuwait CAPT parse error for {url}: {e}")
            continue

        time.sleep(REQUEST_DELAY)

    if not companies:
        logger.warning(
            "Kuwait CAPT: no vendor data accessible publicly. "
            "Portal may require authentication."
        )

    return companies


# ---------------------------------------------------------------------------
# Portal 6: Oman Tender Board
# ---------------------------------------------------------------------------

def _scrape_oman_vendors(session: requests.Session) -> list[dict]:
    """Scrape registered company lists from Oman Tender Board."""
    logger.info("Scraping Oman Tender Board vendor registry...")
    companies = []

    urls_to_try = [
        "https://www.tenderboard.gov.om/Registered-Companies",
        "https://www.tenderboard.gov.om/en/registered-companies",
        "https://etendering.tenderboard.gov.om/product/registered",
    ]

    for url in urls_to_try:
        resp = _safe_get(session, url)
        if not resp:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    name = cells[0].get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    category = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    ref = f"oman-tb-{name}"
                    sector = classify_sector(f"{name} {category}")

                    companies.append({
                        "id": generate_company_id("oman_vendor", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "oman_vendor",
                        "source_ref": ref,
                        "source_url": url,
                        "country": "Oman",
                        "country_code": "OM",
                        "city": "Muscat",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector],
                        "subsectors": [category] if category else [],
                        "company_type": _extract_company_type(category),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "OMR",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [category] if category else [],
                        "prequalified_with": ["oman_tender_board"],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": ["OM"],
                        "description": f"Oman Tender Board registered company. Category: {category}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["oman", "government_registered"],
                        "metadata": {"category": category, "portal": "oman_tender_board"},
                        "verified": True,
                        "active": True,
                    })

            if companies:
                logger.info(f"  Oman TB: parsed {len(companies)} vendors from {url}")
                break

        except Exception as e:
            logger.debug(f"  Oman TB parse error for {url}: {e}")
            continue

        time.sleep(REQUEST_DELAY)

    if not companies:
        logger.warning(
            "Oman Tender Board: no vendor data accessible publicly. "
            "Portal may require registration."
        )

    return companies


# ---------------------------------------------------------------------------
# Main scrape() orchestrator
# ---------------------------------------------------------------------------

def scrape() -> list[dict]:
    """Scrape company/vendor data from government procurement portals.

    Tries multiple MENA government vendor registries. Logs warnings for
    portals that require authentication and continues with accessible data.
    """
    session = _create_session()
    all_companies: list[dict] = []
    seen_ids: set[str] = set()

    # Run each portal scraper
    portal_scrapers = [
        ("Etimad (SA)", _scrape_etimad_contractors),
        ("DEWA (AE)", _scrape_dewa_vendors),
        ("Ashghal (QA)", _scrape_ashghal_contractors),
        ("Abu Dhabi (AE)", _scrape_abudhabi_contractors),
        ("Kuwait CAPT (KW)", _scrape_kuwait_vendors),
        ("Oman TB (OM)", _scrape_oman_vendors),
    ]

    for portal_name, scraper_fn in portal_scrapers:
        try:
            companies = scraper_fn(session)
            new_count = 0
            for company in companies:
                cid = company["id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    all_companies.append(company)
                    new_count += 1
            logger.info(f"{portal_name}: {new_count} unique companies added")
        except Exception as e:
            logger.error(f"{portal_name}: scraper failed — {e}")
            continue

        time.sleep(REQUEST_DELAY)

    logger.info(f"Vendor registries total: {len(all_companies)} unique companies from {len(portal_scrapers)} portals")
    return all_companies


if __name__ == "__main__":
    results = scrape()
    save_companies(results, "vendors")
    print(f"Scraped {len(results)} companies from government vendor registries")
