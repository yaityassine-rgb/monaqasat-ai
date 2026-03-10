"""
Master runner for all expansion scrapers — grants, PPP, companies, prequalification, market intel.

Usage:
    python run_expansion.py                    # Run all expansion scrapers
    python run_expansion.py --type grants      # Run grants scrapers only
    python run_expansion.py --type ppp         # Run PPP scrapers only
    python run_expansion.py --type companies   # Run company scrapers only
    python run_expansion.py --type preq        # Run pre-qualification data only
    python run_expansion.py --type market      # Run market intelligence only
    python run_expansion.py --scraper grants_worldbank  # Run specific scraper
    python run_expansion.py --upload           # Also upload to Supabase after scraping
    python run_expansion.py --dry-run          # List scrapers without running them
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, GRANTS_DIR, PPP_DIR, COMPANIES_DIR, MARKET_DIR, PREQ_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("expansion_runner")


# ============================================================
# Scraper Registry
# ============================================================
# (name, module_name, type, save_fn_name, data_dir)
EXPANSION_SCRAPERS = [
    # --- Grants ---
    ("Grants: World Bank",       "scrape_grants_worldbank",   "grants",    "save_grants",          GRANTS_DIR),
    ("Grants: AfDB",             "scrape_grants_afdb",        "grants",    "save_grants",          GRANTS_DIR),
    ("Grants: IsDB",             "scrape_grants_isdb",        "grants",    "save_grants",          GRANTS_DIR),
    ("Grants: EU/TED",           "scrape_grants_eu",          "grants",    "save_grants",          GRANTS_DIR),
    ("Grants: UNGM",             "scrape_grants_ungm",        "grants",    "save_grants",          GRANTS_DIR),
    ("Grants: EBRD",             "scrape_grants_ebrd",        "grants",    "save_grants",          GRANTS_DIR),
    # --- PPP ---
    ("PPP: World Bank PPI",      "scrape_ppp_worldbank",      "ppp",       "save_ppp_projects",    PPP_DIR),
    ("PPP: Infra Projects",      "scrape_ppp_infraprojects",  "ppp",       "save_ppp_projects",    PPP_DIR),
    ("PPP: MEED/Zawya",          "scrape_ppp_meed",           "ppp",       "save_ppp_projects",    PPP_DIR),
    ("PPP: National Portals",    "scrape_ppp_national",       "ppp",       "save_ppp_projects",    PPP_DIR),
    # --- Companies ---
    ("Companies: OpenCorporates", "scrape_companies_opencorp",  "companies", "save_companies",     COMPANIES_DIR),
    ("Companies: Vendor Registries", "scrape_companies_vendors", "companies", "save_companies",    COMPANIES_DIR),
    ("Companies: Directories",   "scrape_companies_directories", "companies", "save_companies",    COMPANIES_DIR),
    ("Companies: Seed Data",     "scrape_companies_seed",      "companies", "save_companies",      COMPANIES_DIR),
    # --- Pre-Qualification ---
    ("Pre-Qualification: MENA",  "scrape_prequalification",   "preq",      "save_prequalification", PREQ_DIR),
    # --- Market Intelligence ---
    ("Market: World Bank API",   "scrape_market_worldbank",   "market",    "save_market_data",     MARKET_DIR),
    ("Market: Seed Data",        "scrape_market_seed",        "market",    "save_market_data",     MARKET_DIR),
]

# Type filter map
TYPE_MAP = {
    "grants": "grants",
    "ppp": "ppp",
    "companies": "companies",
    "preq": "preq",
    "market": "market",
}


def run_scraper(name: str, module_name: str, save_fn_name: str, data_dir: Path) -> tuple[int, float]:
    """Run a single expansion scraper. Returns (record_count, duration_seconds)."""
    start = time.time()
    try:
        logger.info(f"  Starting: {name}")
        mod = __import__(module_name)
        results = mod.scrape()

        if results:
            # Save using the module's own save function via base_scraper
            from base_scraper import save_grants, save_ppp_projects, save_companies, save_market_data, save_prequalification
            save_fns = {
                "save_grants": save_grants,
                "save_ppp_projects": save_ppp_projects,
                "save_companies": save_companies,
                "save_market_data": save_market_data,
                "save_prequalification": save_prequalification,
            }
            save_fn = save_fns[save_fn_name]
            source_name = module_name.replace("scrape_", "")
            save_fn(results, source_name)

        duration = time.time() - start
        logger.info(f"  Completed: {name} — {len(results)} records in {duration:.1f}s")
        return len(results), duration

    except Exception as e:
        duration = time.time() - start
        logger.error(f"  FAILED: {name} — {e} (after {duration:.1f}s)")
        return 0, duration


def main():
    parser = argparse.ArgumentParser(description="Run expansion scrapers")
    parser.add_argument("--type", choices=list(TYPE_MAP.keys()) + ["all"], default="all",
                        help="Category of scrapers to run")
    parser.add_argument("--scraper", type=str, default="",
                        help="Run a specific scraper by module name (e.g., grants_worldbank)")
    parser.add_argument("--upload", action="store_true",
                        help="Upload to Supabase after scraping")
    parser.add_argument("--dry-run", action="store_true",
                        help="List scrapers without running them")
    args = parser.parse_args()

    # Filter scrapers
    if args.scraper:
        target = f"scrape_{args.scraper}" if not args.scraper.startswith("scrape_") else args.scraper
        scrapers = [(n, m, t, s, d) for n, m, t, s, d in EXPANSION_SCRAPERS if m == target]
        if not scrapers:
            logger.error(f"Scraper '{args.scraper}' not found. Available:")
            for n, m, _, _, _ in EXPANSION_SCRAPERS:
                logger.error(f"  {m.replace('scrape_', '')}: {n}")
            sys.exit(1)
    elif args.type != "all":
        type_filter = TYPE_MAP[args.type]
        scrapers = [(n, m, t, s, d) for n, m, t, s, d in EXPANSION_SCRAPERS if t == type_filter]
    else:
        scrapers = EXPANSION_SCRAPERS

    # Dry run
    if args.dry_run:
        print(f"\nExpansion scrapers ({len(scrapers)}):")
        for name, module, stype, _, _ in scrapers:
            print(f"  [{stype:10s}] {module:35s} — {name}")
        return

    # Run
    logger.info(f"\n{'='*60}")
    logger.info(f"MONAQASAT AI — Expansion Data Scraping")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info(f"Scrapers: {len(scrapers)}")
    logger.info(f"{'='*60}\n")

    results = []
    total_records = 0
    total_time = 0

    for name, module, stype, save_fn, data_dir in scrapers:
        count, duration = run_scraper(name, module, save_fn, data_dir)
        results.append((name, stype, count, duration))
        total_records += count
        total_time += duration

    # Summary
    print(f"\n{'='*60}")
    print("SCRAPING SUMMARY")
    print(f"{'='*60}")
    for name, stype, count, duration in results:
        status = f"{count:>6d} records" if count > 0 else "FAILED"
        print(f"  [{stype:10s}] {name:35s} — {status} ({duration:.1f}s)")
    print(f"\nTotal: {total_records} records scraped in {total_time:.1f}s")

    # Group by type
    type_totals: dict[str, int] = {}
    for _, stype, count, _ in results:
        type_totals[stype] = type_totals.get(stype, 0) + count
    print(f"\nBy type:")
    for stype, count in sorted(type_totals.items()):
        print(f"  {stype}: {count}")

    # Upload to Supabase
    if args.upload:
        logger.info("\nUploading to Supabase...")
        try:
            from upload_all import main as upload_main
            # Determine upload type from scraper type
            if args.type != "all":
                upload_type = args.type if args.type != "preq" else "prequalification"
                sys.argv = ["upload_all.py", "--type", upload_type]
            else:
                sys.argv = ["upload_all.py"]
            upload_main()
        except Exception as e:
            logger.error(f"Upload failed: {e}")

    # Save run report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_records": total_records,
        "total_duration_seconds": round(total_time, 1),
        "scrapers": [
            {"name": n, "type": t, "records": c, "duration": round(d, 1)}
            for n, t, c, d in results
        ],
    }
    report_file = DATA_DIR / "expansion_run_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"\nReport saved to {report_file}")


if __name__ == "__main__":
    main()
