"""
Scraper for Jordan Government Tenders Department (GTD).
Source: https://www.gtd.gov.jo/Default/En

Jordan's official Government Tenders Department, responsible for managing
and overseeing public procurement in the Hashemite Kingdom of Jordan.
This complements the existing JONEPS scraper with the GTD-specific portal.
Content is in Arabic and English.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders
from config import HEADERS

logger = logging.getLogger("jordan_gtd")

BASE_URL = "https://www.gtd.gov.jo"
ENGLISH_URL = f"{BASE_URL}/Default/En"
ARABIC_URL = f"{BASE_URL}/Default/Ar"
TENDERS_URL = f"{BASE_URL}/Tenders/En"
RESULTS_URL = f"{BASE_URL}/Results/En"
ALTERNATE_URLS = [
    f"{BASE_URL}/en/tenders",
    f"{BASE_URL}/en/procurement",
    f"{BASE_URL}/tenders",
    f"{BASE_URL}/Tenders/List",
    f"{BASE_URL}/Tenders/Current",
    f"{BASE_URL}/Default/En/Tenders",
]
MAX_PAGES = 15


def _create_session() -> requests.Session:
    """Create a session with proper headers for GTD."""
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
    """Parse a single tender row from the GTD listing."""
    cells = row.find_all("td")
    if cells and len(cells) >= 2:
        texts = [c.get_text(strip=True) for c in cells]
    else:
        # Card or article layout
        title_el = row.find(["h2", "h3", "h4", "h5", "a", "strong"])
        if not title_el:
            texts = [row.get_text(strip=True)]
        else:
            texts = [title_el.get_text(strip=True)]
            for sub in row.find_all(["p", "span", "div", "small"], recursive=False):
                sub_text = sub.get_text(strip=True)
                if sub_text and sub_text != texts[0] and len(sub_text) > 2:
                    texts.append(sub_text)

    if not texts or all(len(t) < 3 for t in texts):
        return None

    title = ""
    ref = ""
    org = ""
    pub_date = ""
    deadline = ""
    tender_type = ""

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
        elif len(text) > 2 and len(text) < 40 and not tender_type:
            tender_type = text

    if not title or len(title) < 5:
        return None

    # Extract tender number from title
    ref_match = re.search(
        r'(?:Tender\s*(?:No\.?|#)\s*|عطاء\s*رقم\s*|Ref\.?\s*|No\.?\s*)'
        r'([\w\-/]+\d[\w\-/]*)',
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
    if org:
        desc_parts.append(f"Entity: {org}")
    desc = " | ".join(desc_parts)

    return {
        "id": generate_id("jordan_gtd", ref or title[:80], ""),
        "source": "Jordan GTD",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government Tenders Department - Jordan",
            "ar": org or "دائرة العطاءات الحكومية - الأردن",
            "fr": org or "Département des appels d'offres - Jordanie",
        },
        "country": "Jordan",
        "countryCode": "JO",
        "sector": classify_sector(title + " " + (tender_type or "")),
        "budget": 0,
        "currency": "JOD",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [tender_type] if tender_type else [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_page(session: requests.Session, url: str) -> tuple[list[dict], str]:
    """Scrape a single page for tender listings. Returns (tenders, next_page_url)."""
    tenders = []
    next_url = ""

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Jordan GTD page returned {resp.status_code}: {url}")
            return tenders, next_url

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors
        selectors = [
            "table.table tbody tr",
            "table tbody tr",
            ".dataTables_wrapper tbody tr",
            ".tender-item",
            ".tender-row",
            ".list-group-item",
            ".card",
            "article",
            ".content-item",
            ".news-item",
            "div.row div.col",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Jordan GTD: found {len(rows)} rows with '{selector}' at {url}")
                for row in rows:
                    tender = _parse_tender_row(row, url)
                    if tender:
                        tenders.append(tender)
                if tenders:
                    break

        # Check for pagination
        next_link = soup.select_one(
            "a.next, a.page-next, .pagination a[rel='next'], "
            "li.next a, .pager-next a, a:contains('Next'), "
            "a:contains('التالي'), li.PagedList-skipToNext a"
        )
        if next_link:
            next_href = next_link.get("href", "")
            if next_href:
                next_url = next_href if next_href.startswith("http") else f"{BASE_URL}{next_href}"

    except Exception as e:
        logger.error(f"Jordan GTD page error ({url}): {e}")

    return tenders, next_url


def _scrape_arabic_page(session: requests.Session) -> list[dict]:
    """Try the Arabic version of the GTD site for additional tenders."""
    tenders = []

    arabic_urls = [
        ARABIC_URL,
        f"{BASE_URL}/Tenders/Ar",
        f"{BASE_URL}/ar/tenders",
    ]

    for url in arabic_urls:
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            for selector in [
                "table tbody tr",
                ".tender-item",
                ".list-group-item",
                "article",
            ]:
                rows = soup.select(selector)
                if rows:
                    logger.info(f"Jordan GTD Arabic: {len(rows)} rows with '{selector}'")
                    for row in rows:
                        tender = _parse_tender_row(row, url)
                        if tender:
                            tender["sourceLanguage"] = "ar"
                            tenders.append(tender)
                    if tenders:
                        break

            if tenders:
                break

        except Exception as e:
            logger.error(f"Jordan GTD Arabic ({url}): {e}")

    return tenders


def _try_api_endpoints(session: requests.Session) -> list[dict]:
    """Try potential API/JSON endpoints."""
    tenders = []

    api_urls = [
        f"{BASE_URL}/api/tenders",
        f"{BASE_URL}/api/v1/tenders",
        f"{BASE_URL}/Tenders/GetTenders",
        f"{BASE_URL}/Tenders/GetCurrentTenders",
        f"{BASE_URL}/api/procurement",
    ]

    for api_url in api_urls:
        try:
            resp = session.get(api_url, headers={
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }, timeout=15)

            if resp.status_code != 200:
                continue

            try:
                data = resp.json()
            except Exception:
                continue

            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                for key in ["data", "tenders", "results", "items", "records", "value"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break

            for item in items:
                title = (
                    item.get("title", "") or item.get("name", "") or
                    item.get("subject", "") or item.get("tenderName", "") or
                    item.get("description", "")
                )
                if not title or len(title) < 5:
                    continue

                ref = str(
                    item.get("ref", "") or item.get("tenderNo", "") or
                    item.get("number", "") or item.get("id", "")
                )
                org = item.get("organization", "") or item.get("entity", "") or ""
                pub_date = parse_date(str(
                    item.get("publishDate", "") or item.get("date", "") or
                    item.get("createdDate", "")
                )) or ""
                deadline = parse_date(str(
                    item.get("deadline", "") or item.get("closingDate", "") or
                    item.get("endDate", "")
                )) or ""

                tender = {
                    "id": generate_id("jordan_gtd", ref or title[:80], ""),
                    "source": "Jordan GTD",
                    "sourceRef": ref,
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": org or "Government Tenders Department - Jordan",
                        "ar": org or "دائرة العطاءات الحكومية - الأردن",
                        "fr": org or "Département des appels d'offres - Jordanie",
                    },
                    "country": "Jordan",
                    "countryCode": "JO",
                    "sector": classify_sector(title),
                    "budget": 0,
                    "currency": "JOD",
                    "deadline": deadline,
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {"en": title, "ar": title, "fr": title},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": f"{BASE_URL}/Tenders/{ref}" if ref else TENDERS_URL,
                }
                tenders.append(tender)

            if tenders:
                logger.info(f"Jordan GTD API: found {len(tenders)} from {api_url}")
                break

        except Exception:
            continue

    return tenders


def scrape() -> list[dict]:
    """Scrape Jordan Government Tenders Department for procurement notices."""
    all_tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # Try the English tenders page with pagination
    urls_to_try = [TENDERS_URL, ENGLISH_URL] + ALTERNATE_URLS

    for start_url in urls_to_try:
        url = start_url
        for page_num in range(1, MAX_PAGES + 1):
            if not url:
                break

            logger.info(f"Jordan GTD: Scraping page {page_num}: {url}")
            page_tenders, next_url = _scrape_page(session, url)

            page_count = 0
            for t in page_tenders:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
                    page_count += 1

            logger.info(f"Jordan GTD page {page_num}: {page_count} new (total: {len(all_tenders)})")

            if page_count == 0 or not next_url:
                break

            url = next_url
            time.sleep(2)

        if all_tenders:
            break
        time.sleep(2)

    # Try Arabic pages for additional tenders
    time.sleep(2)
    arabic_tenders = _scrape_arabic_page(session)
    for t in arabic_tenders:
        key = t.get("sourceRef", "") or t["title"]["ar"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    # Try results page (awarded tenders for reference)
    time.sleep(2)
    results_tenders, _ = _scrape_page(session, RESULTS_URL)
    for t in results_tenders:
        t["status"] = "awarded"
        key = t.get("sourceRef", "") or t["title"]["en"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    # Try API endpoints
    time.sleep(2)
    api_tenders = _try_api_endpoints(session)
    for t in api_tenders:
        key = t.get("sourceRef", "") or t["title"]["en"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    if not all_tenders:
        logger.warning(
            "Jordan GTD: no tenders scraped. The portal may use ASP.NET "
            "postback/ViewState or JavaScript rendering. Consider using "
            "Selenium or checking if the site structure has changed."
        )

    logger.info(f"Jordan GTD total: {len(all_tenders)} tenders")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "jordan_gtd")
    print(f"Scraped {len(results)} tenders from Jordan GTD")
