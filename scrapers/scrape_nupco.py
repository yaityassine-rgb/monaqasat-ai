"""
Scraper for Saudi NUPCO (National Unified Procurement Company) Healthcare Tenders.
Source: https://www.nupco.com/en/tenders/

NUPCO is Saudi Arabia's national unified procurement company for healthcare
products and services. It centralizes procurement for the Ministry of Health,
government hospitals, and other healthcare entities across the Kingdom.

The website lists tenders on paginated HTML pages. Each tender card contains
the tender title, reference number, deadline, and status. Detail pages
provide full scope and requirements.

NOTE: The NUPCO website may use JavaScript rendering for some content.
This scraper tries the HTML/API approach first. If the site is fully
JS-rendered, results may be limited.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("nupco")

BASE_URL = "https://www.nupco.com"
TENDERS_URL = f"{BASE_URL}/en/tenders/"
# Alternative API endpoint that NUPCO may expose
API_URL = f"{BASE_URL}/api/tenders"
MAX_PAGES = 15


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
        "Referer": BASE_URL,
    })
    return s


def _try_api(session: requests.Session) -> list[dict]:
    """Try to access a JSON API endpoint if available."""
    tenders: list[dict] = []
    try:
        resp = session.get(
            API_URL,
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.info(f"NUPCO API: HTTP {resp.status_code} (not available)")
            return tenders

        data = resp.json()
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("tenders", data.get("results", [])))

        for item in items:
            tender = _parse_api_item(item)
            if tender:
                tenders.append(tender)

        logger.info(f"NUPCO API: {len(tenders)} tenders")
    except (requests.exceptions.JSONDecodeError, ValueError):
        logger.info("NUPCO API: response is not JSON")
    except Exception as e:
        logger.info(f"NUPCO API: {e}")

    return tenders


def _parse_api_item(item: dict) -> dict | None:
    """Parse a single tender from the API response."""
    title = (
        item.get("title", "")
        or item.get("name", "")
        or item.get("tender_name", "")
    )
    if not title or len(title) < 5:
        return None

    ref = (
        item.get("reference", "")
        or item.get("tender_number", "")
        or item.get("ref", "")
        or item.get("id", "")
    )
    deadline = parse_date(
        item.get("deadline", "")
        or item.get("closing_date", "")
        or item.get("end_date", "")
    ) or ""
    pub_date = parse_date(
        item.get("publish_date", "")
        or item.get("start_date", "")
        or item.get("created_at", "")
    ) or ""
    description = item.get("description", "") or item.get("scope", "") or title
    status_raw = item.get("status", "open")

    status = "open"
    if isinstance(status_raw, str):
        if "close" in status_raw.lower():
            status = "closed"
        elif "soon" in status_raw.lower():
            status = "closing-soon"

    return {
        "id": generate_id("nupco", str(ref) or title[:80], ""),
        "source": "NUPCO",
        "sourceRef": str(ref),
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": "National Unified Procurement Company (NUPCO)",
            "ar": "الشركة الوطنية للشراء الموحد (نوبكو)",
            "fr": "Societe Nationale d'Achat Unifie (NUPCO)",
        },
        "country": "Saudi Arabia",
        "countryCode": "SA",
        "sector": classify_sector(title + " " + description + " healthcare medical"),
        "budget": 0,
        "currency": "SAR",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": status,
        "description": {"en": description[:500], "ar": description[:500], "fr": description[:500]},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": f"{TENDERS_URL}",
    }


def _parse_tender_card(card) -> dict | None:
    """Parse a single tender card/row from the HTML listing page."""
    # Try common card/item selectors
    title_el = (
        card.find("h2")
        or card.find("h3")
        or card.find("h4")
        or card.find("a", class_=re.compile(r"title|name|heading", re.I))
        or card.find("div", class_=re.compile(r"title|name|heading", re.I))
    )
    title = title_el.get_text(strip=True) if title_el else ""

    if not title or len(title) < 5:
        # Try getting text from the entire card
        full_text = card.get_text(strip=True)
        if len(full_text) > 10:
            title = full_text[:200]
        else:
            return None

    # Extract link
    link = card.find("a", href=True)
    source_url = TENDERS_URL
    if link:
        href = link.get("href", "")
        if href.startswith("http"):
            source_url = href
        elif href.startswith("/"):
            source_url = f"{BASE_URL}{href}"

    # Extract reference number
    ref = ""
    ref_el = card.find(string=re.compile(r"(ref|number|رقم|no\.?)\s*:?\s*", re.I))
    if ref_el:
        ref_match = re.search(r"(?:ref|number|رقم|no\.?)\s*:?\s*([A-Za-z0-9\-/]+)", ref_el, re.I)
        if ref_match:
            ref = ref_match.group(1)

    # If no ref found, try data attributes
    if not ref:
        ref = card.get("data-id", "") or card.get("data-tender-id", "") or ""

    # Extract dates
    deadline = ""
    pub_date = ""
    date_texts = card.find_all(string=re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2}"))
    for dt_text in date_texts:
        date_match = re.search(r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})", dt_text)
        if date_match:
            parsed = parse_date(date_match.group(1))
            if parsed:
                if not deadline:
                    deadline = parsed
                elif not pub_date:
                    pub_date = parsed

    # Extract description
    desc_el = card.find("p") or card.find("div", class_=re.compile(r"desc|summary|detail|content", re.I))
    description = desc_el.get_text(strip=True) if desc_el else title

    # Determine status
    status = "open"
    status_el = card.find(class_=re.compile(r"status|badge|label|tag", re.I))
    if status_el:
        status_text = status_el.get_text(strip=True).lower()
        if "close" in status_text:
            status = "closed"
        elif "soon" in status_text or "expir" in status_text:
            status = "closing-soon"

    return {
        "id": generate_id("nupco", ref or title[:80], ""),
        "source": "NUPCO",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": "National Unified Procurement Company (NUPCO)",
            "ar": "الشركة الوطنية للشراء الموحد (نوبكو)",
            "fr": "Societe Nationale d'Achat Unifie (NUPCO)",
        },
        "country": "Saudi Arabia",
        "countryCode": "SA",
        "sector": classify_sector(title + " " + description + " healthcare medical"),
        "budget": 0,
        "currency": "SAR",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": status,
        "description": {"en": description[:500], "ar": description[:500], "fr": description[:500]},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_html(session: requests.Session) -> list[dict]:
    """Scrape NUPCO tender listings from HTML pages."""
    tenders: list[dict] = []
    seen: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        try:
            # Try common pagination patterns
            if page == 1:
                url = TENDERS_URL
            else:
                url = f"{TENDERS_URL}?page={page}"

            resp = session.get(url, timeout=30)

            if resp.status_code == 404:
                logger.info(f"NUPCO page {page}: 404 — end of pagination")
                break
            if resp.status_code != 200:
                logger.warning(f"NUPCO page {page}: HTTP {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Try multiple selectors for tender cards
            cards = (
                soup.select(".tender-card, .tender-item, .tender-row")
                or soup.select("article.tender, div.tender")
                or soup.select("[class*='tender']")
                or soup.select(".card, .item, .listing-item")
                or soup.select("table tbody tr")
            )

            if not cards:
                # Try to find any content container with multiple items
                containers = soup.select("main, .content, .page-content, #content")
                for container in containers:
                    items = container.find_all(["article", "div"], recursive=False)
                    if len(items) >= 2:
                        cards = items
                        break

            if not cards:
                logger.info(f"NUPCO page {page}: no tender cards found")
                if page == 1:
                    # Log page structure for debugging
                    logger.info(
                        "NUPCO: Site may require JavaScript rendering. "
                        "Page title: %s",
                        soup.title.get_text(strip=True) if soup.title else "N/A",
                    )
                break

            page_count = 0
            for card in cards:
                tender = _parse_tender_card(card)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["en"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(f"NUPCO page {page}: {page_count} tenders (total: {len(tenders)})")

            if page_count == 0:
                break

            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"NUPCO page {page}: connection error — {e}")
            break
        except Exception as e:
            logger.error(f"NUPCO page {page}: {e}")
            break

    return tenders


def scrape() -> list[dict]:
    """Scrape NUPCO for healthcare procurement tenders."""
    session = _create_session()

    # Try API first
    api_tenders = _try_api(session)
    if api_tenders:
        logger.info(f"NUPCO: got {len(api_tenders)} tenders from API")
        return api_tenders

    # Fall back to HTML scraping
    html_tenders = _scrape_html(session)

    if not html_tenders:
        logger.warning(
            "NUPCO: No tenders retrieved. The website may require JavaScript "
            "rendering or use anti-bot protection. Consider using curl_cffi "
            "or a headless browser for this source."
        )

    logger.info(f"NUPCO total: {len(html_tenders)} tenders")
    return html_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "nupco")
    print(f"Scraped {len(results)} tenders from NUPCO")
