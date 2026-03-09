"""
Scraper for UNDP (UN Development Programme) Procurement — RSS feeds.
Source: https://procurement-notices.undp.org/
UNDP provides per-country RSS feeds that are confirmed working and updated hourly.
"""

import logging
import feedparser
from config import MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("undp")

# UNDP uses ISO 3166 three-letter country codes for RSS feeds
MENA_RSS = {
    "MAR": "MA",  # Morocco
    "SAU": "SA",  # Saudi Arabia
    "ARE": "AE",  # UAE
    "EGY": "EG",  # Egypt
    "KWT": "KW",  # Kuwait
    "QAT": "QA",  # Qatar
    "BHR": "BH",  # Bahrain
    "OMN": "OM",  # Oman
    "JOR": "JO",  # Jordan
    "TUN": "TN",  # Tunisia
    "DZA": "DZ",  # Algeria
    "LBY": "LY",  # Libya
    "IRQ": "IQ",  # Iraq
    "LBN": "LB",  # Lebanon
    "PSE": "PS",  # Palestine
    "SDN": "SD",  # Sudan
    "YEM": "YE",  # Yemen
    "MRT": "MR",  # Mauritania
    "RAB": "XX",  # Arab States (regional)
}

RSS_BASE = "https://procurement-notices.undp.org/rss_feeds"


def scrape() -> list[dict]:
    """Scrape UNDP procurement notices from RSS feeds for all MENA countries."""
    tenders = []

    for alpha3, iso2 in MENA_RSS.items():
        rss_url = f"{RSS_BASE}/{alpha3}.xml"
        try:
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logger.info(f"UNDP {alpha3}: 0 entries")
                continue

            country_name = MENA_COUNTRIES.get(iso2, "MENA Region")

            for entry in feed.entries:
                title = entry.get("title", "")
                if not title or len(title) < 10:
                    continue

                description = entry.get("description", entry.get("summary", ""))
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                # Extract deadline from description if present
                deadline = ""
                desc_lower = description.lower()
                if "deadline" in desc_lower:
                    # Try to find deadline date in description
                    import re
                    deadline_match = re.search(r'deadline[:\s]*(\d{1,2}[\s/-]\w+[\s/-]\d{2,4})', desc_lower)
                    if deadline_match:
                        deadline = parse_date(deadline_match.group(1)) or ""

                tender = {
                    "id": generate_id("undp", title[:80], iso2),
                    "source": "UNDP",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "UNDP",
                        "ar": "برنامج الأمم المتحدة الإنمائي",
                        "fr": "PNUD",
                    },
                    "country": country_name,
                    "countryCode": iso2,
                    "sector": classify_sector(title + " " + description),
                    "budget": 0,
                    "currency": "USD",
                    "deadline": deadline,
                    "publishDate": parse_date(published) or "",
                    "status": "open",
                    "description": {
                        "en": description[:500] if description else title,
                        "ar": description[:500] if description else title,
                        "fr": description[:500] if description else title,
                    },
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link,
                }
                tenders.append(tender)

            logger.info(f"UNDP {alpha3} ({country_name}): {len(feed.entries)} entries")

        except Exception as e:
            logger.error(f"UNDP {alpha3} error: {e}")

    logger.info(f"UNDP total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "undp")
    print(f"Scraped {len(results)} tenders from UNDP")
