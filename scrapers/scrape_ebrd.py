"""
Scraper for European Bank for Reconstruction and Development (EBRD).
Source: https://www.ebrd.com/work-with-us/procurement/notices.html

The EBRD main procurement notices page uses a JS-heavy CMS (Adobe AEM).
We attempt to scrape the HTML listing and fall back to the EBRD project
search API. EBRD covers multiple MENA countries.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ebrd")

NOTICES_URL = "https://www.ebrd.com/work-with-us/procurement/notices.html"
# Alternative: EBRD project search with MENA countries
PROJECT_SEARCH_URL = "https://www.ebrd.com/api/search"

# MENA countries that EBRD covers
EBRD_MENA_COUNTRIES = {
    "EG": "Egypt",
    "JO": "Jordan",
    "LB": "Lebanon",
    "MA": "Morocco",
    "TN": "Tunisia",
    "IQ": "Iraq",
    "PS": "Palestine",
    "TR": "Turkey",
}


def _detect_country(text: str) -> tuple[str, str]:
    """Detect country from tender text."""
    text_lower = text.lower()
    for code, name in EBRD_MENA_COUNTRIES.items():
        if name.lower() in text_lower:
            return name, code
    return "Multi-country", "XX"


def _scrape_notices_html() -> list[dict]:
    """Scrape procurement notices from the EBRD HTML page."""
    tenders: list[dict] = []

    try:
        resp = requests.get(NOTICES_URL, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"EBRD notices page returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for procurement notice items (cards, list items, table rows)
        # The EBRD page uses various card/list structures
        cards = soup.select(".procurement-notice, .notice-item, .card, .result-item, "
                            ".listing-item, article, .cmp-teaser")

        for card in cards:
            # Try to find title
            title_el = card.select_one("h2, h3, h4, .title, .heading, a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Try to get link
            link_el = card.select_one("a[href]")
            href = ""
            if link_el and link_el.get("href"):
                href = link_el["href"]
                if href.startswith("/"):
                    href = "https://www.ebrd.com" + href

            # Try to find dates
            date_els = card.select(".date, time, .published, .deadline")
            pub_date = ""
            deadline = ""
            for d in date_els:
                dt = d.get("datetime", "") or d.get_text(strip=True)
                parsed = parse_date(dt)
                if parsed and not pub_date:
                    pub_date = parsed

            # Detect country
            full_text = card.get_text(" ", strip=True)
            country, country_code = _detect_country(full_text)

            # Try to find reference
            ref_match = re.search(r'(?:ref|reference|no)[:\s]*([A-Z0-9\-/]+)', full_text, re.I)
            source_ref = ref_match.group(1) if ref_match else title[:60]

            tender = {
                "id": generate_id("ebrd", source_ref, ""),
                "source": "EBRD",
                "sourceRef": source_ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "European Bank for Reconstruction and Development",
                    "ar": "البنك الأوروبي لإعادة الإعمار والتنمية",
                    "fr": "Banque européenne pour la reconstruction et le développement",
                },
                "country": country,
                "countryCode": country_code,
                "sector": classify_sector(full_text),
                "budget": 0,
                "currency": "EUR",
                "deadline": deadline,
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": full_text[:500],
                    "ar": full_text[:500],
                    "fr": full_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or NOTICES_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"EBRD HTML scraper error: {e}")

    return tenders


def _scrape_ecepp_portal() -> list[dict]:
    """Try to scrape the EBRD e-procurement portal (ECEPP)."""
    tenders: list[dict] = []

    # The ECEPP portal (ecepp.ebrd.com) is a WordPress site that links
    # to the actual procurement system. Try to find opportunity listings.
    try:
        resp = requests.get("https://ecepp.ebrd.com/", headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        }, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"ECEPP portal returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for any procurement opportunity links
        links = soup.select("a[href*='opportunity'], a[href*='tender'], "
                            "a[href*='procurement'], a[href*='notice']")

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or len(title) < 10 or not href:
                continue

            if not href.startswith("http"):
                href = "https://ecepp.ebrd.com" + href

            country, country_code = _detect_country(title)

            tender = {
                "id": generate_id("ebrd_ecepp", title[:60], ""),
                "source": "EBRD",
                "sourceRef": title[:60],
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "European Bank for Reconstruction and Development",
                    "ar": "البنك الأوروبي لإعادة الإعمار والتنمية",
                    "fr": "Banque européenne pour la reconstruction et le développement",
                },
                "country": country,
                "countryCode": country_code,
                "sector": classify_sector(title),
                "budget": 0,
                "currency": "EUR",
                "deadline": "",
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": title,
                    "ar": title,
                    "fr": title,
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"ECEPP portal scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape EBRD procurement notices from multiple sources."""
    html_tenders = _scrape_notices_html()
    time.sleep(2)
    ecepp_tenders = _scrape_ecepp_portal()

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in html_tenders + ecepp_tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"EBRD total: {len(all_tenders)} notices "
                f"(HTML: {len(html_tenders)}, ECEPP: {len(ecepp_tenders)})")

    if not all_tenders:
        logger.warning("EBRD: No tenders found. The procurement notices page may use "
                        "client-side JavaScript rendering that cannot be scraped with "
                        "requests+BeautifulSoup. Consider using a headless browser.")

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ebrd")
    print(f"Scraped {len(results)} notices from EBRD")
