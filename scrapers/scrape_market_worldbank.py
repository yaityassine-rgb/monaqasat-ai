"""
Market intelligence scraper using World Bank Open Data API.

Fetches key economic indicators for MENA countries:
  - GDP, GDP growth, inflation, population, unemployment
  - FDI net inflows, industry value added (incl. construction)
  - Ease of doing business score

API docs: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information
"""

import requests
import logging
import time
from datetime import datetime, timezone
from config import HEADERS, MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR

from base_scraper import save_market_data

logger = logging.getLogger("market_worldbank")

# World Bank uses ISO-3166 alpha-2 codes but some differ from our config
# Map our codes to World Bank country codes
WB_COUNTRY_CODES = {
    "SA": "SAU",
    "AE": "ARE",
    "QA": "QAT",
    "KW": "KWT",
    "BH": "BHR",
    "OM": "OMN",
    "EG": "EGY",
    "MA": "MAR",
    "JO": "JOR",
    "TN": "TUN",
    "DZ": "DZA",
    "IQ": "IRQ",
    "LY": "LBY",
    "LB": "LBN",
    "PS": "PSE",
    "SD": "SDN",
    "YE": "YEM",
    "MR": "MRT",
}

# ISO-2 codes accepted by World Bank API (simpler variant)
WB_ISO2 = {
    "SA": "SA",
    "AE": "AE",
    "QA": "QA",
    "KW": "KW",
    "BH": "BH",
    "OM": "OM",
    "EG": "EG",
    "MA": "MA",
    "JO": "JO",
    "TN": "TN",
    "DZ": "DZ",
    "IQ": "IQ",
    "LY": "LY",
    "LB": "LB",
    "PS": "PS",
    "SD": "SD",
    "YE": "YE",
    "MR": "MR",
}

# Key indicators to fetch
INDICATORS = {
    "NY.GDP.MKTP.CD": "gdp_current_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "FP.CPI.TOTL.ZG": "inflation_pct",
    "SP.POP.TOTL": "population",
    "SL.UEM.TOTL.ZS": "unemployment_pct",
    "BX.KLT.DINV.CD.WD": "fdi_inflow_usd",
    "IC.BUS.EASE.XQ": "ease_of_business_score",
    "NV.IND.TOTL.CD": "industry_value_added_usd",
}

WB_API_BASE = "https://api.worldbank.org/v2"

# Currency information per country
CURRENCY_INFO = {
    "SA": {"code": "SAR", "name": "Saudi Riyal", "rate": 3.75},
    "AE": {"code": "AED", "name": "UAE Dirham", "rate": 3.67},
    "QA": {"code": "QAR", "name": "Qatari Riyal", "rate": 3.64},
    "KW": {"code": "KWD", "name": "Kuwaiti Dinar", "rate": 0.31},
    "BH": {"code": "BHD", "name": "Bahraini Dinar", "rate": 0.376},
    "OM": {"code": "OMR", "name": "Omani Rial", "rate": 0.385},
    "EG": {"code": "EGP", "name": "Egyptian Pound", "rate": 50.5},
    "MA": {"code": "MAD", "name": "Moroccan Dirham", "rate": 10.1},
    "JO": {"code": "JOD", "name": "Jordanian Dinar", "rate": 0.709},
    "TN": {"code": "TND", "name": "Tunisian Dinar", "rate": 3.15},
    "DZ": {"code": "DZD", "name": "Algerian Dinar", "rate": 135.0},
    "IQ": {"code": "IQD", "name": "Iraqi Dinar", "rate": 1310.0},
    "LY": {"code": "LYD", "name": "Libyan Dinar", "rate": 4.85},
    "LB": {"code": "LBP", "name": "Lebanese Pound", "rate": 89500.0},
    "PS": {"code": "ILS", "name": "Israeli Shekel / JOD", "rate": 3.67},
    "SD": {"code": "SDG", "name": "Sudanese Pound", "rate": 601.0},
    "YE": {"code": "YER", "name": "Yemeni Rial", "rate": 250.0},
    "MR": {"code": "MRU", "name": "Mauritanian Ouguiya", "rate": 39.7},
}

