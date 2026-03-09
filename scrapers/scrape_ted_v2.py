"""
Scraper for TED (Tenders Electronic Daily) — EU procurement.
Uses the TED Europa API v3 POST endpoint.
Covers EU-funded projects relevant to MENA countries.
"""

import requests
import logging
import time
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, save_tenders

logger = logging.getLogger("ted")

# TED API v3 endpoint (POST only, GET returns 405)
TED_SEARCH = "https://api.ted.europa.eu/v3/notices/search"

# MENA countries using ISO 3166 three-letter codes
MENA_TED_3 = {
    "MAR": "MA", "TUN": "TN", "DZA": "DZ", "EGY": "EG",
    "JOR": "JO", "LBN": "LB", "SAU": "SA", "ARE": "AE",
    "KWT": "KW", "QAT": "QA", "BHR": "BH", "OMN": "OM",
    "IRQ": "IQ", "LBY": "LY",
}


def scrape() -> list[dict]:
    """Scrape TED for MENA procurement notices using POST API."""
    tenders = []

    for ted_code, iso2 in MENA_TED_3.items():
        page = 1
        total_for_country = 0

        while page <= 5:  # Max 5 pages per country (500 notices)
            try:
                # TED API v3 requires POST with specific format:
                # - query uses expert search syntax: CY=MAR
                # - fields array is REQUIRED (must include at least one BT code)
                payload = {
                    "query": f"CY={ted_code}",
                    "fields": ["BT-01-notice"],
                    "page": page,
                    "limit": 100,
                }

                resp = requests.post(
                    TED_SEARCH,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    timeout=30,
                )

                if resp.status_code != 200:
                    logger.warning(f"TED {ted_code} page {page}: {resp.status_code}")
                    break

                data = resp.json()
                notices = data.get("notices", [])
                total = data.get("totalNoticeCount", 0)

                if not notices:
                    break

                for notice in notices:
                    if not isinstance(notice, dict):
                        continue

                    pub_number = notice.get("publication-number", "")
                    if not pub_number:
                        continue

                    country_name = MENA_COUNTRIES.get(iso2, "")

                    # TED API returns minimal data per notice (pub number + links)
                    # We create entries with the publication number as identifier
                    tender = {
                        "id": generate_id("ted", pub_number, iso2),
                        "source": "TED (EU)",
                        "sourceRef": pub_number,
                        "title": {
                            "en": f"TED Notice {pub_number} — {country_name}",
                            "ar": f"إشعار TED {pub_number} — {country_name}",
                            "fr": f"Avis TED {pub_number} — {country_name}",
                        },
                        "organization": {
                            "en": f"EU-funded — {country_name}",
                            "ar": f"ممول من الاتحاد الأوروبي — {country_name}",
                            "fr": f"Financé par l'UE — {country_name}",
                        },
                        "country": country_name,
                        "countryCode": iso2,
                        "sector": "it",  # Default; would need XML parsing for detail
                        "budget": 0,
                        "currency": "EUR",
                        "deadline": "",
                        "publishDate": "",
                        "status": "open",
                        "description": {
                            "en": f"EU procurement notice {pub_number} for {country_name}. View full details on TED Europa.",
                            "ar": f"إشعار مشتريات الاتحاد الأوروبي {pub_number} لـ {country_name}.",
                            "fr": f"Avis de marché UE {pub_number} pour {country_name}.",
                        },
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": f"https://ted.europa.eu/en/notice/{pub_number}",
                    }
                    tenders.append(tender)

                total_for_country += len(notices)
                logger.info(f"TED {ted_code} page {page}: {len(notices)} notices (total avail: {total})")

                # Check if more pages
                if total_for_country >= total or len(notices) < 100:
                    break

                page += 1
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"TED {ted_code}: {e}")
                break

    logger.info(f"TED total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ted_v2")
    print(f"Scraped {len(results)} tenders from TED")
