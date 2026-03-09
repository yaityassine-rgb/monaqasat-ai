"""
Scraper for QatarEnergy (formerly Qatar Petroleum).
Source: https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Pages/default.aspx

SharePoint-based portal. The tenders page uses SharePoint's CSOM/REST API
and client-side rendering. We try multiple approaches:
1. Direct HTML scraping of the tender listing page
2. SharePoint REST API for list items
3. SharePoint search API
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger("qatarenergy")

BASE_URL = "https://www.qatarenergy.qa"
TENDERS_URL = f"{BASE_URL}/en/SupplyManagement/Tenders/Pages/default.aspx"
SP_REST_BASE = f"{BASE_URL}/en/SupplyManagement/Tenders/_api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _scrape_html_page() -> list[dict]:
    """Scrape tenders from the QatarEnergy HTML page."""
    tenders: list[dict] = []

    try:
        resp = requests.get(TENDERS_URL, headers=HEADERS, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"QatarEnergy tenders page returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender listing items in the page
        # SharePoint renders content in web part zones
        content_area = soup.select_one("#DeltaPlaceHolderMain, "
                                       ".ms-rte-layoutszone-inner, "
                                       "[class*='WebPartZone']")
        if not content_area:
            content_area = soup

        # Look for tables, list items, or card structures
        rows = content_area.select("table tr, .ms-listviewtable tr, "
                                   "[class*='tender'], [class*='Tender'], "
                                   ".ms-vb2, li")

        for row in rows:
            text = row.get_text(" ", strip=True)
            if not text or len(text) < 20:
                continue

            # Skip navigation/menu items and generic labels
            if any(kw in text.lower() for kw in
                   ["home", "about", "contact", "login", "register",
                    "copyright", "terms", "privacy", "supply management",
                    "overview", "click here", "read more", "search"]):
                continue

            # Must have enough content to be a real tender
            if len(text) < 30:
                continue

            # Look for tender-like content
            if not any(kw in text.lower() for kw in
                       ["tender", "rfp", "rfq", "bid", "supply", "service",
                        "contract", "procurement", "work", "project",
                        "construction", "engineering"]):
                continue

            title = text[:200].strip()

            # Extract reference
            ref_match = re.search(r'([A-Z]{2,}-\d+[-/]?\d*|QE-\d+|QP-\d+)', text)
            ref = ref_match.group(1) if ref_match else title[:60]

            # Extract dates
            date_matches = re.findall(
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text
            )
            pub_date = ""
            deadline = ""
            for dm in date_matches:
                parsed = parse_date(dm)
                if parsed:
                    if not pub_date:
                        pub_date = parsed
                    else:
                        deadline = parsed

            # Get link
            link_el = row.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = BASE_URL + href

            tender = {
                "id": generate_id("qatarenergy", ref, ""),
                "source": "QatarEnergy",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "QatarEnergy",
                    "ar": "قطر للطاقة",
                    "fr": "QatarEnergy",
                },
                "country": "Qatar",
                "countryCode": "QA",
                "sector": classify_sector(title + " energy oil gas"),
                "budget": 0,
                "currency": "QAR",
                "deadline": deadline,
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": text[:500],
                    "ar": text[:500],
                    "fr": text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or TENDERS_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"QatarEnergy HTML scraper error: {e}")

    return tenders


def _try_sharepoint_api() -> list[dict]:
    """Try SharePoint REST API to get tender list items."""
    tenders: list[dict] = []

    # Common SharePoint list names for tenders
    list_names = ["Tenders", "Tender", "Current Tenders",
                  "CurrentTenders", "tender_list"]

    for list_name in list_names:
        try:
            api_url = (f"{SP_REST_BASE}/web/lists/GetByTitle('{list_name}')"
                       f"/items?$top=100&$orderby=Created desc")

            resp = requests.get(api_url, headers={
                **HEADERS,
                "Accept": "application/json;odata=verbose",
            }, timeout=15)

            if resp.status_code != 200:
                continue

            data = resp.json()
            results = data.get("d", {}).get("results", [])

            if not results:
                continue

            logger.info(f"QatarEnergy SharePoint API: Found {len(results)} items "
                        f"in list '{list_name}'")

            for item in results:
                title = item.get("Title", "")
                if not title:
                    continue

                item_id = str(item.get("Id", ""))
                description = item.get("Description", "") or title
                deadline = parse_date(item.get("ClosingDate", "")) or ""
                pub_date = parse_date(item.get("Created", "")) or ""
                ref = item.get("ReferenceNumber", "") or item_id

                tender = {
                    "id": generate_id("qatarenergy", ref, ""),
                    "source": "QatarEnergy",
                    "sourceRef": ref,
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "QatarEnergy",
                        "ar": "قطر للطاقة",
                        "fr": "QatarEnergy",
                    },
                    "country": "Qatar",
                    "countryCode": "QA",
                    "sector": classify_sector(title + " energy oil gas"),
                    "budget": 0,
                    "currency": "QAR",
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
                tenders.append(tender)

            break  # Found a working list

        except Exception as e:
            logger.debug(f"QatarEnergy SharePoint API list '{list_name}': {e}")
            continue

    return tenders


def _scrape_playwright() -> list[dict]:
    """Use Playwright to render QatarEnergy's SharePoint CSOM page."""
    tenders: list[dict] = []
    if not HAS_PLAYWRIGHT:
        logger.debug("QatarEnergy: Playwright not installed, skipping")
        return tenders

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
            })

            logger.info("QatarEnergy Playwright: loading tenders page...")
            page.goto(TENDERS_URL, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(8000)  # SharePoint CSOM needs time to render

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # The page renders a table with columns:
            # ID | Tender ID | Status | Title | Bond(QR) | BID Closing
            # Each data row has a link to the detail page
            rows = soup.select("table tr, .ms-listviewtable tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                texts = [c.get_text(strip=True) for c in cells]
                full_text = " ".join(texts)

                # Skip header rows
                if "tender id" in full_text.lower() or "status" == texts[0].lower():
                    continue

                # Extract tender ID (e.g., LT25106600, LT26MT0010)
                tender_id_match = re.search(r'(LT[A-Z0-9]+)', full_text)
                ref = tender_id_match.group(1) if tender_id_match else ""

                # Extract numeric ID for URL
                numeric_id = ""
                for t in texts:
                    if t.isdigit() and len(t) >= 4:
                        numeric_id = t
                        break

                # Extract title — the longest text cell that isn't a number/date
                title = ""
                for t in texts:
                    if (len(t) > len(title) and not t.isdigit()
                            and "tender" != t.lower() and "status" != t.lower()):
                        title = t

                if not title or len(title) < 10:
                    continue

                # Skip if title looks like a header
                if title.lower().startswith("id ") or "bond(qr)" in title.lower():
                    continue

                # Extract deadline from date-like text
                deadline = ""
                for t in texts:
                    d = parse_date(t)
                    if d:
                        deadline = d
                        break
                # Also check full text for dates like "30  March  2026"
                if not deadline:
                    date_match = re.search(
                        r'(\d{1,2}\s+\w+\s+\d{4})', full_text
                    )
                    if date_match:
                        deadline = parse_date(date_match.group(1)) or ""

                # Extract bond amount
                bond = 0
                for t in texts:
                    if t.isdigit() and 1000 <= int(t) <= 50000000:
                        bond = int(t)

                # Get link to detail page
                link_el = row.select_one("a[href]")
                href = ""
                if link_el:
                    href = link_el.get("href", "")
                    if href and not href.startswith("http"):
                        href = BASE_URL + href
                # Build detail URL from numeric ID if no link found
                if not href and numeric_id:
                    href = (f"{BASE_URL}/en/SupplyManagement/Tenders/Pages/"
                            f"ViewTenders.aspx?TenderId={numeric_id}"
                            f"&awdType=latesttenders")

                if not ref:
                    ref = numeric_id or title[:60]

                tender = {
                    "id": generate_id("qatarenergy", ref, ""),
                    "source": "QatarEnergy",
                    "sourceRef": ref,
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "QatarEnergy",
                        "ar": "قطر للطاقة",
                        "fr": "QatarEnergy",
                    },
                    "country": "Qatar",
                    "countryCode": "QA",
                    "sector": classify_sector(title + " energy oil gas"),
                    "budget": bond,
                    "currency": "QAR",
                    "deadline": deadline,
                    "publishDate": "",
                    "status": "open",
                    "description": {
                        "en": title,
                        "ar": title,
                        "fr": title,
                    },
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": href or TENDERS_URL,
                }
                tenders.append(tender)

            logger.info(f"QatarEnergy Playwright: {len(tenders)} tenders")
            browser.close()

    except Exception as e:
        logger.error(f"QatarEnergy Playwright error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape QatarEnergy tenders."""
    html_tenders = _scrape_html_page()
    time.sleep(2)
    api_tenders = _try_sharepoint_api()

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in html_tenders + api_tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"QatarEnergy total: {len(all_tenders)} tenders "
                f"(HTML: {len(html_tenders)}, API: {len(api_tenders)})")

    # If HTTP methods found nothing, try Playwright
    if not all_tenders:
        logger.info("QatarEnergy: HTTP methods found nothing, trying Playwright...")
        pw_tenders = _scrape_playwright()
        for t in pw_tenders:
            key = t["sourceRef"]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)

    if not all_tenders:
        logger.warning("QatarEnergy: No tenders found. The SharePoint-based portal "
                        "may require authentication or specific network access.")

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "qatarenergy")
    print(f"Scraped {len(results)} tenders from QatarEnergy")
