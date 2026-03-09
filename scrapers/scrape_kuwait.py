"""
Scraper for Kuwait Central Agency for Public Tenders (CAPT).
Source: https://capt.gov.kw/en/tenders/opening-tenders/

Kuwait's official public tenders portal. The site is protected by
Cloudflare bot protection, which blocks automated access. This scraper
attempts the request and falls back gracefully.
Content is in Arabic and English.
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

logger = logging.getLogger("kuwait")

BASE_URL = "https://capt.gov.kw"
TENDERS_EN_URL = f"{BASE_URL}/en/tenders/opening-tenders/"
TENDERS_AR_URL = f"{BASE_URL}/ar/tenders/opening-tenders/"
EGOV_URL = "https://e.gov.kw/sites/kgoenglish/Pages/eServices/CTC/Openedtenders.aspx"
ALTERNATE_URLS = [
    EGOV_URL,
    f"{BASE_URL}/en/tenders/",
    f"{BASE_URL}/en/",
    f"{BASE_URL}/",
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


def _get(url, **kwargs):
    """HTTP GET with TLS fingerprint impersonation if available."""
    if HAS_CURL_CFFI:
        return curl_requests.get(url, impersonate="chrome131", **kwargs)
    return requests.get(url, **kwargs)


def _parse_tender_row(row, page_url: str) -> dict | None:
    """Parse a single tender row from the HTML table or card."""
    cells = row.find_all("td")
    if not cells:
        # Maybe card-based layout
        title_el = row.find(["h3", "h4", "h5", "a", ".tender-title"])
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            return None
    else:
        texts = [c.get_text(strip=True) for c in cells]
        title = ""
        ref = ""
        org = ""
        deadline = ""
        pub_date = ""

        # Extract meaningful fields from cells
        for i, t in enumerate(texts):
            if not t:
                continue
            d = parse_date(t)
            if d:
                if not pub_date:
                    pub_date = d
                else:
                    deadline = d
            elif len(t) < 30 and any(c.isdigit() for c in t) and not ref:
                ref = t
            elif len(t) > 10 and not title:
                title = t
            elif len(t) > 10 and title and not org:
                org = t

        if not title or len(title) < 5:
            return None

    # Get detail link
    source_url = page_url
    link = row.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and not href.startswith("javascript") and href != "#":
            source_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        if not title:
            title = link.get_text(strip=True)

    ref = ref if 'ref' in dir() else ""
    org = org if 'org' in dir() else ""
    deadline = deadline if 'deadline' in dir() else ""
    pub_date = pub_date if 'pub_date' in dir() else ""

    return {
        "id": generate_id("kuwait", ref or title[:80], ""),
        "source": "Kuwait CAPT",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Kuwait",
            "ar": org or "حكومة الكويت",
            "fr": org or "Gouvernement du Koweït",
        },
        "country": "Kuwait",
        "countryCode": "KW",
        "sector": classify_sector(title),
        "budget": 0,
        "currency": "KWD",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": title, "ar": title, "fr": title},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _is_cloudflare_block(resp) -> bool:
    """Check if the response is a Cloudflare challenge page."""
    if resp.status_code == 403:
        return True
    text = resp.text[:2000].lower()
    return "just a moment" in text or "cloudflare" in text or "cf-browser-verification" in text


def scrape() -> list[dict]:
    """Scrape Kuwait CAPT for opening tenders.

    Uses curl_cffi for TLS fingerprint impersonation to bypass Cloudflare.
    Also tries e.gov.kw as an alternative source.
    """
    tenders: list[dict] = []
    seen: set[str] = set()

    # Try multiple URLs in case one works — e.gov.kw first (may not be behind Cloudflare)
    urls_to_try = [EGOV_URL, TENDERS_EN_URL, TENDERS_AR_URL] + ALTERNATE_URLS

    for url in urls_to_try:
        try:
            resp = _get(url, headers=HEADERS, timeout=30)

            if _is_cloudflare_block(resp):
                logger.warning(
                    f"Kuwait {url}: Cloudflare protection detected (HTTP {resp.status_code}). "
                    "Trying next URL."
                )
                continue

            if resp.status_code != 200:
                logger.warning(f"Kuwait {url}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Try multiple selectors for tender listings
            for selector in [
                "table.tenders-table tbody tr",
                "table tbody tr",
                ".tender-item",
                ".tender-card",
                ".post-item",
                "article",
                ".entry-content table tr",
            ]:
                rows = soup.select(selector)
                if rows:
                    logger.info(f"Kuwait: found {len(rows)} rows at {url} with '{selector}'")
                    for row in rows:
                        tender = _parse_tender_row(row, url)
                        if not tender:
                            continue
                        key = tender["sourceRef"] or tender["title"]["en"][:60]
                        if key in seen:
                            continue
                        seen.add(key)
                        tenders.append(tender)
                    if tenders:
                        break

            if tenders:
                break

            time.sleep(2)

        except Exception as e:
            logger.warning(f"Kuwait {url}: {e}")

    if not tenders:
        logger.warning(
            "Kuwait CAPT: no tenders scraped. The site uses Cloudflare "
            "bot protection which blocks automated access. "
            "Consider using a browser-based scraper or manual data entry."
        )

    logger.info(f"Kuwait total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "kuwait")
    print(f"Scraped {len(results)} tenders from Kuwait CAPT")
