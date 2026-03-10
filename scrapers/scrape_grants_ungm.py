"""
Grant scraper for UNGM (United Nations Global Marketplace).
Source: https://www.ungm.org/Public/Notice/Search

Extends the existing UNGM pattern but filters specifically for grant-type
notices: "Grant/support/call for proposal" notice type.

Uses the UNGM POST search endpoint with NoticeTypes filter and parses
the HTML response with BeautifulSoup.
"""

import re
import requests
import logging
import time
from bs4 import BeautifulSoup
from config import (
    MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR,
)
from base_scraper import (
    generate_grant_id, classify_sector, classify_grant_type,
    parse_date, parse_amount, save_grants,
)

logger = logging.getLogger("grants_ungm")

SEARCH_URL = "https://www.ungm.org/Public/Notice/Search"
NOTICE_DETAIL_URL = "https://www.ungm.org/Public/Notice"

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

# Reverse: country name (lowercase) -> ISO2
_NAME_TO_CODE: dict[str, str] = {v.lower(): k for k, v in MENA_COUNTRIES.items()}
_NAME_TO_CODE.update({
    "united arab emirates": "AE",
    "uae": "AE",
    "state of palestine": "PS",
    "palestine, state of": "PS",
    "occupied palestinian territory": "PS",
    "saudi arabia": "SA",
    "kingdom of saudi arabia": "SA",
    "republic of iraq": "IQ",
    "arab republic of egypt": "EG",
    "hashemite kingdom of jordan": "JO",
})

# Known UN agencies
_UN_AGENCIES = {
    "UNDP", "UNICEF", "WHO", "WFP", "UNOPS", "FAO", "ILO",
    "UNESCO", "UNHCR", "UNRWA", "IAEA", "UNFPA", "ITC",
    "UNIDO", "ITU", "ESCWA", "ECLAC", "UN Women",
    "OCHA", "UNAIDS", "UNEP", "UN Secretariat", "UNFCCC",
    "UNWTO", "UNODC", "UNECE", "UNCTAD", "OHCHR",
    "UNHABITAT", "UNCDF", "UNV", "UNDPPA", "DPPA",
    "UNCITRAL", "UNDRR", "WMO", "WIPO", "IMO", "ICAO",
}

# UN agency Arabic names
_UN_AGENCIES_AR: dict[str, str] = {
    "UNDP": "برنامج الأمم المتحدة الإنمائي",
    "UNICEF": "اليونيسف",
    "WHO": "منظمة الصحة العالمية",
    "WFP": "برنامج الأغذية العالمي",
    "UNOPS": "مكتب الأمم المتحدة لخدمات المشاريع",
    "FAO": "منظمة الأغذية والزراعة",
    "UNESCO": "اليونسكو",
    "UNHCR": "المفوضية السامية لشؤون اللاجئين",
    "UNRWA": "وكالة الأونروا",
}

# UN agency French names
_UN_AGENCIES_FR: dict[str, str] = {
    "UNDP": "Programme des Nations Unies pour le développement",
    "UNICEF": "UNICEF",
    "WHO": "Organisation mondiale de la Santé",
    "WFP": "Programme alimentaire mondial",
    "FAO": "Organisation des Nations Unies pour l'alimentation et l'agriculture",
    "UNESCO": "UNESCO",
    "UNHCR": "HCR",
    "UNRWA": "UNRWA",
}

# Grant-related UNGM notice types
GRANT_NOTICE_TYPES = [
    "Grant/support/call for proposal",
    "Call for Proposals",
    "Grant",
]

# Browser headers
UNGM_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://www.ungm.org",
    "Referer": "https://www.ungm.org/Public/Notice/Search",
}


