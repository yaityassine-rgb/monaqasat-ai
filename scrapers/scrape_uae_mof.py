"""
Scraper for UAE Ministry of Finance — Government Procurement Tenders.
Source: https://mof.gov.ae/en/public-finance/government-procurement/tenders-and-auctions/

The UAE Ministry of Finance (MoF) publishes federal government tenders
and auctions on their official website. The tenders page lists current
procurement opportunities from various federal entities.

The website is built on a CMS (likely Drupal/WordPress) and renders
tender listings in paginated HTML format. Some content may be loaded
via AJAX calls.

NOTE: The MoF website uses Cloudflare or similar CDN protection.
This scraper uses browser-like headers to avoid being blocked.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("uae_mof")

BASE_URL = "https://mof.gov.ae"
TENDERS_URL = f"{BASE_URL}/en/public-finance/government-procurement/tenders-and-auctions/"
# Alternative API endpoints
API_URL = f"{BASE_URL}/api/tenders"
WP_API_URL = f"{BASE_URL}/wp-json/wp/v2/tenders"
# Arabic version of the page
TENDERS_AR_URL = f"{BASE_URL}/ar/public-finance/government-procurement/tenders-and-auctions/"
MAX_PAGES = 10


def _create_session() -> requests.Session:
    """Create a session with browser-like headers to bypass CDN protection."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    })
    return s


def _try_api(session: requests.Session) -> list[dict]:
    """Try to access JSON API endpoints if available."""
    tenders: list[dict] = []

    endpoints = [
        (API_URL, "MoF API"),
        (WP_API_URL, "WordPress API"),
        (f"{BASE_URL}/jsonapi/node/tender", "JSON:API"),
    ]

    for url, label in endpoints:
        try:
            resp = session.get(
                url,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.info(f"UAE MoF {label}: HTTP {resp.status_code}")
                continue

            try:
                data = resp.json()
            except (requests.exceptions.JSONDecodeError, ValueError):
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
                logger.info(f"UAE MoF {label}: {len(tenders)} tenders")
                break

        except Exception as e:
            logger.info(f"UAE MoF {label}: {e}")

    return tenders


def _parse_api_item(item: dict) -> dict | None:
    """Parse a single tender from an API response."""
    # Handle both flat and nested (WordPress/Drupal) structures
    attributes = item.get("attributes", item)

    title = (
        attributes.get("title", "")
        or attributes.get("name", "")
        or attributes.get("field_title", "")
    )
    if isinstance(title, dict):
        title = title.get("rendered", title.get("value", ""))
    if not title or len(title) < 5:
        return None

    ref = str(
        attributes.get("reference", "")
        or attributes.get("tender_number", "")
        or attributes.get("field_reference", "")
        or item.get("id", "")
    )
    deadline = parse_date(
        attributes.get("deadline", "")
        or attributes.get("closing_date", "")
        or attributes.get("field_closing_date", "")
    ) or ""
    pub_date = parse_date(
        attributes.get("date", "")
        or attributes.get("publish_date", "")
        or attributes.get("field_publish_date", "")
        or attributes.get("created", "")
    ) or ""

    description = attributes.get("description", "") or attributes.get("content", "")
    if isinstance(description, dict):
        description = description.get("rendered", description.get("value", ""))
    # Strip HTML tags from description
    if description and "<" in description:
        description = BeautifulSoup(description, "lxml").get_text(strip=True)
    if not description:
        description = title

    org = (
        attributes.get("entity", "")
        or attributes.get("organization", "")
        or attributes.get("field_entity", "")
    )

    return {
        "id": generate_id("uae_mof", ref or title[:80], ""),
        "source": "UAE Ministry of Finance",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "UAE Ministry of Finance",
            "ar": org or "وزارة المالية - الإمارات العربية المتحدة",
            "fr": org or "Ministere des Finances des EAU",
        },
        "country": "UAE",
        "countryCode": "AE",
        "sector": classify_sector(title + " " + description),
        "budget": 0,
        "currency": "AED",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {
            "en": description[:500],
            "ar": description[:500],
            "fr": description[:500],
        },
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": TENDERS_URL,
    }


