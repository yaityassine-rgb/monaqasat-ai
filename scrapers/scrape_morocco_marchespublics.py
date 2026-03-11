"""
Scraper for Morocco Public Procurement Portal (Marchés Publics).
Source: https://www.marchespublics.gov.ma/pmmp/

Expanded scraper for Morocco's official procurement portal. This complements
the existing scrape_morocco.py with deeper scraping of the PMMP platform,
including JSF-based search forms and consultation listings.
The portal uses JSF (JavaServer Faces) with PrimeFaces components.
Content is primarily in French and Arabic.
"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders
from config import HEADERS

logger = logging.getLogger("morocco_marchespublics")

BASE_URL = "https://www.marchespublics.gov.ma"
PMMP_URL = f"{BASE_URL}/pmmp/"
SEARCH_URL = f"{BASE_URL}/pmmp/faces/ConsultationAvisSearch.xhtml"
ADVANCED_SEARCH_URL = f"{BASE_URL}/pmmp/faces/ConsultationAvance.xhtml"
AVIS_URL = f"{BASE_URL}/pmmp/faces/AvisConsultation.xhtml"
RESULT_URL = f"{BASE_URL}/pmmp/faces/ConsultationResult.xhtml"
ALTERNATE_URLS = [
    f"{BASE_URL}/pmmp/faces/ConsultationAvisPublie.xhtml",
    f"{BASE_URL}/pmmp/faces/AvisPublie.xhtml",
    f"{BASE_URL}/pmmp/faces/ListeAvis.xhtml",
]
MAX_PAGES = 20


def _create_session() -> requests.Session:
    """Create a session with proper headers for the JSF portal."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,ar;q=0.9,en;q=0.8",
        "Referer": PMMP_URL,
    })
    return s


def _extract_viewstate(soup: BeautifulSoup) -> str:
    """Extract JSF ViewState from a page."""
    vs = soup.find("input", {"name": "javax.faces.ViewState"})
    if vs:
        return vs.get("value", "")
    # Try alternate name
    vs = soup.find("input", {"name": "ViewState"})
    if vs:
        return vs.get("value", "")
    return ""


def _parse_tender_row(row, page_url: str) -> dict | None:
    """Parse a single tender row from the Morocco portal."""
    cells = row.find_all("td")
    if cells and len(cells) >= 2:
        texts = [c.get_text(strip=True) for c in cells]
    else:
        # PrimeFaces panel or card layout
        title_el = row.find(["h3", "h4", "h5", "a", "strong", "span.ui-outputlabel"])
        if not title_el:
            texts = [row.get_text(strip=True)]
        else:
            texts = [title_el.get_text(strip=True)]
            for sub in row.find_all(["span", "div", "p"], recursive=False):
                sub_text = sub.get_text(strip=True)
                if sub_text and sub_text != texts[0] and len(sub_text) > 2:
                    texts.append(sub_text)

    if not texts or all(len(t) < 3 for t in texts):
        return None

    title = ""
    ref = ""
    org = ""
    pub_date = ""
    deadline = ""
    tender_type = ""

    for text in texts:
        if not text:
            continue
        d = parse_date(text)
        if d:
            if not pub_date:
                pub_date = d
            else:
                deadline = d
        elif len(text) < 30 and re.search(r'\d{2,}[/\-]', text) and not ref:
            ref = text
        elif re.match(r'^(AO|RC|DC|MC)\s*\d', text, re.IGNORECASE) and not ref:
            ref = text
        elif len(text) > 10 and not title:
            title = text
        elif len(text) > 10 and title and not org:
            org = text
        elif len(text) > 2 and len(text) < 40 and not tender_type:
            tender_type = text

    if not title or len(title) < 5:
        return None

    # Extract reference from title if not found
    ref_match = re.search(
        r'(?:N[°o]?\s*|AO\s*|RC\s*)([\d\-/]+\d)',
        title, re.IGNORECASE
    )
    if ref_match and not ref:
        ref = ref_match.group(1)

    # Get detail link
    source_url = page_url
    link = row.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and not href.startswith("javascript") and href != "#":
            source_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    desc_parts = [title]
    if tender_type:
        desc_parts.append(tender_type)
    desc = " | ".join(desc_parts)

    return {
        "id": generate_id("ma_pmmp", ref or title[:80], ""),
        "source": "Marchés Publics Maroc",
        "sourceRef": ref,
        "sourceLanguage": "fr",
        "title": {"en": title, "ar": title, "fr": title},
        "organization": {
            "en": org or "Government of Morocco",
            "ar": org or "المملكة المغربية",
            "fr": org or "Royaume du Maroc",
        },
        "country": "Morocco",
        "countryCode": "MA",
        "sector": classify_sector(title + " " + (tender_type or "")),
        "budget": 0,
        "currency": "MAD",
        "deadline": deadline,
        "publishDate": pub_date,
        "status": "open",
        "description": {"en": desc, "ar": desc, "fr": desc},
        "requirements": [tender_type] if tender_type else [],
        "matchScore": 0,
        "sourceUrl": source_url,
    }


