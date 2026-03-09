"""
Scraper for Egypt EEHC (Egyptian Electricity Holding Company) Tenders.
Source: https://eehc.gov.eg/CMSEehc/en/tenders/
Also:   https://eehc.gov.eg/CMSEehc/en/external-tenders/

The tenders page uses a .list-group with items that link to detail pages.
Each list-group-item contains:
  - Title (h5)
  - Date
  - Country info
  - Tender Due Date / Expire Date

Also scrapes the Arabic interface for additional tenders.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("eehc")

BASE_URL = "https://eehc.gov.eg/CMSEehc"
TENDERS_EN = f"{BASE_URL}/en/tenders/"
EXTERNAL_TENDERS_EN = f"{BASE_URL}/en/external-tenders/"
TENDERS_AR = f"{BASE_URL}/tenders/"  # Arabic version

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en,ar",
}


def _parse_tender_detail(url: str) -> dict:
    """Fetch a tender detail page for additional info."""
    info = {"description": "", "deadline": "", "publish_date": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return info

        soup = BeautifulSoup(resp.text, "lxml")

        # Get description from main content
        content = soup.select_one(".entry-content, .post-content, .container p, article")
        if content:
            info["description"] = content.get_text(strip=True)[:1000]

        # Look for dates in the page
        page_text = soup.get_text()
        date_patterns = re.findall(r"(\d{2}/\d{2}/\d{4})", page_text)
        for dp in date_patterns:
            d = parse_date(dp)
            if d:
                if not info["publish_date"]:
                    info["publish_date"] = d
                elif not info["deadline"]:
                    info["deadline"] = d

    except Exception as e:
        logger.debug(f"EEHC detail page error ({url}): {e}")

    return info


def _scrape_listing_page(url: str, lang: str = "en") -> list[dict]:
    """Scrape a single EEHC tenders listing page."""
    tenders = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"EEHC page returned {resp.status_code}: {url}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Strategy 1: Look for .list-group-item elements
        items = soup.select(".list-group-item, .list-group a")
        if items:
            logger.info(f"EEHC: Found {len(items)} list-group items on {url}")
            for item in items:
                # Get title from h5 or the item text
                title_el = item.select_one("h5, h4, h3, .title, strong")
                if title_el:
                    title = title_el.get_text(strip=True)
                else:
                    title = item.get_text(strip=True)[:200]

                if not title or len(title) < 5:
                    continue

                # Get link
                link = ""
                if item.name == "a":
                    link = item.get("href", "")
                else:
                    a = item.select_one("a[href]")
                    if a:
                        link = a.get("href", "")

                if link and not link.startswith("http"):
                    link = f"https://eehc.gov.eg{link}"

                # Extract dates from the item text
                item_text = item.get_text()
                pub_date = ""
                deadline = ""

                # Look for specific date labels
                due_match = re.search(
                    r"(?:Tender\s*Due\s*Date|Due\s*Date|Deadline)\s*[:.]?\s*(\d{2}/\d{2}/\d{4})",
                    item_text,
                    re.IGNORECASE,
                )
                if due_match:
                    deadline = parse_date(due_match.group(1)) or ""

                expire_match = re.search(
                    r"(?:Expire|Expiry|Closing)\s*(?:Date)?\s*[:.]?\s*(\d{2}/\d{2}/\d{4})",
                    item_text,
                    re.IGNORECASE,
                )
                if expire_match:
                    deadline = deadline or (parse_date(expire_match.group(1)) or "")

                # Generic date extraction
                dates = re.findall(r"(\d{2}/\d{2}/\d{4})", item_text)
                for d in dates:
                    parsed = parse_date(d)
                    if parsed:
                        if not pub_date:
                            pub_date = parsed
                        elif not deadline:
                            deadline = parsed

                ref = re.search(r"(?:No\.?|Ref\.?)\s*([\w\-/]+)", title)
                ref_str = ref.group(1) if ref else title[:60]

                tender = {
                    "id": generate_id("eehc", ref_str, ""),
                    "source": "EEHC Egypt",
                    "sourceRef": ref_str,
                    "sourceLanguage": lang,
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "Egyptian Electricity Holding Company",
                        "ar": "الشركة القابضة لكهرباء مصر",
                        "fr": "Société Holding d'Électricité d'Égypte",
                    },
                    "country": "Egypt",
                    "countryCode": "EG",
                    "sector": classify_sector(title + " electricity energy power"),
                    "budget": 0,
                    "currency": "EGP",
                    "deadline": deadline,
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {"en": title, "ar": title, "fr": title},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link or url,
                }
                tenders.append(tender)

        # Strategy 2: Look for cards or article elements
        if not tenders:
            for selector in [
                ".card",
                "article",
                ".post",
                ".tender-item",
                ".accordion-item",
                "table tbody tr",
            ]:
                cards = soup.select(selector)
                if not cards:
                    continue

                for card in cards:
                    title_el = card.select_one("h2, h3, h4, h5, .card-title, a")
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    if len(title) < 5:
                        continue

                    link = ""
                    a = card.select_one("a[href]")
                    if a:
                        href = a.get("href", "")
                        link = (
                            href
                            if href.startswith("http")
                            else f"https://eehc.gov.eg{href}"
                        )

                    card_text = card.get_text()
                    dates = re.findall(r"(\d{2}/\d{2}/\d{4})", card_text)
                    pub_date = parse_date(dates[0]) if dates else ""
                    deadline = parse_date(dates[1]) if len(dates) > 1 else ""

                    tender = {
                        "id": generate_id("eehc", title[:60], ""),
                        "source": "EEHC Egypt",
                        "sourceRef": title[:60],
                        "sourceLanguage": lang,
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": "Egyptian Electricity Holding Company",
                            "ar": "الشركة القابضة لكهرباء مصر",
                            "fr": "Société Holding d'Électricité d'Égypte",
                        },
                        "country": "Egypt",
                        "countryCode": "EG",
                        "sector": classify_sector(
                            title + " electricity energy power"
                        ),
                        "budget": 0,
                        "currency": "EGP",
                        "deadline": deadline,
                        "publishDate": pub_date,
                        "status": "open",
                        "description": {"en": title, "ar": title, "fr": title},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": link or url,
                    }
                    tenders.append(tender)

                if tenders:
                    break

        # Check for pagination
        next_page = soup.select_one("a.next, .pagination .next a, a[rel=next]")
        if next_page:
            next_href = next_page.get("href", "")
            if next_href and not next_href.startswith("http"):
                next_href = f"https://eehc.gov.eg{next_href}"
            if next_href:
                time.sleep(2)
                more_tenders = _scrape_listing_page(next_href, lang)
                tenders.extend(more_tenders)

    except Exception as e:
        logger.error(f"EEHC listing page error ({url}): {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape EEHC Egypt electricity tenders."""
    all_tenders: list[dict] = []
    seen: set[str] = set()

    # Scrape all listing pages
    pages = [
        (TENDERS_EN, "en", "Tenders (EN)"),
        (EXTERNAL_TENDERS_EN, "en", "External Tenders (EN)"),
    ]

    for page_url, lang, label in pages:
        try:
            results = _scrape_listing_page(page_url, lang)
            logger.info(f"EEHC {label}: {len(results)} tenders")
            for t in results:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
        except Exception as e:
            logger.error(f"EEHC {label} error: {e}")

        time.sleep(2)

    # Optionally fetch detail pages for richer descriptions
    for tender in all_tenders[:20]:  # Limit to avoid too many requests
        detail_url = tender.get("sourceUrl", "")
        if detail_url and detail_url != TENDERS_EN and detail_url != EXTERNAL_TENDERS_EN:
            try:
                info = _parse_tender_detail(detail_url)
                if info["description"]:
                    tender["description"] = {
                        "en": info["description"],
                        "ar": info["description"],
                        "fr": info["description"],
                    }
                if info["deadline"] and not tender["deadline"]:
                    tender["deadline"] = info["deadline"]
                if info["publish_date"] and not tender["publishDate"]:
                    tender["publishDate"] = info["publish_date"]
                time.sleep(2)
            except Exception:
                pass

    logger.info(f"EEHC total: {len(all_tenders)}")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "eehc")
    print(f"Scraped {len(results)} tenders from EEHC Egypt")
