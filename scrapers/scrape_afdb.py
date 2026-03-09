"""
Scraper for African Development Bank (AfDB) Procurement.
Source: https://www.afdb.org/en/about-us/corporate-procurement/procurement-notices/current-solicitations
Covers North African MENA countries: Morocco, Tunisia, Algeria, Egypt, Libya, Mauritania.
"""

import requests
import logging
from bs4 import BeautifulSoup
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("afdb")

AFDB_URLS = [
    "https://www.afdb.org/en/about-us/corporate-procurement/procurement-notices/current-solicitations",
    "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices",
    "https://www.afdb.org/en/projects-and-operations/procurement",
]

NORTH_AFRICA = {"MA": "Morocco", "TN": "Tunisia", "DZ": "Algeria", "EG": "Egypt", "LY": "Libya", "MR": "Mauritania", "SD": "Sudan"}


def scrape() -> list[dict]:
    """Scrape AfDB procurement notices."""
    tenders = []

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en,fr",
    })

    for url in AFDB_URLS:
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"AfDB {url} returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Try various selectors
            selectors = [
                "table tbody tr",
                ".views-row",
                "article",
                ".node--type-procurement",
                ".procurement-notice",
                ".field-content",
                ".view-content .item-list li",
                ".list-group-item",
            ]

            for selector in selectors:
                items = soup.select(selector)
                if not items or len(items) < 2:
                    continue

                logger.info(f"AfDB: found {len(items)} items with '{selector}' on {url}")

                for item in items:
                    title_el = item.select_one("a, h2, h3, h4, .title, td:first-child")
                    if not title_el:
                        title_el = item
                    title = title_el.get_text(strip=True)
                    if len(title) < 10:
                        continue

                    link = ""
                    a_tag = item.select_one("a[href]")
                    if a_tag:
                        link = a_tag.get("href", "")
                        if link and not link.startswith("http"):
                            link = f"https://www.afdb.org{link}"

                    # Check if relates to North Africa
                    text = item.get_text()
                    country_code = "XX"
                    country_name = ""
                    for code, name in NORTH_AFRICA.items():
                        if name.lower() in text.lower():
                            country_code = code
                            country_name = name
                            break

                    if country_code == "XX":
                        country_name = "Africa"

                    # Extract date
                    date_el = item.select_one(".date, time, .datetime")
                    pub_date = ""
                    if date_el:
                        pub_date = parse_date(date_el.get_text(strip=True)) or ""

                    tender = {
                        "id": generate_id("afdb", title[:80], country_code),
                        "source": "AfDB",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": "African Development Bank",
                            "ar": "البنك الأفريقي للتنمية",
                            "fr": "Banque africaine de développement",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(title),
                        "budget": 0,
                        "currency": "USD",
                        "deadline": "",
                        "publishDate": pub_date,
                        "status": "open",
                        "description": {"en": title, "ar": title, "fr": title},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": link,
                    }
                    tenders.append(tender)

                if tenders:
                    break

            if tenders:
                break

        except Exception as e:
            logger.error(f"AfDB error on {url}: {e}")

    logger.info(f"AfDB total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "afdb")
    print(f"Scraped {len(results)} tenders from AfDB")
