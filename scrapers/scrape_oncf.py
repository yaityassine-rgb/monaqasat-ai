"""
Scraper for Morocco ONCF (Office National des Chemins de Fer) Tenders.
Source: https://www.oncf.ma/fr/Entreprise/Fournisseurs/Appels-d-offres

ONCF uses a modern eZ Platform CMS that loads tender listings via AJAX.
The tender list is populated dynamically on the client side through filters
(segment, famille, date). The RSS feed only contains site pages, not tenders.

Strategy:
  1. Try to POST/GET the AJAX endpoint that populates the tender list
  2. Fall back to scraping the marchespublics.gov.ma portal (which ONCF links to)
  3. Scrape any tenders visible in the static HTML
"""

import logging
import re
import time
import urllib3

import requests
from bs4 import BeautifulSoup

# ONCF's SSL certificate sometimes fails verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("oncf")

BASE_URL = "https://www.oncf.ma"
TENDERS_PAGE = f"{BASE_URL}/fr/Entreprise/Fournisseurs/Appels-d-offres"
RSS_URL = f"{BASE_URL}/fr/rss/feed/oncf"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json",
    "Accept-Language": "fr,en,ar",
}

# ONCF tender segments
SEGMENTS = [
    "Energie",
    "Equipements",
    "Fournitures ferroviaires",
    "Fournitures générales",
    "Fournitures industrielles",
    "Informatique et télécommunication",
    "Matériel roulant",
    "Prestations intellectuelles",
    "Prestations de services",
    "Travaux BTP",
    "Travaux ferroviaires",
]


