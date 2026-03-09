"""
Scraper for Saudi Etimad (tenders.etimad.sa) — Government Procurement.
Source: https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync

The largest single tender source: 279K+ Saudi government tenders.
API returns JSON, rate-limited to 20 req/min. Max 24 items per page.
Content is in Arabic.
"""

import json
import requests
import logging
import time
from pathlib import Path
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("etimad")

API_URL = "https://tenders.etimad.sa/Tender/AllSupplierTendersForVisitorAsync"

# We scrape recent pages — going deep to capture all open tenders
MAX_PAGES = 500  # 500 pages × 24 items = ~12,000 tenders
CLOSED_RATIO_THRESHOLD = 0.95  # Stop when pages are >95% closed (nearly all)
CONSECUTIVE_CLOSED_PAGES = 5   # Need 5 such pages in a row to be sure
CONSECUTIVE_KNOWN_PAGES = 3    # For incremental: stop after 3 pages of known tenders
DATA_DIR = Path(__file__).parent / "data"


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


def _load_known_refs() -> set[str]:
    """Load sourceRef values from existing etimad.json for incremental mode."""
    etimad_file = DATA_DIR / "etimad.json"
    if not etimad_file.exists():
        return set()
    with open(etimad_file, encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("tenders", [])
    return {t.get("sourceRef") or t.get("id") for t in items}


def _load_existing_tenders() -> list[dict]:
    """Load existing tenders from etimad.json for merging."""
    etimad_file = DATA_DIR / "etimad.json"
    if not etimad_file.exists():
        return []
    with open(etimad_file, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("tenders", [])


def scrape(incremental: bool = False) -> list[dict]:
    """Scrape recent Saudi Etimad tenders.

    Args:
        incremental: If True, skip pages of already-known tenders and merge
                     new results with existing data.
    """
    session = _create_session()
    tenders: list[dict] = []
    seen_refs: set[str] = set()

    # Incremental: load known refs to detect already-scraped tenders
    known_refs = _load_known_refs() if incremental else set()
    if incremental and known_refs:
        logger.info(f"Incremental mode: {len(known_refs)} known tenders loaded")

    consecutive_errors = 0
    consecutive_closed_pages = 0
    consecutive_known_pages = 0
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
                time.sleep(5)
                continue

            ct = resp.headers.get("content-type", "")
            if "json" not in ct:
                logger.warning(f"Etimad page {page}: got {ct} instead of JSON — bot protection triggered")
                consecutive_errors += 1
                time.sleep(10)
                continue

            data = resp.json()
            items = data.get("data", [])

            if not items:
                logger.info(f"Etimad page {page}: no more data")
                break

            # Track closed and known ratios for this page
            page_closed = 0
            page_known = 0
            page_total = 0
            new_count = 0

            for item in items:
                tender = _parse_tender(item)
                if not tender:
                    continue
                page_total += 1
                ref_key = tender["sourceRef"] or tender["id"]

                # Track closed tenders
                if tender.get("status") == "closed":
                    page_closed += 1

                # Track known tenders (incremental)
                if ref_key in known_refs:
                    page_known += 1

                if ref_key in seen_refs:
                    continue
                seen_refs.add(ref_key)
                tenders.append(tender)
                new_count += 1

            consecutive_errors = 0

            # Smart stop: track closed-tender ratio
            closed_ratio = page_closed / max(page_total, 1)
            if closed_ratio > CLOSED_RATIO_THRESHOLD:
                consecutive_closed_pages += 1
                logger.info(f"Etimad page {page}: {closed_ratio:.0%} closed ({consecutive_closed_pages}/{CONSECUTIVE_CLOSED_PAGES} consecutive)")
            else:
                consecutive_closed_pages = 0

            if consecutive_closed_pages >= CONSECUTIVE_CLOSED_PAGES:
                logger.info(f"Smart stop: {CONSECUTIVE_CLOSED_PAGES} consecutive pages with >{CLOSED_RATIO_THRESHOLD:.0%} closed tenders — stopping")
                break

            # Incremental stop: track known-tender ratio
            if incremental and page_total > 0:
                known_ratio = page_known / page_total
                if known_ratio > CLOSED_RATIO_THRESHOLD:
                    consecutive_known_pages += 1
                    logger.info(f"Etimad page {page}: {known_ratio:.0%} already known ({consecutive_known_pages}/{CONSECUTIVE_KNOWN_PAGES} consecutive)")
                else:
                    consecutive_known_pages = 0

                if consecutive_known_pages >= CONSECUTIVE_KNOWN_PAGES:
                    logger.info(f"Incremental stop: {CONSECUTIVE_KNOWN_PAGES} consecutive pages with >{CLOSED_RATIO_THRESHOLD:.0%} known tenders — stopping")
                    break

            logger.info(f"Etimad page {page}: {new_count} new tenders (total: {len(tenders)})")
            page += 1
            time.sleep(3.5)

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Etimad page {page}: connection error — rate limited? ({e})")
            consecutive_errors += 1
            time.sleep(10)

        except Exception as e:
            logger.error(f"Etimad page {page}: {e}")
            consecutive_errors += 1
            time.sleep(5)

    logger.info(f"Etimad total: {len(tenders)} new tenders ({page - 1} pages scraped)")

    # Incremental: merge new tenders with existing (new wins on conflicts)
    if incremental and known_refs:
        existing = _load_existing_tenders()
        existing_by_ref = {(t.get("sourceRef") or t.get("id")): t for t in existing}
        new_by_ref = {(t.get("sourceRef") or t.get("id")): t for t in tenders}
        existing_by_ref.update(new_by_ref)  # new wins
        tenders = list(existing_by_ref.values())
        logger.info(f"Incremental merge: {len(tenders)} total tenders (was {len(existing)}, added/updated {len(new_by_ref)})")

    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "etimad")
    print(f"Scraped {len(results)} tenders from Etimad")
