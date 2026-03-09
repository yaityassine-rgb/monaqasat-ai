"""
Scraper for Qatar Government Monaqasat Portal.
Source: https://monaqasat.mof.gov.qa/TendersOnlineServices/AvailableMinistriesTenders/1

Qatar's official government procurement portal. The site uses HTTPS with
restrictive SSL/networking that may time out from outside Qatar.
Content is primarily in Arabic.
"""

import logging
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger("qatar")

BASE_URL = "https://monaqasat.mof.gov.qa"
LISTING_URL = f"{BASE_URL}/TendersOnlineServices/AvailableMinistriesTenders"
MAX_PAGES = 10

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en;q=0.9",
    "Referer": BASE_URL,
}


def _get(url, **kwargs):
    """HTTP GET with TLS fingerprint impersonation if available."""
    if HAS_CURL_CFFI:
        return curl_requests.get(url, impersonate="chrome131", **kwargs)
    return requests.get(url, **kwargs)


def _create_session() -> requests.Session:
    """Create a session with proper headers (used as fallback only)."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en;q=0.9",
        "Referer": BASE_URL,
    })
    return s


def _parse_tender_row(row, page_url: str) -> dict | None:
    """Parse a single tender row from the HTML table."""
    cells = row.find_all("td")
    if len(cells) < 3:
        return None

    texts = [c.get_text(strip=True) for c in cells]

    # Try to extract title from the row
    title = ""
    ref = ""
    org = ""
    deadline = ""
    pub_date = ""
    source_url = page_url

    # Look for a link in the row that goes to a detail page
    link_tag = row.find("a", href=True)
    if link_tag:
        href = link_tag.get("href", "")
        if href and not href.startswith("javascript"):
            source_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        title = link_tag.get_text(strip=True)

    # Fallback: use cell texts
    if not title and len(texts) >= 2:
        title = texts[1] if len(texts[0]) < len(texts[1]) else texts[0]
    if not title or len(title) < 5:
        return None

    # Try to find reference number (usually short alphanumeric)
    for t in texts:
        if len(t) < 30 and any(c.isdigit() for c in t) and t != title:
            if not ref:
                ref = t
            continue

    # Try to find dates
    for t in texts:
        d = parse_date(t)
        if d:
            if not pub_date:
                pub_date = d
            else:
                deadline = d

    # Try to find organization
    for t in texts:
        if len(t) > 10 and t != title and t != ref:
            if not any(c.isdigit() for c in t[:5]):
                org = t
                break

    return {
        "id": generate_id("qatar", ref or title[:80], ""),
        "source": "Qatar Monaqasat",
        "sourceRef": ref,
        "sourceLanguage": "ar",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Qatar",
            "ar": org or "حكومة قطر",
            "fr": org or "Gouvernement du Qatar",
        },
        "country": "Qatar",
        "countryCode": "QA",
        "sector": classify_sector(title),
        "budget": 0,
        "currency": "QAR",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": title, "ar": title, "fr": title},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_playwright() -> list[dict]:
    """Use Playwright headless browser to render the Qatar Monaqasat portal."""
    tenders: list[dict] = []
    if not HAS_PLAYWRIGHT:
        logger.debug("Qatar: Playwright not installed, skipping browser scrape")
        return tenders

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "ar,en;q=0.9",
            })

            for page_num in range(1, 6):
                url = f"{LISTING_URL}/{page_num}"
                logger.info(f"Qatar Playwright: loading page {page_num}")

                try:
                    page.goto(url, timeout=45000, wait_until="networkidle")
                    page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"Qatar Playwright page {page_num}: {e}")
                    break

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                rows = []
                for selector in [
                    "table.table tbody tr",
                    "table tbody tr",
                    ".tender-item",
                    ".tender-row",
                    "div.panel",
                    ".card",
                ]:
                    rows = soup.select(selector)
                    if rows:
                        break

                if not rows:
                    logger.info(f"Qatar Playwright page {page_num}: no rows found")
                    break

                page_count = 0
                for row in rows:
                    tender = _parse_tender_row(row, url)
                    if not tender:
                        continue
                    key = tender["sourceRef"] or tender["title"]["ar"][:60]
                    existing = {t["sourceRef"] or t["title"]["ar"][:60] for t in tenders}
                    if key not in existing:
                        tenders.append(tender)
                        page_count += 1

                logger.info(f"Qatar Playwright page {page_num}: {page_count} tenders")
                if page_count == 0:
                    break

            browser.close()

    except Exception as e:
        logger.error(f"Qatar Playwright error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Qatar Monaqasat portal for procurement notices."""
    tenders: list[dict] = []
    seen: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        url = f"{LISTING_URL}/{page}"
        try:
            resp = _get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"Qatar page {page}: HTTP {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Try multiple selectors for tender listings
            rows = []
            for selector in [
                "table.table tbody tr",
                "table tbody tr",
                ".tender-item",
                ".tender-row",
                "div.panel",
                ".card",
            ]:
                rows = soup.select(selector)
                if rows:
                    logger.info(f"Qatar page {page}: found {len(rows)} rows with '{selector}'")
                    break

            if not rows:
                logger.info(f"Qatar page {page}: no tender rows found")
                break

            page_count = 0
            for row in rows:
                tender = _parse_tender_row(row, url)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["ar"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(f"Qatar page {page}: {page_count} tenders (total: {len(tenders)})")
            if page_count == 0:
                break

            time.sleep(2)

        except Exception as e:
            err_str = str(e).lower()
            if "ssl" in err_str or "eof" in err_str:
                logger.warning(f"Qatar page {page}: SSL error — {e}")
            elif "timeout" in err_str or "timed out" in err_str:
                logger.warning(f"Qatar page {page}: request timed out — {e}")
            elif "connection" in err_str:
                logger.warning(f"Qatar page {page}: connection error — {e}")
            else:
                logger.error(f"Qatar page {page}: {e}")
            break

    # If HTTP scraping found nothing, try Playwright
    if not tenders:
        logger.info("Qatar: HTTP scraping found nothing, trying Playwright...")
        pw_tenders = _scrape_playwright()
        for t in pw_tenders:
            key = t["sourceRef"] or t["title"]["ar"][:60]
            if key not in seen:
                seen.add(key)
                tenders.append(t)

    if not tenders:
        logger.warning(
            "Qatar: no tenders scraped. The portal may be unreachable "
            "from outside Qatar or requires specific network access."
        )

    logger.info(f"Qatar total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "qatar")
    print(f"Scraped {len(results)} tenders from Qatar Monaqasat")
