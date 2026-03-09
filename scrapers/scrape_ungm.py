"""
Scraper for UNGM (United Nations Global Marketplace).
Source: https://www.ungm.org/Public/Notice
Scrapes the public HTML listing page (no API key needed).
"""

import requests
import logging
from bs4 import BeautifulSoup
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ungm")

UNGM_PUBLIC = "https://www.ungm.org/Public/Notice"

MENA_NAMES = set(MENA_COUNTRIES.values()) | {
    "Morocco", "Kingdom of Morocco", "Saudi Arabia", "United Arab Emirates",
    "Egypt", "Kuwait", "Qatar", "Bahrain", "Oman", "Jordan", "Tunisia",
    "Algeria", "Libya", "Iraq", "Lebanon", "Sudan", "Yemen", "Palestine",
    "Mauritania", "Middle East", "North Africa", "MENA",
}

NAME_TO_CODE: dict[str, str] = {}
for code, name in MENA_COUNTRIES.items():
    NAME_TO_CODE[name.lower()] = code


def get_country_code(text: str) -> tuple[str, str]:
    """Extract country code from text."""
    text_lower = text.lower()
    for code, name in MENA_COUNTRIES.items():
        if name.lower() in text_lower:
            return code, name
    if "middle east" in text_lower or "mena" in text_lower:
        return "XX", "MENA Region"
    return "XX", ""


def scrape() -> list[dict]:
    """Scrape UNGM public notices for MENA."""
    tenders = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en,ar,fr",
    })

    try:
        resp = session.get(UNGM_PUBLIC, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"UNGM public page returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Try various selectors for notice listings
        selectors = [
            "table tbody tr",
            ".dataTable tr",
            ".notice-item",
            ".list-group-item",
            ".search-result",
            "article",
            ".views-row",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows and len(rows) > 1:
                logger.info(f"UNGM: found {len(rows)} items with '{selector}'")
                for row in rows:
                    cells = row.select("td")
                    if cells and len(cells) >= 2:
                        texts = [c.get_text(strip=True) for c in cells]
                        title = texts[0] if texts else ""
                        if len(title) < 5:
                            title = " | ".join(t for t in texts[:4] if t)
                        if len(title) < 10:
                            continue
                    else:
                        title_el = row.select_one("a, h3, h4, .title")
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        if len(title) < 10:
                            continue
                        texts = [row.get_text(strip=True)]

                    full_text = " ".join(texts)
                    code, name = get_country_code(full_text)

                    # Get link
                    link = ""
                    a = row.select_one("a[href]")
                    if a:
                        href = a.get("href", "")
                        link = href if href.startswith("http") else f"https://www.ungm.org{href}"

                    # Extract agency name
                    agency = ""
                    if cells and len(cells) >= 3:
                        agency = cells[1].get_text(strip=True)

                    # Parse dates
                    pub_date = ""
                    deadline = ""
                    for text in texts:
                        d = parse_date(text)
                        if d:
                            if not pub_date:
                                pub_date = d
                            else:
                                deadline = d

                    tender = {
                        "id": generate_id("ungm", title[:80], code),
                        "source": "UNGM",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": agency or "United Nations",
                            "ar": agency or "الأمم المتحدة",
                            "fr": agency or "Nations Unies",
                        },
                        "country": name if name else "International",
                        "countryCode": code,
                        "sector": classify_sector(title),
                        "budget": 0,
                        "currency": "USD",
                        "deadline": deadline,
                        "publishDate": pub_date,
                        "status": "open",
                        "description": {"en": title, "ar": title, "fr": title},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": link,
                    }
                    tenders.append(tender)

                break  # Found working selector

    except Exception as e:
        logger.error(f"UNGM error: {e}")

    logger.info(f"UNGM total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ungm")
    print(f"Scraped {len(results)} tenders from UNGM")
