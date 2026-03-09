"""
Scraper for Suez Canal Authority (SCA) Tenders.
Source: https://www.suezcanal.gov.eg/English/Services/Pages/Tenders.aspx

SharePoint-based site. The tender listing is loaded via an Angular/SPA app
behind the URLs:
  - /English/Services/Pages/Services.aspx#/BidSupplierSubscription
  - /English/Services/Pages/Services.aspx#/SupplierTenderList

Strategy:
  1. Try to find a SharePoint REST API endpoint (_api/web/lists)
  2. Try the Angular SPA API endpoints for tender data
  3. Fall back to HTML scraping of the static page
  4. Also check the Arabic version for additional content
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("suez")

BASE_URL = "https://www.suezcanal.gov.eg"
TENDERS_URL_EN = f"{BASE_URL}/English/Services/Pages/Tenders.aspx"
TENDERS_URL_AR = f"{BASE_URL}/Arabic/Services/Pages/Tenders.aspx"
SERVICES_URL = f"{BASE_URL}/English/Services/Pages/Services.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json",
    "Accept-Language": "en,ar",
}


def _scrape_sharepoint_api() -> list[dict]:
    """Try SharePoint REST API endpoints for tender data."""
    tenders = []

    api_endpoints = [
        f"{BASE_URL}/_api/web/lists/getbytitle('Tenders')/items",
        f"{BASE_URL}/_api/web/lists/getbytitle('Bids')/items",
        f"{BASE_URL}/English/_api/web/lists/getbytitle('Tenders')/items",
        f"{BASE_URL}/_api/web/lists/getbytitle('Tender')/items",
        f"{BASE_URL}/_api/web/lists/getbytitle('Bid')/items",
        f"{BASE_URL}/_vti_bin/listdata.svc/Tenders",
        f"{BASE_URL}/_vti_bin/listdata.svc/Bids",
    ]

    session = requests.Session()
    session.headers.update(HEADERS)

    for endpoint in api_endpoints:
        try:
            resp = session.get(
                endpoint,
                headers={
                    "Accept": "application/json;odata=verbose",
                    "Content-Type": "application/json;odata=verbose",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = (
                        data.get("d", {}).get("results", [])
                        or data.get("value", [])
                        or data.get("d", [])
                    )
                    if isinstance(items, list) and items:
                        logger.info(
                            f"Suez SP API: {len(items)} items from {endpoint}"
                        )
                        for item in items:
                            title = (
                                item.get("Title", "")
                                or item.get("Name", "")
                                or item.get("TenderName", "")
                            )
                            if not title or len(title) < 5:
                                continue

                            ref = str(
                                item.get("Id", "")
                                or item.get("TenderNo", "")
                                or item.get("BidNo", "")
                            )
                            link = item.get("Url", "") or item.get("FileRef", "")
                            if link and not link.startswith("http"):
                                link = f"{BASE_URL}{link}"

                            pub_date = parse_date(
                                item.get("Created", "")
                                or item.get("PublishDate", "")
                            ) or ""
                            deadline = parse_date(
                                item.get("ClosingDate", "")
                                or item.get("Deadline", "")
                                or item.get("ExpiryDate", "")
                            ) or ""

                            desc = (
                                item.get("Description", "")
                                or item.get("Body", "")
                                or title
                            )

                            tender = {
                                "id": generate_id("suez", ref or title[:60], ""),
                                "source": "Suez Canal Authority",
                                "sourceRef": ref,
                                "sourceLanguage": "en",
                                "title": {
                                    "en": title,
                                    "ar": title,
                                    "fr": title,
                                },
                                "organization": {
                                    "en": "Suez Canal Authority",
                                    "ar": "هيئة قناة السويس",
                                    "fr": "Autorité du Canal de Suez",
                                },
                                "country": "Egypt",
                                "countryCode": "EG",
                                "sector": classify_sector(
                                    title + " " + desc + " port maritime canal"
                                ),
                                "budget": 0,
                                "currency": "EGP",
                                "deadline": deadline,
                                "publishDate": pub_date,
                                "status": "open",
                                "description": {
                                    "en": desc,
                                    "ar": desc,
                                    "fr": desc,
                                },
                                "requirements": [],
                                "matchScore": 0,
                                "sourceUrl": link or TENDERS_URL_EN,
                            }
                            tenders.append(tender)
                        return tenders
                except (ValueError, KeyError):
                    pass
        except Exception as e:
            logger.debug(f"Suez SP API {endpoint}: {e}")

    return tenders


def _scrape_html(url: str, lang: str = "en") -> list[dict]:
    """Scrape tenders from the HTML page."""
    tenders = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Suez Canal page returned {resp.status_code}: {url}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender content in various SharePoint structures
        for selector in [
            ".ms-listviewtable tr",
            ".ms-webpart-zone table tr",
            ".ms-vb2",
            ".ms-rtestate-field table tr",
            "table.ms-listviewtable tr",
            "#WebPartWPQ2 tr",
            ".list-item",
            ".tender-item",
            ".row .col",
            "table tbody tr",
            ".ms-webpart-chrome--title",
        ]:
            items = soup.select(selector)
            if not items:
                continue

            for item in items:
                cells = item.find_all(["td", "div", "span"])
                if not cells:
                    continue

                texts = [c.get_text(strip=True) for c in cells if c.get_text(strip=True)]
                full_text = " ".join(texts)

                if len(full_text) < 10:
                    continue

                # Skip navigation/header rows
                if any(
                    kw in full_text.lower()
                    for kw in [
                        "home",
                        "about",
                        "contact",
                        "navigation",
                        "copyright",
                        "footer",
                    ]
                ):
                    continue

                title = texts[0] if texts else ""
                if len(title) < 5:
                    title = full_text[:200]
                if len(title) < 5:
                    continue

                # Get link
                link = ""
                a = item.select_one("a[href]")
                if a:
                    href = a.get("href", "")
                    if href and not href.startswith("javascript"):
                        link = (
                            href
                            if href.startswith("http")
                            else f"{BASE_URL}{href}"
                        )

                # Extract dates
                dates = re.findall(r"(\d{2}/\d{2}/\d{4})", full_text)
                pub_date = parse_date(dates[0]) if dates else ""
                deadline = parse_date(dates[1]) if len(dates) > 1 else ""

                ref_match = re.search(r"(?:No\.?|Ref\.?|#)\s*([\w\-/]+)", full_text)
                ref = ref_match.group(1) if ref_match else title[:60]

                tender = {
                    "id": generate_id("suez", ref, ""),
                    "source": "Suez Canal Authority",
                    "sourceRef": ref,
                    "sourceLanguage": lang,
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "Suez Canal Authority",
                        "ar": "هيئة قناة السويس",
                        "fr": "Autorité du Canal de Suez",
                    },
                    "country": "Egypt",
                    "countryCode": "EG",
                    "sector": classify_sector(
                        title + " port maritime canal transport"
                    ),
                    "budget": 0,
                    "currency": "EGP",
                    "deadline": deadline,
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {"en": title, "ar": title, "fr": title},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link or url,
                }
                tenders.append(tender)

            if tenders:
                break

    except Exception as e:
        logger.error(f"Suez Canal HTML scrape error ({url}): {e}")

    return tenders


def _scrape_angular_api() -> list[dict]:
    """Try to access the Angular SPA API endpoints."""
    tenders = []

    # The SCA site uses Angular with hash routing.
    # Try common API patterns for the tender list.
    api_guesses = [
        f"{BASE_URL}/api/tenders",
        f"{BASE_URL}/api/bids",
        f"{BASE_URL}/English/Services/_api/items",
        f"{BASE_URL}/api/v1/tenders",
        f"{BASE_URL}/English/api/tenders",
    ]

    for endpoint in api_guesses:
        try:
            resp = requests.get(
                endpoint,
                headers={
                    **HEADERS,
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = (
                        data
                        if isinstance(data, list)
                        else data.get("items", data.get("results", data.get("data", [])))
                    )
                    if isinstance(items, list) and items:
                        logger.info(
                            f"Suez Angular API: {len(items)} items from {endpoint}"
                        )
                        for item in items:
                            title = item.get("title", "") or item.get("name", "")
                            if not title or len(title) < 5:
                                continue

                            ref = str(
                                item.get("id", "") or item.get("ref", "")
                            )
                            link = item.get("url", item.get("link", ""))
                            if link and not link.startswith("http"):
                                link = f"{BASE_URL}{link}"

                            tender = {
                                "id": generate_id("suez_api", ref or title[:60], ""),
                                "source": "Suez Canal Authority",
                                "sourceRef": ref,
                                "sourceLanguage": "en",
                                "title": {
                                    "en": title,
                                    "ar": title,
                                    "fr": title,
                                },
                                "organization": {
                                    "en": "Suez Canal Authority",
                                    "ar": "هيئة قناة السويس",
                                    "fr": "Autorité du Canal de Suez",
                                },
                                "country": "Egypt",
                                "countryCode": "EG",
                                "sector": classify_sector(
                                    title + " port maritime canal"
                                ),
                                "budget": 0,
                                "currency": "EGP",
                                "deadline": "",
                                "publishDate": "",
                                "status": "open",
                                "description": {
                                    "en": title,
                                    "ar": title,
                                    "fr": title,
                                },
                                "requirements": [],
                                "matchScore": 0,
                                "sourceUrl": link or TENDERS_URL_EN,
                            }
                            tenders.append(tender)
                        return tenders
                except (ValueError, KeyError):
                    pass
        except Exception:
            pass

    return tenders


def scrape() -> list[dict]:
    """Scrape Suez Canal Authority tenders."""
    all_tenders: list[dict] = []
    seen: set[str] = set()

    for method_name, method in [
        ("SharePoint API", _scrape_sharepoint_api),
        ("Angular API", _scrape_angular_api),
        ("HTML (EN)", lambda: _scrape_html(TENDERS_URL_EN, "en")),
        ("HTML (AR)", lambda: _scrape_html(TENDERS_URL_AR, "ar")),
    ]:
        try:
            results = method()
            logger.info(f"Suez {method_name}: {len(results)} tenders")
            for t in results:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
        except Exception as e:
            logger.error(f"Suez {method_name} failed: {e}")

        time.sleep(2)

    if not all_tenders:
        logger.warning(
            "Suez Canal: No tenders found. The site uses an Angular SPA "
            "with SharePoint backend. Tenders are loaded dynamically and "
            "may require authentication via the BidSupplierSubscription "
            "portal. URL: %s#/SupplierTenderList",
            SERVICES_URL,
        )

    logger.info(f"Suez Canal total: {len(all_tenders)}")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "suez_canal")
    print(f"Scraped {len(results)} tenders from Suez Canal Authority")
