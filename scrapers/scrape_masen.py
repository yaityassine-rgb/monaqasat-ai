"""
Scraper for Morocco Renewable Energy Agency (Masen / MASEN).
Source: https://masen.local-trust.com/ (public e-tendering platform)
Also:  https://www.masen.ma/en/masen-news (press releases with tender announcements)

The local-trust platform replaced the old etendering.masen.ma Atexo system.
It provides public access to current consultations without login.
The masen.ma website lists news/press articles about tender launches.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
from base_scraper import classify_sector, generate_id, parse_date, save_tenders

logger = logging.getLogger("masen")

LOCAL_TRUST_BASE = "https://masen.local-trust.com"
ETENDERING_BASE = "https://etendering.masen.ma"
CURRENT_CONSULT_URL = (
    f"{LOCAL_TRUST_BASE}/?page=entreprise.EntrepriseAdvancedSearch"
    "&AllCons&EnCours&searchAnnCons"
)
ALL_CONSULT_URL = (
    f"{LOCAL_TRUST_BASE}/?page=entreprise.EntrepriseAdvancedSearch"
    "&AllCons&searchAnnCons"
)
MASEN_NEWS_URL = "https://www.masen.ma/en/masen-news"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}


def _parse_lt_date(date_str: str) -> str:
    """Parse local-trust date format like 'Jeu 31 Dec 2026' or 'Lun 30 Mar 2026'."""
    if not date_str:
        return ""
    # Remove French day abbreviations (Lun, Mar, Mer, Jeu, Ven, Sam, Dim)
    cleaned = re.sub(r"^(Lun|Mar|Mer|Jeu|Ven|Sam|Dim)\s+", "", date_str.strip())
    # Map French month abbreviations to English
    fr_months = {
        "Jan": "Jan", "Fev": "Feb", "Fév": "Feb", "Feb": "Feb",
        "Mars": "Mar", "Mar": "Mar", "Avr": "Apr", "Apr": "Apr",
        "Mai": "May", "May": "May", "Juin": "Jun", "Jun": "Jun",
        "Juil": "Jul", "Jul": "Jul", "Aou": "Aug", "Aoû": "Aug", "Aug": "Aug",
        "Sep": "Sep", "Oct": "Oct", "Nov": "Nov", "Dec": "Dec", "Déc": "Dec",
    }
    for fr, en in fr_months.items():
        if fr in cleaned:
            cleaned = cleaned.replace(fr, en)
            break
    parsed = parse_date(cleaned)
    if parsed:
        return parsed
    # Try extracting just date from the string
    match = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", cleaned)
    if match:
        day, month, year = match.groups()
        for fmt in ["%d %b %Y", "%d %B %Y"]:
            try:
                from datetime import datetime
                return datetime.strptime(f"{day} {month} {year}", fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return ""


def _scrape_local_trust(url: str, label: str) -> list[dict]:
    """Scrape tender listings from MASEN's local-trust platform."""
    tenders: list[dict] = []

    try:
        import time as _time
        session = requests.Session()
        session.headers.update(HEADERS)

        # Establish session on home page first
        session.get(
            f"{LOCAL_TRUST_BASE}/?page=entreprise.EntrepriseHome&goto=",
            timeout=30
        )
        _time.sleep(2)  # Wait before making the search request

        # Fetch consultation listings with retry
        resp = None
        for attempt in range(3):
            try:
                resp = session.get(url, timeout=30)
                break
            except requests.exceptions.ConnectionError:
                if attempt < 2:
                    logger.info(f"MASEN {label}: connection error, retry {attempt + 1}")
                    _time.sleep(3)
                else:
                    raise

        if resp is None:
            return tenders

        if resp.status_code != 200:
            logger.warning(f"MASEN {label}: HTTP {resp.status_code}")
            return tenders

        # The page declares ISO-8859-1 but contains UTF-8 content.
        # Decode the raw bytes directly as UTF-8 to get proper characters.
        raw_bytes = resp.content
        try:
            page_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback: decode as latin-1
            page_text = raw_bytes.decode("latin-1", errors="replace")
        soup = BeautifulSoup(page_text, "lxml")

        # Each consultation is wrapped in a div.generalBox
        boxes = soup.select("div.generalBox")
        logger.info(f"MASEN {label}: Found {len(boxes)} consultation boxes")

        for box in boxes:
            full_text = box.get_text(" ", strip=True)

            # Extract reference number (use flexible pattern for accented chars)
            # The text contains "Référence :" or "RÃ©fÃ©rence :" depending on encoding
            ref_match = re.search(
                r"rence\s*:\s*(\S+)",
                full_text
            )
            ref = ref_match.group(1).strip() if ref_match else ""

            # Extract object/title
            obj_match = re.search(
                r"Objet\s*:\s*(.*?)(?:\s*D.{0,2}tail|\s*Estimation|$)",
                full_text, re.DOTALL
            )
            title = ""
            if obj_match:
                title = re.sub(r"\s+", " ", obj_match.group(1)).strip()

            if not title and not ref:
                continue

            if not title:
                title = ref

            # Extract deadline date from "Date limite de remise des plis" section
            deadline = ""
            deadline_match = re.search(
                r"Date limite.*?plis\s*((?:Lun|Mar|Mer|Jeu|Ven|Sam|Dim)\s+\d{1,2}\s+\w+\s+\d{4})",
                full_text
            )
            if deadline_match:
                deadline = _parse_lt_date(deadline_match.group(1))

            # Extract deadline time
            time_match = re.search(
                r"Date limite.*?(\d{1,2}:\d{2})",
                full_text
            )

            # Extract location
            location = ""
            loc_match = re.search(
                r"Lieu d.ex.cution\s*(.*?)(?:\s*\.{3}|$)",
                full_text
            )
            if loc_match:
                location = loc_match.group(1).strip()

            # Extract tender type (AC = Appel de Candidatures, AOO = Appel d'Offres Ouvert)
            tender_type = ""
            type_match = re.match(r"^\s*(AC|AOO|AOR|AON|AO)\b", full_text)
            if type_match:
                tender_type = type_match.group(1)

            # Find detail link (sourceUrl)
            source_url = ""
            for a in box.select("a[href]"):
                href = a.get("href", "")
                if "EntrepriseDetailsConsultation" in href:
                    source_url = href if href.startswith("http") else LOCAL_TRUST_BASE + "/" + href.lstrip("/")
                    break
            # Also check parent for detail links
            if not source_url:
                parent = box.parent
                if parent:
                    for a in parent.select("a[href]"):
                        href = a.get("href", "")
                        if "EntrepriseDetailsConsultation" in href or "Etendering.masen.ma" in href:
                            source_url = href if href.startswith("http") else LOCAL_TRUST_BASE + "/" + href.lstrip("/")
                            break

            if not source_url:
                source_url = url

            # Use ref as sourceRef, fallback to title
            source_ref = ref if ref else title[:60]

            # Build description
            desc_parts = [title]
            if tender_type:
                type_labels = {
                    "AC": "Appel de Candidatures (Call for Candidates)",
                    "AOO": "Appel d'Offres Ouvert (Open Tender)",
                    "AOR": "Appel d'Offres Restreint (Restricted Tender)",
                    "AON": "Appel d'Offres National (National Tender)",
                    "AO": "Appel d'Offres (Tender)",
                }
                desc_parts.append(f"Type: {type_labels.get(tender_type, tender_type)}")
            if location:
                desc_parts.append(f"Location: {location}")
            description = ". ".join(desc_parts)

            tender = {
                "id": generate_id("masen", source_ref, ""),
                "source": "MASEN",
                "sourceRef": source_ref,
                "sourceLanguage": "fr",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Moroccan Agency for Sustainable Energy (MASEN)",
                    "ar": "الوكالة المغربية للطاقة المستدامة (مازن)",
                    "fr": "Agence Marocaine pour l'Energie Durable (MASEN)",
                },
                "country": "Morocco",
                "countryCode": "MA",
                "sector": classify_sector(
                    title + " renewable energy solar wind Morocco"
                ),
                "budget": 0,
                "currency": "MAD",
                "deadline": deadline,
                "publishDate": "",
                "status": "open",
                "description": {
                    "en": description[:500],
                    "ar": description[:500],
                    "fr": description[:500],
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": source_url,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"MASEN {label} scraper error: {e}")

    return tenders


def _scrape_masen_news() -> list[dict]:
    """Scrape MASEN news page for tender-related announcements."""
    tenders: list[dict] = []

    try:
        resp = requests.get(MASEN_NEWS_URL, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"MASEN news page returned HTTP {resp.status_code}")
            return tenders

        soup = BeautifulSoup(resp.text, "lxml")

        # News items are in div.post elements
        posts = soup.select("div.post")
        logger.info(f"MASEN news: Found {len(posts)} news items")

        # Tender-related keywords
        tender_keywords = [
            "tender", "procurement", "appel", "offre", "bid",
            "rfp", "rfq", "contract", "launch", "solar",
            "wind", "power", "energy", "noor", "midelt",
        ]

        for post in posts:
            # Get title from .text-post div
            text_div = post.select_one(".text-post")
            if not text_div:
                continue
            title = text_div.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Check if this is a tender-related announcement
            title_lower = title.lower()
            if not any(kw in title_lower for kw in tender_keywords):
                continue

            # Get date from .img-post div
            date_div = post.select_one(".img-post")
            pub_date = ""
            if date_div:
                date_text = date_div.get_text(strip=True)
                # Format: "02/072021" -> needs parsing
                date_match = re.match(r"(\d{2})/(\d{2})(\d{4})", date_text)
                if date_match:
                    day, month, year = date_match.groups()
                    pub_date = f"{year}-{month}-{day}"

            # Get link
            link_el = post.select_one("a[href]")
            href = ""
            if link_el:
                href = link_el.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.masen.ma" + href

            if not href:
                continue

            source_ref = title[:60]

            tender = {
                "id": generate_id("masen_news", source_ref, ""),
                "source": "MASEN",
                "sourceRef": source_ref,
                "sourceLanguage": "en",
                "title": {"en": title, "ar": title, "fr": title},
                "organization": {
                    "en": "Moroccan Agency for Sustainable Energy (MASEN)",
                    "ar": "الوكالة المغربية للطاقة المستدامة (مازن)",
                    "fr": "Agence Marocaine pour l'Energie Durable (MASEN)",
                },
                "country": "Morocco",
                "countryCode": "MA",
                "sector": classify_sector(
                    title + " renewable energy solar wind Morocco"
                ),
                "budget": 0,
                "currency": "MAD",
                "deadline": "",
                "publishDate": pub_date,
                "status": "open",
                "description": {
                    "en": f"Press announcement: {title}",
                    "ar": f"Press announcement: {title}",
                    "fr": f"Press announcement: {title}",
                },
                "requirements": [],
                "matchScore": 0,
                "sourceUrl": href,
            }
            tenders.append(tender)

    except Exception as e:
        logger.error(f"MASEN news scraper error: {e}")

    return tenders


def scrape() -> list[dict]:
    """Scrape MASEN tenders from the local-trust platform and news page."""
    import time as _time
    lt_current = _scrape_local_trust(CURRENT_CONSULT_URL, "current")
    _time.sleep(3)  # Rate-limit between requests to the same host
    lt_all = _scrape_local_trust(ALL_CONSULT_URL, "all")
    news_tenders = _scrape_masen_news()

    # Merge and deduplicate
    seen: set[str] = set()
    merged: list[dict] = []
    for t in lt_current + lt_all + news_tenders:
        key = t["sourceRef"]
        if key not in seen:
            seen.add(key)
            merged.append(t)

    logger.info(
        f"MASEN total: {len(merged)} tenders "
        f"(current: {len(lt_current)}, all: {len(lt_all)}, "
        f"news: {len(news_tenders)})"
    )

    if not merged:
        logger.warning(
            "MASEN: No tenders found. The local-trust platform structure "
            "may have changed or the news page format may differ."
        )

    return merged


if __name__ == "__main__":
    results = scrape()
    save_tenders(results, "masen")
    print(f"Scraped {len(results)} tenders from MASEN")
