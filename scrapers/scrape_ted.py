"""
Scraper for TED (Tenders Electronic Daily) — EU procurement.
Source: https://ted.europa.eu
Covers EU-funded projects in MENA (especially Morocco, Tunisia, Algeria, Egypt, Jordan).
TED has a public API and open data.
"""

import requests
import logging
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ted")

# TED API v3
TED_API = "https://api.ted.europa.eu/v3/notices/search"

# TED uses ISO country codes
MENA_TED_COUNTRIES = ["MA", "TN", "DZ", "EG", "JO", "LB", "LY", "PS", "SA", "AE", "KW", "QA", "BH", "OM", "IQ"]


def scrape() -> list[dict]:
    """Scrape TED for MENA-related procurement notices."""
    tenders = []

    for country_code in MENA_TED_COUNTRIES:
        try:
            # TED API search
            params = {
                "q": f"TD=[3] AND CY=[{country_code}]",  # Type=Contract notice, Country
                "scope": 3,  # Active notices
                "pageSize": 50,
                "pageNum": 1,
                "sortField": "PD",  # Publication date
                "sortOrder": "desc",
            }

            resp = requests.get(TED_API, params=params, headers=HEADERS, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                notices = data.get("notices", data.get("results", []))

                for notice in notices:
                    if isinstance(notice, str):
                        continue

                    title = notice.get("title", notice.get("TI", ""))
                    if isinstance(title, dict):
                        title = title.get("EN", title.get("FR", str(title)))
                    if not title:
                        continue

                    org = notice.get("officialName", notice.get("AA", ""))
                    if isinstance(org, dict):
                        org = org.get("EN", org.get("FR", str(org)))

                    deadline_raw = notice.get("deadlineDate", notice.get("DT", ""))
                    publish_raw = notice.get("publicationDate", notice.get("PD", ""))
                    doc_id = notice.get("docId", notice.get("ND", ""))

                    country_name = MENA_COUNTRIES.get(country_code, "")

                    tender = {
                        "id": generate_id("ted", str(doc_id) or title[:100], country_code),
                        "source": "TED (EU)",
                        "title": {"en": str(title), "ar": str(title), "fr": str(title)},
                        "organization": {
                            "en": str(org) or f"EU-funded — {country_name}",
                            "ar": str(org) or f"ممول من الاتحاد الأوروبي — {country_name}",
                            "fr": str(org) or f"Financé par l'UE — {country_name}",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(str(title)),
                        "budget": 0,
                        "currency": "EUR",
                        "deadline": parse_date(str(deadline_raw)) or "",
                        "publishDate": parse_date(str(publish_raw)) or "",
                        "status": "open",
                        "description": {"en": str(title), "ar": str(title), "fr": str(title)},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": f"https://ted.europa.eu/en/notice/-/detail/{doc_id}" if doc_id else "",
                    }
                    tenders.append(tender)

                logger.info(f"TED {country_code}: found notices")
            else:
                logger.warning(f"TED API returned {resp.status_code} for {country_code}")

        except Exception as e:
            logger.error(f"TED error for {country_code}: {e}")
            continue

    logger.info(f"Total: {len(tenders)} tenders from TED")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ted")
    print(f"Scraped {len(results)} tenders from TED")
