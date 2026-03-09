"""
Scraper for Libya National Oil Corporation (NOC) Tenders.
Source: https://noc.ly/en/tenders/

WordPress site with a structured HTML table listing tenders.
Table columns: (icon) | Title | Expiry date | Details (View link)
Each tender links to a detail page like:
  https://noc.ly/en/tenders/<tender-slug>/
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("libya_noc")

BASE_URL = "https://noc.ly"
TENDERS_URL = f"{BASE_URL}/en/tenders/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en,ar",
}


def _extract_org_and_ref(title: str) -> tuple[str, str]:
    """Extract organization name and tender reference from the title.

    Titles follow patterns like:
      'Sarir Oil Operations Company ... Tender No. LVTC-OPMT-2026-002'
      'Mellitah Oil & Gas B.V.-Libya ... Tender No PRQ-173-FEL-26'
    """
    org = ""
    ref = ""

    # Extract organization (text before first ... or Tender No)
    org_match = re.match(
        r"^(.*?)(?:\s*[…\.]{2,}|\s*Tender\s*No)", title, re.IGNORECASE
    )
    if org_match:
        org = org_match.group(1).strip().rstrip(".-,")

    # Extract reference number
    ref_match = re.search(
        r"(?:Tender\s*No\.?\s*|Ref\.?\s*|CFT/)([\w\-/]+)", title, re.IGNORECASE
    )
    if ref_match:
        ref = ref_match.group(1).strip() if "CFT/" not in ref_match.group(0) else f"CFT/{ref_match.group(1).strip()}"
    elif "/" in title:
        # Try to find patterns like CFT/LOG/614/2024/AJF
        slash_match = re.search(r"([A-Z]{2,}/[\w/\-]+)", title)
        if slash_match:
            ref = slash_match.group(1)

    return org, ref


def _scrape_page(url: str) -> tuple[list[dict], str]:
    """Scrape a single page of tenders. Returns (tenders, next_page_url)."""
    tenders = []
    next_url = ""

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Libya NOC page returned {resp.status_code}: {url}")
            return tenders, next_url

        soup = BeautifulSoup(resp.text, "lxml")

        # Find the first table (the main listing table)
        # Structure: Row 0 = headers (Title | Expiry date | Details)
        # Row 1+ = data rows
        table = soup.select_one("table")
        if not table:
            logger.warning("Libya NOC: No table found on page")
            return tenders, next_url

        rows = table.select("tr")
        for row in rows[1:]:  # Skip header row
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # Cell 0: icon/empty, Cell 1: Title, Cell 2: Expiry date, Cell 3: Details link
            title_cell = cells[1] if len(cells) >= 4 else cells[0]
            date_cell = cells[2] if len(cells) >= 4 else cells[1]
            link_cell = cells[3] if len(cells) >= 4 else cells[2]

            # Clean title - remove "Title:" prefix from responsive labels
            title = title_cell.get_text(strip=True)
            title = re.sub(r"^Title:\s*", "", title)
            if not title or len(title) < 5:
                continue

            # Get expiry date
            date_text = date_cell.get_text(strip=True)
            date_text = re.sub(r"^Expiry date:\s*", "", date_text)
            deadline = parse_date(date_text) or ""

            # Get detail link
            link_a = link_cell.select_one("a[href]")
            source_url = ""
            if link_a:
                href = link_a.get("href", "")
                source_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            # Extract org and reference from title
            org, ref = _extract_org_and_ref(title)
            if not ref:
                ref = title[:80]

            tender = {
                "id": generate_id("libya_noc", ref, ""),
                "source": "Libya NOC",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": org or "National Oil Corporation - Libya",
                    "ar": org or "المؤسسة الوطنية للنفط - ليبيا",
                    "fr": org or "National Oil Corporation - Libye",
                },
                "country": "Libya",
                "countryCode": "LY",
                "sector": classify_sector(title + " oil gas energy petroleum"),
                "budget": 0,
                "currency": "LYD",
                "deadline": deadline,
                "publishDate": "",
                "status": "open",
                "description": {"en": title, "ar": title, "fr": title},
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url or TENDERS_URL,
            }
            tenders.append(tender)

        # Check for pagination (next page link)
        pagination = soup.select("a.next, a.page-numbers.next, .nav-next a")
        if pagination:
            next_href = pagination[0].get("href", "")
            if next_href:
                next_url = (
                    next_href
                    if next_href.startswith("http")
                    else f"{BASE_URL}{next_href}"
                )

    except Exception as e:
        logger.error(f"Libya NOC page scrape error: {e}")

    return tenders, next_url


def scrape() -> list[dict]:
    """Scrape Libya NOC tenders from all pages."""
    all_tenders: list[dict] = []
    seen: set[str] = set()
    url = TENDERS_URL
    max_pages = 10

    for page_num in range(1, max_pages + 1):
        if not url:
            break

        logger.info(f"Libya NOC: Scraping page {page_num}: {url}")
        tenders, next_url = _scrape_page(url)

        for t in tenders:
            key = t.get("sourceRef", "") or t["title"]["en"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)

        if not tenders or not next_url:
            break

        url = next_url
        time.sleep(2)

    logger.info(f"Libya NOC total: {len(all_tenders)}")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "libya_noc")
    print(f"Scraped {len(results)} tenders from Libya NOC")