# Top sectors per country
TOP_SECTORS = {
    "SA": ["oil_gas", "construction", "tourism", "defense", "real_estate"],
    "AE": ["oil_gas", "real_estate", "tourism", "finance", "transport"],
    "QA": ["oil_gas", "construction", "finance", "real_estate", "transport"],
    "KW": ["oil_gas", "construction", "finance", "real_estate", "telecom"],
    "BH": ["finance", "oil_gas", "tourism", "construction", "telecom"],
    "OM": ["oil_gas", "construction", "tourism", "mining", "agriculture"],
    "EG": ["construction", "energy", "tourism", "agriculture", "telecom"],
    "MA": ["agriculture", "tourism", "mining", "construction", "energy"],
    "JO": ["mining", "tourism", "it", "construction", "energy"],
    "TN": ["agriculture", "tourism", "mining", "energy", "it"],
    "DZ": ["oil_gas", "construction", "agriculture", "mining", "energy"],
    "IQ": ["oil_gas", "construction", "agriculture", "energy", "water"],
    "LY": ["oil_gas", "construction", "agriculture", "energy", "water"],
    "LB": ["finance", "tourism", "real_estate", "agriculture", "it"],
    "PS": ["agriculture", "construction", "it", "tourism", "water"],
    "SD": ["agriculture", "mining", "oil_gas", "construction", "water"],
    "YE": ["oil_gas", "agriculture", "construction", "water", "energy"],
    "MR": ["mining", "agriculture", "oil_gas", "construction", "water"],
}


