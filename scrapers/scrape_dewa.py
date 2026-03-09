"""
Scraper for Dubai Electricity and Water Authority (DEWA) tenders.
Source: https://www.ungm.org/Public/Notice (UN Global Marketplace)
Also tries: https://srm.dewa.gov.ae/irj/portal/anonymous/rfxlistanon (SAP SRM)

DEWA's main website (dewa.gov.ae) is behind Akamai CDN with bot protection
that blocks all automated requests. Dubai Pulse open data also blocks bots.

This scraper uses two alternative sources:
1. UNGM (UN Global Marketplace) - searches for UAE energy/water/electricity
   procurement notices using JSON API (same approach as scrape_ungm.py)
2. DEWA SRM anonymous portal - SAP SRM portal that may be accessible
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("dewa")

UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice/Search"
UNGM_NOTICE_BASE = "https://www.ungm.org"
DEWA_SRM_URL = "https://srm.dewa.gov.ae/irj/portal/anonymous/rfxlistanon"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

# UNGM internal country ID for UAE
UNGM_UAE_ID = "2505"

# UN agencies (for label extraction)
_UN_AGENCIES = {
    "UNDP", "UNICEF", "WHO", "WFP", "UNOPS", "FAO", "ILO",
    "UNESCO", "UNHCR", "UNRWA", "IAEA", "UNFPA", "ITC",
    "UNIDO", "ITU", "ESCWA", "ECLAC", "UN Women",
    "OCHA", "UNAIDS", "UNEP", "UN Secretariat", "UNFCCC",
    "UNWTO", "UNODC", "UNECE", "UNCTAD", "OHCHR",
}

# Notice types
_NOTICE_TYPES = {
    "Request for proposal", "Request for quotation",
    "Invitation to bid", "Request for information",
    "Call for individual consultants",
    "Request for expression of interest",
    "Grant/support/call for proposal",
    "Request for pre-qualification",
    "Pre-bid notice",
}


def _search_ungm_page(page_index: int) -> str:
    """Fetch one page of UNGM search results for UAE (JSON body, returns HTML)."""
    payload = {
        "PageIndex": page_index,
        "PageSize": 15,
        "Countries": [UNGM_UAE_ID],
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
        UNGM_SEARCH_URL,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": HEADERS["User-Agent"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def _parse_ungm_notices(html: str) -> list[dict]:
    """Parse UNGM search result HTML into tender dicts for UAE."""
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

        # Parse structured data
        deadline_str = ""
        pub_date_str = ""
        agency = ""
        notice_type = ""
        reference = ""

        for text in texts:
            if text == title or "subscribe" in text.lower() or "unsave" in text.lower():
                continue
            # Deadline: "22-Mar-2026 11:00 (GMT 1.00)"
            if re.match(r"\d{2}-\w{3}-\d{4}\s+\d", text) and not deadline_str:
                deadline_str = text.split("(")[0].strip()
            # Published: "09-Mar-2026"
            elif re.match(r"\d{2}-\w{3}-\d{4}$", text) and not pub_date_str:
                pub_date_str = text
            elif text in _UN_AGENCIES:
                agency = text
            elif text in _NOTICE_TYPES:
                notice_type = text

        # Find reference from resultInfo1
        ref_el = row.select_one(".resultInfo1:not(.deadline) span")
        if ref_el:
            reference = ref_el.get_text(strip=True)

        # Parse dates
        deadline = parse_date(deadline_str.split()[0]) if deadline_str else ""
        pub_date = parse_date(pub_date_str) or ""

        source_ref = reference if reference else f"UNGM-{notice_id}"

        tender = {
            "id": generate_id("dewa", source_ref, ""),
            "source": "DEWA",
            "sourceRef": source_ref,
            "sourceLanguage": "en",
            "title": {"en": title, "ar": title, "fr": title},
            "organization": {
                "en": f"Dubai Electricity and Water Authority (DEWA) via {agency}"
                if agency
                else "Dubai Electricity and Water Authority (DEWA)",
                "ar": "هيئة كهرباء ومياه دبي (ديوا)",
                "fr": "Autorité de l'électricité et de l'eau de Dubaï (DEWA)",
            },
            "country": "UAE",
            "countryCode": "AE",
            "sector": classify_sector(
                title + " electricity water energy Dubai UAE"
            ),
            "budget": 0,
            "currency": "AED",
            "deadline": deadline or "",
            "publishDate": pub_date,
            "status": "open",
            "description": {
                "en": f"{notice_type}. {title}" if notice_type else title,
                "ar": title,
                "fr": title,
            },
            "requirements": [notice_type] if notice_type else [],
            "matchScore": 0,
            "sourceUrl": f"https://www.ungm.org/Public/Notice/{notice_id}",
        }
        tenders.append(tender)

    return tenders


def _scrape_ungm_uae() -> list[dict]:
    """Scrape UNGM for UAE procurement notices."""
    all_tenders: list[dict] = []
    seen_ids: set[str] = set()

    page = 0
    empty_pages = 0

    while page < 10 and empty_pages < 2:
        try:
            html = _search_ungm_page(page)
            tenders = _parse_ungm_notices(html)

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

            logger.info(f"UNGM UAE page {page}: {new_count} new notices")
            page += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"UNGM UAE page {page} error: {e}")
            break

    logger.info(f"UNGM UAE total: {len(all_tenders)} notices")
    return all_tenders


def _try_dewa_srm() -> list[dict]:
    """Try to access DEWA SRM anonymous portal for RFx listings."""
    tenders: list[dict] = []

    try:
        session = requests.Session()
        resp = session.get(
            DEWA_SRM_URL,
            headers={
                **HEADERS,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=30,
            allow_redirects=True,
        )

        if resp.status_code == 403:
            logger.info(
                "DEWA SRM: Access denied (403). "
                "SAP SRM portal uses bot protection."
            )
            return tenders

        if resp.status_code != 200:
            logger.warning(f"DEWA SRM: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # SAP SRM portal uses tables for RFx listings
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) < 2:
                    continue

                texts = [c.get_text(strip=True) for c in cells]
                full_text = " ".join(texts)

                if len(full_text) < 20:
                    continue

                title = max(texts, key=len)
                if len(title) < 10:
                    continue

                ref = ""
                for t in texts:
                    if re.match(r"^[A-Z0-9\-/]{3,25}$", t.strip()):
                        ref = t.strip()
                        break
                if not ref:
                    ref = title[:60]

                link_el = row.select_one("a[href]")
                href = ""
                if link_el:
                    href = link_el.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://srm.dewa.gov.ae" + href

                tender = {
                    "id": generate_id("dewa_srm", ref, ""),
                    "source": "DEWA",
                    "sourceRef": ref,
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "Dubai Electricity and Water Authority (DEWA)",
                        "ar": "هيئة كهرباء ومياه دبي (ديوا)",
                        "fr": "Autorité de l'électricité et de l'eau de Dubaï (DEWA)",
                    },
                    "country": "UAE",
                    "countryCode": "AE",
                    "sector": classify_sector(
                        title + " electricity water energy"
                    ),
                    "budget": 0,
                    "currency": "AED",
                    "deadline": "",
                    "publishDate": "",
                    "status": "open",
                    "description": {
                        "en": full_text[:500],
                        "ar": full_text[:500],
                        "fr": full_text[:500],
                    },
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": href or DEWA_SRM_URL,
                }
                tenders.append(tender)

    except Exception as e:
        logger.error(f"DEWA SRM scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape DEWA tenders from UNGM and SRM portal."""
    ungm_tenders = _scrape_ungm_uae()
    srm_tenders = _try_dewa_srm()

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in ungm_tenders + srm_tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(
        f"DEWA total: {len(all_tenders)} tenders "
        f"(UNGM: {len(ungm_tenders)}, SRM: {len(srm_tenders)})"
    )

    if not all_tenders:
        logger.warning(
            "DEWA: No tenders retrieved. DEWA's site uses Akamai bot "
            "protection. UNGM may not have UAE tenders at this time. "
            "The SRM portal also blocks automated access."
        )

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "dewa")
    print(f"Scraped {len(results)} tenders from DEWA")
