"""
Scraper for business directories and industry listings across MENA.

Sources:
- Zawya company profiles (major MENA business directory)
- Regional Yellow Pages / business directories
- Construction industry "Top Contractors" rankings
- Chamber of Commerce listings (Saudi Chambers, Dubai Chamber, etc.)

Extracts: company name, sector, country, description, contact info.
"""

import re
import time
import logging
import requests
from typing import Optional
from bs4 import BeautifulSoup

from config import MENA_COUNTRIES, HEADERS
from base_scraper import (
    generate_company_id,
    classify_sector,
    classify_company_size,
    save_companies,
)

logger = logging.getLogger("directories")

# Rate limiting
REQUEST_DELAY = 4.0
MAX_RETRIES = 2
MAX_PAGES_PER_SOURCE = 20


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


def _safe_get(
    session: requests.Session,
    url: str,
    timeout: int = 30,
    **kwargs,
) -> Optional[requests.Response]:
    """GET with retries and graceful error handling."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=timeout, **kwargs)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (403, 401):
                logger.warning(f"Access denied ({resp.status_code}) for {url}")
                return None
            if resp.status_code == 429:
                logger.warning(f"Rate limited (429) for {url}")
                time.sleep(30)
                continue
            logger.warning(f"HTTP {resp.status_code} for {url}")
            if attempt < MAX_RETRIES:
                time.sleep(5)
            continue
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
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
            logger.error(f"Error fetching {url}: {e}")
            return None
    return None


def _extract_company_type(text: str) -> str:
    """Infer company type from descriptive text."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["consult", "advisory", "design", "architect", "supervision"]):
        return "consultant"
    if any(kw in text_lower for kw in ["supply", "supplier", "vendor", "trading", "distributor"]):
        return "supplier"
    if any(kw in text_lower for kw in ["manufactur", "factory", "fabricat", "production"]):
        return "manufacturer"
    if any(kw in text_lower for kw in ["develop", "real estate", "property", "investment"]):
        return "developer"
    return "contractor"


def _extract_email(text: str) -> str:
    """Extract an email address from text."""
    match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    return match.group(0) if match else ""


def _extract_phone(text: str) -> str:
    """Extract a phone number from text."""
    match = re.search(r'[\+]?[\d\s\-().]{7,20}', text)
    return match.group(0).strip() if match else ""


def _extract_website(text: str) -> str:
    """Extract a website URL from text."""
    match = re.search(r'https?://[\w./\-]+', text)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# Source 1: Zawya (Refinitiv) — MENA Business Directory
# ---------------------------------------------------------------------------