def _search_grants_page(page_index: int, grant_only: bool = True) -> str:
    """Fetch one page of UNGM grant search results (HTML).

    Args:
        page_index: Zero-based page index.
        grant_only: If True, filter to grant notice types only.
    """
    payload = {
        "PageIndex": page_index,
        "PageSize": 15,
        "Countries": ALL_MENA_IDS,
        "Agencies": [],
        "UNSPSCs": [],
        "NoticeTypes": ["4"] if grant_only else [],  # 4 = Grant/support/call for proposal
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
        headers=UNGM_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def _search_keyword_page(page_index: int, keyword: str) -> str:
    """Search UNGM with a keyword filter for grant-related terms."""
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
        "Title": keyword,
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
        headers=UNGM_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def _detect_country(text: str) -> tuple[str, str]:
    """Detect MENA country from text. Returns (code, name)."""
    text_lower = text.lower()
    for name, code in _NAME_TO_CODE.items():
        if name in text_lower:
            return code, MENA_COUNTRIES.get(code, "")
    return "", ""


def _parse_grant_notices(html: str) -> list[dict]:
    """Parse UNGM search result HTML into grant records."""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("[data-noticeid]")

    grants: list[dict] = []

    for row in rows:
        notice_id = row.get("data-noticeid", "")
        if not notice_id:
            continue

        # Title
        title_el = row.select_one(".ungm-title")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 10:
            continue

        # Extract all text spans for structured data
        spans = row.select("span")
        texts = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]

        deadline_str = ""
        pub_date_str = ""
        agency = ""
        notice_type = ""
        reference = ""

        for text in texts:
            if text == title or "subscribe" in text.lower() or "unsave" in text.lower():
                continue

            # Deadline pattern: "22-Mar-2026 11:00 (GMT 1.00)"
            if re.match(r"\d{2}-\w{3}-\d{4}\s+\d", text) and not deadline_str:
                deadline_str = text.split("(")[0].strip()
            # Published date: "09-Mar-2026"
            elif re.match(r"\d{2}-\w{3}-\d{4}$", text) and not pub_date_str:
                pub_date_str = text
            # Agency
            elif text in _UN_AGENCIES:
                agency = text
            # Notice type
            elif any(gt.lower() in text.lower() for gt in GRANT_NOTICE_TYPES):
                notice_type = text
            elif text.startswith("UNGM-") or text.startswith("RFP/") or text.startswith("ITB/"):
                reference = text

        # Detect country
        row_text = row.get_text()
        country_code, country_name = _detect_country(row_text)
        if not country_code:
            country_code, country_name = _detect_country(title)
        if not country_code:
            country_code = "XX"
            country_name = "MENA Region"

        # Parse dates
        deadline = ""
        if deadline_str:
            date_part = deadline_str.split()[0] if deadline_str else ""
            deadline = parse_date(date_part) or ""
        pub_date = parse_date(pub_date_str) or ""

        # Classify
        combined = f"{title} {notice_type} {row_text[:200]}"
        sector = classify_sector(combined)
        grant_type = classify_grant_type(combined)

        # Build description
        desc_parts = []
        if notice_type:
            desc_parts.append(f"Type: {notice_type}")
        if agency:
            desc_parts.append(f"Agency: {agency}")
        desc_parts.append(title)
        description = " | ".join(desc_parts)

        # Agency translations
        agency_ar = _UN_AGENCIES_AR.get(agency, agency or "الأمم المتحدة")
        agency_fr = _UN_AGENCIES_FR.get(agency, agency or "Nations Unies")

        ref = reference or notice_id

        grant = {
            "id": generate_grant_id("ungm", notice_id),
            "title": title,
            "title_ar": "",
            "title_fr": "",
            "source": "ungm",
            "source_ref": notice_id,
            "source_url": f"https://www.ungm.org/Public/Notice/{notice_id}",
            "funding_organization": agency or "United Nations",
            "funding_organization_ar": agency_ar,
            "funding_organization_fr": agency_fr,
            "funding_amount": 0,
            "funding_amount_max": 0,
            "currency": "USD",
            "grant_type": grant_type,
            "country": country_name,
            "country_code": country_code,
            "region": "MENA",
            "sector": sector,
            "sectors": [sector],
            "eligibility_criteria": notice_type or "UN grant/call for proposals",
            "eligibility_countries": [country_code] if country_code != "XX" else list(MENA_COUNTRIES.keys()),
            "description": description[:2000],
            "description_ar": "",
            "description_fr": "",
            "application_deadline": deadline,
            "publish_date": pub_date,
            "status": "open",
            "contact_info": agency or "",
            "documents_url": f"https://www.ungm.org/Public/Notice/{notice_id}",
            "tags": ["UN", agency] if agency else ["UN"],
            "metadata": {
                "notice_type": notice_type,
                "agency": agency,
                "reference": reference,
            },
        }
        grants.append(grant)

    return grants


