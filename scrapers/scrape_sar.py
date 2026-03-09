"""
Scraper for Saudi Railway Company (SAR).
Source: https://e.sar.com.sa/tenders

Clean JSON API at /Tenders/Tenders/TenderList returns structured tender data
including title, RFP number, dates, and contact info.
"""

import logging
import time
import requests
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("sar")

API_URL = "https://e.sar.com.sa/Tenders/Tenders/TenderList"
DETAIL_URL = "https://e.sar.com.sa/Tenders/Tenders/TenderDetails"


def scrape() -> list[dict]:
    """Scrape SAR tenders via their JSON API."""
    tenders: list[dict] = []

    try:
        resp = requests.get(API_URL, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"SAR API returned {resp.status_code}")
            return tenders

        data = resp.json()

        if data.get("statusMessage", {}).get("code") != "0":
            logger.warning(f"SAR API error: {data.get('statusMessage', {}).get('message')}")
            return tenders

        items = data.get("TenderDetails", [])
        logger.info(f"SAR API returned {len(items)} tenders")

        for item in items:
            title = item.get("titleID", "").strip()
            if not title:
                continue

            tender_id = str(item.get("tenderID", ""))
            rfp_number = str(item.get("rfpNumber", ""))
            description = item.get("rfpDescription", "") or title
            close_date = parse_date(item.get("rfpCloseDate", "")) or ""
            pub_date = parse_date(item.get("publishedDate", "")) or ""

            # Build contact info for description
            buyer_name = item.get("buyerName") or ""
            buyer_email = item.get("buyerEmail") or ""
            contact_info = ""
            if buyer_name:
                contact_info += f" Contact: {buyer_name}"
            if buyer_email:
                contact_info += f" ({buyer_email})"

            full_desc = f"{description}{contact_info}".strip()

            source_url = f"{DETAIL_URL}/{tender_id}" if tender_id else "https://e.sar.com.sa/tenders"

            tender = {
                "id": generate_id("sar", rfp_number or tender_id, ""),
                "source": "SAR",
                "sourceRef": rfp_number,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Saudi Railway Company (SAR)",
                    "ar": "الشركة السعودية للخطوط الحديدية (سار)",
                    "fr": "Saudi Railway Company (SAR)",
                },
                "country": "Saudi Arabia",
                "countryCode": "SA",
                "sector": classify_sector(title + " " + description + " railway transport"),
                "budget": 0,
                "currency": "SAR",
                "deadline": close_date,
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": full_desc[:500],
                    "ar": full_desc[:500],
                    "fr": full_desc[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"SAR scraper error: {e}")

    logger.info(f"SAR total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "sar")
    print(f"Scraped {len(results)} tenders from SAR")