def _scrape_zawya(session: requests.Session) -> list[dict]:
    """Scrape company profiles from Zawya's public company directory.

    Zawya (by Refinitiv/LSEG) is the leading MENA business intelligence platform.
    Their public company pages list key details for thousands of MENA firms.
    """
    logger.info("Scraping Zawya company directory...")
    companies = []

    # Zawya has sector-based and country-based company listings
    # Try both the company search and sector/country listing pages
    search_urls = [
        # Sector-based listings
        "https://www.zawya.com/en/company/construction",
        "https://www.zawya.com/en/company/engineering",
        "https://www.zawya.com/en/company/real-estate",
        "https://www.zawya.com/en/company/energy",
        "https://www.zawya.com/en/company/infrastructure",
        "https://www.zawya.com/en/company/industrial",
        # Country-based
        "https://www.zawya.com/en/company/saudi-arabia",
        "https://www.zawya.com/en/company/uae",
        "https://www.zawya.com/en/company/egypt",
        "https://www.zawya.com/en/company/qatar",
        "https://www.zawya.com/en/company/kuwait",
        "https://www.zawya.com/en/company/morocco",
        "https://www.zawya.com/en/company/oman",
        "https://www.zawya.com/en/company/bahrain",
        "https://www.zawya.com/en/company/jordan",
    ]

    for url in search_urls:
        resp = _safe_get(session, url)
        if not resp:
            time.sleep(REQUEST_DELAY)
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Zawya company listings are typically in card/list format
            # Look for company name links and associated metadata
            company_elements = soup.find_all(
                ["div", "article", "li"],
                class_=re.compile(r"company|listing|result|card|profile", re.I),
            )

            for el in company_elements:
                # Extract company name
                name_el = el.find(["h2", "h3", "h4", "a", "strong"])
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if not name or len(name) < 3 or len(name) > 300:
                    continue

                # Extract link for detail page
                link = name_el.get("href", "") if name_el.name == "a" else ""
                if not link:
                    link_el = el.find("a")
                    link = link_el.get("href", "") if link_el else ""

                full_url = link if link.startswith("http") else f"https://www.zawya.com{link}" if link else url

                # Extract description/sector text
                desc_el = el.find("p") or el.find("span", class_=re.compile(r"desc|sector|industry|category", re.I))
                desc_text = desc_el.get_text(strip=True) if desc_el else ""

                # Extract country
                country_el = el.find(
                    ["span", "div"],
                    class_=re.compile(r"country|location|region", re.I),
                )
                country_text = country_el.get_text(strip=True) if country_el else ""
                country_code = ""
                country_name = ""
                for code, cname in MENA_COUNTRIES.items():
                    if cname.lower() in country_text.lower() or cname.lower() in url.lower():
                        country_code = code
                        country_name = cname
                        break

                # Extract contact
                full_text = el.get_text(" ", strip=True)
                email = _extract_email(full_text)
                phone = _extract_phone(full_text)
                website = _extract_website(full_text)

                sector_text = f"{name} {desc_text}"
                sector = classify_sector(sector_text)

                ref = f"zawya-{name}-{country_code}"

                companies.append({
                    "id": generate_company_id("zawya", ref),
                    "name": name,
                    "name_ar": "",
                    "name_fr": "",
                    "legal_name": name,
                    "source": "zawya",
                    "source_ref": ref,
                    "source_url": full_url,
                    "country": country_name,
                    "country_code": country_code,
                    "city": "",
                    "address": "",
                    "website": website,
                    "email": email,
                    "phone": phone,
                    "sector": sector,
                    "sectors": [sector],
                    "subsectors": [],
                    "company_type": _extract_company_type(f"{name} {desc_text}"),
                    "company_size": classify_company_size(),
                    "employee_count": None,
                    "annual_revenue": None,
                    "revenue_currency": "USD",
                    "founded_year": None,
                    "registration_number": "",
                    "certifications": [],
                    "classifications": [],
                    "prequalified_with": [],
                    "notable_projects": [],
                    "jv_experience": False,
                    "international_presence": [country_code] if country_code else [],
                    "description": desc_text or f"Company listed on Zawya business directory.",
                    "description_ar": "",
                    "description_fr": "",
                    "tags": ["zawya", "business_directory"],
                    "metadata": {"portal": "zawya"},
                    "verified": False,
                    "active": True,
                })

            # Also look for standard table format
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
                    sector_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    country_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                    country_code = ""
                    country_name = ""
                    for code, cname in MENA_COUNTRIES.items():
                        if cname.lower() in country_text.lower():
                            country_code = code
                            country_name = cname
                            break

                    sector = classify_sector(f"{name} {sector_text}")
                    ref = f"zawya-table-{name}"

                    companies.append({
                        "id": generate_company_id("zawya", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "zawya",
                        "source_ref": ref,
                        "source_url": url,
                        "country": country_name,
                        "country_code": country_code,
                        "city": "",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector],
                        "subsectors": [],
                        "company_type": _extract_company_type(sector_text),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "USD",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [],
                        "prequalified_with": [],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": [country_code] if country_code else [],
                        "description": sector_text,
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["zawya", "business_directory"],
                        "metadata": {"portal": "zawya"},
                        "verified": False,
                        "active": True,
                    })

        except Exception as e:
            logger.debug(f"Zawya parse error for {url}: {e}")

        time.sleep(REQUEST_DELAY)

    if companies:
        logger.info(f"Zawya: parsed {len(companies)} companies")
    else:
        logger.warning(
            "Zawya: no company data extracted. "
            "Site may use JS rendering or require login for company profiles."
        )

    return companies


