"""
Scraper for African Development Bank (AfDB) Procurement.
Source: https://www.afdb.org/en/projects-and-operations/procurement
Covers North African MENA countries: Morocco, Tunisia, Algeria, Libya, Egypt, Mauritania.
"""

import requests
import logging
from bs4 import BeautifulSoup
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("afdb")

# AfDB API/listing
AFDB_URL = "https://www.afdb.org/en/projects-and-operations/procurement"
AFDB_API = "https://projectsportal.afdb.org/dataportal/api/procurement"

# North African countries covered by AfDB
NORTH_AFRICA = {"MA", "TN", "DZ", "LY", "EG", "MR", "SD"}


def scrape() -> list[dict]:
    """Scrape AfDB procurement for North African MENA countries."""
    tenders = []

    # Try AfDB data portal API
    try:
        for country_code in NORTH_AFRICA:
            country_name = MENA_COUNTRIES.get(country_code, "")
            if not country_name:
                continue

            params = {
                "country": country_name,
                "limit": 50,
                "offset": 0,
            }

            resp = requests.get(AFDB_API, params=params, headers=HEADERS, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get("results", data.get("data", []))

                for item in items:
                    if isinstance(item, str):
                        continue
                    title = item.get("title", item.get("description", ""))
                    if not title:
                        continue

                    org = item.get("agency", item.get("borrower", f"AfDB — {country_name}"))
                    deadline_raw = item.get("deadline", item.get("closing_date", ""))
                    publish_raw = item.get("published_date", item.get("approval_date", ""))

                    tender = {
                        "id": generate_id("afdb", title[:100], country_code),
                        "source": "AfDB",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": f"AfDB — {country_name}",
                            "ar": f"بنك التنمية الأفريقي — {country_name}",
                            "fr": f"BAD — {country_name}",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(title),
                        "budget": 0,
                        "currency": "USD",
                        "deadline": parse_date(str(deadline_raw)) or "",
                        "publishDate": parse_date(str(publish_raw)) or "",
                        "status": "open",
                        "description": {"en": title, "ar": title, "fr": title},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": item.get("url", ""),
                    }
                    tenders.append(tender)

                logger.info(f"AfDB API: {len(items)} items for {country_code}")
            else:
                logger.warning(f"AfDB API returned {resp.status_code} for {country_code}")

    except Exception as e:
        logger.error(f"AfDB API error: {e}")

    # Fallback: scrape the public listing page
    if not tenders:
        tenders = scrape_html_fallback()

    logger.info(f"Total: {len(tenders)} tenders from AfDB")
    return tenders


def scrape_html_fallback() -> list[dict]:
    """Fallback scraper using HTML parsing."""
    tenders = []

    try:
        resp = requests.get(AFDB_URL, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"AfDB HTML returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for procurement notice cards/listings
        for article in soup.select("article, .views-row, .procurement-item, .node--type-procurement"):
            title_el = article.select_one("h2 a, h3 a, .title a, .field--name-title a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.afdb.org{link}"

            # Try to find country
            country_el = article.select_one(".country, .field--name-field-country")
            country_text = country_el.get_text(strip=True) if country_el else ""

            country_code = "XX"
            for code, name in MENA_COUNTRIES.items():
                if name.lower() in (country_text + " " + title).lower():
                    country_code = code
                    break

            if country_code == "XX":
                continue

            tender = {
                "id": generate_id("afdb", title[:100], country_code),
                "source": "AfDB",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": f"AfDB — {MENA_COUNTRIES.get(country_code, '')}",
                    "ar": f"بنك التنمية الأفريقي",
                    "fr": f"BAD",
                },
                "country": MENA_COUNTRIES.get(country_code, ""),
                "countryCode": country_code,
                "sector": classify_sector(title),
                "budget": 0,
                "currency": "USD",
                "deadline": "",
                "publishDate": "",
                "status": "open",
                "description": {"en": title, "ar": title, "fr": title},
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": link,
            }
            tenders.append(tender)

        logger.info(f"AfDB HTML fallback: {len(tenders)} tenders")

    except Exception as e:
        logger.error(f"AfDB HTML error: {e}")

    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "afdb")
    print(f"Scraped {len(results)} tenders from AfDB")
