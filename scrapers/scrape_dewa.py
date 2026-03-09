"""
Scraper for Dubai Electricity and Water Authority (DEWA).
Source: https://www.dewa.gov.ae/en/supplier/services/list-of-tender-documents
Also:  https://www.dewa.gov.ae/en/supplier/main-services/open-tender

DEWA's website is behind Akamai CDN with bot protection (returns 403 for
automated requests). This scraper attempts multiple approaches and
falls back to a graceful empty result if blocked.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("dewa")

BASE_URL = "https://www.dewa.gov.ae"
TENDER_LIST_URL = f"{BASE_URL}/en/supplier/services/list-of-tender-documents"
OPEN_TENDER_URL = f"{BASE_URL}/en/supplier/main-services/open-tender"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def _try_scrape_page(url: str, label: str) -> list[dict]:
    """Attempt to scrape a DEWA tender page."""
    tenders: list[dict] = []

    try:
        session = requests.Session()
        resp = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)

        if resp.status_code == 403:
            logger.warning(f"DEWA {label}: Access denied (403). "
                           "Site uses Akamai bot protection.")
            return tenders

        if resp.status_code != 200:
            logger.warning(f"DEWA {label}: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender listing elements
        # DEWA typically uses cards or table rows for tender listings
        cards = soup.select(".tender-item, .tender-card, .card, "
                            "table tr, .list-item, article, "
                            "[class*='tender'], [class*='procurement']")

        for card in cards:
            title_el = card.select_one("h2, h3, h4, .title, a[href], td:nth-child(2)")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Get link
            link_el = card.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = BASE_URL + href

            card_text = card.get_text(" ", strip=True)

            # Find reference number
            ref_match = re.search(r'(?:Tender|Ref|No)[.\s:]*([A-Z0-9\-/]+)', card_text, re.I)
            ref = ref_match.group(1) if ref_match else title[:60]

            # Find dates
            date_matches = re.findall(
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', card_text
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

            tender = {
                "id": generate_id("dewa", ref, ""),
                "source": "DEWA",
                "sourceRef": ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Dubai Electricity and Water Authority (DEWA)",
                    "ar": "هيئة كهرباء ومياه دبي (ديوا)",
                    "fr": "Autorité de l'électricité et de l'eau de Dubaï (DEWA)",
                },
                "country": "UAE",
                "countryCode": "AE",
                "sector": classify_sector(title + " electricity water energy"),
                "budget": 0,
                "currency": "AED",
                "deadline": deadline,
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": card_text[:500],
                    "ar": card_text[:500],
                    "fr": card_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or url,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"DEWA {label} scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape DEWA tenders. May return empty if bot protection blocks access."""
    tenders_list = _try_scrape_page(TENDER_LIST_URL, "tender-list")
    time.sleep(2)
    tenders_open = _try_scrape_page(OPEN_TENDER_URL, "open-tender")

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in tenders_list + tenders_open:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"DEWA total: {len(all_tenders)} tenders "
                f"(list: {len(tenders_list)}, open: {len(tenders_open)})")

    if not all_tenders:
        logger.warning("DEWA: No tenders retrieved. The site uses Akamai CDN "
                        "bot protection that blocks automated requests. "
                        "Consider using a headless browser (Playwright/Selenium) "
                        "or the DEWA supplier portal API if available.")

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "dewa")
    print(f"Scraped {len(results)} tenders from DEWA")