# ---------------------------------------------------------------------------
# Source 2: Chamber of Commerce Listings
# ---------------------------------------------------------------------------

def _scrape_chambers(session: requests.Session) -> list[dict]:
    """Scrape company listings from MENA Chambers of Commerce websites."""
    logger.info("Scraping Chamber of Commerce directories...")
    companies = []

    chambers = [
        {
            "name": "Saudi Chambers",
            "urls": [
                "https://www.saudichambers.sa/en/MemberList",
                "https://www.saudichambers.sa/en/members",
                "https://csc.org.sa/en/members",
                "https://chamber.sa/en/directory",
            ],
            "country": "Saudi Arabia",
            "country_code": "SA",
        },
        {
            "name": "Dubai Chamber",
            "urls": [
                "https://www.dubaichamber.com/en/members-directory",
                "https://www.dubaichamber.com/en/members",
                "https://www.dubaichamber.com/en/directory",
            ],
            "country": "UAE",
            "country_code": "AE",
            "city": "Dubai",
        },
        {
            "name": "Abu Dhabi Chamber",
            "urls": [
                "https://www.abudhabichamber.ae/en/members",
                "https://www.abudhabichamber.ae/en/directory",
                "https://www.abudhabichamber.ae/English/MembersDirectory",
            ],
            "country": "UAE",
            "country_code": "AE",
            "city": "Abu Dhabi",
        },
        {
            "name": "Qatar Chamber",
            "urls": [
                "https://www.qatarchamber.com/en/members-directory",
                "https://www.qatarchamber.com/en/members",
                "https://qcci.org.qa/en/members",
            ],
            "country": "Qatar",
            "country_code": "QA",
            "city": "Doha",
        },
        {
            "name": "Kuwait Chamber",
            "urls": [
                "https://www.kuwaitchamber.org.kw/en/members",
                "https://www.kcci.org.kw/en/members-directory",
            ],
            "country": "Kuwait",
            "country_code": "KW",
            "city": "Kuwait City",
        },
        {
            "name": "Bahrain Chamber",
            "urls": [
                "https://www.bcci.bh/en/members-directory",
                "https://www.bcci.bh/en/members",
            ],
            "country": "Bahrain",
            "country_code": "BH",
            "city": "Manama",
        },
        {
            "name": "Egypt Federation of Industries",
            "urls": [
                "https://www.fei.org.eg/en/members",
                "https://www.fei.org.eg/index.php/en/members-directory",
            ],
            "country": "Egypt",
            "country_code": "EG",
            "city": "Cairo",
        },
        {
            "name": "Morocco CGEM",
            "urls": [
                "https://www.cgem.ma/en/members",
                "https://www.cgem.ma/en/annuaire",
            ],
            "country": "Morocco",
            "country_code": "MA",
            "city": "Casablanca",
        },
        {
            "name": "Jordan Chamber",
            "urls": [
                "https://www.jocc.org.jo/en/members",
                "https://www.acci.org.jo/en/members-directory",
            ],
            "country": "Jordan",
            "country_code": "JO",
            "city": "Amman",
        },
    ]

    for chamber in chambers:
        chamber_name = chamber["name"]
        country = chamber["country"]
        country_code = chamber["country_code"]
        city = chamber.get("city", "")
        found = False

        for url in chamber["urls"]:
            resp = _safe_get(session, url)
            if not resp:
                time.sleep(REQUEST_DELAY)
                continue

            try:
                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for member/company listings
                # Try tables first
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 1:
                            continue
                        name = cells[0].get_text(strip=True)
                        if not name or len(name) < 3:
                            continue

                        sector_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        contact_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        sector = classify_sector(f"{name} {sector_text}")
                        ref = f"chamber-{country_code}-{name}"

                        companies.append({
                            "id": generate_company_id("chamber", ref),
                            "name": name,
                            "name_ar": "",
                            "name_fr": "",
                            "legal_name": name,
                            "source": "chamber",
                            "source_ref": ref,
                            "source_url": url,
                            "country": country,
                            "country_code": country_code,
                            "city": city,
                            "address": "",
                            "website": _extract_website(contact_text),
                            "email": _extract_email(contact_text),
                            "phone": _extract_phone(contact_text),
                            "sector": sector,
                            "sectors": [sector],
                            "subsectors": [],
                            "company_type": _extract_company_type(f"{name} {sector_text}"),
                            "company_size": classify_company_size(),
                            "employee_count": None,
                            "annual_revenue": None,
                            "revenue_currency": "USD",
                            "founded_year": None,
                            "registration_number": "",
                            "certifications": [],
                            "classifications": [],
                            "prequalified_with": [],
                            "notable_projects": [],
                            "jv_experience": False,
                            "international_presence": [country_code],
                            "description": f"{chamber_name} member. Sector: {sector_text}.",
                            "description_ar": "",
                            "description_fr": "",
                            "tags": ["chamber_of_commerce", country_code.lower()],
                            "metadata": {"chamber": chamber_name, "portal": "chamber"},
                            "verified": False,
                            "active": True,
                        })
                        found = True

                # Try card/list layouts
                member_elements = soup.find_all(
                    ["div", "li", "article"],
                    class_=re.compile(r"member|company|listing|result|card|directory", re.I),
                )
                for el in member_elements:
                    name_el = el.find(["h2", "h3", "h4", "strong", "a"])
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3 or len(name) > 300:
                        continue

                    full_text = el.get_text(" ", strip=True)
                    desc_el = el.find("p")
                    desc_text = desc_el.get_text(strip=True) if desc_el else ""

                    sector = classify_sector(f"{name} {desc_text}")
                    ref = f"chamber-{country_code}-card-{name}"

                    link = name_el.get("href", "") if name_el.name == "a" else ""

                    companies.append({
                        "id": generate_company_id("chamber", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "chamber",
                        "source_ref": ref,
                        "source_url": link if link.startswith("http") else url,
                        "country": country,
                        "country_code": country_code,
                        "city": city,
                        "address": "",
                        "website": _extract_website(full_text),
                        "email": _extract_email(full_text),
                        "phone": _extract_phone(full_text),
                        "sector": sector,
                        "sectors": [sector],
                        "subsectors": [],
                        "company_type": _extract_company_type(f"{name} {desc_text}"),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "USD",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [],
                        "prequalified_with": [],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": [country_code],
                        "description": desc_text or f"{chamber_name} member.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["chamber_of_commerce", country_code.lower()],
                        "metadata": {"chamber": chamber_name, "portal": "chamber"},
                        "verified": False,
                        "active": True,
                    })
                    found = True

                if found:
                    logger.info(f"  {chamber_name}: found company data at {url}")
                    break

            except Exception as e:
                logger.debug(f"  {chamber_name} parse error for {url}: {e}")

            time.sleep(REQUEST_DELAY)

        if not found:
            logger.warning(f"  {chamber_name}: no member data accessible publicly")

    logger.info(f"Chambers: {len(companies)} companies total")
    return companies


# ---------------------------------------------------------------------------
# Source 3: Construction Industry Rankings / Top Contractor Lists
# ---------------------------------------------------------------------------

def _scrape_top_contractors(session: requests.Session) -> list[dict]:
    """Scrape publicly available top contractor/ENR-style rankings for MENA."""
    logger.info("Scraping construction industry top contractor rankings...")
    companies = []

    ranking_urls = [
        # MEED / ENR style rankings (public pages)
        "https://www.meed.com/top-contractors-gcc",
        "https://www.meed.com/top-contractors-middle-east",
        "https://www.constructionweekonline.com/power-100",
        "https://www.constructionweekonline.com/top-contractors",
        # BNC Network (construction intelligence)
        "https://www.bncnetwork.com/top-contractors",
        # Gulf Business / Arabian Business rankings
        "https://gulfbusiness.com/top-construction-companies",
        "https://www.arabianbusiness.com/lists/construction",
    ]

    for url in ranking_urls:
        resp = _safe_get(session, url)
        if not resp:
            time.sleep(REQUEST_DELAY)
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Rankings are often in tables or ordered lists
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue

                    # First cell often rank number, second is name
                    rank_or_name = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True) if len(cells) > 1 else rank_or_name

                    # If first cell is just a number (rank), use second cell as name
                    if rank_or_name.isdigit():
                        name = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    else:
                        name = rank_or_name

                    if not name or len(name) < 3:
                        continue

                    country_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    revenue_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""

                    country_code = ""
                    country_name = ""
                    for code, cname in MENA_COUNTRIES.items():
                        if cname.lower() in country_text.lower():
                            country_code = code
                            country_name = cname
                            break

                    sector = classify_sector(f"{name} construction contracting")
                    ref = f"ranking-{name}"

                    companies.append({
                        "id": generate_company_id("ranking", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "industry_ranking",
                        "source_ref": ref,
                        "source_url": url,
                        "country": country_name,
                        "country_code": country_code,
                        "city": "",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector, "construction"],
                        "subsectors": [],
                        "company_type": "contractor",
                        "company_size": "large",
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "USD",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [],
                        "prequalified_with": [],
                        "notable_projects": [],
                        "jv_experience": True,
                        "international_presence": [country_code] if country_code else [],
                        "description": f"Ranked contractor from {url.split('/')[2]}. Revenue: {revenue_text}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["top_contractor", "industry_ranking"],
                        "metadata": {
                            "revenue_text": revenue_text,
                            "ranking_source": url,
                        },
                        "verified": False,
                        "active": True,
                    })

            # Also try ranked list (ol/li) format
            ranked_lists = soup.find_all("ol")
            for ol in ranked_lists:
                items = ol.find_all("li")
                for i, li in enumerate(items, 1):
                    name_el = li.find(["a", "strong", "h3", "h4"])
                    name = name_el.get_text(strip=True) if name_el else li.get_text(strip=True)
                    if not name or len(name) < 3 or len(name) > 200:
                        continue

                    full_text = li.get_text(" ", strip=True)
                    country_code = ""
                    country_name = ""
                    for code, cname in MENA_COUNTRIES.items():
                        if cname.lower() in full_text.lower():
                            country_code = code
                            country_name = cname
                            break

                    ref = f"ranking-list-{name}"
                    sector = classify_sector(f"{name} construction")

                    companies.append({
                        "id": generate_company_id("ranking", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "industry_ranking",
                        "source_ref": ref,
                        "source_url": url,
                        "country": country_name,
                        "country_code": country_code,
                        "city": "",
                        "address": "",
                        "website": "",
                        "email": "",
                        "phone": "",
                        "sector": sector,
                        "sectors": [sector, "construction"],
                        "subsectors": [],
                        "company_type": "contractor",
                        "company_size": "large",
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "USD",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [],
                        "prequalified_with": [],
                        "notable_projects": [],
                        "jv_experience": True,
                        "international_presence": [country_code] if country_code else [],
                        "description": f"Ranked #{i} contractor.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["top_contractor", "industry_ranking"],
                        "metadata": {"rank": i, "ranking_source": url},
                        "verified": False,
                        "active": True,
                    })

            # Card-based article layouts (common in modern ranking pages)
            cards = soup.find_all(
                ["div", "article"],
                class_=re.compile(r"card|result|item|listing|rank|entry", re.I),
            )
            for card in cards:
                name_el = card.find(["h2", "h3", "h4", "a"])
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if not name or len(name) < 3 or len(name) > 200:
                    continue

                desc_el = card.find("p")
                desc = desc_el.get_text(strip=True) if desc_el else ""

                country_code = ""
                country_name = ""
                for code, cname in MENA_COUNTRIES.items():
                    if cname.lower() in desc.lower() or cname.lower() in name.lower():
                        country_code = code
                        country_name = cname
                        break

                ref = f"ranking-card-{name}"
                sector = classify_sector(f"{name} {desc} construction")

                companies.append({
                    "id": generate_company_id("ranking", ref),
                    "name": name,
                    "name_ar": "",
                    "name_fr": "",
                    "legal_name": name,
                    "source": "industry_ranking",
                    "source_ref": ref,
                    "source_url": url,
                    "country": country_name,
                    "country_code": country_code,
                    "city": "",
                    "address": "",
                    "website": "",
                    "email": "",
                    "phone": "",
                    "sector": sector,
                    "sectors": [sector, "construction"],
                    "subsectors": [],
                    "company_type": _extract_company_type(f"{name} {desc}"),
                    "company_size": "large",
                    "employee_count": None,
                    "annual_revenue": None,
                    "revenue_currency": "USD",
                    "founded_year": None,
                    "registration_number": "",
                    "certifications": [],
                    "classifications": [],
                    "prequalified_with": [],
                    "notable_projects": [],
                    "jv_experience": True,
                    "international_presence": [country_code] if country_code else [],
                    "description": desc or f"Ranked contractor.",
                    "description_ar": "",
                    "description_fr": "",
                    "tags": ["top_contractor", "industry_ranking"],
                    "metadata": {"ranking_source": url},
                    "verified": False,
                    "active": True,
                })

        except Exception as e:
            logger.debug(f"Ranking parse error for {url}: {e}")

        time.sleep(REQUEST_DELAY)

    if companies:
        logger.info(f"Industry rankings: {len(companies)} companies")
    else:
        logger.warning(
            "Industry rankings: no data extracted. "
            "Ranking sites may use JS rendering or paywalls."
        )

    return companies


# ---------------------------------------------------------------------------
# Source 4: Yellow Pages / Regional Directories
# ---------------------------------------------------------------------------

def _scrape_yellow_pages(session: requests.Session) -> list[dict]:
    """Scrape MENA regional Yellow Pages / business directories."""
    logger.info("Scraping regional Yellow Pages directories...")
    companies = []

    yellow_pages = [
        {
            "name": "Saudi Yellow Pages",
            "urls": [
                "https://www.yellowpages.com.sa/category/construction-companies",
                "https://www.yellowpages.com.sa/category/engineering-companies",
                "https://www.saudiayp.com/category/construction",
            ],
            "country": "Saudi Arabia",
            "country_code": "SA",
        },
        {
            "name": "UAE Yellow Pages",
            "urls": [
                "https://www.yellowpages.ae/category/construction-companies",
                "https://www.yellowpages-uae.com/category/construction",
                "https://www.yellowpages.ae/category/engineering-companies",
            ],
            "country": "UAE",
            "country_code": "AE",
        },
        {
            "name": "Egypt Yellow Pages",
            "urls": [
                "https://www.yellowpages.com.eg/category/construction-companies",
                "https://www.yellowpages.com.eg/category/engineering",
            ],
            "country": "Egypt",
            "country_code": "EG",
        },
        {
            "name": "Qatar Yellow Pages",
            "urls": [
                "https://www.qataryellowpages.com.qa/category/construction",
            ],
            "country": "Qatar",
            "country_code": "QA",
        },
        {
            "name": "Kuwait Yellow Pages",
            "urls": [
                "https://www.yellowpages.com.kw/category/construction",
            ],
            "country": "Kuwait",
            "country_code": "KW",
        },
        {
            "name": "Morocco Pages Jaunes",
            "urls": [
                "https://www.pagesjaunes.ma/recherche/construction",
                "https://www.pagesjaunes.ma/recherche/entreprise-batiment",
            ],
            "country": "Morocco",
            "country_code": "MA",
        },
    ]

    for directory in yellow_pages:
        dir_name = directory["name"]
        country = directory["country"]
        country_code = directory["country_code"]
        found = False

        for url in directory["urls"]:
            resp = _safe_get(session, url)
            if not resp:
                time.sleep(REQUEST_DELAY)
                continue

            try:
                soup = BeautifulSoup(resp.text, "html.parser")

                # Yellow pages typically use card/list format
                listings = soup.find_all(
                    ["div", "li", "article"],
                    class_=re.compile(r"listing|result|company|business|card|item", re.I),
                )

                for el in listings:
                    name_el = el.find(["h2", "h3", "h4", "a", "strong"])
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3 or len(name) > 200:
                        continue

                    full_text = el.get_text(" ", strip=True)
                    desc_el = el.find("p")
                    desc_text = desc_el.get_text(strip=True) if desc_el else ""

                    # Address
                    addr_el = el.find(
                        ["span", "div", "p"],
                        class_=re.compile(r"address|location|addr", re.I),
                    )
                    address = addr_el.get_text(strip=True) if addr_el else ""

                    email = _extract_email(full_text)
                    phone = _extract_phone(full_text)
                    website = _extract_website(full_text)

                    sector = classify_sector(f"{name} {desc_text} construction")
                    ref = f"yp-{country_code}-{name}"

                    companies.append({
                        "id": generate_company_id("yellowpages", ref),
                        "name": name,
                        "name_ar": "",
                        "name_fr": "",
                        "legal_name": name,
                        "source": "yellowpages",
                        "source_ref": ref,
                        "source_url": url,
                        "country": country,
                        "country_code": country_code,
                        "city": "",
                        "address": address,
                        "website": website,
                        "email": email,
                        "phone": phone,
                        "sector": sector,
                        "sectors": [sector],
                        "subsectors": [],
                        "company_type": _extract_company_type(f"{name} {desc_text}"),
                        "company_size": classify_company_size(),
                        "employee_count": None,
                        "annual_revenue": None,
                        "revenue_currency": "USD",
                        "founded_year": None,
                        "registration_number": "",
                        "certifications": [],
                        "classifications": [],
                        "prequalified_with": [],
                        "notable_projects": [],
                        "jv_experience": False,
                        "international_presence": [country_code],
                        "description": desc_text or f"Listed in {dir_name}.",
                        "description_ar": "",
                        "description_fr": "",
                        "tags": ["yellow_pages", "business_directory", country_code.lower()],
                        "metadata": {"directory": dir_name},
                        "verified": False,
                        "active": True,
                    })
                    found = True

                if found:
                    logger.info(f"  {dir_name}: found listings at {url}")
                    break

            except Exception as e:
                logger.debug(f"  {dir_name} parse error for {url}: {e}")

            time.sleep(REQUEST_DELAY)

        if not found:
            logger.warning(f"  {dir_name}: no listings accessible")

    logger.info(f"Yellow Pages: {len(companies)} companies total")
    return companies


# ---------------------------------------------------------------------------
# Main scrape() orchestrator
# ---------------------------------------------------------------------------

def scrape() -> list[dict]:
    """Scrape company data from business directories and industry listings.

    Targets Zawya, Chambers of Commerce, construction industry rankings,
    and regional Yellow Pages directories across MENA.
    """
    session = _create_session()
    all_companies: list[dict] = []
    seen_ids: set[str] = set()

    source_scrapers = [
        ("Zawya", _scrape_zawya),
        ("Chambers of Commerce", _scrape_chambers),
        ("Industry Rankings", _scrape_top_contractors),
        ("Yellow Pages", _scrape_yellow_pages),
    ]

    for source_name, scraper_fn in source_scrapers:
        try:
            companies = scraper_fn(session)
            new_count = 0
            for company in companies:
                cid = company["id"]
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    all_companies.append(company)
                    new_count += 1
            logger.info(f"{source_name}: {new_count} unique companies added (total: {len(all_companies)})")
        except Exception as e:
            logger.error(f"{source_name}: scraper failed — {e}")
            continue

    logger.info(f"Directories total: {len(all_companies)} unique companies")
    return all_companies


if __name__ == "__main__":
    results = scrape()
    save_companies(results, "directories")
    print(f"Scraped {len(results)} companies from business directories")
