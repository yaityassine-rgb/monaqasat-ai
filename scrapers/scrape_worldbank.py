"""
Scraper for World Bank Procurement.
Source: https://projects.worldbank.org/en/projects-operations/procurement
The World Bank has a public API for procurement notices.
"""

import requests
import logging
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("worldbank")

# World Bank API for procurement
API_BASE = "https://search.worldbank.org/api/v2/procnotices"

# World Bank country codes for MENA
WB_COUNTRY_MAP = {
    "MA": "Morocco",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "EG": "Egypt, Arab Rep.",
    "KW": "Kuwait",
    "QA": "Qatar",
    "BH": "Bahrain",
    "OM": "Oman",
    "JO": "Jordan",
    "TN": "Tunisia",
    "DZ": "Algeria",
    "LY": "Libya",
    "IQ": "Iraq",
    "LB": "Lebanon",
    "YE": "Yemen, Rep.",
    "SD": "Sudan",
    "MR": "Mauritania",
}


def scrape() -> list[dict]:
    """Scrape World Bank procurement notices for MENA."""
    tenders = []

    # Query for each MENA country
    mena_codes = list(WB_COUNTRY_MAP.keys())

    for country_code in mena_codes:
        try:
            params = {
                "format": "json",
                "countrycode": country_code,
                "rows": 50,
                "os": 0,
                "srt": "new",  # Sort by newest
            }

            resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=30)

            if resp.status_code != 200:
                logger.warning(f"World Bank API returned {resp.status_code} for {country_code}")
                continue

            data = resp.json()
            notices = data.get("procnotices", {})

            if isinstance(notices, dict):
                notice_list = list(notices.values()) if notices else []
            elif isinstance(notices, list):
                notice_list = notices
            else:
                continue

            for notice in notice_list:
                if isinstance(notice, str):
                    continue

                title = notice.get("notice_text", notice.get("project_name", ""))
                if not title:
                    continue

                org = notice.get("bid_description", notice.get("borrower", ""))
                project_name = notice.get("project_name", "")
                deadline_raw = notice.get("submission_date", notice.get("deadline_date", ""))
                publish_raw = notice.get("notice_posted_date", notice.get("noticedate", ""))
                notice_type = notice.get("notice_type", "")
                procurement_method = notice.get("procurement_method", "")

                description = f"{project_name}. {notice_type}. {procurement_method}. {org}".strip(". ")
                country_name = WB_COUNTRY_MAP.get(country_code, MENA_COUNTRIES.get(country_code, ""))

                tender = {
                    "id": generate_id("wb", title[:100], country_code),
                    "source": "World Bank",
                    "title": {"en": title[:200], "ar": title[:200], "fr": title[:200]},
                    "organization": {
                        "en": f"World Bank — {country_name}",
                        "ar": f"البنك الدولي — {country_name}",
                        "fr": f"Banque mondiale — {country_name}",
                    },
                    "country": MENA_COUNTRIES.get(country_code, country_name),
                    "countryCode": country_code,
                    "sector": classify_sector(title + " " + description),
                    "budget": 0,
                    "currency": "USD",
                    "deadline": parse_date(str(deadline_raw)) or "",
                    "publishDate": parse_date(str(publish_raw)) or "",
                    "status": "open",
                    "description": {"en": description, "ar": description, "fr": description},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": notice.get("url", notice.get("notice_url", "")),
                }
                tenders.append(tender)

            logger.info(f"Found {len(notice_list)} notices for {country_code}")

        except Exception as e:
            logger.error(f"World Bank error for {country_code}: {e}")
            continue

    logger.info(f"Total: {len(tenders)} MENA tenders from World Bank")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "worldbank")
    print(f"Scraped {len(results)} tenders from World Bank")
