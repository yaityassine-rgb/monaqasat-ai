"""
Scraper for Morocco's public procurement portal.
Source: https://www.marchespublics.gov.ma
Morocco's official government procurement portal.
"""

import requests
import logging
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("morocco")

BASE_URL = "https://www.marchespublics.gov.ma"
SEARCH_URL = f"{BASE_URL}/pmmp/faces/ConsultationAvisSearch.xhtml"


def scrape() -> list[dict]:
    """Scrape Morocco's marchespublics.gov.ma."""
    tenders = []

    try:
        # Try the main consultation page
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr,ar,en",
        })

        # Get the main page
        resp = session.get(BASE_URL, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Morocco portal returned {resp.status_code}")
            # Try alternate URLs
            for url in [
                f"{BASE_URL}/pmmp/faces/ConsultationAvance.xhtml",
                f"{BASE_URL}/pmmp/faces/AvisConsultation.xhtml",
                "https://www.marchespublics.gov.ma/pmmp/",
            ]:
                resp = session.get(url, timeout=30)
                if resp.status_code == 200:
                    break

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")

            # Look for tender listings
            selectors = [
                "table tbody tr",
                ".dataTables_wrapper tr",
                ".avis-item",
                ".consultation-row",
                ".ui-datatable-data tr",
            ]

            for selector in selectors:
                rows = soup.select(selector)
                if rows:
                    logger.info(f"Found {len(rows)} rows with selector: {selector}")
                    for row in rows:
                        cells = row.select("td")
                        if len(cells) < 2:
                            continue

                        # Extract text from cells
                        texts = [c.get_text(strip=True) for c in cells]
                        title = texts[0] if texts else ""
                        if len(title) < 5:
                            title = " | ".join(texts[:3])
                        if len(title) < 5:
                            continue

                        # Get link
                        link = ""
                        a = row.select_one("a[href]")
                        if a:
                            href = a.get("href", "")
                            link = href if href.startswith("http") else f"{BASE_URL}{href}"

                        # Try to find dates
                        pub_date = ""
                        deadline = ""
                        for text in texts:
                            d = parse_date(text)
                            if d:
                                if not pub_date:
                                    pub_date = d
                                else:
                                    deadline = d

                        tender = {
                            "id": generate_id("ma", title[:80], "MA"),
                            "source": "Marchés Publics Maroc",
                            "title": {
                                "en": title,
                                "ar": title,
                                "fr": title,
                            },
                            "organization": {
                                "en": "Government of Morocco",
                                "ar": "المملكة المغربية",
                                "fr": "Royaume du Maroc",
                            },
                            "country": "Morocco",
                            "countryCode": "MA",
                            "sector": classify_sector(title),
                            "budget": 0,
                            "currency": "MAD",
                            "deadline": deadline,
                            "publishDate": pub_date,
                            "status": "open",
                            "description": {"en": title, "ar": title, "fr": title},
                            "requirements": [],
                            "matchScore": 0,
                            "sourceUrl": link,
                        }
                        tenders.append(tender)
                    break  # Found working selector

        # Also try the RSS/open data endpoint if available
        for rss_url in [
            f"{BASE_URL}/pmmp/rss",
            f"{BASE_URL}/pmmp/feeds/avis.xml",
        ]:
            try:
                import feedparser
                feed = feedparser.parse(rss_url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    if not title or len(title) < 5:
                        continue
                    tender = {
                        "id": generate_id("ma_rss", title[:80], "MA"),
                        "source": "Marchés Publics Maroc",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {"en": "Government of Morocco", "ar": "المملكة المغربية", "fr": "Royaume du Maroc"},
                        "country": "Morocco",
                        "countryCode": "MA",
                        "sector": classify_sector(title),
                        "budget": 0,
                        "currency": "MAD",
                        "deadline": "",
                        "publishDate": parse_date(entry.get("published", "")) or "",
                        "status": "open",
                        "description": {"en": entry.get("summary", title), "ar": entry.get("summary", title), "fr": entry.get("summary", title)},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": entry.get("link", ""),
                    }
                    tenders.append(tender)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Morocco scraper error: {e}")

    logger.info(f"Morocco total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "morocco")
    print(f"Scraped {len(results)} tenders from Morocco")
