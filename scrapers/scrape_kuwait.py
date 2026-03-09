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

logger = logging.getLogger("kuwait")

BASE_URL = "https://capt.gov.kw"
TENDERS_EN_URL = f"{BASE_URL}/en/tenders/opening-tenders/"
TENDERS_AR_URL = f"{BASE_URL}/ar/tenders/opening-tenders/"
ALTERNATE_URLS = [
    f"{BASE_URL}/en/tenders/",
    f"{BASE_URL}/en/",
    f"{BASE_URL}/",
]


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
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })
    return s


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


def _is_cloudflare_block(resp: requests.Response) -> bool:
    """Check if the response is a Cloudflare challenge page."""
    if resp.status_code == 403:
        return True
    text = resp.text[:2000].lower()
    return "just a moment" in text or "cloudflare" in text or "cf-browser-verification" in text


def scrape() -> list[dict]:
    """Scrape Kuwait CAPT for opening tenders.

    Note: The site uses Cloudflare protection which may block automated
    requests. If blocked, this returns an empty list gracefully.
    """
    tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # Try multiple URLs in case one works
    urls_to_try = [TENDERS_EN_URL, TENDERS_AR_URL] + ALTERNATE_URLS

    for url in urls_to_try:
        try:
            resp = session.get(url, timeout=30)

            if _is_cloudflare_block(resp):
                logger.warning(
                    f"Kuwait {url}: Cloudflare protection detected (HTTP {resp.status_code}). "
                    "Automated access is blocked."
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

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Kuwait {url}: connection error — {e}")
        except requests.exceptions.Timeout:
            logger.warning(f"Kuwait {url}: request timed out")
        except Exception as e:
            logger.error(f"Kuwait {url}: {e}")

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