def _scrape_grant_type_notices() -> list[dict]:
    """Scrape UNGM notices filtered by grant notice type."""
    all_grants: list[dict] = []
    seen_ids: set[str] = set()

    page = 0
    empty_pages = 0
    max_pages = 40

    while page < max_pages and empty_pages < 2:
        try:
            html = _search_grants_page(page, grant_only=True)
            grants = _parse_grant_notices(html)

            if not grants:
                empty_pages += 1
                page += 1
                continue

            empty_pages = 0
            new_count = 0
            for g in grants:
                if g["source_ref"] not in seen_ids:
                    seen_ids.add(g["source_ref"])
                    all_grants.append(g)
                    new_count += 1

            logger.info(
                f"UNGM grants page {page}: {new_count} new grant notices"
            )
            page += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"UNGM grants page {page} error: {e}")
            break

    return all_grants


def _scrape_keyword_grants() -> list[dict]:
    """Scrape UNGM using grant-related keyword searches."""
    all_grants: list[dict] = []
    seen_ids: set[str] = set()

    keywords = [
        "grant",
        "call for proposals",
        "funding opportunity",
        "financial support",
        "capacity building grant",
    ]

    for keyword in keywords:
        page = 0
        empty_pages = 0

        while page < 10 and empty_pages < 2:
            try:
                html = _search_keyword_page(page, keyword)
                grants = _parse_grant_notices(html)

                if not grants:
                    empty_pages += 1
                    page += 1
                    continue

                empty_pages = 0
                new_count = 0
                for g in grants:
                    if g["source_ref"] not in seen_ids:
                        seen_ids.add(g["source_ref"])
                        all_grants.append(g)
                        new_count += 1

                logger.info(
                    f"UNGM keyword '{keyword}' page {page}: "
                    f"{new_count} new notices"
                )
                page += 1
                time.sleep(0.5)

            except Exception as e:
                logger.error(
                    f"UNGM keyword '{keyword}' page {page} error: {e}"
                )
                break

        time.sleep(1.0)

    return all_grants


def scrape() -> list[dict]:
    """Scrape UNGM for MENA grant/call-for-proposal notices."""
    logger.info("Starting UNGM grants scraper...")

    # Phase 1: Grant notice type filter
    type_grants = _scrape_grant_type_notices()
    logger.info(f"Phase 1 — Grant type filter: {len(type_grants)} notices")

    # Phase 2: Keyword-based search for additional grants
    keyword_grants = _scrape_keyword_grants()
    logger.info(f"Phase 2 — Keyword search: {len(keyword_grants)} notices")

    # Merge and deduplicate
    all_grants = type_grants
    seen_refs = {g["source_ref"] for g in all_grants}
    for g in keyword_grants:
        if g["source_ref"] not in seen_refs:
            seen_refs.add(g["source_ref"])
            all_grants.append(g)

    logger.info(f"UNGM total grants: {len(all_grants)}")
    return all_grants


if __name__ == "__main__":
    results = scrape()
    save_grants(results, "ungm")
    print(f"Scraped {len(results)} grants from UNGM")
