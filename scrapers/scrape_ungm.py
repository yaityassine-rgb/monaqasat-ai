"""
Scraper for UNGM (United Nations Global Marketplace).
Source: https://www.ungm.org/Public/Notice/Search

All UN agencies' procurement notices for MENA countries.
Uses POST search endpoint that returns HTML fragments.
"""

import re
import logging
import time
import requests
from bs4 import BeautifulSoup
from config import MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ungm")

SEARCH_URL = "https://www.ungm.org/Public/Notice/Search"

# UNGM internal country IDs for MENA
UNGM_COUNTRY_IDS: dict[str, str] = {
    "2295": "DZ",  # Algeria
    "2308": "BH",  # Bahrain
    "2353": "EG",  # Egypt
    "2389": "IQ",  # Iraq
    "2395": "JO",  # Jordan
    "2401": "KW",  # Kuwait
    "2405": "LB",  # Lebanon
    "2408": "LY",  # Libya
    "2422": "MR",  # Mauritania
    "2431": "MA",  # Morocco
    "2446": "OM",  # Oman
    "2458": "QA",  # Qatar
    "2471": "SA",  # Saudi Arabia
    "2484": "SD",  # Sudan
    "2498": "TN",  # Tunisia
    "2505": "AE",  # UAE
    "2518": "YE",  # Yemen
    "2522": "PS",  # Palestine
}

ALL_MENA_IDS = list(UNGM_COUNTRY_IDS.keys())

# Reverse: country name → ISO2
_NAME_TO_CODE: dict[str, str] = {v.lower(): k for k, v in MENA_COUNTRIES.items()}
_NAME_TO_CODE.update({
    "united arab emirates": "AE", "uae": "AE",
    "state of palestine": "PS", "palestine, state of": "PS",
    "occupied palestinian territory": "PS",
    "saudi arabia": "SA", "kingdom of saudi arabia": "SA",
})

# Known UN agencies
_UN_AGENCIES = {
    "UNDP", "UNICEF", "WHO", "WFP", "UNOPS", "FAO", "ILO",
    "UNESCO", "UNHCR", "UNRWA", "IAEA", "UNFPA", "ITC",
    "UNIDO", "ITU", "ESCWA", "ECLAC", "UN Women",
    "OCHA", "UNAIDS", "UNEP", "UN Secretariat", "UNFCCC",
    "UNWTO", "UNODC", "UNECE", "UNCTAD", "OHCHR",
}

# Known notice types
_NOTICE_TYPES = {
    "Request for proposal", "Request for quotation",
    "Invitation to bid", "Request for information",
    "Call for individual consultants",
    "Request for expression of interest",
    "Grant/support/call for proposal",
    "Request for pre-qualification",
    "Pre-bid notice",
}


def _search_page(page_index: int) -> str:
    """Fetch one page of UNGM search results (HTML)."""
    payload = {
        "PageIndex": page_index,
        "PageSize": 15,
        "Countries": ALL_MENA_IDS,
        "Agencies": [],
        "UNSPSCs": [],
        "NoticeTypes": [],
        "SortField": "DatePublished",
        "SortAscending": False,
        "IsActive": True,
        "Title": "",
        "Description": "",
        "Reference": "",
        "PublishedFrom": "",
        "PublishedTo": "",
        "DeadlineFrom": "",
        "DeadlineTo": "",
        "isPicker": False,
        "IsSustainable": False,
        "NoticeDisplayType": "",
        "NoticeSearchTotalLabelId": "noticeSearchTotal",
        "TypeOfCompetitions": [],
    }
    resp = requests.post(
        SEARCH_URL,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def _parse_notices(html: str) -> list[dict]:
    """Parse UNGM search result HTML into tender dicts."""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("[data-noticeid]")

    tenders: list[dict] = []
    seen_ids: set[str] = set()

    for row in rows:
        notice_id = row.get("data-noticeid", "")
        if not notice_id or notice_id in seen_ids:
            continue
        seen_ids.add(notice_id)

        # Title
        title_el = row.select_one(".ungm-title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 10:
            continue

        # Extract all text spans
        spans = row.select("span")
        texts = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]

        # Parse structured data from spans
        deadline_str = ""
        pub_date_str = ""
        agency = ""
        notice_type = ""

        for text in texts:
            # Skip the title itself and save/subscribe text
            if text == title or "subscribe" in text.lower() or "unsave" in text.lower():
                continue
            # Deadline pattern: "22-Mar-2026 11:00 (GMT 1.00)"
            if re.match(r"\d{2}-\w{3}-\d{4}\s+\d", text) and not deadline_str:
                deadline_str = text.split("(")[0].strip()
            # Published date: just "09-Mar-2026"
            elif re.match(r"\d{2}-\w{3}-\d{4}$", text) and not pub_date_str:
                pub_date_str = text
            # Agency
            elif text in _UN_AGENCIES:
                agency = text
            # Notice type
            elif text in _NOTICE_TYPES:
                notice_type = text

        # Try to find country from the full row text
        row_text = row.get_text().lower()
        country_code = ""
        country_name = ""
        for name, code in _NAME_TO_CODE.items():
            if name in row_text:
                country_code = code
                country_name = MENA_COUNTRIES.get(code, "")
                break

        if not country_code:
            title_lower = title.lower()
            for name, code in _NAME_TO_CODE.items():
                if name in title_lower:
                    country_code = code
                    country_name = MENA_COUNTRIES.get(code, "")
                    break

        if not country_code:
            country_code = "XX"
            country_name = "MENA Region"

        # Parse dates — "22-Mar-2026" format
        deadline = parse_date(deadline_str.split()[0]) if deadline_str else ""
        pub_date = parse_date(pub_date_str) or ""

        tender = {
            "id": generate_id("ungm", notice_id, ""),
            "source": "UNGM",
            "sourceRef": notice_id,
            "sourceLanguage": "en",
            "title": {"en": title, "ar": title, "fr": title},
            "organization": {
                "en": agency or "United Nations",
                "ar": agency or "الأمم المتحدة",
                "fr": agency or "Nations Unies",
            },
            "country": country_name,
            "countryCode": country_code,
            "sector": classify_sector(title + " " + notice_type),
            "budget": 0,
            "currency": "USD",
            "deadline": deadline or "",
            "publishDate": pub_date,
            "status": "open",
            "description": {
                "en": f"{notice_type}. {title}" if notice_type else title,
                "ar": f"{notice_type}. {title}" if notice_type else title,
                "fr": f"{notice_type}. {title}" if notice_type else title,
            },
            "requirements": [notice_type] if notice_type else [],
            "matchScore": 0,
            "sourceUrl": f"https://www.ungm.org/Public/Notice/{notice_id}",
        }
        tenders.append(tender)

    return tenders


def scrape() -> list[dict]:
    """Scrape UNGM for all active MENA procurement notices."""
    all_tenders: list[dict] = []
    seen_ids: set[str] = set()

    page = 0
    empty_pages = 0

    while page < 40 and empty_pages < 2:
        try:
            html = _search_page(page)
            tenders = _parse_notices(html)

            if not tenders:
                empty_pages += 1
                page += 1
                continue

            empty_pages = 0
            new_count = 0
            for t in tenders:
                if t["sourceRef"] not in seen_ids:
                    seen_ids.add(t["sourceRef"])
                    all_tenders.append(t)
                    new_count += 1

            logger.info(f"UNGM page {page}: {new_count} new notices")
            page += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"UNGM page {page} error: {e}")
            break

    logger.info(f"UNGM total: {len(all_tenders)} MENA notices")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ungm")
    print(f"Scraped {len(results)} tenders from UNGM")
