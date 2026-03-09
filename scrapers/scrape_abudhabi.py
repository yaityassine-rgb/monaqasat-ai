"""
Scraper for Abu Dhabi Government Procurement (ADGPG / AlMaqtaa).
Source: https://www.adgpg.gov.ae/en/For-Suppliers/Public-Tenders

Abu Dhabi's official government procurement portal (AlMaqtaa platform).
Uses a clean JSON API at /SCAPI/ADGEs/AlMaqtaa/Tender/List that returns
structured tender data with pagination support.
Content is primarily in English.
"""

import logging
import time
import requests
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("abudhabi")

BASE_URL = "https://www.adgpg.gov.ae"
API_LIST_URL = f"{BASE_URL}/SCAPI/ADGEs/AlMaqtaa/Tender/List"
API_DETAIL_URL = f"{BASE_URL}/SCAPI/ADGEs/AlMaqtaa/Tender/Details"
PUBLIC_TENDERS_URL = f"{BASE_URL}/en/For-Suppliers/Public-Tenders"
PAGE_SIZE = 20
MAX_PAGES = 10  # 20 * 10 = 200 tenders max


def _create_session() -> requests.Session:
    """Create a session with proper headers."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": PUBLIC_TENDERS_URL,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


def _parse_tender(item: dict) -> dict | None:
    """Parse a single tender from the API response."""
    tender_id = item.get("TenderID", "")
    name = item.get("TenderName", "")
    tender_number = item.get("TenderNumber", "")
    entity = item.get("EntityName", "")
    status_raw = item.get("InternalStatus", "")
    due_date_raw = item.get("DueDate", "")
    details = item.get("TenderDetails", "")
    bidding_open = item.get("BiddingOpenDate", "")
    due_days = item.get("DueDays", 0)

    if not name or len(name) < 5:
        return None

    # Parse dates
    deadline = parse_date(due_date_raw) or ""
    pub_date = parse_date(bidding_open) or ""

    # Determine status
    status = "open"
    if status_raw == "OPEN":
        if due_days is not None and isinstance(due_days, (int, float)) and due_days <= 7:
            status = "closing-soon"
    elif status_raw in ("CLOSED", "COMPL"):
        return None  # Skip closed tenders

    # Build source URL pointing to the public tenders page with tender details
    # The detail page is accessed via the SCAPI endpoint
    source_url = f"{PUBLIC_TENDERS_URL}?{tender_number}"

    # Build description
    desc_parts = []
    if details and details != name:
        desc_parts.append(details)
    if entity:
        desc_parts.append(f"Entity: {entity}")
    if tender_number:
        desc_parts.append(f"Ref: {tender_number}")
    desc = " | ".join(desc_parts) if desc_parts else name

    return {
        "id": generate_id("abudhabi", tender_number or str(tender_id), ""),
        "source": "Abu Dhabi ADGPG",
        "sourceRef": tender_number,
        "sourceLanguage": "en",
        "title": {"en": name, "ar": name, "fr": name},
        "organization": {
            "en": entity or "Abu Dhabi Government",
            "ar": entity or "حكومة أبوظبي",
            "fr": entity or "Gouvernement d'Abou Dabi",
        },
        "country": "UAE",
        "countryCode": "AE",
        "sector": classify_sector(name + " " + (details or "")),
        "budget": 0,
        "currency": "AED",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": status,
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _enrich_with_details(session: requests.Session, tenders: list[dict]) -> list[dict]:
    """Optionally enrich tenders with detail API data (category, estimated value)."""
    enriched = 0
    for tender in tenders:
        # Extract tender ID from sourceRef or id
        tender_id = None
        # We stored the number as sourceRef, need the TenderID for detail API
        # Skip enrichment if we don't have it
        if not tender_id:
            continue

        try:
            resp = session.get(
                f"{API_DETAIL_URL}/{tender_id}",
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            data = resp.json()
            detail = data.get("TenderDetails", {})
            if isinstance(detail, dict):
                category_en = detail.get("CategoryDescriptionEn", "")
                category_ar = detail.get("CategoryDescriptionAr", "")
                estimated = detail.get("EstimatedValue", "")
                event_type = detail.get("EventType", "")

                if category_en:
                    tender["sector"] = classify_sector(
                        tender["title"]["en"] + " " + category_en
                    )
                if event_type:
                    tender["requirements"] = [event_type]
                enriched += 1

            time.sleep(1)
        except Exception:
            pass

    if enriched > 0:
        logger.info(f"Abu Dhabi: enriched {enriched} tenders with detail data")
    return tenders


def scrape() -> list[dict]:
    """Scrape Abu Dhabi ADGPG for public procurement notices."""
    tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()
    consecutive_errors = 0

    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        try:
            resp = session.post(
                API_LIST_URL,
                data={
                    "status": "OPEN",
                    "offset": str(offset),
                    "limit": str(PAGE_SIZE),
                    "Category": "",
                    "Entity": "",
                    "DueDate": "",
                    "TenderName": "",
                    "sorting": "LAST_CREATED",
                },
                timeout=30,
            )

            if resp.status_code != 200:
                logger.warning(f"Abu Dhabi page {page + 1}: HTTP {resp.status_code}")
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    break
                time.sleep(2)
                continue

            data = resp.json()
            total_count = data.get("TenderCount", 0)
            tender_list = data.get("TenderList", [])

            if not tender_list:
                logger.info(f"Abu Dhabi page {page + 1}: no more tenders")
                break

            consecutive_errors = 0
            page_count = 0

            for item in tender_list:
                tender = _parse_tender(item)
                if not tender:
                    continue
                key = tender["sourceRef"] or tender["title"]["en"][:60]
                if key in seen:
                    continue
                seen.add(key)
                tenders.append(tender)
                page_count += 1

            logger.info(
                f"Abu Dhabi page {page + 1}: {page_count} tenders "
                f"(total: {len(tenders)}/{total_count})"
            )

            # Stop if we have all tenders
            if len(tenders) >= total_count:
                break

            time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Abu Dhabi page {page + 1}: connection error — {e}")
            consecutive_errors += 1
            if consecutive_errors >= 3:
                break
            time.sleep(5)
        except Exception as e:
            logger.error(f"Abu Dhabi page {page + 1}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= 3:
                break
            time.sleep(2)

    logger.info(f"Abu Dhabi total: {len(tenders)} tenders")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "abudhabi")
    print(f"Scraped {len(results)} tenders from Abu Dhabi ADGPG")
