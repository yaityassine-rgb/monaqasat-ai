"""
Scraper for Iraq Government Tenders.
Sources:
  - https://mop.gov.iq/en/general-government-contracts-department
    (Iraq Ministry of Planning - General Government Contracts Department)
  - https://iraq.iom.int/do-business-us-procurement
    (IOM Iraq - UN procurement opportunities)

Iraq's official government contracts portal and IOM procurement.
Content is in Arabic and English.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders
from config import HEADERS

logger = logging.getLogger("iraq")

# Ministry of Planning
MOP_BASE_URL = "https://mop.gov.iq"
MOP_CONTRACTS_URL = f"{MOP_BASE_URL}/en/general-government-contracts-department"
MOP_ALTERNATE_URLS = [
    f"{MOP_BASE_URL}/en/tenders",
    f"{MOP_BASE_URL}/en/procurement",
    f"{MOP_BASE_URL}/en/bids",
    f"{MOP_BASE_URL}/ar/general-government-contracts-department",
]

# IOM Iraq procurement
IOM_BASE_URL = "https://iraq.iom.int"
IOM_PROCUREMENT_URL = f"{IOM_BASE_URL}/do-business-us-procurement"
IOM_ALTERNATE_URLS = [
    f"{IOM_BASE_URL}/procurement",
    f"{IOM_BASE_URL}/tenders",
]

MAX_PAGES = 10


def _create_session() -> requests.Session:
    """Create a session with proper headers."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,ar;q=0.9",
    })
    return s


def _parse_tender_row(row, source: str, page_url: str) -> dict | None:
    """Parse a single tender row from an HTML listing."""
    cells = row.find_all("td")
    if cells and len(cells) >= 2:
        texts = [c.get_text(strip=True) for c in cells]
    else:
        # Try extracting from card/article/div layout
        title_el = row.find(["h2", "h3", "h4", "h5", "a", "strong"])
        if not title_el:
            texts = [row.get_text(strip=True)]
        else:
            texts = [title_el.get_text(strip=True)]
            for sub in row.find_all(["p", "span", "div"], recursive=False):
                sub_text = sub.get_text(strip=True)
                if sub_text and sub_text != texts[0]:
                    texts.append(sub_text)

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

    # Try to extract reference from title
    ref_match = re.search(
        r'(?:No\.?\s*|#\s*|Ref\.?\s*|رقم\s*)([\w\-/]+\d[\w\-/]*)',
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
            base = MOP_BASE_URL if "mop.gov.iq" in page_url else IOM_BASE_URL
            source_url = href if href.startswith("http") else f"{base}{href}"

    # Determine source-specific organization defaults
    if source == "MOP":
        default_org_en = "Iraq Ministry of Planning"
        default_org_ar = "وزارة التخطيط العراقية"
        default_org_fr = "Ministère de la Planification irakien"
        source_name = "Iraq MOP"
    else:
        default_org_en = "IOM Iraq"
        default_org_ar = "المنظمة الدولية للهجرة - العراق"
        default_org_fr = "OIM Irak"
        source_name = "IOM Iraq"

    return {
        "id": generate_id(f"iraq_{source.lower()}", ref or title[:80], ""),
        "source": source_name,
        "sourceRef": ref,
        "sourceLanguage": "ar" if source == "MOP" else "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or default_org_en,
            "ar": org or default_org_ar,
            "fr": org or default_org_fr,
        },
        "country": "Iraq",
        "countryCode": "IQ",
        "sector": classify_sector(title),
        "budget": 0,
        "currency": "IQD",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": title, "ar": title, "fr": title},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_html_page(session: requests.Session, url: str, source: str) -> tuple[list[dict], str]:
    """Scrape an HTML page for tender listings. Returns (tenders, next_page_url)."""
    tenders = []
    next_url = ""

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Iraq {source} returned {resp.status_code}: {url}")
            return tenders, next_url

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors
        selectors = [
            "table.table tbody tr",
            "table tbody tr",
            ".views-row",
            ".view-content .item-list li",
            ".tender-item",
            ".contract-item",
            ".procurement-item",
            ".node--type-tender",
            "article",
            ".list-group-item",
            ".card",
            ".field-content",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Iraq {source}: found {len(rows)} rows with '{selector}' at {url}")
                for row in rows:
                    tender = _parse_tender_row(row, source, url)
                    if tender:
                        tenders.append(tender)
                if tenders:
                    break

        # Check for pagination (Drupal/WordPress style)
        next_link = soup.select_one(
            "li.pager__item--next a, a.next, .pagination a[rel='next'], "
            "li.next a, .pager-next a"
        )
        if next_link:
            next_href = next_link.get("href", "")
            if next_href:
                base = MOP_BASE_URL if "mop.gov.iq" in url else IOM_BASE_URL
                next_url = next_href if next_href.startswith("http") else f"{base}{next_href}"

    except Exception as e:
        logger.error(f"Iraq {source} page error ({url}): {e}")

    return tenders, next_url


def _scrape_mop(session: requests.Session) -> list[dict]:
    """Scrape Iraq Ministry of Planning contracts."""
    all_tenders = []
    seen: set[str] = set()

    # Try main URL and alternates
    urls_to_try = [MOP_CONTRACTS_URL] + MOP_ALTERNATE_URLS

    for start_url in urls_to_try:
        url = start_url
        for page_num in range(1, MAX_PAGES + 1):
            if not url:
                break

            tenders, next_url = _scrape_html_page(session, url, "MOP")

            page_count = 0
            for t in tenders:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
                    page_count += 1

            if page_count == 0 or not next_url:
                break

            url = next_url
            time.sleep(2)

        if all_tenders:
            break
        time.sleep(2)

    return all_tenders


def _scrape_iom(session: requests.Session) -> list[dict]:
    """Scrape IOM Iraq procurement opportunities."""
    all_tenders = []
    seen: set[str] = set()

    urls_to_try = [IOM_PROCUREMENT_URL] + IOM_ALTERNATE_URLS

    for start_url in urls_to_try:
        url = start_url
        for page_num in range(1, MAX_PAGES + 1):
            if not url:
                break

            tenders, next_url = _scrape_html_page(session, url, "IOM")

            page_count = 0
            for t in tenders:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
                    page_count += 1

            if page_count == 0 or not next_url:
                break

            url = next_url
            time.sleep(2)

        if all_tenders:
            break
        time.sleep(2)

    return all_tenders


def scrape() -> list[dict]:
    """Scrape Iraq government tenders from MOP and IOM."""
    session = _create_session()

    # Scrape both sources
    mop_tenders = _scrape_mop(session)
    logger.info(f"Iraq MOP: {len(mop_tenders)} tenders")

    time.sleep(3)

    iom_tenders = _scrape_iom(session)
    logger.info(f"Iraq IOM: {len(iom_tenders)} tenders")

    # Merge and deduplicate
    all_tenders: list[dict] = []
    seen: set[str] = set()

    for t in mop_tenders + iom_tenders:
        key = t.get("sourceRef", "") or t["title"]["en"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    if not all_tenders:
        logger.warning(
            "Iraq: no tenders scraped from either MOP or IOM. "
            "The MOP site may use dynamic rendering or require authentication. "
            "The IOM site may have changed its procurement page structure."
        )

    logger.info(f"Iraq total: {len(all_tenders)} tenders (MOP: {len(mop_tenders)}, IOM: {len(iom_tenders)})")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "iraq")
    print(f"Scraped {len(results)} tenders from Iraq (MOP + IOM)")
