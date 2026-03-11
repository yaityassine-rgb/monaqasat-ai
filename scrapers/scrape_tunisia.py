"""
Scraper for Tunisia TUNEPS (Tunisian National E-Procurement System).
Source: https://www.tuneps.tn/

Tunisia's mandatory e-procurement portal for all public procurement.
All government entities are required to publish tenders here.
Content is primarily in Arabic and French.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders
from config import HEADERS

logger = logging.getLogger("tunisia")

BASE_URL = "https://www.tuneps.tn"
SEARCH_URL = f"{BASE_URL}/publish/searchAo"
CONSULTATION_URL = f"{BASE_URL}/publish/consultationList"
MAX_PAGES = 15


def _create_session() -> requests.Session:
    """Create a session with proper headers for TUNEPS."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,ar;q=0.9,en;q=0.8",
        "Referer": BASE_URL,
    })
    return s


def _scrape_search_page(session: requests.Session, page: int) -> list[dict]:
    """Scrape a single page of TUNEPS tender listings."""
    tenders = []

    try:
        # TUNEPS uses a search form with pagination
        params = {
            "page": page,
            "size": 20,
        }
        resp = session.get(SEARCH_URL, params=params, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"TUNEPS search page {page}: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors for tender listings
        selectors = [
            "table.table tbody tr",
            "table tbody tr",
            ".dataTables_wrapper tbody tr",
            ".tender-row",
            ".ao-item",
            ".consultation-item",
            ".list-group-item",
            "div.card",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"TUNEPS page {page}: found {len(rows)} rows with '{selector}'")
                for row in rows:
                    tender = _parse_tender_row(row)
                    if tender:
                        tenders.append(tender)
                break

    except Exception as e:
        logger.error(f"TUNEPS search page {page}: {e}")

    return tenders


def _parse_tender_row(row) -> dict | None:
    """Parse a single tender row from the TUNEPS listing."""
    cells = row.find_all("td")
    if cells and len(cells) >= 2:
        texts = [c.get_text(strip=True) for c in cells]
    else:
        # Card-based layout
        texts = [row.get_text(strip=True)]

    if not texts or all(len(t) < 3 for t in texts):
        return None

    # Extract title (longest text field)
    title = ""
    ref = ""
    org = ""
    pub_date = ""
    deadline = ""

    for text in texts:
        if not text:
            continue
        d = parse_date(text)
        if d:
            if not pub_date:
                pub_date = d
            else:
                deadline = d
        elif len(text) < 30 and re.search(r'\d{2,}', text) and not ref:
            ref = text
        elif len(text) > 10 and not title:
            title = text
        elif len(text) > 10 and title and not org:
            org = text

    if not title or len(title) < 5:
        return None

    # Get detail link
    source_url = SEARCH_URL
    link = row.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and not href.startswith("javascript") and href != "#":
            source_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        if not title or len(title) < 5:
            title = link.get_text(strip=True)

    return {
        "id": generate_id("tuneps", ref or title[:80], ""),
        "source": "TUNEPS",
        "sourceRef": ref,
        "sourceLanguage": "fr",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Tunisia",
            "ar": org or "الجمهورية التونسية",
            "fr": org or "République Tunisienne",
        },
        "country": "Tunisia",
        "countryCode": "TN",
        "sector": classify_sector(title),
        "budget": 0,
        "currency": "TND",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": title, "ar": title, "fr": title},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_consultation_list(session: requests.Session) -> list[dict]:
    """Try the consultation list endpoint as alternative."""
    tenders = []

    try:
        resp = session.get(CONSULTATION_URL, timeout=30)
        if resp.status_code != 200:
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for consultation items
        for selector in [
            "table tbody tr",
            ".consultation-row",
            ".list-group-item",
            "div.card",
        ]:
            items = soup.select(selector)
            if items:
                logger.info(f"TUNEPS consultation list: {len(items)} items with '{selector}'")
                for item in items:
                    tender = _parse_tender_row(item)
                    if tender:
                        tenders.append(tender)
                break

    except Exception as e:
        logger.error(f"TUNEPS consultation list: {e}")

    return tenders


def _scrape_main_page(session: requests.Session) -> list[dict]:
    """Try scraping the main page for recent tenders."""
    tenders = []

    try:
        resp = session.get(BASE_URL, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"TUNEPS main page: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender listings on the home page
        for selector in [
            "table tbody tr",
            ".tender-list .item",
            ".ao-list .item",
            ".recent-tenders .item",
            ".list-group-item",
        ]:
            items = soup.select(selector)
            if items:
                logger.info(f"TUNEPS main page: {len(items)} items with '{selector}'")
                for item in items:
                    tender = _parse_tender_row(item)
                    if tender:
                        tenders.append(tender)
                break

    except Exception as e:
        logger.error(f"TUNEPS main page: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Tunisia TUNEPS for public procurement notices."""
    all_tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # Try the main page first
    main_tenders = _scrape_main_page(session)
    for t in main_tenders:
        key = t.get("sourceRef", "") or t["title"]["fr"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    time.sleep(2)

    # Try paginated search
    for page in range(1, MAX_PAGES + 1):
        page_tenders = _scrape_search_page(session, page)

        page_count = 0
        for t in page_tenders:
            key = t.get("sourceRef", "") or t["title"]["fr"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)
                page_count += 1

        logger.info(f"TUNEPS page {page}: {page_count} new tenders (total: {len(all_tenders)})")

        if page_count == 0:
            break

        time.sleep(2)

    # Try consultation list as alternative
    consultation_tenders = _scrape_consultation_list(session)
    for t in consultation_tenders:
        key = t.get("sourceRef", "") or t["title"]["fr"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    if not all_tenders:
        logger.warning(
            "TUNEPS: no tenders scraped. The portal may require authentication "
            "or use dynamic JavaScript rendering. Consider using Selenium or "
            "checking if the site structure has changed."
        )

    logger.info(f"Tunisia TUNEPS total: {len(all_tenders)} tenders")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "tunisia_tuneps")
    print(f"Scraped {len(results)} tenders from Tunisia TUNEPS")