def _parse_tender_item(item, base_page_url: str) -> dict | None:
    """Parse a single tender item from the HTML page."""
    # Try to extract title from headings or links
    title_el = (
        item.find(["h2", "h3", "h4", "h5"])
        or item.find("a", class_=re.compile(r"title|name|heading", re.I))
        or item.find("div", class_=re.compile(r"title|name|heading", re.I))
        or item.find("strong")
    )
    title = title_el.get_text(strip=True) if title_el else ""

    if not title or len(title) < 5:
        # Try table cells
        cells = item.find_all("td")
        if cells:
            texts = [c.get_text(strip=True) for c in cells if len(c.get_text(strip=True)) > 5]
            if texts:
                title = max(texts, key=len)

    if not title or len(title) < 5:
        return None

    # Extract link
    link = item.find("a", href=True)
    source_url = base_page_url
    if link:
        href = link.get("href", "")
        if href.startswith("http"):
            source_url = href
        elif href.startswith("/"):
            source_url = f"{BASE_URL}{href}"

    # Extract reference number
    ref = ""
    full_text = item.get_text(" ", strip=True)
    ref_match = re.search(
        r"(?:ref|no|number|tender\s*#|رقم)\s*[:\.]?\s*([A-Za-z0-9\-/]+)",
        full_text,
        re.I,
    )
    if ref_match:
        ref = ref_match.group(1)

    # Extract dates
    deadline = ""
    pub_date = ""
    date_matches = re.findall(
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4})",
        full_text,
    )
    for dm in date_matches:
        parsed = parse_date(dm)
        if parsed:
            if not pub_date:
                pub_date = parsed
            elif not deadline:
                deadline = parsed

    # Extract organization/entity
    org = ""
    org_el = item.find(class_=re.compile(r"org|entity|department|ministry", re.I))
    if org_el:
        org = org_el.get_text(strip=True)

    # Extract description
    desc_el = item.find("p") or item.find(
        class_=re.compile(r"desc|summary|excerpt|detail", re.I)
    )
    description = desc_el.get_text(strip=True) if desc_el else ""
    if not description:
        description = full_text[:300]

    # Determine status
    status = "open"
    status_el = item.find(class_=re.compile(r"status|badge|label|tag", re.I))
    if status_el:
        status_text = status_el.get_text(strip=True).lower()
        if "close" in status_text or "مغلق" in status_text:
            status = "closed"
        elif "soon" in status_text or "قريب" in status_text:
            status = "closing-soon"

    # Check for PDF download links (common in gov tender pages)
    pdf_link = item.find("a", href=re.compile(r"\.pdf$", re.I))
    requirements = []
    if pdf_link:
        requirements.append("PDF documents available")

    return {
        "id": generate_id("uae_mof", ref or title[:80], ""),
        "source": "UAE Ministry of Finance",
        "sourceRef": ref,
        "sourceLanguage": "en",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "UAE Ministry of Finance",
            "ar": org or "وزارة المالية - الإمارات العربية المتحدة",
            "fr": org or "Ministere des Finances des EAU",
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
        "requirements": requirements,
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_html(session: requests.Session) -> list[dict]:
    """Scrape UAE MoF tenders page via HTML."""
    tenders: list[dict] = []
    seen: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        try:
            if page == 1:
                url = TENDERS_URL
            else:
                # Try common pagination patterns
                url = f"{TENDERS_URL}?page={page}"

            resp = session.get(url, timeout=30, allow_redirects=True)

            if resp.status_code == 403:
                logger.warning(
                    "UAE MoF: access denied (403). Site uses CDN protection."
                )
                break
            if resp.status_code == 404 and page > 1:
                logger.info(f"UAE MoF page {page}: 404 — end of pagination")
                break
            if resp.status_code != 200:
                logger.warning(f"UAE MoF page {page}: HTTP {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Check for bot challenge pages
            if soup.find("div", id="challenge-running"):
                logger.warning(
                    "UAE MoF: Cloudflare challenge page detected. "
                    "Consider using curl_cffi with impersonate='chrome'."
                )
                break

            # Try multiple selectors for tender items
            items = (
                soup.select(".tender-item, .tender-card, .tender-row")
                or soup.select("article.tender, div.tender")
                or soup.select("[class*='tender-list'] > div, [class*='tender-list'] > li")
                or soup.select(".views-row, .node--type-tender")  # Drupal patterns
                or soup.select(".wp-block-post, .entry-content li")  # WordPress patterns
            )

            if not items:
                # Try finding a table with tender data
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    if len(rows) >= 2:
                        header_text = " ".join(
                            th.get_text(strip=True).lower()
                            for th in rows[0].find_all(["th", "td"])
                        )
                        if any(
                            kw in header_text
                            for kw in ["tender", "procurement", "مناقصة", "title", "deadline"]
                        ):
                            items = rows[1:]
                            break

            if not items:
                # Try generic content containers
                content = soup.select_one(
                    "main, .content, .page-content, #main-content, .field-items"
                )
                if content:
                    # Look for list items or articles
                    items = (
                        content.find_all("article")
                        or content.find_all("li")
                        or content.find_all(
                            "div", class_=re.compile(r"item|card|row|block", re.I)
                        )
                    )

            if not items:
                if page == 1:
                    logger.info(
                        "UAE MoF: no tender elements found on page. "
                        "Page title: %s",
                        soup.title.get_text(strip=True) if soup.title else "N/A",
                    )
                break

            page_count = 0
            for item in items:
                tender = _parse_tender_item(item, url)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["en"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(f"UAE MoF page {page}: {page_count} tenders (total: {len(tenders)})")

            if page_count == 0:
                break

            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"UAE MoF page {page}: connection error — {e}")
            break
        except Exception as e:
            logger.error(f"UAE MoF page {page}: {e}")
            break

    return tenders


def _try_curl_cffi(url: str) -> str | None:
    """Try to fetch a page using curl_cffi to bypass bot protection."""
    try:
        from curl_cffi import requests as curl_requests

        resp = curl_requests.get(
            url,
            impersonate="chrome",
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.text
    except ImportError:
        logger.info("curl_cffi not installed — skipping impersonation")
    except Exception as e:
        logger.info(f"curl_cffi failed: {e}")

    return None


def scrape() -> list[dict]:
    """Scrape UAE Ministry of Finance for government procurement tenders."""
    session = _create_session()

    # Try API first
    api_tenders = _try_api(session)
    if api_tenders:
        logger.info(f"UAE MoF: got {len(api_tenders)} tenders from API")
        return api_tenders

    # Try HTML scraping
    html_tenders = _scrape_html(session)

    if not html_tenders:
        # Try curl_cffi as last resort
        logger.info("UAE MoF: trying curl_cffi for bot protection bypass")
        page_html = _try_curl_cffi(TENDERS_URL)
        if page_html:
            soup = BeautifulSoup(page_html, "lxml")
            items = (
                soup.select(".tender-item, .tender-card, .tender-row")
                or soup.select("article, .card")
                or soup.select("table tbody tr")
            )
            seen: set[str] = set()
            for item in items:
                tender = _parse_tender_item(item, TENDERS_URL)
                if tender:
                    key = tender["sourceRef"] or tender["title"]["en"][:60]
                    if key not in seen:
                        seen.add(key)
                        html_tenders.append(tender)
            if html_tenders:
                logger.info(
                    f"UAE MoF: got {len(html_tenders)} tenders via curl_cffi"
                )

    if not html_tenders:
        logger.warning(
            "UAE MoF: No tenders retrieved. The website may use Cloudflare "
            "protection or require JavaScript rendering. Consider using "
            "curl_cffi (pip install curl_cffi) or a headless browser."
        )

    logger.info(f"UAE MoF total: {len(html_tenders)} tenders")
    return html_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "uae_mof")
    print(f"Scraped {len(results)} tenders from UAE Ministry of Finance")
