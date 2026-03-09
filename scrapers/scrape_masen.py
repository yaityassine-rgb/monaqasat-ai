"""
Scraper for Morocco Renewable Energy Agency (Masen / MASEN).
Source: https://etendering.masen.ma/index.php?page=entreprise.EntrepriseHome&lang=en

Atexo/PRADO e-tendering platform. The page has a menu structure that links
to current and closed tenders via advanced search pages. We scrape the
public-facing tender listings and the quick search functionality.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("masen")

BASE_URL = "https://etendering.masen.ma"
HOME_URL = f"{BASE_URL}/index.php?page=entreprise.EntrepriseHome&lang=en"
SEARCH_URL = f"{BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch&AllCons&searchAnnCons&lang=en"
CURRENT_URL = f"{BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch&AllCons&EnCours&searchAnnCons&lang=en"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


def _scrape_tender_list(url: str, label: str) -> list[dict]:
    """Scrape tender listings from Masen's Atexo platform."""
    tenders: list[dict] = []

    try:
        session = requests.Session()

        # First visit the home page to establish session
        session.get(HOME_URL, headers=HEADERS, timeout=30)
        time.sleep(1)

        # Then fetch the search/listing page
        resp = session.get(url, headers=HEADERS, timeout=30)

        if resp.status_code != 200:
            logger.warning(f"Masen {label}: HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Atexo platform renders tenders in table rows or card divs
        # Look for the main content area with tender listings
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) < 2:
                    continue

                texts = [c.get_text(strip=True) for c in cells]
                full_text = " ".join(texts)

                # Skip very short rows
                if len(full_text) < 20:
                    continue

                # Skip header rows
                if any(kw in full_text.lower() for kw in
                       ["reference", "object", "date", "status", "type"]):
                    if len(texts) > 3 and len(max(texts, key=len)) < 30:
                        continue

                # Get title - usually the longest cell
                title = max(texts, key=len)
                if len(title) < 10:
                    continue

                # Get reference
                ref = ""
                for t in texts:
                    if re.match(r'^[A-Z0-9\-/]{3,25}$', t.strip()):
                        ref = t.strip()
                        break

                if not ref:
                    ref = title[:60]

                # Get link
                link_el = row.select_one("a[href]")
                href = ""
                if link_el:
                    href = link_el.get("href", "")
                    if href and not href.startswith("http"):
                        href = BASE_URL + "/" + href.lstrip("/")

                # Get dates
                pub_date = ""
                deadline = ""
                for t in texts:
                    parsed = parse_date(t)
                    if parsed:
                        if not pub_date:
                            pub_date = parsed
                        else:
                            deadline = parsed

                tender = {
                    "id": generate_id("masen", ref, ""),
                    "source": "MASEN",
                    "sourceRef": ref,
                    "sourceLanguage": "fr",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "Moroccan Agency for Sustainable Energy (MASEN)",
                        "ar": "الوكالة المغربية للطاقة المستدامة (مازن)",
                        "fr": "Agence Marocaine pour l'Energie Durable (MASEN)",
                    },
                    "country": "Morocco",
                    "countryCode": "MA",
                    "sector": classify_sector(
                        title + " renewable energy solar wind Morocco"
                    ),
                    "budget": 0,
                    "currency": "MAD",
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
                    "sourceUrl": href or url,
                }
                tenders.append(tender)

        # Also look for card/div-based listings (Atexo sometimes uses divs)
        cards = soup.select(".consultation, .annonce, [class*='consult'], "
                            "[class*='annonce'], .result-item, .tender-item")
        for card in cards:
            title_el = card.select_one("a, .title, h3, h4, .objet")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            card_text = card.get_text(" ", strip=True)
            ref_match = re.search(r'(?:Ref|Réf|N°)[.\s:]*([A-Z0-9\-/]+)', card_text, re.I)
            ref = ref_match.group(1) if ref_match else title[:60]

            # Avoid duplicates
            if any(t["sourceRef"] == ref for t in tenders):
                continue

            link_el = card.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = BASE_URL + "/" + href.lstrip("/")

            # Extract dates
            date_matches = re.findall(
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', card_text
            )
            pub_date = ""
            deadline = ""
            for dm in date_matches:
                parsed = parse_date(dm)
                if parsed:
                    if not pub_date:
                        pub_date = parsed
                    else:
                        deadline = parsed

            tender = {
                "id": generate_id("masen", ref, ""),
                "source": "MASEN",
                "sourceRef": ref,
                "sourceLanguage": "fr",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Moroccan Agency for Sustainable Energy (MASEN)",
                    "ar": "الوكالة المغربية للطاقة المستدامة (مازن)",
                    "fr": "Agence Marocaine pour l'Energie Durable (MASEN)",
                },
                "country": "Morocco",
                "countryCode": "MA",
                "sector": classify_sector(
                    title + " renewable energy solar wind Morocco"
                ),
                "budget": 0,
                "currency": "MAD",
                "deadline": deadline,
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": card_text[:500],
                    "ar": card_text[:500],
                    "fr": card_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or url,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"Masen {label} scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Masen e-tendering platform for procurement notices."""
    all_tenders = _scrape_tender_list(SEARCH_URL, "all-tenders")
    time.sleep(2)
    current = _scrape_tender_list(CURRENT_URL, "current-tenders")

    # Merge and deduplicate
    seen: set[str] = set()
    merged: list[dict] = []
    for t in all_tenders + current:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            merged.append(t)

    logger.info(f"MASEN total: {len(merged)} tenders "
                f"(all: {len(all_tenders)}, current: {len(current)})")

    if not merged:
        logger.warning("MASEN: No tenders found. The Atexo/PRADO e-tendering "
                        "platform may require login to view tender listings, "
                        "or the search results may be loaded via AJAX. "
                        "Consider using a headless browser.")

    return merged


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "masen")
    print(f"Scraped {len(results)} tenders from MASEN")