def _fetch_indicator(country_iso2: str, indicator: str, date_range: str = "2018:2025") -> tuple:
    """Fetch a single indicator value for a country from World Bank API.

    Returns:
        tuple: (value, year) for the most recent available data point, or (None, None).
    """
    url = f"{WB_API_BASE}/country/{country_iso2}/indicator/{indicator}"
    params = {
        "format": "json",
        "date": date_range,
        "per_page": 10,
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # World Bank API returns [metadata, data_array]
        if not isinstance(data, list) or len(data) < 2:
            return None, None

        records = data[1]
        if not records:
            return None, None

        # Find the most recent year with a non-null value
        for record in records:
            if record.get("value") is not None:
                return record["value"], int(record["date"])

        return None, None

    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        logger.warning(f"Failed to fetch {indicator} for {country_iso2}: {e}")
        return None, None


def _generate_market_summary(country_name: str, country_code: str, data: dict) -> dict:
    """Generate market summary text in English, Arabic, and French."""
    gdp_str = f"${data.get('gdp_usd', 'N/A')}B" if data.get("gdp_usd") else "N/A"
    growth_str = f"{data.get('gdp_growth_pct', 'N/A')}%" if data.get("gdp_growth_pct") is not None else "N/A"
    pop_str = f"{data.get('population', 'N/A')}M" if data.get("population") else "N/A"
    sectors_str = ", ".join(data.get("top_sectors", [])[:3])

    en = (
        f"{country_name} has a GDP of {gdp_str} with {growth_str} growth. "
        f"Population: {pop_str}. Key sectors: {sectors_str}. "
        f"The country offers opportunities in government procurement and infrastructure development."
    )

    ar = (
        f"يبلغ الناتج المحلي الإجمالي لـ{MENA_COUNTRIES_AR.get(country_code, country_name)} "
        f"{gdp_str} بمعدل نمو {growth_str}. "
        f"عدد السكان: {pop_str}. القطاعات الرئيسية: {sectors_str}."
    )

    fr = (
        f"Le PIB de {MENA_COUNTRIES_FR.get(country_code, country_name)} est de {gdp_str} "
        f"avec une croissance de {growth_str}. "
        f"Population: {pop_str}. Secteurs clés: {sectors_str}."
    )

    return {"en": en, "ar": ar, "fr": fr}


def _fetch_country_data(country_code: str, country_name: str) -> dict:
    """Fetch all indicators for a single country and build the market data record."""
    logger.info(f"Fetching World Bank data for {country_name} ({country_code})...")

    wb_code = country_code  # World Bank accepts ISO-2
    indicator_values = {}
    latest_year = 2020  # fallback

    for indicator_id, field_name in INDICATORS.items():
        value, year = _fetch_indicator(wb_code, indicator_id)
        indicator_values[field_name] = value
        if year and year > latest_year:
            latest_year = year
        # Rate limit: be respectful to the API
        time.sleep(0.3)

    # Process values into the output format
    gdp_raw = indicator_values.get("gdp_current_usd")
    gdp_billions = round(gdp_raw / 1e9, 2) if gdp_raw else None

    pop_raw = indicator_values.get("population")
    pop_millions = round(pop_raw / 1e6, 2) if pop_raw else None

    fdi_raw = indicator_values.get("fdi_inflow_usd")
    fdi_billions = round(fdi_raw / 1e9, 2) if fdi_raw else None

    industry_raw = indicator_values.get("industry_value_added_usd")
    industry_billions = round(industry_raw / 1e9, 2) if industry_raw else None

    currency = CURRENCY_INFO.get(country_code, {"code": "USD", "name": "US Dollar", "rate": 1.0})
    top_sectors = TOP_SECTORS.get(country_code, [])

    record = {
        "id": f"MKT-{country_code}-{latest_year}",
        "country": country_name,
        "country_code": country_code,
        "year": latest_year,
        "gdp_usd": gdp_billions,
        "gdp_growth_pct": round(indicator_values.get("gdp_growth_pct"), 2) if indicator_values.get("gdp_growth_pct") is not None else None,
        "inflation_pct": round(indicator_values.get("inflation_pct"), 2) if indicator_values.get("inflation_pct") is not None else None,
        "population": pop_millions,
        "unemployment_pct": round(indicator_values.get("unemployment_pct"), 2) if indicator_values.get("unemployment_pct") is not None else None,
        "fdi_inflow_usd": fdi_billions,
        "construction_output_usd": industry_billions,
        "ease_of_business_rank": round(indicator_values.get("ease_of_business_score")) if indicator_values.get("ease_of_business_score") is not None else None,
        "sector_breakdown": {},
        "top_sectors": top_sectors,
        "currency_code": currency["code"],
        "currency_name": currency["name"],
        "exchange_rate_usd": currency["rate"],
        "market_summary": "",
        "market_summary_ar": "",
        "market_summary_fr": "",
        "source": "world_bank_api",
        "metadata": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "api_base": WB_API_BASE,
            "indicators_fetched": list(INDICATORS.keys()),
            "data_year": latest_year,
        },
    }

    # Generate summaries
    summaries = _generate_market_summary(country_name, country_code, record)
    record["market_summary"] = summaries["en"]
    record["market_summary_ar"] = summaries["ar"]
    record["market_summary_fr"] = summaries["fr"]

    return record


def scrape() -> list[dict]:
    """Fetch World Bank economic indicators for all MENA countries.

    Returns:
        list[dict]: Market intelligence records with economic indicators.
    """
    logger.info("Starting World Bank market data scrape for MENA countries...")
    records = []

    for country_code, country_name in MENA_COUNTRIES.items():
        try:
            record = _fetch_country_data(country_code, country_name)
            records.append(record)
            logger.info(
                f"  {country_name}: GDP=${record.get('gdp_usd')}B, "
                f"Growth={record.get('gdp_growth_pct')}%, "
                f"Pop={record.get('population')}M, "
                f"Year={record.get('year')}"
            )
        except Exception as e:
            logger.error(f"Failed to fetch data for {country_name}: {e}")
            continue

        # Rate limit between countries
        time.sleep(0.5)

    logger.info(f"Completed World Bank scrape: {len(records)} country records")
    return records


if __name__ == "__main__":
    data = scrape()
    save_market_data(data, "market_worldbank")
    print(f"\nSaved {len(data)} market records from World Bank API")
    print("-" * 70)
    for rec in data:
        print(
            f"  {rec['country']:20s} | GDP: ${str(rec.get('gdp_usd', 'N/A')):>10s}B | "
            f"Growth: {str(rec.get('gdp_growth_pct', 'N/A')):>6s}% | "
            f"Pop: {str(rec.get('population', 'N/A')):>7s}M | "
            f"Year: {rec.get('year')}"
        )
