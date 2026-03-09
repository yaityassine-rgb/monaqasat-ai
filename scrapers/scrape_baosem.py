"""
Scraper for Algeria BAOSEM Energy Sector Tenders.
Source: https://baosem.com/site/tenders/?lang=en
RSS:    https://baosem.com/site/feed/?lang=en

BAOSEM publishes Sonatrach + Sonelgaz tenders for the Algerian energy sector.
WordPress-based site. We try the WP REST API first, then RSS feed, then HTML.
"""

import logging
import re
import time

import feedparser
import requests
from bs4 import BeautifulSoup

from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("baosem")

BASE_URL = "https://baosem.com/site"
TENDERS_URL = f"{BASE_URL}/tenders/?lang=en"
TENDERS_URL_FR = f"{BASE_URL}/appels-doffres/"
RSS_URL = f"{BASE_URL}/feed/?lang=en"
RSS_URL_FR = f"{BASE_URL}/feed/"
WP_API = f"{BASE_URL}/wp-json/wp/v2/posts"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json",
    "Accept-Language": "en,fr,ar",
}


def _extract_ref(text: str) -> str:
    """Try to extract a tender reference number from the title/text."""
    patterns = [
        r"(?:N[°o]?|No\.?|Ref\.?|Tender\s*(?:No\.?)?)\s*[:.]?\s*([A-Z0-9][\w\-/]+)",
        r"([A-Z]{2,5}[-/]\d{2,}[-/]?\w*)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _scrape_wp_api() -> list[dict]:
    """Try to scrape tenders from WordPress REST API."""
    tenders = []
    try:
        for page in range(1, 6):
            resp = requests.get(
                WP_API,
                params={
                    "per_page": 100,
                    "page": page,
                    "lang": "en",
                    "_fields": "id,title,link,date,excerpt,categories",
                },
                headers=HEADERS,
                timeout=30,
            )
            if resp.status_code != 200:
                break

            items = resp.json()
            if not items:
                break

            for item in items:
                raw_title = item.get("title", {}).get("rendered", "")
                title = BeautifulSoup(raw_title, "html.parser").get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                link = item.get("link", "")
                date_str = item.get("date", "")
                excerpt_html = item.get("excerpt", {}).get("rendered", "")
                excerpt = BeautifulSoup(excerpt_html, "html.parser").get_text(strip=True)

                ref = _extract_ref(title) or str(item.get("id", ""))
                pub_date = parse_date(date_str) or ""

                tender = {
                    "id": generate_id("baosem", ref, ""),
                    "source": "BAOSEM Algeria",
                    "sourceRef": ref,
                    "sourceLanguage": "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "BAOSEM / Sonatrach / Sonelgaz",
                        "ar": "سوناطراك / سونلغاز",
                        "fr": "BAOSEM / Sonatrach / Sonelgaz",
                    },
                    "country": "Algeria",
                    "countryCode": "DZ",
                    "sector": classify_sector(title + " " + excerpt + " energy oil gas"),
                    "budget": 0,
                    "currency": "DZD",
                    "deadline": "",
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {
                        "en": excerpt or title,
                        "ar": excerpt or title,
                        "fr": excerpt or title,
                    },
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link or TENDERS_URL,
                }
                tenders.append(tender)

            time.sleep(2)

    except Exception as e:
        logger.warning(f"BAOSEM WP API error: {e}")

    return tenders


def _scrape_rss() -> list[dict]:
    """Try to scrape tenders from RSS feeds."""
    tenders = []
    for rss_url in [RSS_URL, RSS_URL_FR]:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title = entry.get("title", "")
                if not title or len(title) < 5:
                    continue

                link = entry.get("link", "")
                summary = entry.get("summary", "")
                pub_date = entry.get("published", "")

                ref = _extract_ref(title) or title[:60]
                parsed_date = parse_date(pub_date) or ""

                tender = {
                    "id": generate_id("baosem_rss", ref, ""),
                    "source": "BAOSEM Algeria",
                    "sourceRef": ref,
                    "sourceLanguage": "fr" if "lang=en" not in rss_url else "en",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "BAOSEM / Sonatrach / Sonelgaz",
                        "ar": "سوناطراك / سونلغاز",
                        "fr": "BAOSEM / Sonatrach / Sonelgaz",
                    },
                    "country": "Algeria",
                    "countryCode": "DZ",
                    "sector": classify_sector(title + " " + summary + " energy"),
                    "budget": 0,
                    "currency": "DZD",
                    "deadline": "",
                    "publishDate": parsed_date,
                    "status": "open",
                    "description": {
                        "en": summary or title,
                        "ar": summary or title,
                        "fr": summary or title,
                    },
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link or TENDERS_URL,
                }
                tenders.append(tender)
        except Exception as e:
            logger.warning(f"BAOSEM RSS ({rss_url}) error: {e}")
    return tenders


