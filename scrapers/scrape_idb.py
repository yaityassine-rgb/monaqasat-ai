"""
Scraper for Islamic Development Bank (IsDB) Procurement.
Source: https://www.isdb.org/project-procurement/tenders
The IsDB funds major projects across all OIC member states including MENA.
"""

import requests
import logging
from bs4 import BeautifulSoup
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("isdb")

ISDB_URLS = [
    "https://www.isdb.org/project-procurement/tenders",
    "https://www.isdb.org/project-procurement",
    "https://www.isdb.org/procurement",
]


def scrape() -> list[dict]:
    """Scrape IsDB procurement notices."""
    tenders = []

    for url in ISDB_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"IsDB {url} returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for procurement items with various selectors
            selectors = [
                ".views-row",
                ".node--type-tender",
                "article",
                ".procurement-item",
                ".tender-item",
                "table tbody tr",
                ".view-content .item-list li",
                ".field-content a",
            ]

            for selector in selectors:
                items = soup.select(selector)
                if not items or len(items) < 2:
                    continue

                logger.info(f"IsDB: found {len(items)} items with '{selector}' on {url}")

                for item in items:
                    title_el = item.select_one("a, h2, h3, h4, .title, .field--name-title, td:first-child")
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
                            link = f"https://www.isdb.org{link}"

                    # Try to identify country
                    text = item.get_text()
                    country_code = "XX"
                    country_name = ""
                    for code, name in MENA_COUNTRIES.items():
                        if name.lower() in text.lower():
                            country_code = code
                            country_name = name
                            break

                    if country_code == "XX":
                        country_name = "MENA Region"

                    # Extract date if present
                    date_el = item.select_one(".date, time, .field--name-field-date, .datetime")
                    pub_date = ""
                    if date_el:
                        pub_date = parse_date(date_el.get_text(strip=True)) or ""

                    tender = {
                        "id": generate_id("isdb", title[:80], ""),
                        "source": "IsDB",
                        "sourceLanguage": "en",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": "Islamic Development Bank",
                            "ar": "البنك الإسلامي للتنمية",
                            "fr": "Banque islamique de développement",
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
                    break  # Found working selector

            if tenders:
                break  # Found working URL

        except Exception as e:
            logger.error(f"IsDB error on {url}: {e}")

    logger.info(f"IsDB total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "isdb")
    print(f"Scraped {len(results)} tenders from IsDB")