def _scrape_page(session: requests.Session, url: str) -> tuple[list[dict], str]:
    """Scrape a single page for tender listings. Returns (tenders, next_page_url)."""
    tenders = []
    next_url = ""

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Morocco PMMP page returned {resp.status_code}: {url}")
            return tenders, next_url

        soup = BeautifulSoup(resp.text, "lxml")

        # Try multiple selectors for JSF/PrimeFaces components
        selectors = [
            ".ui-datatable-data tr",
            "table.ui-datatable tbody tr",
            "table.table tbody tr",
            "table tbody tr",
            ".dataTables_wrapper tbody tr",
            ".ui-datagrid-content .ui-datagrid-row",
            ".avis-item",
            ".consultation-row",
            ".list-group-item",
            ".card",
            "article",
        ]

        for selector in selectors:
            rows = soup.select(selector)
            if rows:
                logger.info(f"Morocco PMMP: found {len(rows)} rows with '{selector}' at {url}")
                for row in rows:
                    tender = _parse_tender_row(row, url)
                    if tender:
                        tenders.append(tender)
                if tenders:
                    break

        # Check for PrimeFaces pagination
        next_link = soup.select_one(
            ".ui-paginator-next:not(.ui-state-disabled), "
            "a.next, .pagination a[rel='next'], "
            "li.next a"
        )
        if next_link:
            next_href = next_link.get("href", "")
            if next_href and next_href != "#":
                next_url = next_href if next_href.startswith("http") else f"{BASE_URL}{next_href}"

    except Exception as e:
        logger.error(f"Morocco PMMP page error ({url}): {e}")

    return tenders, next_url


def _scrape_jsf_search(session: requests.Session) -> list[dict]:
    """Try to interact with the JSF search form."""
    tenders = []

    try:
        # First get the search page to extract ViewState
        resp = session.get(SEARCH_URL, timeout=30)
        if resp.status_code != 200:
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")
        viewstate = _extract_viewstate(soup)

        if not viewstate:
            logger.warning("Morocco PMMP: no ViewState found on search page")
            # Still try to parse the page content
            for selector in [
                ".ui-datatable-data tr",
                "table tbody tr",
                ".list-group-item",
            ]:
                rows = soup.select(selector)
                if rows:
                    for row in rows:
                        tender = _parse_tender_row(row, SEARCH_URL)
                        if tender:
                            tenders.append(tender)
                    break
            return tenders

        # Try to submit the search form with empty criteria (get all)
        form_data = {
            "javax.faces.ViewState": viewstate,
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "formSearch:btnSearch",
            "javax.faces.partial.execute": "@all",
            "javax.faces.partial.render": "formSearch:resultPanel",
            "formSearch:btnSearch": "formSearch:btnSearch",
            "formSearch": "formSearch",
        }

        resp = session.post(
            SEARCH_URL,
            data=form_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Faces-Request": "partial/ajax",
            },
            timeout=30,
        )

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            for selector in [
                ".ui-datatable-data tr",
                "table tbody tr",
                "tr",
            ]:
                rows = soup.select(selector)
                if rows:
                    for row in rows:
                        tender = _parse_tender_row(row, SEARCH_URL)
                        if tender:
                            tenders.append(tender)
                    break

    except Exception as e:
        logger.error(f"Morocco PMMP JSF search: {e}")

    return tenders


