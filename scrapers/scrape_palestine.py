"""
Scraper for Palestine Shiraa Procurement Portal.
Source: https://www.shiraa.gov.ps/en-US/ProcurementList

DNN (DotNetNuke) platform with DevExpress grid controls.
The grid ID is dnn_ctr13023_ProcurementListForPublic_gvProcurementList
and renders data rows with class dxgvDataRow_Office2010Blue.

Columns (0-indexed):
  0: Procurement Entity
  1: Procurement Ref
  2: Description (Arabic)
  3: Type (Goods/Works/Services)
  4: Published Date (dd/mm/yyyy)
  5: Closing Date (dd/mm/yyyy HH:MM)
  6: Status
  7: Bid Type (Public Bid, etc.)
  8: Details link
"""

import logging
import re
import time
import urllib3
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

# Suppress SSL warnings - Palestinian gov site has certificate issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("palestine")

BASE_URL = "https://www.shiraa.gov.ps"
LIST_URL = f"{BASE_URL}/en-US/ProcurementList"

GRID_ID = "dnn_ctr13023_ProcurementListForPublic_gvProcurementList"


def _scrape_grid_page(url: str) -> list[dict]:
    """Scrape procurement listings from the Shiraa DevExpress grid."""
    tenders: list[dict] = []

    try:
        resp = requests.get(url, verify=False, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        }, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"Shiraa page returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Find the DevExpress GridView
        grid = soup.select_one(f"#{GRID_ID}")
        if not grid:
            # Try a broader selector
            grid = soup.select_one("[class*='dxgvControl']")

        if not grid:
            logger.warning("Shiraa: DevExpress grid not found in page")
            return tenders

        # Extract data rows (DevExpress uses class pattern dxgvDataRow*)
        data_rows = grid.select("tr[class*='dxgvDataRow']")
        logger.info(f"Shiraa: Found {len(data_rows)} data rows in grid")

        for row in data_rows:
            cells = row.select("td")
            if len(cells) < 7:
                continue

            texts = [c.get_text(strip=True) for c in cells]

            # Column mapping
            org_name = texts[0] if len(texts) > 0 else ""
            proc_ref = texts[1] if len(texts) > 1 else ""
            description = texts[2] if len(texts) > 2 else ""
            proc_type = texts[3] if len(texts) > 3 else ""
            pub_date_str = texts[4] if len(texts) > 4 else ""
            close_date_str = texts[5] if len(texts) > 5 else ""
            status_text = texts[6] if len(texts) > 6 else ""
            bid_type = texts[7] if len(texts) > 7 else ""

            if not description or len(description) < 5:
                continue

            # Parse dates (format: dd/mm/yyyy or dd/mm/yyyy HH:MM)
            pub_date = parse_date(pub_date_str.split()[0]) if pub_date_str else ""
            deadline = parse_date(close_date_str.split()[0]) if close_date_str else ""

            # Get the detail link
            link_el = row.select_one("a[href*='ProcurementView'], a[href*='refID']")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = BASE_URL + href
                # Ensure HTTPS
                href = href.replace("http://", "https://")
            else:
                # Try to find any link
                any_link = row.select_one("a[href]")
                if any_link:
                    href = any_link.get("href", "")
                    if href and not href.startswith("http"):
                        href = BASE_URL + href
                    href = href.replace("http://", "https://")

            # Also try extracting refID from links
            ref_id = ""
            if href:
                ref_match = re.search(r'refID=(\d+)', href)
                if ref_match:
                    ref_id = ref_match.group(1)

            source_ref = ref_id or proc_ref or description[:60]

            # Map status
            status = "open"
            status_lower = status_text.lower()
            if "award" in status_lower or "closed" in status_lower:
                status = "closed"
            elif "cancel" in status_lower:
                status = "closed"

            # Build title from description and ref
            title = description
            if proc_ref and proc_ref not in description:
                title = f"{proc_ref} - {description}"

            tender = {
                "id": generate_id("shiraa", source_ref, ""),
                "source": "Palestine Shiraa",
                "sourceRef": source_ref,
                "sourceLanguage": "ar",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": org_name or "Palestinian Authority",
                    "ar": org_name or "السلطة الوطنية الفلسطينية",
                    "fr": org_name or "Autorité palestinienne",
                },
                "country": "Palestine",
                "countryCode": "PS",
                "sector": classify_sector(
                    description + " " + proc_type + " " + org_name
                ),
                "budget": 0,
                "currency": "USD",
                "deadline": deadline or "",
                "publishDate": pub_date or "",
                "status": status,
                "description": {
                    "en": f"{proc_type}: {description} ({bid_type})",
                    "ar": f"{proc_type}: {description} ({bid_type})",
                    "fr": f"{proc_type}: {description} ({bid_type})",
                },
                "requirements": [bid_type] if bid_type else [],
                "matchScore": 0,
                "sourceUrl": href or url,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"Shiraa scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Palestine Shiraa procurement portal."""
    tenders = _scrape_grid_page(LIST_URL)

    # Filter to only open/active tenders
    open_tenders = [t for t in tenders if t["status"] == "open"]

    logger.info(f"Palestine Shiraa total: {len(tenders)} "
                f"(open: {len(open_tenders)}, all: {len(tenders)})")

    # Return all tenders (including awarded for historical reference)
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "palestine_shiraa")
    print(f"Scraped {len(results)} tenders from Palestine Shiraa")
