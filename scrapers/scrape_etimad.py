"""
Scraper for Saudi Etimad (tenders.etimad.sa) — Government Procurement.
Source: https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync

The largest single tender source: 279K+ Saudi government tenders.
API returns JSON, rate-limited to 20 req/min. Max 24 items per page.
Content is in Arabic.
"""

import requests
import logging
import time
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("etimad")

API_URL = "https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync"

# We scrape recent pages — going too deep returns old/closed tenders
MAX_PAGES = 200  # 200 pages × 24 items = ~4,800 recent tenders


def _create_session() -> requests.Session:
    """Create a session with proper headers to avoid bot detection."""
    s = requests.Session()
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ar,en;q=0.9",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": "https://tenders.etimad.sa/Tender/AllTendersForVisitor",
        "Origin": "https://tenders.etimad.sa",
    })
    return s


def _parse_tender(item: dict) -> dict | None:
    """Parse a single Etimad tender into our schema."""
    name = item.get("tenderName", "")
    if not name or len(name) < 5:
        return None

    tender_id = str(item.get("tenderId", ""))
    ref = item.get("referenceNumber", "")
    agency = item.get("agencyName", "")
    branch = item.get("branchName", "")
    tender_type = item.get("tenderTypeName", "")
    activity = item.get("tenderActivityName", "")

    # Dates
    deadline_raw = item.get("lastOfferPresentationDate", "")
    publish_raw = item.get("submitionDate", "")
    deadline = parse_date(deadline_raw) or ""
    publish = parse_date(publish_raw) or ""

    # Budget/fees
    fees = item.get("condetionalBookletPrice", 0) or 0
    invitation_cost = item.get("invitationCost", 0) or 0

    # Status based on remaining time
    remaining_days = item.get("remainingDays", 0) or 0
    if remaining_days > 7:
        status = "open"
    elif remaining_days > 0:
        status = "closing-soon"
    else:
        status = "closed"

    # Build description
    desc_parts = []
    if tender_type:
        desc_parts.append(tender_type)
    if activity:
        desc_parts.append(activity)
    if agency:
        desc_parts.append(agency)
    if branch:
        desc_parts.append(branch)
    desc = " | ".join(desc_parts)

    org_en = agency or "Saudi Government"

    return {
        "id": generate_id("etimad", ref or tender_id, ""),
        "source": "Etimad",
        "sourceRef": ref,
        "sourceLanguage": "ar",
        "title": {"en": name, "ar": name, "fr": name},
        "organization": {
            "en": org_en,
            "ar": agency or "الحكومة السعودية",
            "fr": org_en,
        },
        "country": "Saudi Arabia",
        "countryCode": "SA",
        "sector": classify_sector(name + " " + (activity or "") + " " + (tender_type or "")),
        "budget": float(fees + invitation_cost),
        "currency": "SAR",
        "deadline": deadline,
        "publishDate": publish,
        "status": status,
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [tender_type] if tender_type else [],
        "matchScore": 0,
        "sourceUrl": f"https://tenders.etimad.sa/Tender/DetailsForVisitor?STenderId={item.get('tenderIdString', '')}",
    }


def scrape() -> list[dict]:
    """Scrape recent Saudi Etimad tenders."""
    session = _create_session()
    tenders: list[dict] = []
    seen_refs: set[str] = set()

    consecutive_errors = 0
    page = 1

    while page <= MAX_PAGES and consecutive_errors < 5:
        try:
            resp = session.get(API_URL, params={
                "pageNumber": page,
                "pageSize": 24,
            }, timeout=30)

            if resp.status_code != 200:
                logger.warning(f"Etimad page {page}: HTTP {resp.status_code}")
                consecutive_errors += 1
                time.sleep(5)  # Back off on errors
                continue

            # Check if we got HTML (bot protection) instead of JSON
            ct = resp.headers.get("content-type", "")
            if "json" not in ct:
                logger.warning(f"Etimad page {page}: got {ct} instead of JSON — bot protection triggered")
                consecutive_errors += 1
                time.sleep(10)  # Longer back-off
                continue

            data = resp.json()
            items = data.get("data", [])

            if not items:
                logger.info(f"Etimad page {page}: no more data")
                break

            new_count = 0
            for item in items:
                tender = _parse_tender(item)
                if not tender:
                    continue
                ref_key = tender["sourceRef"] or tender["id"]
                if ref_key in seen_refs:
                    continue
                seen_refs.add(ref_key)
                tenders.append(tender)
                new_count += 1

            consecutive_errors = 0
            logger.info(f"Etimad page {page}: {new_count} new tenders (total: {len(tenders)})")

            page += 1

            # Respect rate limit: 20 req/min = 3s between requests
            time.sleep(3.5)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Etimad page {page}: connection error — rate limited? ({e})")
            consecutive_errors += 1
            time.sleep(10)

        except Exception as e:
            logger.error(f"Etimad page {page}: {e}")
            consecutive_errors += 1
            time.sleep(5)

    logger.info(f"Etimad total: {len(tenders)} tenders ({page - 1} pages scraped)")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "etimad")
    print(f"Scraped {len(results)} tenders from Etimad")
