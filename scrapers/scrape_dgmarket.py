"""
Scraper for dgMarket (Development Gateway).
Source: https://www.dgmarket.com
Major aggregator of international development tenders. Free RSS feeds available.
"""

import feedparser
import logging
from config import MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("dgmarket")

# dgMarket RSS feeds for MENA countries
# These are publicly accessible RSS feeds
FEEDS = {
    "MA": "https://www.dgmarket.com/tenders/RssFeed.do?country=MA",
    "SA": "https://www.dgmarket.com/tenders/RssFeed.do?country=SA",
    "AE": "https://www.dgmarket.com/tenders/RssFeed.do?country=AE",
    "EG": "https://www.dgmarket.com/tenders/RssFeed.do?country=EG",
    "KW": "https://www.dgmarket.com/tenders/RssFeed.do?country=KW",
    "QA": "https://www.dgmarket.com/tenders/RssFeed.do?country=QA",
    "BH": "https://www.dgmarket.com/tenders/RssFeed.do?country=BH",
    "OM": "https://www.dgmarket.com/tenders/RssFeed.do?country=OM",
    "JO": "https://www.dgmarket.com/tenders/RssFeed.do?country=JO",
    "TN": "https://www.dgmarket.com/tenders/RssFeed.do?country=TN",
    "DZ": "https://www.dgmarket.com/tenders/RssFeed.do?country=DZ",
    "LY": "https://www.dgmarket.com/tenders/RssFeed.do?country=LY",
    "IQ": "https://www.dgmarket.com/tenders/RssFeed.do?country=IQ",
    "LB": "https://www.dgmarket.com/tenders/RssFeed.do?country=LB",
}


def scrape() -> list[dict]:
    """Scrape dgMarket RSS feeds for MENA tenders."""
    tenders = []

    for country_code, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning(f"dgMarket feed error for {country_code}: {feed.bozo_exception}")
                continue

            country_name = MENA_COUNTRIES.get(country_code, "")

            for entry in feed.entries:
                title = entry.get("title", "")
                if not title:
                    continue

                summary = entry.get("summary", entry.get("description", ""))
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                # Try to extract deadline from summary
                deadline = ""
                if "deadline" in summary.lower():
                    # Simple extraction
                    parts = summary.lower().split("deadline")
                    if len(parts) > 1:
                        deadline_str = parts[1][:30].strip(": ")
                        deadline = parse_date(deadline_str) or ""

                tender = {
                    "id": generate_id("dgm", title[:100], country_code),
                    "source": "dgMarket",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": f"Government of {country_name}",
                        "ar": f"حكومة {country_name}",
                        "fr": f"Gouvernement du {country_name}",
                    },
                    "country": country_name,
                    "countryCode": country_code,
                    "sector": classify_sector(title + " " + summary),
                    "budget": 0,
                    "currency": "USD",
                    "deadline": deadline,
                    "publishDate": parse_date(published) or "",
                    "status": "open",
                    "description": {"en": summary or title, "ar": summary or title, "fr": summary or title},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link,
                }
                tenders.append(tender)

            logger.info(f"dgMarket {country_code}: {len(feed.entries)} entries")

        except Exception as e:
            logger.error(f"dgMarket error for {country_code}: {e}")
            continue

    logger.info(f"Total: {len(tenders)} tenders from dgMarket")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "dgmarket")
    print(f"Scraped {len(results)} tenders from dgMarket")