def _try_rss_feeds(session: requests.Session) -> list[dict]:
    """Try RSS/Atom feeds for tender data."""
    tenders = []
    rss_urls = [
        f"{BASE_URL}/pmmp/rss",
        f"{BASE_URL}/pmmp/feeds/avis.xml",
        f"{BASE_URL}/pmmp/rss/avis",
        f"{BASE_URL}/rss",
    ]

    for rss_url in rss_urls:
        try:
            resp = session.get(rss_url, timeout=15)
            if resp.status_code != 200:
                continue

            # Try parsing as XML/RSS
            soup = BeautifulSoup(resp.text, "lxml-xml")
            items = soup.find_all("item") or soup.find_all("entry")

            for entry in items:
                title_el = entry.find("title")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title or len(title) < 5:
                    continue

                link_el = entry.find("link")
                link = ""
                if link_el:
                    link = link_el.get("href", "") or link_el.get_text(strip=True)

                pub_el = entry.find("pubDate") or entry.find("published") or entry.find("updated")
                pub_date = ""
                if pub_el:
                    pub_date = parse_date(pub_el.get_text(strip=True)) or ""

                desc_el = entry.find("description") or entry.find("summary") or entry.find("content")
                desc = desc_el.get_text(strip=True) if desc_el else title

                tender = {
                    "id": generate_id("ma_pmmp_rss", title[:80], ""),
                    "source": "Marchés Publics Maroc",
                    "sourceRef": "",
                    "sourceLanguage": "fr",
                    "title": {"en": title, "ar": title, "fr": title},
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
                    "deadline": "",
                    "publishDate": pub_date,
                    "status": "open",
                    "description": {"en": desc, "ar": desc, "fr": desc},
                    "requirements": [],
                    "matchScore": 0,
                    "sourceUrl": link or PMMP_URL,
                }
                tenders.append(tender)

            if tenders:
                logger.info(f"Morocco PMMP RSS: {len(tenders)} tenders from {rss_url}")
                break

        except Exception:
            continue

    return tenders


def scrape() -> list[dict]:
    """Scrape Morocco Public Procurement Portal for tender notices."""
    all_tenders: list[dict] = []
    seen: set[str] = set()
    session = _create_session()

    # Try the main PMMP page with pagination
    url = PMMP_URL
    for page_num in range(1, MAX_PAGES + 1):
        if not url:
            break

        logger.info(f"Morocco PMMP: Scraping page {page_num}: {url}")
        page_tenders, next_url = _scrape_page(session, url)

        page_count = 0
        for t in page_tenders:
            key = t.get("sourceRef", "") or t["title"]["fr"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)
                page_count += 1

        logger.info(f"Morocco PMMP page {page_num}: {page_count} new (total: {len(all_tenders)})")

        if page_count == 0 or not next_url:
            break

        url = next_url
        time.sleep(2)

    # Try JSF search form
    time.sleep(2)
    search_tenders = _scrape_jsf_search(session)
    for t in search_tenders:
        key = t.get("sourceRef", "") or t["title"]["fr"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    # Try alternate URLs
    for alt_url in [SEARCH_URL, ADVANCED_SEARCH_URL, AVIS_URL, RESULT_URL] + ALTERNATE_URLS:
        if len(all_tenders) > 50:
            break
        time.sleep(2)
        alt_tenders, _ = _scrape_page(session, alt_url)
        for t in alt_tenders:
            key = t.get("sourceRef", "") or t["title"]["fr"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)

    # Try RSS feeds
    time.sleep(2)
    rss_tenders = _try_rss_feeds(session)
    for t in rss_tenders:
        key = t.get("sourceRef", "") or t["title"]["fr"][:60]
        if key not in seen:
            seen.add(key)
            all_tenders.append(t)

    if not all_tenders:
        logger.warning(
            "Morocco PMMP: no tenders scraped. The portal uses JSF/PrimeFaces "
            "with ViewState management. Consider using Selenium for full "
            "JavaScript rendering."
        )

    logger.info(f"Morocco Marchés Publics total: {len(all_tenders)} tenders")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "morocco_marchespublics")
    print(f"Scraped {len(results)} tenders from Morocco Marchés Publics")