def _scrape_html() -> list[dict]:
    """Scrape tenders from the HTML tenders page."""
    tenders = []
    for url in [TENDERS_URL, TENDERS_URL_FR]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"BAOSEM HTML {url} returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Look for tender entries in various WordPress structures
            for selector in [
                "article",
                ".entry-content .tender-item",
                ".entry-content table tr",
                ".post",
                ".hentry",
                ".type-post",
                ".wp-block-table tr",
            ]:
                items = soup.select(selector)
                if not items or len(items) < 1:
                    continue

                for item in items:
                    # Get title from heading or first strong/link
                    title_el = (
                        item.select_one("h2 a, h3 a, h4 a, .entry-title a")
                        or item.select_one("h2, h3, h4, .entry-title")
                        or item.select_one("a")
                    )
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    if len(title) < 5:
                        continue

                    link = ""
                    if title_el.name == "a":
                        link = title_el.get("href", "")
                    else:
                        a = title_el.select_one("a")
                        if a:
                            link = a.get("href", "")

                    if link and not link.startswith("http"):
                        link = f"https://baosem.com{link}"

                    # Try to get date
                    date_el = item.select_one("time, .entry-date, .published")
                    pub_date = ""
                    if date_el:
                        pub_date = (
                            parse_date(date_el.get("datetime", ""))
                            or parse_date(date_el.get_text(strip=True))
                            or ""
                        )

                    # Get description/excerpt
                    desc_el = item.select_one(
                        ".entry-summary, .entry-content, .excerpt, p"
                    )
                    desc = desc_el.get_text(strip=True)[:500] if desc_el else title

                    ref = _extract_ref(title) or title[:60]

                    tender = {
                        "id": generate_id("baosem_html", ref, ""),
                        "source": "BAOSEM Algeria",
                        "sourceRef": ref,
                        "sourceLanguage": "fr"
                        if "appels-doffres" in url
                        else "en",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": "BAOSEM / Sonatrach / Sonelgaz",
                            "ar": "سوناطراك / سونلغاز",
                            "fr": "BAOSEM / Sonatrach / Sonelgaz",
                        },
                        "country": "Algeria",
                        "countryCode": "DZ",
                        "sector": classify_sector(
                            title + " " + desc + " energy oil gas"
                        ),
                        "budget": 0,
                        "currency": "DZD",
                        "deadline": "",
                        "publishDate": pub_date,
                        "status": "open",
                        "description": {
                            "en": desc,
                            "ar": desc,
                            "fr": desc,
                        },
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": link or url,
                    }
                    tenders.append(tender)

                if tenders:
                    break  # Found a working selector

            time.sleep(2)

        except Exception as e:
            logger.warning(f"BAOSEM HTML scrape ({url}): {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape BAOSEM Algeria energy sector tenders."""
    all_tenders: list[dict] = []
    seen: set[str] = set()

    # Try all methods
    for method_name, method in [
        ("WP API", _scrape_wp_api),
        ("RSS", _scrape_rss),
        ("HTML", _scrape_html),
    ]:
        try:
            results = method()
            logger.info(f"BAOSEM {method_name}: {len(results)} tenders")
            for t in results:
                key = t.get("sourceRef", "") or t["title"]["en"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
        except Exception as e:
            logger.error(f"BAOSEM {method_name} failed: {e}")

    if not all_tenders:
        logger.warning(
            "BAOSEM: No tenders found. The site may require JavaScript "
            "rendering or tenders may be behind a login wall."
        )

    logger.info(f"BAOSEM total: {len(all_tenders)}")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "baosem")
    print(f"Scraped {len(results)} tenders from BAOSEM Algeria")
