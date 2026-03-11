"""
Scraper for Dubai eSupply Government Procurement Portal.
Source: https://esupply.dubai.gov.ae/

Dubai's official eSupply platform provides public access to government
procurement opportunities across Dubai's departments and entities.
The portal is built on Oracle EBS / iProcurement and may expose
public tender listings via HTML tables or AJAX endpoints.

NOTE: The eSupply portal may require JavaScript rendering or use
anti-bot protection. This scraper tries the HTML/API approach first,
and also attempts to access any publicly available API endpoints.
If the portal is fully behind authentication, we fall back to
scraping the Dubai Government's procurement announcements page.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("dubai_esupply")

BASE_URL = "https://esupply.dubai.gov.ae"
# Main portal URL
PORTAL_URL = f"{BASE_URL}/"
# Common Oracle iProcurement public URLs
PUBLIC_SOURCING_URL = f"{BASE_URL}/OA_HTML/OA.jsp?OAFunc=PON_ABSTRACT_PAGE"
PUBLIC_NEGO_URL = f"{BASE_URL}/OA_HTML/OA.jsp?OAFunc=PON_NEGO_SUMMARY"
# Alternative: Dubai Government open data / procurement page
DUBAI_GOV_URL = "https://www.dubai.gov.ae/en/information-and-services/finance-and-investment/public-tenders"
# Dubai SME procurement portal
DUBAI_SME_URL = "https://www.sme.ae/en/Pages/Tenders.aspx"
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
    })
    return s


def _parse_oracle_table(soup: BeautifulSoup, source_label: str) -> list[dict]:
    """Parse Oracle iProcurement HTML tables for tender listings."""
    tenders: list[dict] = []

    # Oracle EBS uses specific table structures
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # Check if this looks like a tender listing table
        header_row = rows[0]
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        header_text = " ".join(headers)

        # Look for procurement-related tables
        if not any(kw in header_text for kw in [
            "title", "description", "negotiation", "tender", "rfq",
            "rfp", "auction", "sourcing", "reference", "عنوان", "مناقصة",
        ]):
            continue

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            texts = [c.get_text(strip=True) for c in cells]
            full_text = " ".join(texts)

            if len(full_text) < 20:
                continue

            # Find the longest text as title
            title = max(texts, key=len)
            if len(title) < 10:
                continue

            # Extract reference number
            ref = ""
            for t in texts:
                if re.match(r"^[A-Z0-9\-/]{3,30}$", t.strip()):
                    ref = t.strip()
                    break

            # Extract dates
            deadline = ""
            pub_date = ""
            for t in texts:
                date_match = re.search(
                    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})", t
                )
                if date_match:
                    parsed = parse_date(date_match.group(1))
                    if parsed:
                        if not pub_date:
                            pub_date = parsed
                        else:
                            deadline = parsed

            # Extract link
            link_el = row.find("a", href=True)
            source_url = BASE_URL
            if link_el:
                href = link_el.get("href", "")
                if href.startswith("http"):
                    source_url = href
                elif href.startswith("/"):
                    source_url = f"{BASE_URL}{href}"

            if not ref:
                ref = title[:60]

            tender = {
                "id": generate_id("dubai_esupply", ref, ""),
                "source": "Dubai eSupply",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Government of Dubai",
                    "ar": "حكومة دبي",
                    "fr": "Gouvernement de Dubai",
                },
                "country": "UAE",
                "countryCode": "AE",
                "sector": classify_sector(title + " " + full_text),
                "budget": 0,
                "currency": "AED",
                "deadline": deadline,
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": full_text[:500],
                    "ar": full_text[:500],
                    "fr": full_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

    return tenders


def _scrape_esupply_portal(session: requests.Session) -> list[dict]:
    """Try to scrape the main eSupply portal."""
    tenders: list[dict] = []

    # Try multiple entry points
    urls_to_try = [
        (PORTAL_URL, "main portal"),
        (PUBLIC_SOURCING_URL, "public sourcing"),
        (PUBLIC_NEGO_URL, "public negotiations"),
    ]

    for url, label in urls_to_try:
        try:
            resp = session.get(url, timeout=30, allow_redirects=True)

            if resp.status_code == 403:
                logger.info(f"Dubai eSupply {label}: access denied (403)")
                continue
            if resp.status_code != 200:
                logger.info(f"Dubai eSupply {label}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Check if we got a login page
            login_indicators = soup.find_all(
                string=re.compile(r"log\s*in|sign\s*in|username|password", re.I)
            )
            if len(login_indicators) >= 2:
                logger.info(
                    f"Dubai eSupply {label}: redirected to login page "
                    "(portal requires authentication)"
                )
                continue

            # Try to parse any visible tender tables
            page_tenders = _parse_oracle_table(soup, label)
            if page_tenders:
                tenders.extend(page_tenders)
                logger.info(f"Dubai eSupply {label}: {len(page_tenders)} tenders")

            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Dubai eSupply {label}: connection error — {e}")
        except Exception as e:
            logger.error(f"Dubai eSupply {label}: {e}")

    return tenders


def _scrape_dubai_gov(session: requests.Session) -> list[dict]:
    """Scrape Dubai Government public tender announcements as fallback."""
    tenders: list[dict] = []

    try:
        resp = session.get(DUBAI_GOV_URL, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            logger.info(f"Dubai Gov: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender-related content blocks
        cards = (
            soup.select(".tender-card, .tender-item")
            or soup.select("article, .card, .item")
            or soup.select("[class*='tender'], [class*='procurement']")
        )

        for card in cards:
            title_el = card.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if len(title) < 10:
                continue

            link = card.find("a", href=True)
            source_url = DUBAI_GOV_URL
            if link:
                href = link.get("href", "")
                if href.startswith("http"):
                    source_url = href
                elif href.startswith("/"):
                    source_url = f"https://www.dubai.gov.ae{href}"

            desc_el = card.find("p")
            description = desc_el.get_text(strip=True) if desc_el else title

            # Extract dates
            deadline = ""
            date_texts = card.find_all(
                string=re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2}")
            )
            for dt_text in date_texts:
                date_match = re.search(
                    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})", dt_text
                )
                if date_match:
                    parsed = parse_date(date_match.group(1))
                    if parsed:
                        deadline = parsed
                        break

            ref = card.get("data-id", "") or title[:60]

            tender = {
                "id": generate_id("dubai_esupply", ref, ""),
                "source": "Dubai eSupply",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Government of Dubai",
                    "ar": "حكومة دبي",
                    "fr": "Gouvernement de Dubai",
                },
                "country": "UAE",
                "countryCode": "AE",
                "sector": classify_sector(title + " " + description),
                "budget": 0,
                "currency": "AED",
                "deadline": deadline,
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": description[:500],
                    "ar": description[:500],
                    "fr": description[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

        logger.info(f"Dubai Gov: {len(tenders)} tenders")

    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Dubai Gov: connection error — {e}")
    except Exception as e:
        logger.error(f"Dubai Gov: {e}")

    return tenders


def _scrape_dubai_sme(session: requests.Session) -> list[dict]:
    """Try to scrape Dubai SME tenders page as an additional source."""
    tenders: list[dict] = []

    try:
        resp = session.get(DUBAI_SME_URL, timeout=30, allow_redirects=True)

        if resp.status_code != 200:
            logger.info(f"Dubai SME: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender items
        items = (
            soup.select(".tender-item, .tender-card")
            or soup.select("table tbody tr")
            or soup.select(".ms-listviewtable tr")  # SharePoint list
        )

        for item in items:
            cells = item.find_all(["td", "div"])
            if len(cells) < 2:
                continue

            texts = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
            if not texts:
                continue

            title = max(texts, key=len) if texts else ""
            if len(title) < 10:
                continue

            ref = ""
            for t in texts:
                if re.match(r"^[A-Z0-9\-/]{3,25}$", t.strip()):
                    ref = t.strip()
                    break
            if not ref:
                ref = title[:60]

            link_el = item.find("a", href=True)
            source_url = DUBAI_SME_URL
            if link_el:
                href = link_el.get("href", "")
                if href.startswith("http"):
                    source_url = href
                elif href.startswith("/"):
                    source_url = f"https://www.sme.ae{href}"

            tender = {
                "id": generate_id("dubai_esupply", ref, ""),
                "source": "Dubai eSupply",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Dubai SME / Government of Dubai",
                    "ar": "مؤسسة محمد بن راشد لتنمية المشاريع الصغيرة والمتوسطة",
                    "fr": "Dubai SME / Gouvernement de Dubai",
                },
                "country": "UAE",
                "countryCode": "AE",
                "sector": classify_sector(title),
                "budget": 0,
                "currency": "AED",
                "deadline": "",
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": " ".join(texts)[:500],
                    "ar": " ".join(texts)[:500],
                    "fr": " ".join(texts)[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

        logger.info(f"Dubai SME: {len(tenders)} tenders")

    except Exception as e:
        logger.error(f"Dubai SME: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Dubai eSupply and related portals for government procurement."""
    session = _create_session()

    # Try the main eSupply portal first
    esupply_tenders = _scrape_esupply_portal(session)

    # Try Dubai Government page as fallback
    gov_tenders = _scrape_dubai_gov(session)

    # Try Dubai SME as additional source
    sme_tenders = _scrape_dubai_sme(session)

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []

    for t in esupply_tenders + gov_tenders + sme_tenders:
        key = t["sourceRef"] or t["title"]["en"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(
        f"Dubai eSupply total: {len(all_tenders)} tenders "
        f"(eSupply: {len(esupply_tenders)}, Gov: {len(gov_tenders)}, "
        f"SME: {len(sme_tenders)})"
    )

    if not all_tenders:
        logger.warning(
            "Dubai eSupply: No tenders retrieved. The portal likely requires "
            "authentication or uses JavaScript rendering. Consider using "
            "curl_cffi or a headless browser for full access."
        )

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "dubai_esupply")
    print(f"Scraped {len(results)} tenders from Dubai eSupply")
