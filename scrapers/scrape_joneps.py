"""
Scraper for Jordan JONEPS (National E-Procurement System).
Source: https://www.joneps.gov.jo

Uses the AJAX JSON endpoints and HTML tender listing page.
Content is primarily in Arabic.
"""

import json
import logging
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("joneps")

BASE_URL = "https://www.joneps.gov.jo"
BID_INFO_URL = f"{BASE_URL}/pt/main/callBidInformationAll.do"
TENDER_LIST_URL = f"{BASE_URL}/ep/invt/selectListTendInvitAL.do"


def _parse_multi_json(text: str) -> list:
    """Parse JONEPS response which may contain multiple concatenated JSON arrays."""
    decoder = json.JSONDecoder()
    results = []
    pos = 0
    while pos < len(text):
        text_sub = text[pos:].lstrip()
        if not text_sub:
            break
        try:
            obj, end = decoder.raw_decode(text_sub)
            if isinstance(obj, list):
                results.extend(obj)
            pos += len(text) - len(text_sub) + end
        except json.JSONDecodeError:
            break
    return results


def _scrape_ajax_bids() -> list[dict]:
    """Scrape from the AJAX bid information endpoints."""
    tenders = []

    endpoints = [
        f"{BASE_URL}/pt/main/callBidInformationAll.do",
        f"{BASE_URL}/pt/main/callBidInformationGoods.do",
    ]

    for url in endpoints:
        try:
            resp = requests.get(url, headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
            }, timeout=30)
            if resp.status_code != 200:
                continue

            items = _parse_multi_json(resp.text)
            for item in items:
                name = item.get("tendNm", "")
                if not name or len(name) < 5:
                    continue

                tend_no = str(item.get("tendNo", ""))
                pub_date = parse_date(item.get("pubcatDt", "")) or ""
                tend_type = item.get("tendTypeNm", "")

                tender = {
                    "id": generate_id("joneps", tend_no or name[:80], ""),
                    "source": "JONEPS",
                    "sourceRef": tend_no,
                    "sourceLanguage": "ar",
                    "title": {"en": name, "ar": name, "fr": name},
                    "organization": {
                        "en": "Government of Jordan",
                        "ar": "المملكة الأردنية الهاشمية",
                        "fr": "Gouvernement de Jordanie",
                    },
                    "country": "Jordan",
                    "countryCode": "JO",
                    "sector": classify_sector(name + " " + tend_type),
                    "budget": 0,
                    "currency": "JOD",
                    "deadline": "",
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {
                        "en": f"{tend_type}: {name}" if tend_type else name,
                        "ar": f"{tend_type}: {name}" if tend_type else name,
                        "fr": f"{tend_type}: {name}" if tend_type else name,
                    },
                    "requirements": [tend_type] if tend_type else [],
                    "matchScore": 0,
                    "sourceUrl": f"{BASE_URL}/ep/invt/selectListTendInvitAL.do",
                }
                tenders.append(tender)

        except Exception as e:
            logger.error(f"JONEPS AJAX {url}: {e}")

    return tenders


def _scrape_html_listing() -> list[dict]:
    """Scrape the HTML tender listing page."""
    tenders = []

    try:
        resp = requests.get(TENDER_LIST_URL, params={
            "menuId": "EP03000000",
            "upperMenuId": "EP03020000",
            "subMenuId": "EP03020100",
        }, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "ar,en",
        }, timeout=30)

        if resp.status_code != 200:
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Find the main data table with tender listings
        tables = soup.select("table")
        for tbl in tables:
            headers = [th.get_text(strip=True) for th in tbl.select("th")]
            if not headers or "رقم العطاء" not in headers[0]:
                continue

            rows = tbl.select("tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) < 4:
                    continue

                texts = [c.get_text(strip=True) for c in cells]
                tend_no = texts[0] if texts else ""
                name = texts[1] if len(texts) > 1 else ""
                org = texts[2] if len(texts) > 2 else ""
                tend_type = texts[3] if len(texts) > 3 else ""
                pub_date_str = texts[4] if len(texts) > 4 else ""
                deadline_str = texts[5] if len(texts) > 5 else ""

                if not name or len(name) < 5:
                    continue

                tender = {
                    "id": generate_id("joneps", tend_no or name[:80], ""),
                    "source": "JONEPS",
                    "sourceRef": tend_no,
                    "sourceLanguage": "ar",
                    "title": {"en": name, "ar": name, "fr": name},
                    "organization": {
                        "en": org or "Government of Jordan",
                        "ar": org or "المملكة الأردنية الهاشمية",
                        "fr": org or "Gouvernement de Jordanie",
                    },
                    "country": "Jordan",
                    "countryCode": "JO",
                    "sector": classify_sector(name + " " + tend_type),
                    "budget": 0,
                    "currency": "JOD",
                    "deadline": parse_date(deadline_str) or "",
                    "publishDate": parse_date(pub_date_str) or "",
                    "status": "open",
                    "description": {
                        "en": f"{tend_type}: {name}" if tend_type else name,
                        "ar": f"{tend_type}: {name}" if tend_type else name,
                        "fr": f"{tend_type}: {name}" if tend_type else name,
                    },
                    "requirements": [tend_type] if tend_type else [],
                    "matchScore": 0,
                    "sourceUrl": f"{BASE_URL}/ep/invt/selectListTendInvitAL.do",
                }
                tenders.append(tender)

            break  # Found the right table

    except Exception as e:
        logger.error(f"JONEPS HTML listing: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Jordan JONEPS for procurement notices."""
    ajax_tenders = _scrape_ajax_bids()
    html_tenders = _scrape_html_listing()

    # Merge and deduplicate by sourceRef
    seen: set[str] = set()
    all_tenders: list[dict] = []

    for t in ajax_tenders + html_tenders:
        key = t.get("sourceRef", "") or t["title"]["ar"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"JONEPS total: {len(all_tenders)} (AJAX: {len(ajax_tenders)}, HTML: {len(html_tenders)})")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "joneps")
    print(f"Scraped {len(results)} tenders from JONEPS")
