"""
Scraper for Algeria BOMOP (Bulletin Officiel des Marchés de l'Opérateur Public).
Source: https://bomop.anep.dz/en/

Algeria's national tender bulletin published by ANEP (Agence Nationale d'Édition
et de Publicité). This is the official gazette for public procurement notices
in Algeria. All government entities must publish here.
Content is in Arabic, French, and English.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders
from config import HEADERS

logger = logging.getLogger("bomop")

BASE_URL = "https://bomop.anep.dz"
ENGLISH_URL = f"{BASE_URL}/en/"
FRENCH_URL = f"{BASE_URL}/fr/"
ARABIC_URL = f"{BASE_URL}/ar/"
SEARCH_URL = f"{BASE_URL}/en/search"
MAX_PAGES = 15


def _create_session() -> requests.Session:
    """Create a session with proper headers for BOMOP."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,fr;q=0.9,ar;q=0.8",
        "Referer": BASE_URL,
    })
    return s


def _parse_tender_item(item, page_url: str) -> dict | None:
    """Parse a single tender item from a BOMOP listing."""
    # Try table row format
    cells = item.find_all("td")
    if cells and len(cells) >= 2:
        texts = [c.get_text(strip=True) for c in cells]
    else:
        # Try card/div-based format
        title_el = item.find(["h3", "h4", "h5", "a", "strong"])
        if not title_el:
            texts = [item.get_text(strip=True)]
        else:
            texts = [title_el.get_text(strip=True)]
            # Get additional details
            desc_el = item.find(["p", ".description", ".details"])
            if desc_el:
                texts.append(desc_el.get_text(strip=True))

    if not texts or all(len(t) < 3 for t in texts):
        return None

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
        elif len(text) < 30 and re.search(r'\d{3,}', text) and not ref:
            ref = text
        elif len(text) > 10 and not title:
            title = text
        elif len(text) > 10 and title and not org:
            org = text

    if not title or len(title) < 5:
        return None

    # Extract reference number from title if present
    ref_match = re.search(r'(?:N[°o]?\s*|Ref\.?\s*|Avis\s+N[°o]?\s*)(\d[\d\-/]+)', title)
    if ref_match and not ref:
        ref = ref_match.group(1)

    # Get detail link
    source_url = page_url
    link = item.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and not href.startswith("javascript") and href != "#":
            source_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    return {
        "id": generate_id("bomop", ref or title[:80], ""),
        "source": "BOMOP Algeria",
        "sourceRef": ref,
        "sourceLanguage": "fr",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Algeria",
            "ar": org or "الجمهورية الجزائرية الديمقراطية الشعبية",
            "fr": org or "République Algérienne Démocratique et Populaire",
        },
        "country": "Algeria",
        "countryCode": "DZ",
        "sector": classify_sector(title),
        "budget": 0,
        "currency": "DZD",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": title, "ar": title, "fr": title},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_listing_page(session: requests.Session, url: str) -> tuple[list[dict], str]:
    """Scrape a single page of BOMOP listings. Returns (tenders, next_page_url)."""
    tenders = []
    next_url = ""

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"BOMOP page returned {resp.status_code}: {url}")
            return tenders, next_url

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors for tender listings
        selectors = [
            "table.table tbody tr",
            "table tbody tr",
            ".tender-item",
            ".avis-item",
            ".marche-item",
            ".list-group-item",
            ".card",
            "article",
            ".search-result",
            ".result-item",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"BOMOP: found {len(rows)} rows with '{selector}' at {url}")
                for row in rows:
                    tender = _parse_tender_item(row, url)
                    if tender:
                        tenders.append(tender)
                break

        # Check for pagination
        next_link = soup.select_one(
            "a.next, a.page-next, .pagination a[rel='next'], "
            "li.next a, .pager-next a"
        )
        if next_link:
            next_href = next_link.get("href", "")
            if next_href:
                next_url = next_href if next_href.startswith("http") else f"{BASE_URL}{next_href}"

    except Exception as e:
        logger.error(f"BOMOP page scrape error ({url}): {e}")

    return tenders, next_url


def _scrape_french_site(session: requests.Session) -> list[dict]:
    """Try the French version of the site which may have more content."""
    tenders = []

    try:
        resp = session.get(FRENCH_URL, timeout=30)
        if resp.status_code != 200:
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        for selector in [
            "table tbody tr",
            ".avis-item",
            ".marche-item",
            ".list-group-item",
            "article",
        ]:
            items = soup.select(selector)
            if items:
                logger.info(f"BOMOP French: {len(items)} items with '{selector}'")
                for item in items:
                    tender = _parse_tender_item(item, FRENCH_URL)
                    if tender:
                        tenders.append(tender)
                break

    except Exception as e:
        logger.error(f"BOMOP French site: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Algeria BOMOP for public procurement notices."""
    all_tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # Try English listing pages with pagination
    url = ENGLISH_URL
    for page_num in range(1, MAX_PAGES + 1):
        if not url:
            break

        logger.info(f"BOMOP: Scraping page {page_num}: {url}")
        page_tenders, next_url = _scrape_listing_page(session, url)

        page_count = 0
        for t in page_tenders:
            key = t.get("sourceRef", "") or t["title"]["en"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)
                page_count += 1

        logger.info(f"BOMOP page {page_num}: {page_count} new (total: {len(all_tenders)})")

        if page_count == 0 or not next_url:
            break

        url = next_url
        time.sleep(2)

    # Also try French site for additional tenders
    time.sleep(2)
    french_tenders = _scrape_french_site(session)
    for t in french_tenders:
        key = t.get("sourceRef", "") or t["title"]["fr"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    # Try search endpoint
    time.sleep(2)
    search_tenders, _ = _scrape_listing_page(session, SEARCH_URL)
    for t in search_tenders:
        key = t.get("sourceRef", "") or t["title"]["en"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    if not all_tenders:
        logger.warning(
            "BOMOP: no tenders scraped. The site may require specific query parameters "
            "or use dynamic rendering. Consider checking the site structure."
        )

    logger.info(f"Algeria BOMOP total: {len(all_tenders)} tenders")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "bomop_algeria")
    print(f"Scraped {len(results)} tenders from Algeria BOMOP")
