"""
Scraper for Sharjah Finance Department eProcurement Portal.
Source: https://www.eprocurement.sfd.gov.ae/

The Sharjah Finance Department (SFD) operates the eProcurement platform
for Sharjah government entities. The portal provides public access to
current tenders and procurement opportunities.

The platform is built on an enterprise procurement system and may
expose tender listings via HTML pages or AJAX/JSON endpoints.

NOTE: The portal may require JavaScript rendering or use anti-bot
protection. This scraper tries the HTML/API approach first.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("sharjah")

BASE_URL = "https://www.eprocurement.sfd.gov.ae"
PORTAL_URL = f"{BASE_URL}/"
# Common eProcurement portal endpoints
PUBLIC_TENDERS_URL = f"{BASE_URL}/public/tenders"
SEARCH_URL = f"{BASE_URL}/api/tenders/search"
LISTING_URL = f"{BASE_URL}/tenders/list"
# Sharjah Government official site as fallback
SHARJAH_GOV_URL = "https://www.sharjah.gov.ae"
MAX_PAGES = 10


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


def _try_api_endpoints(session: requests.Session) -> list[dict]:
    """Try common API endpoints that eProcurement platforms expose."""
    tenders: list[dict] = []

    api_endpoints = [
        (SEARCH_URL, "search API", "POST"),
        (f"{BASE_URL}/api/public/tenders", "public tenders API", "GET"),
        (f"{BASE_URL}/api/v1/tenders", "v1 tenders API", "GET"),
        (f"{BASE_URL}/api/tenders", "tenders API", "GET"),
    ]

    for url, label, method in api_endpoints:
        try:
            if method == "POST":
                resp = session.post(
                    url,
                    json={
                        "status": "open",
                        "page": 1,
                        "pageSize": 50,
                    },
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
            else:
                resp = session.get(
                    url,
                    headers={"Accept": "application/json"},
                    timeout=30,
                )

            if resp.status_code != 200:
                logger.info(f"Sharjah {label}: HTTP {resp.status_code}")
                continue

            try:
                data = resp.json()
            except (requests.exceptions.JSONDecodeError, ValueError):
                logger.info(f"Sharjah {label}: response is not JSON")
                continue

            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (
                    data.get("data", [])
                    or data.get("tenders", [])
                    or data.get("results", [])
                    or data.get("items", [])
                )

            for item in items:
                tender = _parse_api_item(item)
                if tender:
                    tenders.append(tender)

            if tenders:
                logger.info(f"Sharjah {label}: {len(tenders)} tenders")
                break  # Stop trying other endpoints

        except Exception as e:
            logger.info(f"Sharjah {label}: {e}")

    return tenders


def _parse_api_item(item: dict) -> dict | None:
    """Parse a single tender from an API response."""
    title = (
        item.get("title", "")
        or item.get("name", "")
        or item.get("tenderName", "")
        or item.get("subject", "")
        or item.get("TenderName", "")
    )
    if not title or len(title) < 5:
        return None

    ref = str(
        item.get("reference", "")
        or item.get("tenderNumber", "")
        or item.get("ref", "")
        or item.get("TenderNumber", "")
        or item.get("id", "")
    )
    deadline = parse_date(
        item.get("deadline", "")
        or item.get("closingDate", "")
        or item.get("endDate", "")
        or item.get("ClosingDate", "")
    ) or ""
    pub_date = parse_date(
        item.get("publishDate", "")
        or item.get("startDate", "")
        or item.get("PublishDate", "")
        or item.get("createdDate", "")
    ) or ""
    description = (
        item.get("description", "")
        or item.get("scope", "")
        or item.get("details", "")
        or title
    )
    org = (
        item.get("organization", "")
        or item.get("entity", "")
        or item.get("department", "")
        or item.get("EntityName", "")
    )

    status = "open"
    status_raw = item.get("status", "")
    if isinstance(status_raw, str) and "close" in status_raw.lower():
        status = "closed"

    return {
        "id": generate_id("sharjah", ref or title[:80], ""),
        "source": "Sharjah eProcurement",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Sharjah Finance Department",
            "ar": org or "دائرة المالية - الشارقة",
            "fr": org or "Departement des Finances de Sharjah",
        },
        "country": "UAE",
        "countryCode": "AE",
        "sector": classify_sector(title + " " + description),
        "budget": 0,
        "currency": "AED",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": status,
        "description": {
            "en": description[:500],
            "ar": description[:500],
            "fr": description[:500],
        },
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": f"{BASE_URL}/tender/{ref}" if ref else PORTAL_URL,
    }


def _parse_tender_element(element) -> dict | None:
    """Parse a single tender from an HTML element."""
    # Try to extract title
    title_el = (
        element.find(["h2", "h3", "h4"])
        or element.find("a", class_=re.compile(r"title|name", re.I))
        or element.find("div", class_=re.compile(r"title|name", re.I))
        or element.find("span", class_=re.compile(r"title|name", re.I))
    )
    title = title_el.get_text(strip=True) if title_el else ""

    if not title or len(title) < 5:
        # Try getting from table cells
        cells = element.find_all("td")
        if cells:
            texts = [c.get_text(strip=True) for c in cells if len(c.get_text(strip=True)) > 5]
            if texts:
                title = max(texts, key=len)

    if not title or len(title) < 5:
        return None

    # Extract link
    link = element.find("a", href=True)
    source_url = PORTAL_URL
    if link:
        href = link.get("href", "")
        if href.startswith("http"):
            source_url = href
        elif href.startswith("/"):
            source_url = f"{BASE_URL}{href}"

    # Extract reference
    ref = ""
    ref_el = element.find(
        string=re.compile(r"(ref|number|رقم|no\.?|tender\s*#)\s*:?\s*", re.I)
    )
    if ref_el:
        ref_match = re.search(
            r"(?:ref|number|رقم|no\.?|tender\s*#)\s*:?\s*([A-Za-z0-9\-/]+)",
            ref_el,
            re.I,
        )
        if ref_match:
            ref = ref_match.group(1)

    if not ref:
        ref = element.get("data-id", "") or element.get("data-tender-id", "") or ""

    # Extract dates
    deadline = ""
    pub_date = ""
    date_strings = element.find_all(
        string=re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2}")
    )
    for dt_str in date_strings:
        match = re.search(
            r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})", dt_str
        )
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                if not pub_date:
                    pub_date = parsed
                else:
                    deadline = parsed

    # Extract organization
    org = ""
    org_el = element.find(class_=re.compile(r"org|entity|department|authority", re.I))
    if org_el:
        org = org_el.get_text(strip=True)

    # Extract description
    desc_el = element.find("p") or element.find(
        class_=re.compile(r"desc|summary|detail", re.I)
    )
    description = desc_el.get_text(strip=True) if desc_el else title

    # Status
    status = "open"
    status_el = element.find(class_=re.compile(r"status|badge|label", re.I))
    if status_el:
        status_text = status_el.get_text(strip=True).lower()
        if "close" in status_text:
            status = "closed"
        elif "soon" in status_text:
            status = "closing-soon"

    return {
        "id": generate_id("sharjah", ref or title[:80], ""),
        "source": "Sharjah eProcurement",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Sharjah Finance Department",
            "ar": org or "دائرة المالية - الشارقة",
            "fr": org or "Departement des Finances de Sharjah",
        },
        "country": "UAE",
        "countryCode": "AE",
        "sector": classify_sector(title + " " + description),
        "budget": 0,
        "currency": "AED",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": status,
        "description": {
            "en": description[:500],
            "ar": description[:500],
            "fr": description[:500],
        },
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_html(session: requests.Session) -> list[dict]:
    """Scrape Sharjah eProcurement portal via HTML pages."""
    tenders: list[dict] = []
    seen: set[str] = set()

    urls_to_try = [
        (PORTAL_URL, "main portal"),
        (PUBLIC_TENDERS_URL, "public tenders"),
        (LISTING_URL, "tender listing"),
    ]

    for url, label in urls_to_try:
        try:
            resp = session.get(url, timeout=30, allow_redirects=True)

            if resp.status_code == 403:
                logger.info(f"Sharjah {label}: access denied (403)")
                continue
            if resp.status_code != 200:
                logger.info(f"Sharjah {label}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Check if we got a login page
            login_indicators = soup.find_all(
                string=re.compile(r"log\s*in|sign\s*in|تسجيل الدخول", re.I)
            )
            form_inputs = soup.find_all("input", attrs={"type": "password"})
            if len(login_indicators) >= 2 or form_inputs:
                logger.info(
                    f"Sharjah {label}: login page detected "
                    "(portal requires authentication)"
                )
                continue

            # Try multiple selectors for tender items
            cards = (
                soup.select(".tender-card, .tender-item, .tender-row")
                or soup.select("article, .card, .item")
                or soup.select("[class*='tender'], [class*='procurement']")
                or soup.select("table tbody tr")
            )

            if not cards:
                logger.info(f"Sharjah {label}: no tender elements found")
                # Log page info for debugging
                if label == "main portal":
                    logger.info(
                        "Sharjah: page title: %s",
                        soup.title.get_text(strip=True) if soup.title else "N/A",
                    )
                continue

            page_count = 0
            for card in cards:
                tender = _parse_tender_element(card)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["en"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(f"Sharjah {label}: {page_count} tenders")

            if page_count > 0:
                break  # Got results, stop trying

            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Sharjah {label}: connection error — {e}")
        except Exception as e:
            logger.error(f"Sharjah {label}: {e}")

    # Pagination: try additional pages if we got results
    if tenders:
        for page in range(2, MAX_PAGES + 1):
            try:
                url = f"{PUBLIC_TENDERS_URL}?page={page}"
                resp = session.get(url, timeout=30)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "lxml")
                cards = (
                    soup.select(".tender-card, .tender-item, .tender-row")
                    or soup.select("article, .card, .item")
                    or soup.select("table tbody tr")
                )

                if not cards:
                    break

                page_count = 0
                for card in cards:
                    tender = _parse_tender_element(card)
                    if not tender:
                        continue
                    key = tender["sourceRef"] or tender["title"]["en"][:60]
                    if key in seen:
                        continue
                    seen.add(key)
                    tenders.append(tender)
                    page_count += 1

                logger.info(f"Sharjah page {page}: {page_count} tenders (total: {len(tenders)})")
                if page_count == 0:
                    break

                time.sleep(2)

            except Exception as e:
                logger.error(f"Sharjah page {page}: {e}")
                break

    return tenders


def scrape() -> list[dict]:
    """Scrape Sharjah eProcurement for public procurement notices."""
    session = _create_session()

    # Try API endpoints first
    api_tenders = _try_api_endpoints(session)
    if api_tenders:
        logger.info(f"Sharjah: got {len(api_tenders)} tenders from API")
        return api_tenders

    # Fall back to HTML scraping
    html_tenders = _scrape_html(session)

    if not html_tenders:
        logger.warning(
            "Sharjah: No tenders retrieved. The eProcurement portal may "
            "require authentication, use JavaScript rendering, or have "
            "anti-bot protection. Consider using curl_cffi or a headless "
            "browser for full access."
        )

    logger.info(f"Sharjah total: {len(html_tenders)} tenders")
    return html_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "sharjah")
    print(f"Scraped {len(results)} tenders from Sharjah eProcurement")
