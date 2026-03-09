"""
Scraper for Kurdistan Regional Government E-Procurement.
Sources:
  - https://keps.digital.gov.krd/ (e-procurement portal)
  - https://gov.krd/english/hot-topics/tenders/ (tender listings)

Both sites use Cloudflare bot protection. The gov.krd site returns a
Cloudflare challenge page. This scraper attempts multiple approaches
and falls back gracefully if blocked.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

logger = logging.getLogger("kurdistan")

KEPS_URL = "https://keps.digital.gov.krd/"
GOV_KRD_URL = "https://gov.krd/english/hot-topics/tenders/"
GOV_KRD_API = "https://gov.krd/wp-json/wp/v2/posts"  # WordPress REST API attempt
GOV_KRD_TENDER_SEARCH = "https://gov.krd/wp-json/wp/v2/posts?search=tender&per_page=50"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,ku;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}


def _get(url, **kwargs):
    """HTTP GET with TLS fingerprint impersonation if available."""
    if HAS_CURL_CFFI:
        return curl_requests.get(url, impersonate="chrome131", **kwargs)
    return requests.get(url, **kwargs)


def _scrape_gov_krd_html() -> list[dict]:
    """Scrape the gov.krd tenders page."""
    tenders: list[dict] = []

    try:
        resp = _get(GOV_KRD_URL, headers=HEADERS, timeout=30,
                    allow_redirects=True)

        if resp.status_code == 403:
            logger.warning("Kurdistan gov.krd: Cloudflare protection (403)")
            return tenders

        if resp.status_code != 200:
            logger.warning(f"Kurdistan gov.krd: HTTP {resp.status_code}")
            return tenders

        # Check for Cloudflare challenge
        if "challenge-platform" in resp.text or "Just a moment" in resp.text:
            logger.warning("Kurdistan gov.krd: Cloudflare JS challenge detected")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # gov.krd is a WordPress site, look for post/article elements
        articles = soup.select("article, .post, .entry, .tender-item, "
                               ".hot-topic-item, [class*='tender']")

        for article in articles:
            title_el = article.select_one("h2 a, h3 a, .entry-title a, "
                                          ".post-title a, a[href]")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            href = title_el.get("href", "")
            if href and not href.startswith("http"):
                href = "https://gov.krd" + href

            article_text = article.get_text(" ", strip=True)

            # Extract date
            date_el = article.select_one("time, .date, .entry-date, .post-date")
            pub_date = ""
            if date_el:
                dt = date_el.get("datetime", "") or date_el.get_text(strip=True)
                pub_date = parse_date(dt) or ""

            # Extract reference
            ref_match = re.search(r'(?:No|Ref|#)[.\s:]*([A-Z0-9\-/]+)',
                                  article_text, re.I)
            ref = ref_match.group(1) if ref_match else title[:60]

            tender = {
                "id": generate_id("kurdistan", ref, ""),
                "source": "Kurdistan KRG",
                "sourceRef": ref,
                "sourceLanguage": "ar",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Kurdistan Regional Government",
                    "ar": "حكومة إقليم كردستان",
                    "fr": "Gouvernement régional du Kurdistan",
                },
                "country": "Iraq",
                "countryCode": "IQ",
                "sector": classify_sector(title),
                "budget": 0,
                "currency": "IQD",
                "deadline": "",
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": article_text[:500],
                    "ar": article_text[:500],
                    "fr": article_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or GOV_KRD_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"Kurdistan gov.krd error: {e}")

    return tenders


def _scrape_gov_krd_api() -> list[dict]:
    """Try WordPress REST API on gov.krd to find tender posts."""
    tenders: list[dict] = []

    try:
        # Try searching for tender-related posts
        params = {
            "search": "tender",
            "per_page": 50,
            "orderby": "date",
            "order": "desc",
        }

        resp = _get(GOV_KRD_API, params=params, headers={
            **HEADERS,
            "Accept": "application/json",
        }, timeout=15)

        if resp.status_code == 403:
            logger.info("Kurdistan WP API: Cloudflare blocked")
            return tenders

        if resp.status_code != 200:
            logger.debug(f"Kurdistan WP API: HTTP {resp.status_code}")
            return tenders

        posts = resp.json()
        if not isinstance(posts, list):
            return tenders

        logger.info(f"Kurdistan WP API: Found {len(posts)} posts")

        for post in posts:
            title_data = post.get("title", {})
            title = title_data.get("rendered", "") if isinstance(title_data, dict) else str(title_data)
            # Clean HTML from title
            title = BeautifulSoup(title, "lxml").get_text(strip=True)
            if not title:
                continue

            post_id = str(post.get("id", ""))
            link = post.get("link", "")
            pub_date = parse_date(post.get("date", "")) or ""

            # Get description from excerpt
            excerpt_data = post.get("excerpt", {})
            description = excerpt_data.get("rendered", "") if isinstance(excerpt_data, dict) else ""
            description = BeautifulSoup(description, "lxml").get_text(strip=True)
            if not description:
                description = title

            tender = {
                "id": generate_id("kurdistan", post_id or title[:60], ""),
                "source": "Kurdistan KRG",
                "sourceRef": post_id,
                "sourceLanguage": "ar",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Kurdistan Regional Government",
                    "ar": "حكومة إقليم كردستان",
                    "fr": "Gouvernement régional du Kurdistan",
                },
                "country": "Iraq",
                "countryCode": "IQ",
                "sector": classify_sector(title + " " + description),
                "budget": 0,
                "currency": "IQD",
                "deadline": "",
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": description[:500],
                    "ar": description[:500],
                    "fr": description[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": link or GOV_KRD_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"Kurdistan WP API error: {e}")

    return tenders


def _scrape_keps_portal() -> list[dict]:
    """Try to scrape the KEPS e-procurement portal."""
    tenders: list[dict] = []

    try:
        resp = _get(KEPS_URL, headers=HEADERS, timeout=30,
                    allow_redirects=True)

        if resp.status_code == 403:
            logger.warning("KEPS portal: Cloudflare protection (403)")
            return tenders

        if resp.status_code != 200:
            logger.warning(f"KEPS portal: HTTP {resp.status_code}")
            return tenders

        if "challenge-platform" in resp.text or "Just a moment" in resp.text:
            logger.warning("KEPS portal: Cloudflare JS challenge detected")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Look for tender listing elements
        items = soup.select("table tr, .tender-item, .opportunity, "
                            "[class*='tender'], article, .card")

        for item in items:
            title_el = item.select_one("a, h2, h3, .title, td:nth-child(2)")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            link_el = item.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = KEPS_URL.rstrip("/") + "/" + href.lstrip("/")

            item_text = item.get_text(" ", strip=True)
            ref_match = re.search(r'([A-Z0-9]{2,}-\d+)', item_text)
            ref = ref_match.group(1) if ref_match else title[:60]

            tender = {
                "id": generate_id("keps", ref, ""),
                "source": "Kurdistan KRG",
                "sourceRef": ref,
                "sourceLanguage": "ar",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Kurdistan Regional Government - E-Procurement",
                    "ar": "حكومة إقليم كردستان - المشتريات الإلكترونية",
                    "fr": "Gouvernement régional du Kurdistan - E-Procurement",
                },
                "country": "Iraq",
                "countryCode": "IQ",
                "sector": classify_sector(title),
                "budget": 0,
                "currency": "IQD",
                "deadline": "",
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": item_text[:500],
                    "ar": item_text[:500],
                    "fr": item_text[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href or KEPS_URL,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"KEPS portal error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape Kurdistan Regional Government tender listings."""
    html_tenders = _scrape_gov_krd_html()
    time.sleep(2)
    api_tenders = _scrape_gov_krd_api()
    time.sleep(2)
    keps_tenders = _scrape_keps_portal()

    # Merge and deduplicate
    seen: set[str] = set()
    all_tenders: list[dict] = []
    for t in html_tenders + api_tenders + keps_tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    logger.info(f"Kurdistan total: {len(all_tenders)} tenders "
                f"(HTML: {len(html_tenders)}, API: {len(api_tenders)}, "
                f"KEPS: {len(keps_tenders)})")

    if not all_tenders:
        logger.warning("Kurdistan: No tenders found. Both gov.krd and "
                        "keps.digital.gov.krd use Cloudflare bot protection "
                        "that blocks automated requests. Consider using a "
                        "headless browser (Playwright/Selenium) to bypass "
                        "the JS challenge.")

    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "kurdistan")
    print(f"Scraped {len(results)} tenders from Kurdistan KRG")
