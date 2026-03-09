"""
Scraper for UNGM (United Nations Global Marketplace).
Source: https://www.ungm.org/Public/Notice
Publicly accessible API with MENA tenders from UN agencies.
"""

import requests
import logging
from config import HEADERS, MENA_COUNTRIES
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("ungm")

API_URL = "https://www.ungm.org/api/Public/Notice"

MENA_NAMES = set(MENA_COUNTRIES.values()) | {
    "Morocco", "Kingdom of Morocco",
    "Saudi Arabia", "Kingdom of Saudi Arabia",
    "United Arab Emirates",
    "Egypt", "Arab Republic of Egypt",
    "Kuwait", "State of Kuwait",
    "Qatar", "State of Qatar",
    "Bahrain", "Kingdom of Bahrain",
    "Oman", "Sultanate of Oman",
    "Jordan", "Hashemite Kingdom of Jordan",
    "Tunisia", "Republic of Tunisia",
    "Algeria", "People's Democratic Republic of Algeria",
    "Libya", "State of Libya",
    "Iraq", "Republic of Iraq",
    "Lebanon", "Lebanese Republic",
    "Sudan", "Republic of Sudan",
    "Yemen", "Republic of Yemen",
}

# Map country names to codes
NAME_TO_CODE: dict[str, str] = {}
for code, name in MENA_COUNTRIES.items():
    NAME_TO_CODE[name.lower()] = code


def get_country_code(country_name: str) -> str:
    """Map country name to ISO code."""
    name_lower = country_name.lower().strip()
    for full_name, code in NAME_TO_CODE.items():
        if full_name in name_lower or name_lower in full_name:
            return code
    # Fallback mappings
    if "morocco" in name_lower or "maroc" in name_lower:
        return "MA"
    if "saudi" in name_lower:
        return "SA"
    if "emirates" in name_lower or "uae" in name_lower:
        return "AE"
    if "egypt" in name_lower:
        return "EG"
    if "kuwait" in name_lower:
        return "KW"
    if "qatar" in name_lower:
        return "QA"
    if "bahrain" in name_lower:
        return "BH"
    if "oman" in name_lower:
        return "OM"
    if "jordan" in name_lower:
        return "JO"
    if "tunisia" in name_lower or "tunisie" in name_lower:
        return "TN"
    if "algeria" in name_lower or "algérie" in name_lower:
        return "DZ"
    if "libya" in name_lower or "libye" in name_lower:
        return "LY"
    if "iraq" in name_lower:
        return "IQ"
    if "lebanon" in name_lower or "liban" in name_lower:
        return "LB"
    if "sudan" in name_lower or "soudan" in name_lower:
        return "SD"
    if "yemen" in name_lower or "yémen" in name_lower:
        return "YE"
    return "XX"


def scrape() -> list[dict]:
    """Scrape UNGM notices for MENA region."""
    tenders = []

    # UNGM API endpoint for public notices
    params = {
        "PageIndex": 0,
        "PageSize": 100,
        "SortField": "DatePublished",
        "SortAscending": False,
    }

    try:
        # Try the search endpoint
        resp = requests.post(
            API_URL,
            json=params,
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(f"UNGM API returned {resp.status_code}, trying alternate approach")
            return scrape_rss_fallback()

        data = resp.json()
        notices = data if isinstance(data, list) else data.get("Results", data.get("results", []))

        for notice in notices:
            title = notice.get("Title", notice.get("title", ""))
            org = notice.get("AgencyName", notice.get("Organization", ""))
            country_raw = notice.get("BeneficiaryCountry", notice.get("Country", ""))

            # Check if MENA
            if not any(name.lower() in (country_raw + " " + title + " " + org).lower() for name in MENA_NAMES):
                continue

            country_code = get_country_code(country_raw)
            deadline_raw = notice.get("Deadline", notice.get("DeadlineDate", ""))
            publish_raw = notice.get("DatePublished", notice.get("PublishedDate", ""))
            description = notice.get("Description", notice.get("Summary", title))

            tender = {
                "id": generate_id("ungm", title, org),
                "source": "UNGM",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {"en": org, "ar": org, "fr": org},
                "country": MENA_COUNTRIES.get(country_code, country_raw),
                "countryCode": country_code,
                "sector": classify_sector(title + " " + description),
                "budget": 0,
                "currency": "USD",
                "deadline": parse_date(str(deadline_raw)) or "",
                "publishDate": parse_date(str(publish_raw)) or "",
                "status": "open",
                "description": {"en": description, "ar": description, "fr": description},
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": notice.get("Url", notice.get("url", "")),
            }
            tenders.append(tender)

        logger.info(f"Found {len(tenders)} MENA tenders from UNGM API")

    except Exception as e:
        logger.error(f"UNGM API error: {e}")
        return scrape_rss_fallback()

    return tenders


def scrape_rss_fallback() -> list[dict]:
    """Fallback: scrape UNGM via their RSS/public listing."""
    import feedparser

    tenders = []
    rss_url = "https://www.ungm.org/Public/Notice/RSSFeed"

    try:
        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            link = entry.get("link", "")
            published = entry.get("published", "")

            # Check MENA relevance
            full_text = f"{title} {summary}".lower()
            is_mena = any(name.lower() in full_text for name in MENA_NAMES)

            if not is_mena:
                continue

            # Determine country
            country_code = "XX"
            for name in MENA_NAMES:
                if name.lower() in full_text:
                    country_code = get_country_code(name)
                    break

            tender = {
                "id": generate_id("ungm", title, "UN"),
                "source": "UNGM",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {"en": "United Nations", "ar": "الأمم المتحدة", "fr": "Nations Unies"},
                "country": MENA_COUNTRIES.get(country_code, ""),
                "countryCode": country_code,
                "sector": classify_sector(title + " " + summary),
                "budget": 0,
                "currency": "USD",
                "deadline": "",
                "publishDate": parse_date(published) or "",
                "status": "open",
                "description": {"en": summary, "ar": summary, "fr": summary},
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": link,
            }
            tenders.append(tender)

        logger.info(f"Found {len(tenders)} MENA tenders from UNGM RSS")

    except Exception as e:
        logger.error(f"UNGM RSS error: {e}")

    return tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "ungm")
    print(f"Scraped {len(results)} tenders from UNGM")
