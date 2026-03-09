"""
Scraper for Morocco ONEE (Office National de l'Electricité et de l'Eau Potable).
Source: https://www.one.org.ma/FR/pages/aoselect.asp?esp=2&id1=7&id2=64&id3=54&t2=1&t3=1

Old ASP-based site with HTML tables listing tenders.
Table columns: Numéro | Objet | Caution | Date limite | Renseignements & Cahier des charges
Encoding: iso-8859-1

Also scrapes:
  - aoouvert.asp: Tenders opened but not yet judged
  - Pagination via "Suivant" link
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("onee")

BASE_URL = "https://www.one.org.ma/FR/pages"

# Lancés non encore ouverts (launched, not yet opened)
LAUNCHED_URL = f"{BASE_URL}/aoselect.asp?esp=2&id1=7&id2=64&id3=54&t2=1&t3=1"
# Ouverts non encore jugés (opened, not yet judged)
OPENED_URL = f"{BASE_URL}/aoouvert.asp?esp=2&id1=7&id2=64&id3=55&t2=1&t3=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr,en,ar",
}


def _parse_budget(text: str) -> float:
    """Parse a budget/caution amount from text like '3 000 000 MAD'."""
    if not text or text.lower() in ("sans", "-", ""):
        return 0
    # Remove currency and spaces, keep digits and separators
    cleaned = re.sub(r"[A-Za-z]", "", text).strip()
    cleaned = cleaned.replace(" ", "").replace("\xa0", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0


def _parse_onee_date(text: str) -> str:
    """Parse ONEE date format like '22/04/2026 à 09:30'."""
    if not text:
        return ""
    # Strip time part
    date_part = re.sub(r"\s*[àa]\s*\d{1,2}[h:]\d{2}.*", "", text).strip()
    return parse_date(date_part) or ""


def _scrape_page(url: str, page_type: str = "launched") -> tuple[list[dict], str]:
    """Scrape a single page of ONEE tenders.

    Returns (tenders, next_page_url).
    """
    tenders = []
    next_url = ""

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"ONEE page returned {resp.status_code}: {url}")
            return tenders, next_url

        # ONEE uses iso-8859-1 encoding
        resp.encoding = "iso-8859-1"
        soup = BeautifulSoup(resp.text, "lxml")

        # Find the tender data table
        # Look for a table containing both "Numéro" and "Objet" text
        target_table = None
        for table in soup.find_all("table"):
            table_text = table.get_text()
            if "Numéro" in table_text and "Objet" in table_text and "Date" in table_text:
                # Make sure this is the right table (not a navigation table)
                # Check it has enough rows with data
                rows = table.find_all("tr")
                data_rows = 0
                for r in rows:
                    cells = r.find_all("td")
                    if len(cells) >= 3:
                        data_rows += 1
                if data_rows >= 2:  # Header + at least 1 data row
                    target_table = table
                    break

        if not target_table:
            logger.warning(f"ONEE: No tender table found on {url}")
            return tenders, next_url

        rows = target_table.find_all("tr")
        header_found = False

        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            texts = [c.get_text(strip=True) for c in cells]
            full_text = " ".join(texts)

            # Skip header row
            if "Numéro" in full_text and "Objet" in full_text:
                header_found = True
                continue

            if not header_found:
                continue

            # Check for "Suivant" (next page) link
            if "Suivant" in full_text:
                for a in row.find_all("a", href=True):
                    if "Suivant" in a.get_text():
                        next_href = a["href"]
                        if not next_href.startswith("http"):
                            next_url = f"{BASE_URL}/{next_href}"
                        else:
                            next_url = next_href
                continue

            # Parse tender data
            # Expected: Numéro | Objet | Caution | Date limite | Renseignements
            # But cells may be split across multiple td elements
            # Look for the pattern: ref_number starts with 2-letter code
            ref_match = re.search(r"([A-Z]{2}\d[\w]+)", full_text)
            if not ref_match:
                continue

            ref = ref_match.group(1)

            # Find cells with content
            content_cells = [c for c in cells if c.get_text(strip=True)]
            if len(content_cells) < 3:
                continue

            # Extract fields based on position
            # The ref number is in the first content cell
            ref_text = ""
            objet = ""
            caution_text = ""
            date_text = ""
            doc_links = []

            cell_contents = []
            for c in content_cells:
                t = c.get_text(strip=True)
                links = c.find_all("a", href=True)
                cell_contents.append((t, links))

            # Map fields: first is ref, then objet, then caution, then date, then docs
            for i, (text, links) in enumerate(cell_contents):
                if re.match(r"^[A-Z]{2}\d", text):
                    ref_text = text
                elif "MAD" in text or text.lower() == "sans" or re.match(
                    r"^[\d\s]+$", text.replace(" ", "")
                ):
                    if not caution_text:
                        caution_text = text
                elif re.search(r"\d{2}/\d{2}/\d{4}", text):
                    if not date_text:
                        date_text = text
                elif links and ("Téléchargez" in text or "ici" in text.lower()):
                    for a in links:
                        href = a["href"]
                        if not href.startswith("http"):
                            href = f"https://www.one.org.ma/FR/pages/{href}"
                        doc_links.append(href)
                elif len(text) > 10 and not objet:
                    objet = text

            if not objet:
                # If we couldn't identify the objet, use all text except ref and date
                objet = " ".join(
                    t
                    for t, _ in cell_contents
                    if t != ref_text
                    and t != caution_text
                    and t != date_text
                    and "Téléchargez" not in t
                    and len(t) > 5
                )

            if not objet or len(objet) < 5:
                continue

            deadline = _parse_onee_date(date_text)
            budget = _parse_budget(caution_text)

            # Build source URL - link to the tender page
            source_url = url
            if doc_links:
                source_url = doc_links[0]

            status = "open"
            if page_type == "opened":
                status = "open"

            tender = {
                "id": generate_id("onee", ref or objet[:60], ""),
                "source": "ONEE Morocco",
                "sourceRef": ref,
                "sourceLanguage": "fr",
                "title": {"en": objet, "ar": objet, "fr": objet},
                "organization": {
                    "en": "ONEE - National Office of Electricity and Drinking Water",
                    "ar": "المكتب الوطني للكهرباء والماء الصالح للشرب",
                    "fr": "ONEE - Office National de l'Electricité et de l'Eau Potable",
                },
                "country": "Morocco",
                "countryCode": "MA",
                "sector": classify_sector(
                    objet + " electricity water energy"
                ),
                "budget": budget,
                "currency": "MAD",
                "deadline": deadline,
                "publishDate": "",
                "status": status,
                "description": {
                    "en": f"[{ref}] {objet}",
                    "ar": f"[{ref}] {objet}",
                    "fr": f"[{ref}] {objet}",
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"ONEE page scrape error ({url}): {e}")

    return tenders, next_url


def _scrape_all_pages(start_url: str, page_type: str) -> list[dict]:
    """Scrape all pages of a given ONEE tender category."""
    all_tenders = []
    url = start_url
    max_pages = 10

    for page_num in range(1, max_pages + 1):
        if not url:
            break

        logger.info(f"ONEE ({page_type}): Scraping page {page_num}")
        tenders, next_url = _scrape_page(url, page_type)
        all_tenders.extend(tenders)

        if not tenders or not next_url:
            break

        url = next_url
        time.sleep(2)

    return all_tenders


def scrape() -> list[dict]:
    """Scrape ONEE Morocco electricity/water tenders."""
    all_tenders: list[dict] = []
    seen: set[str] = set()

    # Scrape launched tenders (not yet opened)
    try:
        launched = _scrape_all_pages(LAUNCHED_URL, "launched")
        logger.info(f"ONEE launched tenders: {len(launched)}")
        for t in launched:
            key = t.get("sourceRef", "") or t["title"]["fr"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)
    except Exception as e:
        logger.error(f"ONEE launched tenders error: {e}")

    time.sleep(2)

    # Scrape opened tenders (not yet judged)
    try:
        opened = _scrape_all_pages(OPENED_URL, "opened")
        logger.info(f"ONEE opened tenders: {len(opened)}")
        for t in opened:
            key = t.get("sourceRef", "") or t["title"]["fr"][:60]
            if key not in seen:
                seen.add(key)
                all_tenders.append(t)
    except Exception as e:
        logger.error(f"ONEE opened tenders error: {e}")

    logger.info(f"ONEE total: {len(all_tenders)}")
    return all_tenders


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "onee")
    print(f"Scraped {len(results)} tenders from ONEE Morocco")
