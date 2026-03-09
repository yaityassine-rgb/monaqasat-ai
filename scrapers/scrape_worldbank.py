"""
Scraper for World Bank Procurement — FULL PAGINATION.
Source: https://search.worldbank.org/api/v2/procnotices
Paginate through all results for each MENA country.
"""

import requests
import logging
import time
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("worldbank")

API_BASE = "https://search.worldbank.org/api/v2/procnotices"

WB_COUNTRIES = list(MENA_COUNTRIES.keys())


def scrape() -> list[dict]:
    """Scrape ALL World Bank procurement notices for MENA with full pagination."""
    tenders = []

    for country_code in WB_COUNTRIES:
        offset = 0
        page_size = 100  # Max allowed
        country_total = 0

        while True:
            try:
                params = {
                    "format": "json",
                    "countrycode": country_code,
                    "rows": page_size,
                    "os": offset,
                    "srt": "new",
                }

                resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=30)

                if resp.status_code != 200:
                    logger.warning(f"WB API {resp.status_code} for {country_code} offset={offset}")
                    break

                data = resp.json()
                total = int(data.get("total", 0))
                notices = data.get("procnotices", {})

                if isinstance(notices, dict):
                    notice_list = [v for v in notices.values() if isinstance(v, dict)]
                elif isinstance(notices, list):
                    notice_list = notices
                else:
                    break

                if not notice_list:
                    break

                for notice in notice_list:
                    title = notice.get("notice_text", notice.get("project_name", ""))
                    if not title:
                        continue

                    org = notice.get("bid_description", notice.get("borrower", ""))
                    project_name = notice.get("project_name", "")
                    deadline_raw = notice.get("submission_date", notice.get("deadline_date", ""))
                    publish_raw = notice.get("notice_posted_date", notice.get("noticedate", ""))
                    notice_type = notice.get("notice_type", "")
                    procurement_method = notice.get("procurement_method", "")
                    procurement_group = notice.get("procurement_group", "")
                    notice_status = notice.get("notice_status", "")
                    lang = notice.get("notice_lang_name", "")
                    contact = notice.get("contact_info", "")
                    ref_no = notice.get("notice_no", notice.get("id", ""))

                    country_name = MENA_COUNTRIES.get(country_code, "")
                    description = " | ".join(filter(None, [
                        project_name, notice_type, procurement_method,
                        procurement_group, org
                    ]))

                    # Determine status
                    status = "open"
                    if notice_status and "close" in notice_status.lower():
                        status = "closed"

                    # Extract requirements from procurement method
                    reqs = []
                    if procurement_method:
                        reqs.append(procurement_method)
                    if procurement_group:
                        reqs.append(procurement_group)

                    tender = {
                        "id": generate_id("wb", str(ref_no) or title[:80], country_code),
                        "source": "World Bank",
                        "sourceRef": str(ref_no),
                        "title": {"en": title[:500], "ar": title[:500], "fr": title[:500]},
                        "organization": {
                            "en": org or f"World Bank Project — {country_name}",
                            "ar": org or f"مشروع البنك الدولي — {country_name}",
                            "fr": org or f"Projet Banque mondiale — {country_name}",
                        },
                        "country": country_name,
                        "countryCode": country_code,
                        "sector": classify_sector(title + " " + description),
                        "budget": 0,
                        "currency": "USD",
                        "deadline": parse_date(str(deadline_raw)) or "",
                        "publishDate": parse_date(str(publish_raw)) or "",
                        "status": status,
                        "description": {"en": description, "ar": description, "fr": description},
                        "requirements": reqs,
                        "matchScore": 0,
                        "sourceUrl": notice.get("url", ""),
                        "contact": contact,
                    }
                    tenders.append(tender)

                country_total += len(notice_list)
                offset += page_size

                # Stop if we've got all
                if offset >= total or offset >= 500:  # Cap at 500 per country
                    break

                time.sleep(0.3)  # Be polite

            except Exception as e:
                logger.error(f"WB error {country_code} offset={offset}: {e}")
                break

        logger.info(f"WB {country_code}: {country_total} tenders (total available: {total if 'total' in dir() else '?'})")

    logger.info(f"World Bank total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "worldbank")
    print(f"Scraped {len(results)} tenders from World Bank")
