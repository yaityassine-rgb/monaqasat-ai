"""
Master scraper runner — runs all scrapers and merges results.

Usage:
    python run_all.py                # Full scrape
    python run_all.py --incremental  # Incremental (Etimad skips known tenders)
"""

import argparse
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from config import OUTPUT_FILE, DATA_DIR
from base_scraper import load_all_tenders

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("runner")


def run_scraper(name: str, module_name: str, **kwargs) -> int:
    """Run a single scraper and return count."""
    try:
        logger.info(f"Running {name} scraper...")
        mod = __import__(module_name)
        results = mod.scrape(**kwargs)
        mod.save_tenders(results, module_name.replace("scrape_", ""))
        logger.info(f"{name}: {len(results)} tenders")
        return len(results)
    except Exception as e:
        logger.error(f"{name} scraper failed: {e}")
        return 0


def merge_all() -> list[dict]:
    """Merge all scraped data, deduplicate by ID."""
    all_tenders = load_all_tenders()

    # Deduplicate by ID
    seen = set()
    unique = []
    for t in all_tenders:
        if t["id"] not in seen:
            seen.add(t["id"])
            unique.append(t)

    # Sort by publish date (newest first)
    unique.sort(key=lambda x: x.get("publishDate", ""), reverse=True)

    # Save merged output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "lastUpdated": datetime.now().isoformat(),
            "totalCount": len(unique),
            "tenders": unique,
        }, f, ensure_ascii=False, indent=2)

    logger.info(f"Merged: {len(unique)} unique tenders → {OUTPUT_FILE}")
    return unique


def main(incremental: bool = False):
    DATA_DIR.mkdir(exist_ok=True)

    scrapers = [
        # --- Original 11 sources ---
        ("World Bank Notices", "scrape_worldbank", {}),
        ("World Bank Projects", "scrape_wb_projects", {}),
        ("World Bank Documents", "scrape_wb_docs", {}),
        ("UNDP", "scrape_undp", {}),
        ("TED (EU)", "scrape_ted_v2", {}),
        ("IsDB", "scrape_idb", {}),
        ("Morocco Portal", "scrape_morocco", {}),
        ("UNGM", "scrape_ungm", {}),
        ("AfDB (IATI)", "scrape_afdb", {}),
        ("Jordan JONEPS", "scrape_joneps", {}),
        ("Saudi Etimad", "scrape_etimad", {"incremental": incremental}),
        # --- Gulf government portals ---
        ("Qatar Monaqasat", "scrape_qatar", {}),
        ("Bahrain Tender Board", "scrape_bahrain", {}),
        ("Kuwait CAPT", "scrape_kuwait", {}),
        ("Oman Tender Board", "scrape_oman", {}),
        ("Abu Dhabi ADGPG", "scrape_abudhabi", {}),
        # --- North Africa ---
        ("Algeria BAOSEM", "scrape_baosem", {}),
        ("Libya NOC", "scrape_libya_noc", {}),
        ("Morocco ONCF", "scrape_oncf", {}),
        ("Morocco ONEE", "scrape_onee", {}),
        ("Egypt EEHC", "scrape_eehc", {}),
        ("Egypt Suez Canal", "scrape_suez", {}),
        # --- Corporate & regional ---
        ("EBRD", "scrape_ebrd", {}),
        ("Palestine Shiraa", "scrape_palestine", {}),
        ("Qatar Ashghal", "scrape_ashghal", {}),
        ("Saudi Railway SAR", "scrape_sar", {}),
        ("Dubai DEWA", "scrape_dewa", {}),
        ("Kuwait KNPC Oil", "scrape_knpc", {}),
        ("QatarEnergy", "scrape_qatarenergy", {}),
        ("Morocco MASEN", "scrape_masen", {}),
        ("Kurdistan KEPS", "scrape_kurdistan", {}),
        # --- GCC expansion (new) ---
        ("Saudi NUPCO", "scrape_nupco", {}),
        ("Dubai eSupply", "scrape_dubai_esupply", {}),
        ("Sharjah eProcurement", "scrape_sharjah", {}),
        ("UAE Ministry of Finance", "scrape_uae_mof", {}),
        ("Oman eTendering", "scrape_oman_etendering", {}),
        ("Bahrain eTendering", "scrape_bahrain_etendering", {}),
        # --- North Africa & Levant expansion (new) ---
        ("Tunisia TUNEPS", "scrape_tunisia", {}),
        ("Algeria BOMOP", "scrape_bomop", {}),
        ("Egypt GPP", "scrape_egypt_gpp", {}),
        ("Iraq MOP/IOM", "scrape_iraq", {}),
        ("Morocco Marchés Publics", "scrape_morocco_marchespublics", {}),
        ("Jordan GTD", "scrape_jordan_gtd", {}),
    ]

    total = 0
    for name, module, kwargs in scrapers:
        count = run_scraper(name, module, **kwargs)
        total += count

    logger.info(f"\nTotal scraped: {total} tenders")

    # Merge all into single file
    merged = merge_all()
    logger.info(f"Final merged: {len(merged)} unique tenders")

    # Clean data (filter closed, deduplicate, validate)
    import clean_data
    clean_data.main()

    # Copy cleaned output to public/data/tenders.json
    clean_output = DATA_DIR / "tenders_clean.json"
    public_dir = Path(__file__).parent.parent / "public" / "data"
    public_dir.mkdir(parents=True, exist_ok=True)
    public_output = public_dir / "tenders.json"
    shutil.copy2(clean_output, public_output)
    logger.info(f"Copied cleaned data → {public_output}")

    # Print summary
    countries: dict[str, int] = {}
    sources: dict[str, int] = {}
    for t in merged:
        c = t.get("countryCode", "XX")
        countries[c] = countries.get(c, 0) + 1
        s = t.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    print("\n=== SCRAPING SUMMARY ===")
    print(f"Total unique tenders: {len(merged)}")
    print(f"\nBy source:")
    for s, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {s}: {count}")
    print(f"\nBy country:")
    for c, count in sorted(countries.items(), key=lambda x: -x[1]):
        print(f"  {c}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all tender scrapers")
    parser.add_argument("--incremental", action="store_true",
                        help="Incremental mode: skip already-known Etimad tenders")
    args = parser.parse_args()
    main(incremental=args.incremental)