def _scrape_ajax_tenders() -> list[dict]:
    """Attempt to scrape tenders from ONCF's AJAX/API endpoints."""
    tenders = []

    # Try common eZ Platform / Symfony API patterns
    api_endpoints = [
        f"{BASE_URL}/api/ezp/v2/content/views",
        f"{BASE_URL}/api/content/search",
        f"{BASE_URL}/fr/Entreprise/Fournisseurs/Appels-d-offres?ajax=1",
        f"{BASE_URL}/fr/Entreprise/Fournisseurs/Appels-d-offres?page=1&format=json",
    ]

    session = requests.Session()
    session.headers.update(HEADERS)
    session.verify = False  # ONCF SSL cert sometimes fails

    # First get the main page to establish a session/CSRF
    try:
        session.get(TENDERS_PAGE, timeout=30)
    except Exception:
        pass

    for endpoint in api_endpoints:
        try:
            for accept in [
                "application/json",
                "application/vnd.ez.api.ContentList+json",
            ]:
                resp = session.get(
                    endpoint,
                    headers={"Accept": accept, "X-Requested-With": "XMLHttpRequest"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, dict):
                            items = data.get("items", data.get("results", data.get("ContentList", {}).get("ContentInfo", [])))
                            if isinstance(items, list) and items:
                                logger.info(
                                    f"ONCF API found {len(items)} items from {endpoint}"
                                )
                                for item in items:
                                    title = ""
                                    if isinstance(item, dict):
                                        title = (
                                            item.get("title", "")
                                            or item.get("name", "")
                                            or item.get("Content", {}).get("Name", "")
                                        )
                                    if not title or len(title) < 5:
                                        continue

                                    link = item.get("url", item.get("link", ""))
                                    if link and not link.startswith("http"):
                                        link = f"{BASE_URL}{link}"

                                    ref = item.get("ref", item.get("id", title[:60]))

                                    tender = {
                                        "id": generate_id("oncf", str(ref), ""),
                                        "source": "ONCF Morocco",
                                        "sourceRef": str(ref),
                                        "sourceLanguage": "fr",
                                        "title": {
                                            "en": title,
                                            "ar": title,
                                            "fr": title,
                                        },
                                        "organization": {
                                            "en": "ONCF - Morocco Railways",
                                            "ar": "المكتب الوطني للسكك الحديدية",
                                            "fr": "ONCF - Office National des Chemins de Fer",
                                        },
                                        "country": "Morocco",
                                        "countryCode": "MA",
                                        "sector": classify_sector(
                                            title + " railway transport"
                                        ),
                                        "budget": 0,
                                        "currency": "MAD",
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
                                        "sourceUrl": link or TENDERS_PAGE,
                                    }
                                    tenders.append(tender)
                                return tenders
                    except (ValueError, KeyError):
                        pass
            time.sleep(1)
        except Exception as e:
            logger.debug(f"ONCF API endpoint {endpoint}: {e}")

    return tenders


def _scrape_html_page() -> list[dict]:
    """Scrape any tender data visible in the static HTML page."""
    tenders = []

    try:
        resp = requests.get(TENDERS_PAGE, headers=HEADERS, timeout=30, verify=False)
        if resp.status_code != 200:
            logger.warning(f"ONCF HTML page returned {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # ONCF loads tenders dynamically. Look for any rendered tender items.
        # Possible selectors for tender cards/list items
        for selector in [
            ".ao-card",
            ".ao-item",
            ".tender-card",
            ".result-item",
            ".appel-offre",
            ".card",
            "table tbody tr",
            ".list-group-item",
            ".search-result",
        ]:
            items = soup.select(selector)
            if items and len(items) > 0:
                logger.info(f"ONCF found {len(items)} items with selector: {selector}")
                for item in items:
                    title_el = item.select_one(
                        "h3, h4, h5, .title, .card-title, a"
                    )
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if len(title) < 5:
                        continue

                    link = ""
                    a = item.select_one("a[href]")
                    if a:
                        href = a.get("href", "")
                        link = (
                            href if href.startswith("http") else f"{BASE_URL}{href}"
                        )

                    # Look for date and reference
                    text = item.get_text(strip=True)
                    ref_match = re.search(r"(AO[/-]?\d[\w\-/]*)", text)
                    ref = ref_match.group(1) if ref_match else title[:60]

                    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
                    deadline = parse_date(date_match.group(1)) if date_match else ""

                    tender = {
                        "id": generate_id("oncf", ref, ""),
                        "source": "ONCF Morocco",
                        "sourceRef": ref,
                        "sourceLanguage": "fr",
                        "title": {"en": title, "ar": title, "fr": title},
                        "organization": {
                            "en": "ONCF - Morocco Railways",
                            "ar": "المكتب الوطني للسكك الحديدية",
                            "fr": "ONCF - Office National des Chemins de Fer",
                        },
                        "country": "Morocco",
                        "countryCode": "MA",
                        "sector": classify_sector(title + " railway transport"),
                        "budget": 0,
                        "currency": "MAD",
                        "deadline": deadline,
                        "publishDate": "",
                        "status": "open",
                        "description": {"en": title, "ar": title, "fr": title},
                        "requirements": [],
                        "matchScore": 0,
                        "sourceUrl": link or TENDERS_PAGE,
                    }
                    tenders.append(tender)

                if tenders:
                    break

    except Exception as e:
        logger.error(f"ONCF HTML scrape error: {e}")

    return tenders


def _scrape_marches_publics() -> list[dict]:
    """Scrape ONCF tenders from marchespublics.gov.ma (the national portal).

    ONCF's tender page links to this portal for actual tender details.
    """
    tenders = []
    portal_url = "https://www.marchespublics.gov.ma/pmmp/faces/ConsultationAvisSearch.xhtml"

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        resp = session.get(portal_url, timeout=30)
        if resp.status_code != 200:
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # Search for ONCF-related tenders in the listing
        for selector in [
            "table tbody tr",
            ".ui-datatable-data tr",
            ".dataTables_wrapper tr",
        ]:
            rows = soup.select(selector)
            if not rows:
                continue

            for row in rows:
                cells = row.select("td")
                if len(cells) < 2:
                    continue

                texts = [c.get_text(strip=True) for c in cells]
                full_text = " ".join(texts)

                # Filter for ONCF-related tenders
                if not any(
                    kw in full_text.lower()
                    for kw in ["oncf", "chemin", "ferroviaire", "rail", "train"]
                ):
                    continue

                title = texts[0] if texts else ""
                if len(title) < 5:
                    title = " | ".join(texts[:3])
                if len(title) < 5:
                    continue

                link = ""
                a = row.select_one("a[href]")
                if a:
                    href = a.get("href", "")
                    link = (
                        href
                        if href.startswith("http")
                        else f"https://www.marchespublics.gov.ma{href}"
                    )

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
                    "id": generate_id("oncf_mp", title[:80], ""),
                    "source": "ONCF Morocco",
                    "sourceRef": title[:60],
                    "sourceLanguage": "fr",
                    "title": {"en": title, "ar": title, "fr": title},
                    "organization": {
                        "en": "ONCF - Morocco Railways",
                        "ar": "المكتب الوطني للسكك الحديدية",
                        "fr": "ONCF - Office National des Chemins de Fer",
                    },
                    "country": "Morocco",
                    "countryCode": "MA",
                    "sector": classify_sector(title + " railway transport"),
                    "budget": 0,
                    "currency": "MAD",
                    "deadline": deadline,
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {"en": title, "ar": title, "fr": title},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link or portal_url,
                }
                tenders.append(tender)

            if tenders:
                break

    except Exception as e:
        logger.warning(f"ONCF marchespublics scrape error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape ONCF Morocco railway tenders."""
    all_tenders: list[dict] = []
    seen: set[str] = set()

    for method_name, method in [
        ("AJAX/API", _scrape_ajax_tenders),
        ("HTML", _scrape_html_page),
        ("Marchés Publics", _scrape_marches_publics),
    ]:
        try:
            results = method()
            logger.info(f"ONCF {method_name}: {len(results)} tenders")
            for t in results:
                key = t.get("sourceRef", "") or t["title"]["fr"][:60]
                if key not in seen:
                    seen.add(key)
                    all_tenders.append(t)
        except Exception as e:
            logger.error(f"ONCF {method_name} failed: {e}")

    if not all_tenders:
        logger.warning(
            "ONCF: No tenders found. The tender list is loaded via AJAX "
            "and may require JavaScript rendering or authentication. "
            "Consider accessing marchespublics.gov.ma directly."
        )

    logger.info(f"ONCF total: {len(all_tenders)}")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "oncf")
    print(f"Scraped {len(results)} tenders from ONCF Morocco")
