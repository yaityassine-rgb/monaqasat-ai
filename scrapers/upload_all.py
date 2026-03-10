"""
Upload all expansion data to Supabase — grants, PPP, companies, prequalification, market intel.

Usage:
    python upload_all.py                          # Upload everything
    python upload_all.py --type grants            # Upload grants only
    python upload_all.py --type ppp               # Upload PPP projects only
    python upload_all.py --type companies         # Upload companies only
    python upload_all.py --type prequalification  # Upload pre-qualification data
    python upload_all.py --type market            # Upload market intelligence
    python upload_all.py --type tenders           # Upload tenders (original)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("upload_all")

try:
    from supabase import create_client, Client
except ImportError:
    logger.error("supabase-py not installed. Run: pip install supabase")
    sys.exit(1)

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_ANON_KEY,
    GRANTS_DIR, PPP_DIR, COMPANIES_DIR, MARKET_DIR, PREQ_DIR,
)
from base_scraper import load_all_from_dir

BATCH_SIZE = 100


def get_supabase() -> Client:
    """Create Supabase client with service role key."""
    key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    if not SUPABASE_URL or not key:
        logger.error("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables")
        sys.exit(1)
    return create_client(SUPABASE_URL, key)


TIMESTAMP_FIELDS = {
    "application_deadline", "publish_date", "start_date", "end_date",
    "financial_close_date", "tender_deadline", "award_date", "completion_date",
    "contract_duration_years", "founded_year",
}


def _clean_row(row: dict) -> dict:
    """Clean a row before upload: convert empty strings to None for timestamp fields only."""
    cleaned = {}
    for k, v in row.items():
        if k in TIMESTAMP_FIELDS and (v == "" or v == "None" or v is None):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def _dedup_rows(rows: list[dict], key: str = "id") -> list[dict]:
    """Remove duplicate rows by key, keeping the last occurrence."""
    seen = {}
    for row in rows:
        seen[row.get(key, id(row))] = row
    return list(seen.values())


def _batch_upsert(supabase: Client, table: str, rows: list[dict], conflict_col: str = "id") -> tuple[int, int]:
    """Batch upsert rows into a Supabase table. Returns (uploaded, errors)."""
    uploaded = 0
    errors = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [_clean_row(r) for r in rows[i:i + BATCH_SIZE]]
        try:
            supabase.table(table).upsert(batch, on_conflict=conflict_col).execute()
            uploaded += len(batch)
            logger.info(f"  {table}: uploaded {uploaded}/{len(rows)}")
        except Exception as e:
            logger.error(f"  {table} batch upsert failed at {i}: {e}")
            errors += len(batch)
    return uploaded, errors


# ============================================================
# Grant upload
# ============================================================
def _grant_to_row(g: dict) -> dict:
    """Convert grant dict to Supabase row."""
    return {
        "id": g["id"],
        "title": g.get("title", ""),
        "title_ar": g.get("title_ar", ""),
        "title_fr": g.get("title_fr", ""),
        "source": g.get("source", ""),
        "source_ref": g.get("source_ref", ""),
        "source_url": g.get("source_url", ""),
        "funding_organization": g.get("funding_organization", ""),
        "funding_organization_ar": g.get("funding_organization_ar", ""),
        "funding_organization_fr": g.get("funding_organization_fr", ""),
        "funding_amount": float(g.get("funding_amount", 0) or 0),
        "funding_amount_max": float(g.get("funding_amount_max", 0) or 0),
        "currency": g.get("currency", "USD"),
        "grant_type": g.get("grant_type", ""),
        "country": g.get("country", ""),
        "country_code": g.get("country_code", ""),
        "region": g.get("region", "MENA"),
        "sector": g.get("sector", ""),
        "sectors": g.get("sectors", []),
        "eligibility_criteria": g.get("eligibility_criteria", ""),
        "eligibility_countries": g.get("eligibility_countries", []),
        "description": g.get("description", ""),
        "description_ar": g.get("description_ar", ""),
        "description_fr": g.get("description_fr", ""),
        "application_deadline": g.get("application_deadline"),
        "publish_date": g.get("publish_date"),
        "start_date": g.get("start_date"),
        "end_date": g.get("end_date"),
        "status": g.get("status", "open"),
        "contact_info": g.get("contact_info", ""),
        "documents_url": g.get("documents_url", ""),
        "tags": g.get("tags", []),
        "metadata": g.get("metadata", {}),
    }


def upload_grants():
    """Upload all grants from GRANTS_DIR to Supabase."""
    grants = load_all_from_dir(GRANTS_DIR)
    if not grants:
        logger.info("No grants data found")
        return 0, 0
    logger.info(f"Loaded {len(grants)} grants from {GRANTS_DIR}")
    rows = []
    for g in grants:
        try:
            rows.append(_grant_to_row(g))
        except Exception as e:
            logger.warning(f"Skipping grant {g.get('id', '?')}: {e}")
    rows = _dedup_rows(rows)
    logger.info(f"After dedup: {len(rows)} unique grants")
    supabase = get_supabase()
    return _batch_upsert(supabase, "grants", rows)


# ============================================================
# PPP upload
# ============================================================
def _ppp_to_row(p: dict) -> dict:
    """Convert PPP project dict to Supabase row."""
    return {
        "id": p["id"],
        "name": p.get("name", ""),
        "name_ar": p.get("name_ar", ""),
        "name_fr": p.get("name_fr", ""),
        "source": p.get("source", ""),
        "source_ref": p.get("source_ref", ""),
        "source_url": p.get("source_url", ""),
        "country": p.get("country", ""),
        "country_code": p.get("country_code", ""),
        "region": p.get("region", "MENA"),
        "sector": p.get("sector", ""),
        "subsector": p.get("subsector", ""),
        "stage": p.get("stage", "planning"),
        "contract_type": p.get("contract_type", ""),
        "investment_value": float(p.get("investment_value", 0) or 0),
        "debt_value": float(p.get("debt_value", 0) or 0),
        "equity_value": float(p.get("equity_value", 0) or 0),
        "currency": p.get("currency", "USD"),
        "government_entity": p.get("government_entity", ""),
        "government_entity_ar": p.get("government_entity_ar", ""),
        "government_entity_fr": p.get("government_entity_fr", ""),
        "sponsors": p.get("sponsors", []),
        "lenders": p.get("lenders", []),
        "advisors": p.get("advisors", []),
        "description": p.get("description", ""),
        "description_ar": p.get("description_ar", ""),
        "description_fr": p.get("description_fr", ""),
        "financial_close_date": p.get("financial_close_date"),
        "contract_duration_years": p.get("contract_duration_years"),
        "tender_deadline": p.get("tender_deadline"),
        "award_date": p.get("award_date"),
        "start_date": p.get("start_date"),
        "completion_date": p.get("completion_date"),
        "risk_allocation": p.get("risk_allocation", {}),
        "key_terms": p.get("key_terms", {}),
        "tags": p.get("tags", []),
        "metadata": p.get("metadata", {}),
    }


def upload_ppp():
    """Upload all PPP projects from PPP_DIR to Supabase."""
    projects = load_all_from_dir(PPP_DIR)
    if not projects:
        logger.info("No PPP data found")
        return 0, 0
    logger.info(f"Loaded {len(projects)} PPP projects from {PPP_DIR}")
    rows = []
    for p in projects:
        try:
            rows.append(_ppp_to_row(p))
        except Exception as e:
            logger.warning(f"Skipping PPP {p.get('id', '?')}: {e}")
    supabase = get_supabase()
    return _batch_upsert(supabase, "ppp_projects", rows)


# ============================================================
# Companies upload
# ============================================================
def _company_to_row(c: dict) -> dict:
    """Convert company dict to Supabase row."""
    return {
        "id": c["id"],
        "name": c.get("name", ""),
        "name_ar": c.get("name_ar", ""),
        "name_fr": c.get("name_fr", ""),
        "legal_name": c.get("legal_name", ""),
        "source": c.get("source", ""),
        "source_ref": c.get("source_ref", ""),
        "source_url": c.get("source_url", ""),
        "country": c.get("country", ""),
        "country_code": c.get("country_code", ""),
        "city": c.get("city", ""),
        "address": c.get("address", ""),
        "website": c.get("website", ""),
        "email": c.get("email", ""),
        "phone": c.get("phone", ""),
        "sector": c.get("sector", ""),
        "sectors": c.get("sectors", []),
        "subsectors": c.get("subsectors", []),
        "company_type": c.get("company_type", ""),
        "company_size": c.get("company_size", ""),
        "employee_count": c.get("employee_count"),
        "annual_revenue": float(c.get("annual_revenue", 0) or 0) if c.get("annual_revenue") else None,
        "revenue_currency": c.get("revenue_currency", "USD"),
        "founded_year": c.get("founded_year"),
        "registration_number": c.get("registration_number", ""),
        "tax_id": c.get("tax_id", ""),
        "certifications": c.get("certifications", []),
        "classifications": c.get("classifications", []),
        "prequalified_with": c.get("prequalified_with", []),
        "notable_projects": c.get("notable_projects", []),
        "jv_experience": c.get("jv_experience", False),
        "international_presence": c.get("international_presence", []),
        "description": c.get("description", ""),
        "description_ar": c.get("description_ar", ""),
        "description_fr": c.get("description_fr", ""),
        "financial_data": c.get("financial_data", {}),
        "tags": c.get("tags", []),
        "metadata": c.get("metadata", {}),
        "verified": c.get("verified", False),
        "active": c.get("active", True),
    }


def upload_companies():
    """Upload all companies from COMPANIES_DIR to Supabase."""
    companies = load_all_from_dir(COMPANIES_DIR)
    if not companies:
        logger.info("No companies data found")
        return 0, 0
    logger.info(f"Loaded {len(companies)} companies from {COMPANIES_DIR}")
    rows = []
    for c in companies:
        try:
            rows.append(_company_to_row(c))
        except Exception as e:
            logger.warning(f"Skipping company {c.get('id', '?')}: {e}")
    supabase = get_supabase()
    return _batch_upsert(supabase, "companies", rows)


# ============================================================
# Pre-qualification upload
# ============================================================
def upload_prequalification():
    """Upload pre-qualification requirements from PREQ_DIR to Supabase."""
    data = load_all_from_dir(PREQ_DIR)
    if not data:
        logger.info("No prequalification data found")
        return 0, 0
    data = _dedup_rows(data)
    logger.info(f"Loaded {len(data)} unique prequalification records from {PREQ_DIR}")
    supabase = get_supabase()
    return _batch_upsert(supabase, "prequalification_requirements", data)


# ============================================================
# Market intelligence upload
# ============================================================
def _market_to_row(m: dict) -> dict:
    """Convert market intel dict to Supabase row."""
    return {
        "id": m["id"],
        "country": m.get("country", ""),
        "country_code": m.get("country_code", ""),
        "year": m.get("year", 2024),
        "gdp_usd": m.get("gdp_usd"),
        "gdp_growth_pct": m.get("gdp_growth_pct"),
        "inflation_pct": m.get("inflation_pct"),
        "population": m.get("population"),
        "unemployment_pct": m.get("unemployment_pct"),
        "fdi_inflow_usd": m.get("fdi_inflow_usd"),
        "construction_output_usd": m.get("construction_output_usd"),
        "construction_growth_pct": m.get("construction_growth_pct"),
        "infrastructure_spend_usd": m.get("infrastructure_spend_usd"),
        "active_projects_count": m.get("active_projects_count"),
        "active_projects_value_usd": m.get("active_projects_value_usd"),
        "ease_of_business_rank": m.get("ease_of_business_rank"),
        "ease_of_business_score": m.get("ease_of_business_score"),
        "corruption_perception_index": m.get("corruption_perception_index"),
        "government_effectiveness_score": m.get("government_effectiveness_score"),
        "sector_breakdown": m.get("sector_breakdown", {}),
        "top_sectors": m.get("top_sectors", []),
        "major_trading_partners": m.get("major_trading_partners", []),
        "bilateral_agreements": m.get("bilateral_agreements", []),
        "free_trade_zones": m.get("free_trade_zones", []),
        "currency_code": m.get("currency_code", ""),
        "currency_name": m.get("currency_name", ""),
        "exchange_rate_usd": m.get("exchange_rate_usd"),
        "market_summary": m.get("market_summary", ""),
        "market_summary_ar": m.get("market_summary_ar", ""),
        "market_summary_fr": m.get("market_summary_fr", ""),
        "opportunities": m.get("opportunities", ""),
        "opportunities_ar": m.get("opportunities_ar", ""),
        "opportunities_fr": m.get("opportunities_fr", ""),
        "challenges": m.get("challenges", ""),
        "challenges_ar": m.get("challenges_ar", ""),
        "challenges_fr": m.get("challenges_fr", ""),
        "regulatory_environment": m.get("regulatory_environment", ""),
        "key_regulations": m.get("key_regulations", []),
        "source": m.get("source", ""),
        "metadata": m.get("metadata", {}),
    }


def upload_market():
    """Upload market intelligence from MARKET_DIR to Supabase."""
    data = load_all_from_dir(MARKET_DIR)
    if not data:
        logger.info("No market intelligence data found")
        return 0, 0
    logger.info(f"Loaded {len(data)} market records from {MARKET_DIR}")
    rows = []
    for m in data:
        try:
            rows.append(_market_to_row(m))
        except Exception as e:
            logger.warning(f"Skipping market record {m.get('id', '?')}: {e}")
    # Dedup by country_code+year (compound unique constraint)
    seen = {}
    for row in rows:
        key = f"{row.get('country_code', '')}_{row.get('year', '')}"
        seen[key] = row  # last one wins (worldbank data preferred over seed)
    rows = list(seen.values())
    logger.info(f"After dedup: {len(rows)} unique market records")
    supabase = get_supabase()
    return _batch_upsert(supabase, "market_intelligence", rows)


# ============================================================
# Main
# ============================================================
UPLOAD_MAP = {
    "grants": ("Grants", upload_grants),
    "ppp": ("PPP Projects", upload_ppp),
    "companies": ("Companies", upload_companies),
    "prequalification": ("Pre-Qualification", upload_prequalification),
    "market": ("Market Intelligence", upload_market),
}


def main():
    parser = argparse.ArgumentParser(description="Upload expansion data to Supabase")
    parser.add_argument("--type", choices=list(UPLOAD_MAP.keys()) + ["tenders", "all"],
                        default="all", help="Data type to upload")
    args = parser.parse_args()

    if args.type == "tenders":
        # Use existing upload_to_supabase.py
        from upload_to_supabase import main as upload_tenders_main
        upload_tenders_main()
        return

    types_to_upload = list(UPLOAD_MAP.keys()) if args.type == "all" else [args.type]

    total_uploaded = 0
    total_errors = 0
    results = []

    for data_type in types_to_upload:
        label, upload_fn = UPLOAD_MAP[data_type]
        logger.info(f"\n{'='*50}")
        logger.info(f"Uploading {label}...")
        logger.info(f"{'='*50}")
        try:
            uploaded, errors = upload_fn()
            total_uploaded += uploaded
            total_errors += errors
            results.append((label, uploaded, errors))
        except Exception as e:
            logger.error(f"{label} upload failed: {e}")
            results.append((label, 0, -1))

    # Summary
    print(f"\n{'='*50}")
    print("UPLOAD SUMMARY")
    print(f"{'='*50}")
    for label, uploaded, errors in results:
        status = "OK" if errors == 0 else f"ERRORS: {errors}" if errors > 0 else "FAILED"
        print(f"  {label}: {uploaded} records [{status}]")
    print(f"\nTotal: {total_uploaded} uploaded, {total_errors} errors")


if __name__ == "__main__":
    main()
