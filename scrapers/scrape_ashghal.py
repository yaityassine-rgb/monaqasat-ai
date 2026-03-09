"""
Scraper for Qatar Public Works Authority (Ashghal).
Source: https://www.ashghal.gov.qa/en/Tenders/pages/erptenders.aspx

SharePoint-based portal with ASP.NET WebForms. The tender listing is rendered
server-side. We scrape the General Tenders page which includes Open, Closed,
and Archived tender tabs with rendered HTML tables. We also try the
DetailedTenderListPage which lists open tenders directly.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ashghal")

BASE_URL = "https://www.ashghal.gov.qa"
TENDER_DEFAULT_URL = f"{BASE_URL}/en/Tenders/Pages/Tenderdefault.aspx"
OPEN_TENDERS_URL = f"{BASE_URL}/en/Tenders/pages/DetailedTenderListPage.aspx?Status=Open"
ERP_TENDERS_URL = f"{BASE_URL}/en/Tenders/pages/erptenders.aspx"


def _scrape_tender_page(url: str, label: str) -> list[dict]:
    """Scrape tenders from a SharePoint tender listing page."""
    tenders: list[dict] = []

    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"Ashghal {label} returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Find tender rows - Ashghal renders tenders in repeated div/table patterns
        # Each tender has: Tender No, Type (GTC/STC), Description, Eligibility,
        # Published Date, Closing Date, Category

        # Look for data rows that contain tender reference patterns like PWA/GTC/xxx
        # These are rendered inside GridView controls
        rows = soup.select("[class*='Row'], [class*='row']")
        tender_divs = []

        for row in rows:
            text = row.get_text(" ", strip=True)
            # Match Ashghal tender reference patterns
            if re.search(r'PWA/(?:GTC|STC)/\d+', text):
                tender_divs.append(row)

        # Also look for links to individual tender pages
        tender_links = soup.select("a[href*='TenderId='], a[href*='TenderID='], "
                                   "a[href*='Tenderdefault.aspx?TenderID']")

        for link in tender_links:
            href = link.get("href", "")
            if not href:
                continue
            if not href.startswith("http"):
                href = BASE_URL + href

            # Get the tender reference from the link text
            ref_text = link.get_text(strip=True)
            if not ref_text or len(ref_text) < 5:
                continue

            # Walk up to find the parent container with all tender data
            parent = link.find_parent("div") or link.find_parent("tr")
            if not parent:
                continue

            full_text = parent.get_text(" ", strip=True)

            # Extract tender reference
            ref_match = re.search(r'(PWA/(?:GTC|STC)/\d+/[\d\-]+(?:/[A-Z/]*)?)', full_text)
            source_ref = ref_match.group(1) if ref_match else ref_text

            # Extract type
            tender_type = ""
            if "GTC" in full_text:
                tender_type = "GTC"
            elif "STC" in full_text:
                tender_type = "STC"

            # Extract description - look for the longer text that describes the tender
            # It's usually in a specific cell/span
            desc_spans = parent.select("span, div")
            description = ""
            for span in desc_spans:
                span_text = span.get_text(strip=True)
                if len(span_text) > len(description) and len(span_text) > 20:
                    # Skip if it's a date or short label
                    if not re.match(r'^\d{1,2}\s+\w+\s+\d{4}$', span_text):
                        description = span_text

            if not description:
                description = full_text[:300]

            # Extract dates
            date_matches = re.findall(r'(\d{1,2}\s+\w+\s+\d{4})', full_text)
            pub_date = ""
            deadline = ""
            for dm in date_matches:
                parsed = parse_date(dm)
                if parsed:
                    if not pub_date:
                        pub_date = parsed
                    else:
                        deadline = parsed

            # Extract category
            category = ""
            categories = ["Roads", "Drainage", "Building", "Consultancy",
                          "Procurement", "ICT", "General Services"]
            for cat in categories:
                if cat in full_text:
                    category = cat
                    break

            tender = {
                "id": generate_id("ashghal", source_ref, ""),
                "source": "Ashghal",
                "sourceRef": source_ref,
                "sourceLanguage": "en",
                "title": {
                    "en": f"{source_ref} - {description[:100]}",
                    "ar": f"{source_ref} - {description[:100]}",
                    "fr": f"{source_ref} - {description[:100]}",
                },
                "organization": {
                    "en": "Public Works Authority (Ashghal)",
                    "ar": "هيئة الأشغال العامة (أشغال)",
                    "fr": "Autorité des travaux publics (Ashghal)",
                },
                "country": "Qatar",
                "countryCode": "QA",
                "sector": classify_sector(
                    description + " " + category + " construction infrastructure"
                ),
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
                "requirements": [f"Tender Type: {tender_type}"] if tender_type else [],
                "matchScore": 0,
                "sourceUrl": href,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"Ashghal {label} scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Ashghal (Qatar Public Works Authority) tenders."""
    # Try multiple pages
    tenders_default = _scrape_tender_page(TENDER_DEFAULT_URL, "default")
    time.sleep(2)
    tenders_open = _scrape_tender_page(OPEN_TENDERS_URL, "open")
    time.sleep(2)
    tenders_erp = _scrape_tender_page(ERP_TENDERS_URL, "erp")

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in tenders_default + tenders_open + tenders_erp:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"Ashghal total: {len(all_tenders)} tenders "
                f"(default: {len(tenders_default)}, "
                f"open: {len(tenders_open)}, erp: {len(tenders_erp)})")

    if not all_tenders:
        logger.warning("Ashghal: No tenders found. The SharePoint-based e-Tender "
                        "pages may load data via client-side JavaScript or require "
                        "authentication. Current open tenders show 0 in the page. "
                        "Consider using a headless browser or monitoring the page.")

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ashghal")
    print(f"Scraped {len(results)} tenders from Ashghal")
