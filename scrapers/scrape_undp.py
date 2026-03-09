"""
Scraper for UNDP (UN Development Programme) Procurement — RSS feeds.
Source: https://procurement-notices.undp.org/

Parses UNDP reference codes (e.g. "UNDP-MUS-00205") to cross-validate
country attribution against the RSS feed code.
"""

import logging
import re
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

# UNDP 3-letter codes found in reference numbers (ISO 3166-1 alpha-3)
_UNDP_REF_TO_ISO2: dict[str, str] = {
    "MAR": "MA", "SAU": "SA", "ARE": "AE", "EGY": "EG",
    "KWT": "KW", "QAT": "QA", "BHR": "BH", "OMN": "OM",
    "JOR": "JO", "TUN": "TN", "DZA": "DZ", "LBY": "LY",
    "IRQ": "IQ", "LBN": "LB", "PSE": "PS", "SDN": "SD",
    "YEM": "YE", "MRT": "MR",
    # Non-MENA codes that appear in MENA feeds (cross-posted)
    "MUS": "",   # Mauritius — NOT Morocco
    "MDG": "",   # Madagascar
    "COM": "",   # Comoros
    "SYC": "",   # Seychelles
    "DJI": "",   # Djibouti
    "SOM": "",   # Somalia
    "ETH": "",   # Ethiopia
    "KEN": "",   # Kenya
    "UGA": "",   # Uganda
    "TZA": "",   # Tanzania
    "COD": "",   # DRC
    "COG": "",   # Congo
    "CMR": "",   # Cameroon
    "NGA": "",   # Nigeria
    "SEN": "",   # Senegal
    "MLI": "",   # Mali
    "NER": "",   # Niger
    "TCD": "",   # Chad
    "BFA": "",   # Burkina Faso
}

RSS_BASE = "https://procurement-notices.undp.org/rss_feeds"

# Pattern to extract UNDP reference code like "UNDP-MUS-00205"
_REF_PATTERN = re.compile(r'UNDP-([A-Z]{3})-\d+', re.IGNORECASE)


def _extract_ref_country(title: str, description: str) -> str:
    """Extract country code from UNDP reference pattern in title/description.

    Returns ISO2 code if found in MENA, empty string if non-MENA, None if no match.
    """
    for text in (title, description):
        match = _REF_PATTERN.search(text)
        if match:
            alpha3 = match.group(1).upper()
            return _UNDP_REF_TO_ISO2.get(alpha3, "")
    return None  # type: ignore


def scrape() -> list[dict]:
    """Scrape UNDP procurement notices from RSS feeds for all MENA countries."""
    tenders: list[dict] = []

    for alpha3, iso2 in MENA_RSS.items():
        rss_url = f"{RSS_BASE}/{alpha3}.xml"
        try:
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                logger.info(f"UNDP {alpha3}: 0 entries")
                continue

            feed_country_name = MENA_COUNTRIES.get(iso2, "MENA Region")

            for entry in feed.entries:
                title = entry.get("title", "")
                if not title or len(title) < 10:
                    continue

                description = entry.get("description", entry.get("summary", ""))
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                # Cross-validate: check if UNDP ref code matches a different country
                ref_country = _extract_ref_country(title, description)
                if ref_country is not None:
                    if ref_country == "":
                        # Reference points to a non-MENA country (e.g. MUS=Mauritius)
                        logger.debug(f"UNDP: skipping non-MENA ref in {alpha3} feed: {title[:60]}")
                        continue
                    # Use the country from the reference code (more accurate)
                    actual_code = ref_country
                    actual_name = MENA_COUNTRIES.get(actual_code, feed_country_name)
                else:
                    actual_code = iso2
                    actual_name = feed_country_name

                # Skip regional feed entries that couldn't be attributed
                if actual_code == "XX":
                    continue

                # Extract deadline from description if present
                deadline = ""
                desc_lower = description.lower()
                if "deadline" in desc_lower:
                    deadline_match = re.search(r'deadline[:\s]*(\d{1,2}[\s/-]\w+[\s/-]\d{2,4})', desc_lower)
                    if deadline_match:
                        deadline = parse_date(deadline_match.group(1)) or ""

                tender = {
                    "id": generate_id("undp", title[:80], ""),
                    "source": "UNDP",
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "UNDP",
                        "ar": "برنامج الأمم المتحدة الإنمائي",
                        "fr": "PNUD",
                    },
                    "country": actual_name,
                    "countryCode": actual_code,
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

            logger.info(f"UNDP {alpha3} ({feed_country_name}): {len(feed.entries)} entries")

        except Exception as e:
            logger.error(f"UNDP {alpha3} error: {e}")

    logger.info(f"UNDP total: {len(tenders)}")
    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "undp")
    print(f"Scraped {len(results)} tenders from UNDP")
