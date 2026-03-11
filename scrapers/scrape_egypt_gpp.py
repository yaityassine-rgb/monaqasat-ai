"""
Scraper for Egypt Government Procurement Portal (e-Tenders).
Source: https://etenders.gov.eg

Egypt's official e-procurement platform managed by the Ministry of Finance.
All government entities publish their tenders through this portal.
Content is in Arabic and English.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders
from config import HEADERS

logger = logging.getLogger("egypt_gpp")

BASE_URL = "https://etenders.gov.eg"
TENDERS_URL = f"{BASE_URL}/tenders"
SEARCH_URL = f"{BASE_URL}/tenders/search"
ALTERNATE_URLS = [
    f"{BASE_URL}/Tenders/TendersList",
    f"{BASE_URL}/Tenders/PublicTenders",
    f"{BASE_URL}/Home/Tenders",
    f"{BASE_URL}/public/tenders",
    f"{BASE_URL}/ar/tenders",
    f"{BASE_URL}/en/tenders",
]
MAX_PAGES = 15


def _create_session() -> requests.Session:
    """Create a session with proper headers for Egypt GPP."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,ar;q=0.9",
        "Referer": BASE_URL,
    })
    return s


def _parse_tender_row(row, page_url: str) -> dict | None:
    """Parse a single tender row from the Egypt GPP listing."""
    cells = row.find_all("td")
    if cells and len(cells) >= 2:
        texts = [c.get_text(strip=True) for c in cells]
    else:
        # Try card or div-based layout
        title_el = row.find(["h3", "h4", "h5", "a", "strong", ".tender-title"])
        if not title_el:
            texts = [row.get_text(strip=True)]
        else:
            texts = [title_el.get_text(strip=True)]
            # Get additional details
            for detail_cls in [".tender-org", ".organization", ".entity", "p"]:
                detail_el = row.find(detail_cls) if detail_cls.startswith(".") else row.find(detail_cls)
                if detail_el and detail_el != title_el:
                    texts.append(detail_el.get_text(strip=True))

    if not texts or all(len(t) < 3 for t in texts):
        return None

    title = ""
    ref = ""
    org = ""
    pub_date = ""
    deadline = ""
    tender_type = ""

    for i, text in enumerate(texts):
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
        elif len(text) > 3 and len(text) < 30 and not tender_type:
            tender_type = text

    if not title or len(title) < 5:
        return None

    # Try to extract reference from title
    ref_match = re.search(
        r'(?:Tender\s*(?:No\.?|#)\s*|مناقصة\s*رقم\s*|Ref\.?\s*)([\w\-/]+)',
        title, re.IGNORECASE
    )
    if ref_match and not ref:
        ref = ref_match.group(1)

    # Get detail link
    source_url = page_url
    link = row.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and not href.startswith("javascript") and href != "#":
            source_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    desc_parts = [title]
    if tender_type:
        desc_parts.append(f"Type: {tender_type}")
    desc = " | ".join(desc_parts)

    return {
        "id": generate_id("egypt_gpp", ref or title[:80], ""),
        "source": "Egypt e-Tenders",
        "sourceRef": ref,
        "sourceLanguage": "ar",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Egypt",
            "ar": org or "جمهورية مصر العربية",
            "fr": org or "Gouvernement d'Égypte",
        },
        "country": "Egypt",
        "countryCode": "EG",
        "sector": classify_sector(title + " " + (tender_type or "")),
        "budget": 0,
        "currency": "EGP",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [tender_type] if tender_type else [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_page(session: requests.Session, url: str) -> tuple[list[dict], str]:
    """Scrape a single page. Returns (tenders, next_page_url)."""
    tenders = []
    next_url = ""

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Egypt GPP page returned {resp.status_code}: {url}")
            return tenders, next_url

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors
        selectors = [
            "table.table tbody tr",
            "table tbody tr",
            ".dataTables_wrapper tbody tr",
            ".tender-item",
            ".tender-card",
            ".list-group-item",
            ".card",
            "article",
            ".search-result",
            ".result-row",
            ".ui-datatable-data tr",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Egypt GPP: found {len(rows)} rows with '{selector}' at {url}")
                for row in rows:
                    tender = _parse_tender_row(row, url)
                    if tender:
                        tenders.append(tender)
                break

        # Check for pagination
        next_link = soup.select_one(
            "a.next, a.page-next, .pagination a[rel='next'], "
            "li.next a, .pager-next a, a:contains('Next'), a:contains('التالي')"
        )
        if next_link:
            next_href = next_link.get("href", "")
            if next_href:
                next_url = next_href if next_href.startswith("http") else f"{BASE_URL}{next_href}"

    except Exception as e:
        logger.error(f"Egypt GPP page error ({url}): {e}")

    return tenders, next_url


def _try_api_endpoint(session: requests.Session) -> list[dict]:
    """Try potential API/JSON endpoints for tender data."""
    tenders = []

    api_urls = [
        f"{BASE_URL}/api/tenders",
        f"{BASE_URL}/api/v1/tenders",
        f"{BASE_URL}/tenders/list",
        f"{BASE_URL}/api/procurement/list",
    ]

    for api_url in api_urls:
        try:
            resp = session.get(api_url, headers={
                "Accept": "application/json",
            }, timeout=15)

            if resp.status_code != 200:
                continue

            try:
                data = resp.json()
            except Exception:
                continue

            # Handle various JSON response formats
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                for key in ["data", "tenders", "results", "items", "records"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break

            for item in items:
                title = (
                    item.get("title", "") or item.get("name", "") or
                    item.get("subject", "") or item.get("description", "")
                )
                if not title or len(title) < 5:
                    continue

                ref = str(item.get("ref", "") or item.get("id", "") or
                         item.get("tenderNo", "") or item.get("number", ""))
                org = item.get("organization", "") or item.get("entity", "") or ""
                pub_date = parse_date(str(item.get("publishDate", "") or item.get("date", ""))) or ""
                deadline = parse_date(str(item.get("deadline", "") or item.get("closingDate", ""))) or ""

                tender = {
                    "id": generate_id("egypt_gpp", ref or title[:80], ""),
                    "source": "Egypt e-Tenders",
                    "sourceRef": ref,
                    "sourceLanguage": "ar",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": org or "Government of Egypt",
                        "ar": org or "جمهورية مصر العربية",
                        "fr": org or "Gouvernement d'Égypte",
                    },
                    "country": "Egypt",
                    "countryCode": "EG",
                    "sector": classify_sector(title),
                    "budget": 0,
                    "currency": "EGP",
                    "deadline": deadline,
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {"en": title, "ar": title, "fr": title},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": f"{BASE_URL}/tenders/{ref}" if ref else BASE_URL,
                }
                tenders.append(tender)

            if tenders:
                logger.info(f"Egypt GPP API: found {len(tenders)} from {api_url}")
                break

        except Exception:
            continue

    return tenders


def scrape() -> list[dict]:
    """Scrape Egypt Government Procurement Portal for tender notices."""
    all_tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # Try the main tender listing page with pagination
    url = TENDERS_URL
    for page_num in range(1, MAX_PAGES + 1):
        if not url:
            break

        logger.info(f"Egypt GPP: Scraping page {page_num}: {url}")
        page_tenders, next_url = _scrape_page(session, url)

        page_count = 0
        for t in page_tenders:
            key = t.get("sourceRef", "") or t["title"]["en"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)
                page_count += 1

        logger.info(f"Egypt GPP page {page_num}: {page_count} new (total: {len(all_tenders)})")

        if page_count == 0 or not next_url:
            break

        url = next_url
        time.sleep(2)

    # Try alternate URLs if main page didn't work
    if not all_tenders:
        for alt_url in ALTERNATE_URLS:
            time.sleep(2)
            alt_tenders, _ = _scrape_page(session, alt_url)
            for t in alt_tenders:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
            if all_tenders:
                break

    # Try API endpoints
    if not all_tenders:
        time.sleep(2)
        api_tenders = _try_api_endpoint(session)
        for t in api_tenders:
            key = t.get("sourceRef", "") or t["title"]["en"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)

    if not all_tenders:
        logger.warning(
            "Egypt GPP: no tenders scraped. The portal may use ASP.NET "
            "ViewState/postback or JavaScript rendering. Consider using "
            "Selenium or checking if the site structure has changed."
        )

    logger.info(f"Egypt GPP total: {len(all_tenders)} tenders")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "egypt_gpp")
    print(f"Scraped {len(results)} tenders from Egypt GPP")
