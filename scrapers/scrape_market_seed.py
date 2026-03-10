"""
Curated market intelligence seed data for 18 MENA countries.

This is NOT a web scraper — it provides hardcoded, researched market data
based on publicly available economic statistics (approximate 2024 values).

Covers: GDP, population, construction spend, top sectors, business environment,
opportunities, challenges, regulations, currency, trading partners, and free zones.
"""

import logging
from datetime import datetime, timezone
from config import MENA_COUNTRIES, MENA_COUNTRIES_AR, MENA_COUNTRIES_FR
from base_scraper import save_market_data

logger = logging.getLogger("market_seed")


def _build_record(
    country_code: str,
    year: int,
    gdp_usd: float,
    gdp_growth_pct: float,
    inflation_pct: float,
    population: float,
    unemployment_pct: float,
    fdi_inflow_usd: float,
    construction_output_usd: float,
    ease_of_business_rank: int,
    top_sectors: list,
    currency_code: str,
    currency_name: str,
    exchange_rate_usd: float,
    construction_spend_usd: float,
    business_environment: str,
    opportunities_en: str,
    opportunities_ar: str,
    opportunities_fr: str,
    challenges_en: str,
    challenges_ar: str,
    challenges_fr: str,
    key_regulations: str,
    major_trading_partners: list,
    free_trade_zones: list,
    market_summary_en: str,
    market_summary_ar: str,
    market_summary_fr: str,
) -> dict:
    """Build a standardized market data record."""
    country_name = MENA_COUNTRIES.get(country_code, country_code)
    return {
        "id": f"MKT-SEED-{country_code}-{year}",
        "country": country_name,
        "country_code": country_code,
        "country_name_ar": MENA_COUNTRIES_AR.get(country_code, ""),
        "country_name_fr": MENA_COUNTRIES_FR.get(country_code, ""),
        "year": year,
        "gdp_usd": gdp_usd,
        "gdp_growth_pct": gdp_growth_pct,
        "inflation_pct": inflation_pct,
        "population": population,
        "unemployment_pct": unemployment_pct,
        "fdi_inflow_usd": fdi_inflow_usd,
        "construction_output_usd": construction_output_usd,
        "construction_spend_usd": construction_spend_usd,
        "ease_of_business_rank": ease_of_business_rank,
        "sector_breakdown": {},
        "top_sectors": top_sectors,
        "currency_code": currency_code,
        "currency_name": currency_name,
        "exchange_rate_usd": exchange_rate_usd,
        "business_environment": business_environment,
        "opportunities": opportunities_en,
        "opportunities_ar": opportunities_ar,
        "opportunities_fr": opportunities_fr,
        "challenges": challenges_en,
        "challenges_ar": challenges_ar,
        "challenges_fr": challenges_fr,
        "key_regulations": key_regulations,
        "major_trading_partners": major_trading_partners,
        "free_trade_zones": free_trade_zones,
        "market_summary": market_summary_en,
        "market_summary_ar": market_summary_ar,
        "market_summary_fr": market_summary_fr,
        "source": "curated_seed_data",
        "metadata": {
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "data_source": "curated_seed_data",
            "data_year": year,
            "notes": "Approximate values based on publicly available economic data",
        },
    }


def _saudi_arabia() -> dict:
    return _build_record(
        country_code="SA",
        year=2024,
        gdp_usd=1061.9,
        gdp_growth_pct=3.2,
        inflation_pct=2.3,
        population=36.95,
        unemployment_pct=5.1,
        fdi_inflow_usd=7.9,
        construction_output_usd=85.0,
        ease_of_business_rank=62,
        top_sectors=["oil_gas", "construction", "tourism", "defense", "real_estate", "mining"],
        currency_code="SAR",
        currency_name="Saudi Riyal",
        exchange_rate_usd=3.75,
        construction_spend_usd=180.0,
        business_environment="Saudi Arabia is undergoing massive economic transformation through Vision 2030. The Kingdom is the largest economy in the MENA region, driven by oil revenues but rapidly diversifying into tourism (NEOM, Red Sea Project, Qiddiya), entertainment, mining, and technology. Government procurement is centralized through the Etimad platform. The construction sector is booming with mega projects worth over $1 trillion in the pipeline.",
        opportunities_en="Mega projects (NEOM, The Line, Red Sea, Qiddiya, Diriyah Gate); Vision 2030 privatization; defense localization (GAMI); renewable energy (REPDO); mining sector opening; tourism infrastructure; smart city development; healthcare expansion.",
        opportunities_ar="المشاريع الكبرى (نيوم، ذا لاين، البحر الأحمر، القدية)؛ خصخصة رؤية 2030؛ توطين الدفاع؛ الطاقة المتجددة؛ قطاع التعدين؛ البنية التحتية السياحية.",
        opportunities_fr="Méga projets (NEOM, The Line, Mer Rouge, Qiddiya); privatisation Vision 2030; localisation de la défense; énergie renouvelable; secteur minier; infrastructure touristique.",
        challenges_en="Saudization requirements (Nitaqat); bureaucratic processes; competition from established contractors; payment delays on some projects; need for local partnerships.",
        challenges_ar="متطلبات السعودة (نطاقات)؛ الإجراءات البيروقراطية؛ المنافسة من المقاولين المعروفين؛ تأخر الدفعات في بعض المشاريع.",
        challenges_fr="Exigences de saoudisation (Nitaqat); processus bureaucratiques; concurrence des entreprises établies; retards de paiement sur certains projets.",
        key_regulations="Government Tenders and Procurement Law (2019); Saudization (Nitaqat) requirements; Etimad mandatory registration; ZATCA tax compliance; Contractor Classification system; Local Content (Iktva for energy sector).",
        major_trading_partners=["China", "USA", "Japan", "South Korea", "India", "UAE", "Germany"],
        free_trade_zones=["King Abdullah Economic City (KAEC)", "Jazan City for Primary and Downstream Industries (JCPDI)", "Ras Al Khair Industrial City", "Knowledge Economic City (Medina)", "NEOM"],
        market_summary_en="Saudi Arabia's GDP stands at approximately $1,062B, making it the largest Arab economy. Vision 2030 is driving unprecedented investment in construction, tourism, and diversification, with over $1 trillion in projects planned or underway.",
        market_summary_ar="يبلغ الناتج المحلي الإجمالي للمملكة العربية السعودية حوالي 1,062 مليار دولار، مما يجعلها أكبر اقتصاد عربي. تقود رؤية 2030 استثمارات غير مسبوقة في البناء والسياحة والتنويع.",
        market_summary_fr="Le PIB de l'Arabie Saoudite s'élève à environ 1 062 milliards de dollars, ce qui en fait la plus grande économie arabe. La Vision 2030 stimule des investissements sans précédent dans la construction, le tourisme et la diversification.",
    )


def _uae() -> dict:
    return _build_record(
        country_code="AE",
        year=2024,
        gdp_usd=509.2,
        gdp_growth_pct=3.5,
        inflation_pct=2.1,
        population=10.15,
        unemployment_pct=2.7,
        fdi_inflow_usd=22.7,
        construction_output_usd=48.0,
        ease_of_business_rank=16,
        top_sectors=["oil_gas", "real_estate", "tourism", "finance", "transport", "it"],
        currency_code="AED",
        currency_name="UAE Dirham",
        exchange_rate_usd=3.67,
        construction_spend_usd=90.0,
        business_environment="The UAE is the most business-friendly economy in the MENA region, ranking 16th globally for ease of doing business. Dubai and Abu Dhabi lead with world-class infrastructure and diverse economies. 100% foreign ownership is allowed since 2020 reforms. The UAE is a regional hub for trade, finance, logistics, and tourism with major upcoming projects including Expo City Dubai legacy development.",
        opportunities_en="Real estate mega projects; Abu Dhabi ICV program; Expo City Dubai legacy; renewable energy (Masdar); AI and digital transformation; logistics (Khalifa Port, Jebel Ali); healthcare; education; space sector.",
        opportunities_ar="المشاريع العقارية الكبرى؛ برنامج القيمة المحلية المضافة أبوظبي؛ إرث إكسبو دبي؛ الطاقة المتجددة (مصدر)؛ الذكاء الاصطناعي؛ اللوجستيات.",
        opportunities_fr="Méga projets immobiliers; programme ICV Abu Dhabi; héritage Expo City Dubai; énergie renouvelable (Masdar); IA et transformation numérique; logistique.",
        challenges_en="High competition; ICV requirements for Abu Dhabi; corporate tax implementation (2023); rising operating costs; talent acquisition challenges.",
        challenges_ar="المنافسة الشديدة؛ متطلبات القيمة المحلية المضافة لأبوظبي؛ تطبيق ضريبة الشركات؛ ارتفاع تكاليف التشغيل.",
        challenges_fr="Forte concurrence; exigences ICV pour Abu Dhabi; mise en œuvre de l'impôt sur les sociétés; coûts d'exploitation croissants.",
        key_regulations="Federal Procurement Law; 100% foreign ownership (2020); Corporate Tax (9%, effective June 2023); VAT (5%); ICV program (Abu Dhabi); Data protection law (2021); Anti-money laundering regulations.",
        major_trading_partners=["China", "India", "USA", "Japan", "Saudi Arabia", "Germany", "UK", "Switzerland"],
        free_trade_zones=["JAFZA (Jebel Ali)", "DAFZA (Dubai Airport)", "DMCC", "ADGM (Abu Dhabi Global Market)", "DIFC", "Masdar City", "Khalifa Industrial Zone (KIZAD)", "Sharjah Airport Free Zone", "RAK Free Trade Zone"],
        market_summary_en="The UAE's $509B economy is the most diversified in the Gulf, with Dubai as a global business hub and Abu Dhabi as a major energy and investment center. Strong FDI inflows of $22.7B reflect the country's attractiveness.",
        market_summary_ar="يعد اقتصاد الإمارات البالغ 509 مليار دولار الأكثر تنوعاً في الخليج، مع دبي كمركز أعمال عالمي وأبوظبي كمركز طاقة واستثمار رئيسي.",
        market_summary_fr="L'économie des EAU de 509 milliards de dollars est la plus diversifiée du Golfe, avec Dubaï comme centre d'affaires mondial et Abu Dhabi comme centre majeur d'énergie et d'investissement.",
    )


def _qatar() -> dict:
    return _build_record(
        country_code="QA",
        year=2024,
        gdp_usd=219.6,
        gdp_growth_pct=2.4,
        inflation_pct=2.8,
        population=2.98,
        unemployment_pct=0.1,
        fdi_inflow_usd=2.8,
        construction_output_usd=25.0,
        ease_of_business_rank=77,
        top_sectors=["oil_gas", "construction", "finance", "real_estate", "transport"],
        currency_code="QAR",
        currency_name="Qatari Riyal",
        exchange_rate_usd=3.64,
        construction_spend_usd=35.0,
        business_environment="Qatar has the highest GDP per capita in the world, driven by massive LNG exports. Post-FIFA World Cup 2022, the country continues investing in infrastructure, North Field LNG expansion, and economic diversification under Qatar National Vision 2030. Ashghal (Public Works Authority) manages major infrastructure projects.",
        opportunities_en="North Field LNG expansion (world's largest); post-World Cup infrastructure maintenance; Lusail City development; metro expansion; healthcare and education cities; cybersecurity; fintech.",
        opportunities_ar="توسعة حقل الشمال للغاز المسال؛ صيانة البنية التحتية بعد كأس العالم؛ تطوير مدينة لوسيل؛ توسعة المترو.",
        opportunities_fr="Expansion North Field GNL; maintenance des infrastructures post-Coupe du monde; développement de Lusail City; extension du métro.",
        challenges_en="Small market size; Qatarization requirements; high cost of living; limited local talent pool; dependency on hydrocarbon revenues.",
        challenges_ar="حجم السوق الصغير؛ متطلبات التقطير؛ تكلفة المعيشة المرتفعة؛ الاعتماد على عائدات النفط والغاز.",
        challenges_fr="Taille de marché réduite; exigences de qatarisation; coût de la vie élevé; dépendance aux revenus des hydrocarbures.",
        key_regulations="Government Procurement Law; Qatar National Vision 2030; Qatarization requirements; QFC regulations for foreign companies; PPP framework; Data privacy law.",
        major_trading_partners=["Japan", "South Korea", "India", "China", "Singapore", "UK", "USA"],
        free_trade_zones=["Qatar Financial Centre (QFC)", "Qatar Free Zones Authority (QFZA)", "Umm Alhoul Free Zone", "Ras Bufontas Free Zone"],
        market_summary_en="Qatar's $220B economy has the world's highest GDP per capita, powered by LNG exports. The North Field expansion will increase LNG capacity by 85%, driving massive investment in the energy sector.",
        market_summary_ar="يتمتع اقتصاد قطر البالغ 220 مليار دولار بأعلى ناتج محلي للفرد في العالم، مدعوماً بصادرات الغاز المسال. سيزيد توسع حقل الشمال طاقة الغاز بنسبة 85%.",
        market_summary_fr="L'économie du Qatar de 220 milliards de dollars a le PIB par habitant le plus élevé au monde, alimenté par les exportations de GNL. L'expansion du North Field augmentera la capacité de GNL de 85%.",
    )


def _kuwait() -> dict:
    return _build_record(
        country_code="KW",
        year=2024,
        gdp_usd=161.8,
        gdp_growth_pct=2.3,
        inflation_pct=3.6,
        population=4.86,
        unemployment_pct=2.2,
        fdi_inflow_usd=1.5,
        construction_output_usd=12.0,
        ease_of_business_rank=83,
        top_sectors=["oil_gas", "construction", "finance", "real_estate", "telecom"],
        currency_code="KWD",
        currency_name="Kuwaiti Dinar",
        exchange_rate_usd=0.31,
        construction_spend_usd=25.0,
        business_environment="Kuwait's economy is heavily reliant on oil, with ambitious plans under Kuwait Vision 2035 (New Kuwait) to diversify. The Central Agency for Public Tenders (CAPT) manages government procurement. Major projects include Silk City (Madinat Al-Hareer), Al Zour refinery, and airport expansion.",
        opportunities_en="Kuwait Vision 2035 projects; Silk City mega-development; airport terminal expansion; oil sector modernization; PPP projects; healthcare infrastructure; renewable energy.",
        opportunities_ar="مشاريع رؤية الكويت 2035؛ مشروع مدينة الحرير؛ توسعة المطار؛ تحديث قطاع النفط؛ مشاريع الشراكة بين القطاعين.",
        opportunities_fr="Projets Vision Kuwait 2035; méga-développement Silk City; extension de l'aéroport; modernisation du secteur pétrolier; projets PPP.",
        challenges_en="Bureaucratic delays; Kuwaitization requirements; political instability affecting project timelines; limited diversification progress; local agent requirements.",
        challenges_ar="التأخيرات البيروقراطية؛ متطلبات التكويت؛ عدم الاستقرار السياسي؛ بطء التنويع؛ متطلبات الوكيل المحلي.",
        challenges_fr="Retards bureaucratiques; exigences de koweïtisation; instabilité politique; diversification limitée; exigences d'agent local.",
        key_regulations="Public Tenders Law; CAPT procurement rules; Kuwait Vision 2035; Kuwaitization labor quotas; BOT Law for PPP; Offset program for defense contracts.",
        major_trading_partners=["China", "South Korea", "Japan", "India", "USA", "Saudi Arabia", "EU"],
        free_trade_zones=["Kuwait Free Trade Zone (Shuwaikh)"],
        market_summary_en="Kuwait's $162B economy is the fourth largest in the GCC. Kuwait Vision 2035 aims to transform the country into a financial and commercial hub, with major infrastructure projects worth over $100B planned.",
        market_summary_ar="يعد اقتصاد الكويت البالغ 162 مليار دولار رابع أكبر اقتصاد في مجلس التعاون. تهدف رؤية 2035 إلى تحويل البلاد إلى مركز مالي وتجاري.",
        market_summary_fr="L'économie du Koweït de 162 milliards de dollars est la quatrième du CCG. La Vision Kuwait 2035 vise à transformer le pays en centre financier et commercial.",
    )


def _bahrain() -> dict:
    return _build_record(
        country_code="BH",
        year=2024,
        gdp_usd=44.4,
        gdp_growth_pct=3.1,
        inflation_pct=1.8,
        population=1.55,
        unemployment_pct=3.8,
        fdi_inflow_usd=1.8,
        construction_output_usd=4.5,
        ease_of_business_rank=43,
        top_sectors=["finance", "oil_gas", "tourism", "construction", "telecom", "it"],
        currency_code="BHD",
        currency_name="Bahraini Dinar",
        exchange_rate_usd=0.376,
        construction_spend_usd=8.0,
        business_environment="Bahrain positions itself as a financial hub in the Gulf with a progressive regulatory environment. The Tender Board manages transparent government procurement. Bahrain was the first GCC country to introduce VAT (2019). Key projects include Bahrain Bay, Diyar Al Muharraq, and the Bahrain Metro.",
        opportunities_en="Financial services (fintech hub); Bahrain Metro project; Diyar Al Muharraq development; tourism expansion; logistics and manufacturing; aluminum industry (Alba).",
        opportunities_ar="الخدمات المالية (مركز التكنولوجيا المالية)؛ مشروع مترو البحرين؛ تطوير ديار المحرق؛ توسع السياحة.",
        opportunities_fr="Services financiers (hub fintech); projet Métro de Bahreïn; développement Diyar Al Muharraq; expansion touristique.",
        challenges_en="Small market size; high government debt; limited natural resources; competition with Dubai and Riyadh for business; fiscal consolidation pressures.",
        challenges_ar="صغر حجم السوق؛ ارتفاع الدين الحكومي؛ محدودية الموارد الطبيعية؛ المنافسة مع دبي والرياض.",
        challenges_fr="Petite taille de marché; dette publique élevée; ressources naturelles limitées; concurrence avec Dubaï et Riyad.",
        key_regulations="Tender Board procurement regulations; VAT (10%, increased 2022); Bahrainization requirements; Central Bank of Bahrain regulations; Data protection law; Anti-money laundering framework.",
        major_trading_partners=["Saudi Arabia", "UAE", "USA", "China", "Japan", "India", "EU"],
        free_trade_zones=["Bahrain International Investment Park (BIIP)", "Bahrain Logistics Zone (BLZ)", "Bahrain FinTech Bay"],
        market_summary_en="Bahrain's $44B economy is the smallest in the GCC but punches above its weight as a financial hub. The country offers a transparent procurement system and progressive business regulations.",
        market_summary_ar="يعد اقتصاد البحرين البالغ 44 مليار دولار الأصغر في مجلس التعاون لكنه يتفوق كمركز مالي. تقدم البلاد نظام مشتريات شفاف ولوائح أعمال متقدمة.",
        market_summary_fr="L'économie de Bahreïn de 44 milliards de dollars est la plus petite du CCG mais se distingue comme centre financier. Le pays offre un système de marchés publics transparent.",
    )


def _oman() -> dict:
    return _build_record(
        country_code="OM",
        year=2024,
        gdp_usd=104.9,
        gdp_growth_pct=2.0,
        inflation_pct=1.1,
        population=5.28,
        unemployment_pct=3.0,
        fdi_inflow_usd=4.2,
        construction_output_usd=10.0,
        ease_of_business_rank=68,
        top_sectors=["oil_gas", "construction", "tourism", "mining", "agriculture", "logistics"],
        currency_code="OMR",
        currency_name="Omani Rial",
        exchange_rate_usd=0.385,
        construction_spend_usd=18.0,
        business_environment="Oman is diversifying under Oman Vision 2040, focusing on tourism, logistics, mining, and manufacturing. The Duqm Special Economic Zone is a major development hub. The Government Tender Board oversees public procurement with increasing use of electronic tendering.",
        opportunities_en="Duqm Special Economic Zone; Oman Rail network; tourism (luxury and eco-tourism); mining (copper, chromite); green hydrogen projects; logistics hub (Sohar Port); fisheries modernization.",
        opportunities_ar="المنطقة الاقتصادية الخاصة بالدقم؛ شبكة سكك حديد عمان؛ السياحة؛ التعدين؛ مشاريع الهيدروجين الأخضر؛ مركز لوجستي.",
        opportunities_fr="Zone économique spéciale de Duqm; réseau ferroviaire d'Oman; tourisme; mines; projets d'hydrogène vert; hub logistique.",
        challenges_en="Omanization requirements; fiscal constraints; small domestic market; limited diversification to date; remote project locations (Duqm).",
        challenges_ar="متطلبات التعمين؛ القيود المالية؛ صغر السوق المحلي؛ محدودية التنويع حتى الآن.",
        challenges_fr="Exigences d'omanisation; contraintes fiscales; petit marché intérieur; diversification limitée jusqu'à présent.",
        key_regulations="Government Tender Board law; Oman Vision 2040; Omanization labor quotas; ICV requirements (energy sector); Foreign Capital Investment Law; VAT (5%, introduced 2021).",
        major_trading_partners=["China", "India", "Japan", "South Korea", "UAE", "Saudi Arabia", "USA"],
        free_trade_zones=["Duqm Special Economic Zone (SEZAD)", "Sohar Free Zone", "Salalah Free Zone", "Al Mazunah Free Zone", "Knowledge Oasis Muscat"],
        market_summary_en="Oman's $105B economy is focusing on diversification through Vision 2040. The Duqm Special Economic Zone and green hydrogen projects represent major investment opportunities.",
        market_summary_ar="يركز اقتصاد عمان البالغ 105 مليار دولار على التنويع من خلال رؤية 2040. تمثل منطقة الدقم الاقتصادية ومشاريع الهيدروجين الأخضر فرصاً استثمارية كبرى.",
        market_summary_fr="L'économie d'Oman de 105 milliards de dollars se concentre sur la diversification via la Vision 2040. La zone économique de Duqm et les projets d'hydrogène vert représentent d'importantes opportunités.",
    )


def _egypt() -> dict:
    return _build_record(
        country_code="EG",
        year=2024,
        gdp_usd=395.9,
        gdp_growth_pct=3.8,
        inflation_pct=28.5,
        population=106.4,
        unemployment_pct=7.1,
        fdi_inflow_usd=9.8,
        construction_output_usd=35.0,
        ease_of_business_rank=114,
        top_sectors=["construction", "energy", "tourism", "agriculture", "telecom", "real_estate"],
        currency_code="EGP",
        currency_name="Egyptian Pound",
        exchange_rate_usd=50.5,
        construction_spend_usd=55.0,
        business_environment="Egypt is the most populous Arab country and the third-largest economy in the MENA region. The New Administrative Capital (NAC), Suez Canal Economic Zone, and major renewable energy projects drive construction demand. The government has undertaken significant economic reforms including EGP devaluation and IMF programs.",
        opportunities_en="New Administrative Capital; Suez Canal Economic Zone (SCZONE); renewable energy (Benban solar park); New Alamein city; real estate development; transportation (monorail, high-speed rail); digital transformation; Ras El Hekma mega development.",
        opportunities_ar="العاصمة الإدارية الجديدة؛ المنطقة الاقتصادية لقناة السويس؛ الطاقة المتجددة؛ مدينة العلمين الجديدة؛ التطوير العقاري؛ النقل؛ التحول الرقمي.",
        opportunities_fr="Nouvelle Capitale Administrative; Zone économique du Canal de Suez; énergie renouvelable; Nouvelle Alamein; développement immobilier; transport; transformation numérique.",
        challenges_en="High inflation (28%+); currency volatility; bureaucratic complexity; payment delays; informal economy; infrastructure gaps outside Cairo.",
        challenges_ar="التضخم المرتفع؛ تقلبات العملة؛ التعقيدات البيروقراطية؛ تأخر المدفوعات؛ الاقتصاد غير الرسمي.",
        challenges_fr="Inflation élevée (28%+); volatilité de la monnaie; complexité bureaucratique; retards de paiement; économie informelle.",
        key_regulations="Government Procurement Law (2018); Public-Private Partnership Law; Investment Law (2017); 15% local content preference; Contractor Classification system (Categories 1-7); Special Economic Zones regulations.",
        major_trading_partners=["EU", "USA", "China", "Saudi Arabia", "Turkey", "UAE", "India", "Russia"],
        free_trade_zones=["Suez Canal Economic Zone (SCZONE)", "New Administrative Capital", "Ain Sokhna Industrial Zone", "Alexandria Free Zone", "Nasr City Free Zone", "Port Said Free Zone"],
        market_summary_en="Egypt's $396B economy is the largest in North Africa with 106M people. Despite high inflation, massive infrastructure projects (New Capital, SCZONE, Ras El Hekma) offer significant procurement opportunities.",
        market_summary_ar="يعد اقتصاد مصر البالغ 396 مليار دولار الأكبر في شمال أفريقيا بتعداد 106 مليون نسمة. رغم التضخم المرتفع، تقدم المشاريع الكبرى فرصاً كبيرة للمشتريات.",
        market_summary_fr="L'économie de l'Égypte de 396 milliards de dollars est la plus grande d'Afrique du Nord avec 106M d'habitants. Malgré l'inflation élevée, les méga projets offrent d'importantes opportunités.",
    )


def _morocco() -> dict:
    return _build_record(
        country_code="MA",
        year=2024,
        gdp_usd=150.0,
        gdp_growth_pct=3.4,
        inflation_pct=3.2,
        population=37.84,
        unemployment_pct=11.8,
        fdi_inflow_usd=2.1,
        construction_output_usd=12.0,
        ease_of_business_rank=53,
        top_sectors=["agriculture", "tourism", "mining", "construction", "energy", "it", "transport"],
        currency_code="MAD",
        currency_name="Moroccan Dirham",
        exchange_rate_usd=10.1,
        construction_spend_usd=22.0,
        business_environment="Morocco is North Africa's most open economy, positioned as a gateway between Europe and Africa. The country has strong automotive and aerospace manufacturing sectors (Renault, Boeing, Bombardier). Morocco hosted COP22 and is a leader in renewable energy (Noor-Ouarzazate solar complex). The 2030 FIFA World Cup co-hosting will drive major infrastructure investment.",
        opportunities_en="2030 FIFA World Cup infrastructure; high-speed rail expansion (TGV); Tanger Med port expansion; Noor solar complex; automotive free zones; Mohammed VI Tangier Tech City; phosphate value chain (OCP); desalination projects.",
        opportunities_ar="بنية كأس العالم 2030؛ توسعة القطار فائق السرعة؛ توسعة ميناء طنجة المتوسط؛ مجمع نور الشمسي؛ المناطق الحرة للسيارات؛ مدينة محمد السادس طنجة تك.",
        opportunities_fr="Infrastructures Coupe du Monde 2030; extension TGV; extension Tanger Med; complexe solaire Noor; zones franches automobiles; Mohammed VI Tangier Tech City; chaîne de valeur phosphates (OCP).",
        challenges_en="High unemployment (12%); water scarcity; regional disparities; informal economy; complex procurement procedures; French language requirement for documentation.",
        challenges_ar="ارتفاع البطالة؛ ندرة المياه؛ التفاوت الإقليمي؛ الاقتصاد غير الرسمي؛ تعقيد إجراءات المشتريات.",
        challenges_fr="Chômage élevé (12%); rareté de l'eau; disparités régionales; économie informelle; procédures de marchés publics complexes.",
        key_regulations="Decree 2-12-349 (Public Procurement); 15% national preference; Agrément system for public works; Marchés publics portal mandatory; Renault/PSA automotive regulations; OCP partnership framework.",
        major_trading_partners=["EU (France, Spain)", "USA", "China", "Turkey", "India", "Brazil", "Sub-Saharan Africa"],
        free_trade_zones=["Tanger Free Zone", "Tanger Med Zones", "Kenitra Atlantic Free Zone", "Casablanca Finance City (CFC)", "Midparc (aerospace)", "Oujda Free Zone"],
        market_summary_en="Morocco's $150B economy is North Africa's most diversified. The upcoming 2030 World Cup will drive $10B+ in infrastructure investment. Strong automotive and renewable energy sectors offer procurement opportunities.",
        market_summary_ar="يعد اقتصاد المغرب البالغ 150 مليار دولار الأكثر تنوعاً في شمال أفريقيا. سيدفع كأس العالم 2030 استثمارات تزيد عن 10 مليارات دولار في البنية التحتية.",
        market_summary_fr="L'économie du Maroc de 150 milliards de dollars est la plus diversifiée d'Afrique du Nord. La Coupe du Monde 2030 va générer plus de 10 milliards de dollars d'investissement en infrastructures.",
    )


def _jordan() -> dict:
    return _build_record(
        country_code="JO",
        year=2024,
        gdp_usd=50.8,
        gdp_growth_pct=2.7,
        inflation_pct=2.1,
        population=11.5,
        unemployment_pct=22.0,
        fdi_inflow_usd=1.2,
        construction_output_usd=3.5,
        ease_of_business_rank=75,
        top_sectors=["mining", "tourism", "it", "construction", "energy", "agriculture"],
        currency_code="JOD",
        currency_name="Jordanian Dinar",
        exchange_rate_usd=0.709,
        construction_spend_usd=6.0,
        business_environment="Jordan has a small but stable economy, positioned as a hub for IT services and a gateway to the Levant. The country has strong human capital and is a major recipient of international development aid. JONEPS is the mandatory e-procurement platform. The IT/outsourcing sector is a regional leader.",
        opportunities_en="IT and outsourcing services; renewable energy (solar and wind); Aqaba Special Economic Zone; water sector (desalination, Red Sea-Dead Sea project); tourism development; healthcare services; Amman Bus Rapid Transit.",
        opportunities_ar="خدمات تكنولوجيا المعلومات والتعهيد؛ الطاقة المتجددة؛ المنطقة الاقتصادية الخاصة بالعقبة؛ قطاع المياه؛ تطوير السياحة.",
        opportunities_fr="Services IT et externalisation; énergie renouvelable; Zone économique spéciale d'Aqaba; secteur de l'eau; développement touristique.",
        challenges_en="High unemployment (22%); limited natural resources; water scarcity; high public debt; regional instability impact; small market size; refugee population pressure.",
        challenges_ar="ارتفاع البطالة (22%)؛ محدودية الموارد الطبيعية؛ شح المياه؛ ارتفاع الدين العام؛ تأثير عدم الاستقرار الإقليمي.",
        challenges_fr="Chômage élevé (22%); ressources naturelles limitées; pénurie d'eau; dette publique élevée; impact de l'instabilité régionale.",
        key_regulations="Government Tenders Directorate regulations; JONEPS mandatory registration; PPP Law (2014); Investment Law (2014); Aqaba Special Economic Zone Authority (ASEZA); Free Zones regulations.",
        major_trading_partners=["USA", "Saudi Arabia", "EU", "India", "China", "Iraq", "UAE", "Turkey"],
        free_trade_zones=["Aqaba Special Economic Zone (ASEZ)", "Zarqa Free Zone", "Sahab Industrial Zone", "Al Hassan Industrial Zone", "Irbid Qualifying Industrial Zone"],
        market_summary_en="Jordan's $51B economy is stable but resource-constrained. The country is a regional IT hub and benefits from significant international aid and trade agreements (US FTA, EU Association). Water and energy sectors offer major procurement opportunities.",
        market_summary_ar="يتسم اقتصاد الأردن البالغ 51 مليار دولار بالاستقرار رغم محدودية الموارد. تعد البلاد مركزاً إقليمياً لتكنولوجيا المعلومات.",
        market_summary_fr="L'économie de la Jordanie de 51 milliards de dollars est stable mais contrainte en ressources. Le pays est un hub IT régional.",
    )


def _tunisia() -> dict:
    return _build_record(
        country_code="TN",
        year=2024,
        gdp_usd=48.5,
        gdp_growth_pct=1.8,
        inflation_pct=7.5,
        population=12.2,
        unemployment_pct=15.4,
        fdi_inflow_usd=0.8,
        construction_output_usd=2.5,
        ease_of_business_rank=78,
        top_sectors=["agriculture", "tourism", "mining", "energy", "it", "textile"],
        currency_code="TND",
        currency_name="Tunisian Dinar",
        exchange_rate_usd=3.15,
        construction_spend_usd=4.5,
        business_environment="Tunisia has a relatively diversified economy with strong agricultural, tourism, and manufacturing sectors. The country is a major olive oil exporter and has significant phosphate reserves. TUNEPS is the mandatory e-procurement platform. Economic recovery is ongoing after the 2011 revolution.",
        opportunities_en="Renewable energy (solar, wind); phosphate value chain; IT and nearshoring services; agricultural modernization; tourism rehabilitation; Enfidha deep-water port; water management.",
        opportunities_ar="الطاقة المتجددة؛ سلسلة قيمة الفوسفات؛ خدمات تكنولوجيا المعلومات؛ تحديث الزراعة؛ إعادة تأهيل السياحة.",
        opportunities_fr="Énergie renouvelable; chaîne de valeur des phosphates; services IT et nearshoring; modernisation agricole; réhabilitation touristique; port en eaux profondes d'Enfidha.",
        challenges_en="High unemployment (15%+); political uncertainty; fiscal pressures; inflation (7.5%); slow reform implementation; aging infrastructure; brain drain.",
        challenges_ar="ارتفاع البطالة؛ عدم اليقين السياسي؛ الضغوط المالية؛ التضخم؛ بطء الإصلاحات؛ البنية التحتية القديمة.",
        challenges_fr="Chômage élevé (15%+); incertitude politique; pressions fiscales; inflation; mise en œuvre lente des réformes; infrastructure vieillissante.",
        key_regulations="Public Procurement Decree 2014-1039; TUNEPS mandatory platform; HAICOP regulatory oversight; 10% national preference; Agrément BTP system; Investment Law (2016).",
        major_trading_partners=["EU (France, Italy, Germany)", "Libya", "Algeria", "Turkey", "China", "USA"],
        free_trade_zones=["Bizerte Economic Activity Park", "Zarzis Free Zone", "Enfidha Free Zone"],
        market_summary_en="Tunisia's $49B economy faces economic challenges but offers opportunities in renewable energy, IT nearshoring, and agricultural modernization. Proximity to Europe and educated workforce are key advantages.",
        market_summary_ar="يواجه اقتصاد تونس البالغ 49 مليار دولار تحديات اقتصادية لكنه يقدم فرصاً في الطاقة المتجددة والتكنولوجيا والزراعة.",
        market_summary_fr="L'économie tunisienne de 49 milliards de dollars fait face à des défis mais offre des opportunités dans l'énergie renouvelable, le nearshoring IT et la modernisation agricole.",
    )


def _algeria() -> dict:
    return _build_record(
        country_code="DZ",
        year=2024,
        gdp_usd=233.4,
        gdp_growth_pct=3.8,
        inflation_pct=7.2,
        population=46.3,
        unemployment_pct=11.4,
        fdi_inflow_usd=1.6,
        construction_output_usd=20.0,
        ease_of_business_rank=157,
        top_sectors=["oil_gas", "construction", "agriculture", "mining", "energy"],
        currency_code="DZD",
        currency_name="Algerian Dinar",
        exchange_rate_usd=135.0,
        construction_spend_usd=30.0,
        business_environment="Algeria has Africa's largest gas reserves and is the third-largest economy in MENA. The government is pursuing economic diversification and infrastructure development. The 51/49 foreign ownership rule has been relaxed for non-strategic sectors since 2020. Public procurement follows Presidential Decree 15-247.",
        opportunities_en="Oil & gas sector modernization; renewable energy (Desertec concept); infrastructure rehabilitation; housing (5M unit deficit); port modernization; Hassi Messaoud petrochemical complex; agriculture development.",
        opportunities_ar="تحديث قطاع النفط والغاز؛ الطاقة المتجددة؛ إعادة تأهيل البنية التحتية؛ الإسكان؛ تحديث الموانئ؛ تطوير الزراعة.",
        opportunities_fr="Modernisation du secteur des hydrocarbures; énergie renouvelable; réhabilitation des infrastructures; logement; modernisation portuaire; complexe pétrochimique de Hassi Messaoud.",
        challenges_en="Bureaucratic complexity; 51/49 rule (partially relaxed); limited transparency; currency controls; import restrictions; slow reform pace; corruption perceptions.",
        challenges_ar="التعقيدات البيروقراطية؛ قاعدة 51/49؛ محدودية الشفافية؛ قيود العملة؛ قيود الاستيراد؛ بطء الإصلاحات.",
        challenges_fr="Complexité bureaucratique; règle 51/49; transparence limitée; contrôle des changes; restrictions d'importation; rythme lent des réformes.",
        key_regulations="Presidential Decree 15-247 (Public Procurement); 51/49 rule (relaxed for non-strategic sectors 2020); 25% national preference for Algerian products; Hydrocarbons Law (2019); Investment Law (2022); BOMOP publication requirement.",
        major_trading_partners=["EU (Italy, France, Spain)", "China", "Turkey", "USA", "Brazil"],
        free_trade_zones=["Bellara Industrial Zone (Jijel)", "Hassi Messaoud Industrial Zone"],
        market_summary_en="Algeria's $233B economy is Africa's fourth largest, driven by hydrocarbons. The country has significant infrastructure needs and housing deficit. Relaxation of the 51/49 rule is opening new opportunities for foreign investors.",
        market_summary_ar="يعد اقتصاد الجزائر البالغ 233 مليار دولار رابع أكبر اقتصاد في أفريقيا. تفتح الإصلاحات فرصاً جديدة للمستثمرين الأجانب.",
        market_summary_fr="L'économie de l'Algérie de 233 milliards de dollars est la quatrième d'Afrique. L'assouplissement de la règle 51/49 ouvre de nouvelles opportunités pour les investisseurs étrangers.",
    )


def _libya() -> dict:
    return _build_record(
        country_code="LY",
        year=2024,
        gdp_usd=45.6,
        gdp_growth_pct=7.5,
        inflation_pct=3.8,
        population=7.05,
        unemployment_pct=19.0,
        fdi_inflow_usd=0.3,
        construction_output_usd=3.0,
        ease_of_business_rank=186,
        top_sectors=["oil_gas", "construction", "agriculture", "energy", "water"],
        currency_code="LYD",
        currency_name="Libyan Dinar",
        exchange_rate_usd=4.85,
        construction_spend_usd=5.0,
        business_environment="Libya has Africa's largest proven oil reserves but has been affected by political instability since 2011. Reconstruction needs are massive. When stability returns, Libya will offer significant opportunities in infrastructure rehabilitation, oil sector modernization, and housing reconstruction.",
        opportunities_en="Post-conflict reconstruction; oil sector rehabilitation; infrastructure rebuilding; housing reconstruction; power generation; water management (Great Man-Made River maintenance).",
        opportunities_ar="إعادة الإعمار بعد النزاع؛ تأهيل قطاع النفط؛ إعادة بناء البنية التحتية؛ إعادة بناء المساكن؛ توليد الطاقة.",
        opportunities_fr="Reconstruction post-conflit; réhabilitation du secteur pétrolier; reconstruction des infrastructures; reconstruction des logements.",
        challenges_en="Political instability; security concerns; institutional fragmentation; limited banking system; sanctions risk; payment uncertainty; dual government structures.",
        challenges_ar="عدم الاستقرار السياسي؛ المخاوف الأمنية؛ التفكك المؤسسي؛ محدودية النظام المصرفي؛ مخاطر العقوبات.",
        challenges_fr="Instabilité politique; préoccupations sécuritaires; fragmentation institutionnelle; système bancaire limité; risque de sanctions.",
        key_regulations="Administrative Contracts Law (inherited); National Oil Corporation procurement rules; UN-backed government regulations; Central Bank of Libya oversight.",
        major_trading_partners=["Italy", "Spain", "France", "China", "Turkey", "Germany"],
        free_trade_zones=["Misrata Free Zone"],
        market_summary_en="Libya's $46B economy is driven by oil but faces significant political instability. Massive reconstruction needs represent long-term opportunities when stability is achieved.",
        market_summary_ar="يعتمد اقتصاد ليبيا البالغ 46 مليار دولار على النفط لكنه يواجه عدم استقرار سياسي كبير. تمثل احتياجات إعادة الإعمار فرصاً طويلة المدى.",
        market_summary_fr="L'économie libyenne de 46 milliards de dollars est tirée par le pétrole mais fait face à une instabilité politique significative.",
    )


def _iraq() -> dict:
    return _build_record(
        country_code="IQ",
        year=2024,
        gdp_usd=264.2,
        gdp_growth_pct=3.7,
        inflation_pct=4.0,
        population=44.5,
        unemployment_pct=15.5,
        fdi_inflow_usd=7.6,
        construction_output_usd=18.0,
        ease_of_business_rank=172,
        top_sectors=["oil_gas", "construction", "agriculture", "energy", "water"],
        currency_code="IQD",
        currency_name="Iraqi Dinar",
        exchange_rate_usd=1310.0,
        construction_spend_usd=28.0,
        business_environment="Iraq has the fifth-largest proven oil reserves globally and is a major OPEC producer. The country is rebuilding after decades of conflict and sanctions. The Development Road project (Grand Faw Port to Turkey) is a transformational mega project. Kurdistan Region has a separate, more business-friendly framework.",
        opportunities_en="Development Road project (Grand Faw Port); oil sector expansion; post-conflict reconstruction; housing (massive deficit); power generation; water treatment; Basra Gas Company expansion; Kurdistan Region projects.",
        opportunities_ar="مشروع طريق التنمية (ميناء الفاو الكبير)؛ توسعة قطاع النفط؛ إعادة الإعمار؛ الإسكان؛ توليد الطاقة؛ معالجة المياه.",
        opportunities_fr="Projet Route du développement (Grand Port de Faw); expansion pétrolière; reconstruction; logement; production d'énergie; traitement de l'eau.",
        challenges_en="Bureaucratic complexity; corruption; security concerns in some areas; payment delays; currency restrictions; infrastructure gaps; dual procurement systems (federal/Kurdistan).",
        challenges_ar="التعقيدات البيروقراطية؛ الفساد؛ المخاوف الأمنية؛ تأخر المدفوعات؛ قيود العملة؛ فجوات البنية التحتية.",
        challenges_fr="Complexité bureaucratique; corruption; préoccupations sécuritaires; retards de paiement; restrictions de change; lacunes d'infrastructure.",
        key_regulations="Government Procurement regulations; Kurdistan Region procurement regulations; National Investment Law (2006, amended); Oil & Gas framework; Central Bank regulations.",
        major_trading_partners=["China", "India", "Turkey", "South Korea", "USA", "EU", "UAE", "Iran"],
        free_trade_zones=["Basra Free Zone", "Khor Al-Zubair Free Zone", "Fallujah Free Zone", "Sulaymaniyah Free Zone (KRI)", "Erbil Free Zone (KRI)"],
        market_summary_en="Iraq's $264B economy is oil-driven with massive reconstruction needs. The $17B Development Road project (Grand Faw Port) aims to make Iraq a trade corridor between Asia and Europe.",
        market_summary_ar="يعتمد اقتصاد العراق البالغ 264 مليار دولار على النفط مع احتياجات إعمار ضخمة. يهدف مشروع طريق التنمية البالغ 17 مليار دولار إلى جعل العراق ممراً تجارياً.",
        market_summary_fr="L'économie irakienne de 264 milliards de dollars est tirée par le pétrole avec d'importants besoins de reconstruction. Le projet Route du développement de 17 milliards de dollars vise à faire de l'Irak un corridor commercial.",
    )


def _lebanon() -> dict:
    return _build_record(
        country_code="LB",
        year=2024,
        gdp_usd=21.8,
        gdp_growth_pct=0.2,
        inflation_pct=15.0,
        population=5.6,
        unemployment_pct=29.6,
        fdi_inflow_usd=0.4,
        construction_output_usd=1.5,
        ease_of_business_rank=143,
        top_sectors=["finance", "tourism", "real_estate", "agriculture", "it"],
        currency_code="LBP",
        currency_name="Lebanese Pound",
        exchange_rate_usd=89500.0,
        construction_spend_usd=2.5,
        business_environment="Lebanon has experienced a severe economic crisis since 2019, with the banking sector collapse, hyperinflation, and political paralysis. The LBP has lost over 98% of its value. However, the country has a highly educated workforce, strong diaspora network, and historically vibrant services sector. Recovery will depend on political reforms and international support.",
        opportunities_en="Post-crisis reconstruction; banking sector reform; renewable energy (distributed solar); diaspora-funded projects; IT and outsourcing; agriculture modernization; Beirut port reconstruction.",
        opportunities_ar="إعادة الإعمار بعد الأزمة؛ إصلاح القطاع المصرفي؛ الطاقة المتجددة؛ مشاريع الشتات؛ تكنولوجيا المعلومات؛ إعمار مرفأ بيروت.",
        opportunities_fr="Reconstruction post-crise; réforme du secteur bancaire; énergie renouvelable; projets de la diaspora; IT et externalisation; reconstruction du port de Beyrouth.",
        challenges_en="Severe economic crisis; banking collapse; hyperinflation; political paralysis; infrastructure deterioration; brain drain; electricity shortages; Beirut port explosion aftermath.",
        challenges_ar="أزمة اقتصادية حادة؛ انهيار مصرفي؛ تضخم مفرط؛ شلل سياسي؛ تدهور البنية التحتية؛ هجرة الكفاءات.",
        challenges_fr="Crise économique sévère; effondrement bancaire; hyperinflation; paralysie politique; détérioration des infrastructures; fuite des cerveaux.",
        key_regulations="Public Procurement Law (2021, new); Central Bank circulars; Tender Board regulations; Investment Development Authority of Lebanon (IDAL); Banking secrecy laws (under reform).",
        major_trading_partners=["UAE", "Saudi Arabia", "China", "Turkey", "EU", "USA", "Iraq", "Syria"],
        free_trade_zones=["Tripoli Special Economic Zone (TSEZ)"],
        market_summary_en="Lebanon's economy has contracted significantly since 2019. Recovery depends on political reforms and international support. The new procurement law (2021) aims to improve transparency when implemented.",
        market_summary_ar="تقلص اقتصاد لبنان بشكل كبير منذ 2019. يعتمد التعافي على الإصلاحات السياسية والدعم الدولي.",
        market_summary_fr="L'économie libanaise s'est considérablement contractée depuis 2019. La reprise dépend des réformes politiques et du soutien international.",
    )


def _palestine() -> dict:
    return _build_record(
        country_code="PS",
        year=2024,
        gdp_usd=18.0,
        gdp_growth_pct=-5.0,
        inflation_pct=3.5,
        population=5.5,
        unemployment_pct=26.0,
        fdi_inflow_usd=0.2,
        construction_output_usd=1.0,
        ease_of_business_rank=117,
        top_sectors=["agriculture", "construction", "it", "tourism", "water"],
        currency_code="ILS",
        currency_name="Israeli Shekel / Jordanian Dinar",
        exchange_rate_usd=3.67,
        construction_spend_usd=2.0,
        business_environment="The Palestinian economy faces unique challenges due to the geopolitical situation. Despite constraints, there is an active IT sector and strong international donor support. The Palestinian Authority manages procurement for government projects. International organizations (UNDP, UNRWA, World Bank) are major procurement entities.",
        opportunities_en="Donor-funded reconstruction; IT and outsourcing services; renewable energy (solar); water management; agricultural technology; institutional capacity building.",
        opportunities_ar="إعادة الإعمار الممولة من المانحين؛ خدمات تكنولوجيا المعلومات؛ الطاقة المتجددة؛ إدارة المياه؛ التكنولوجيا الزراعية.",
        opportunities_fr="Reconstruction financée par les donateurs; services IT; énergie renouvelable; gestion de l'eau; technologie agricole.",
        challenges_en="Geopolitical instability; movement restrictions; limited sovereignty over resources; high unemployment; donor dependency; infrastructure constraints.",
        challenges_ar="عدم الاستقرار الجيوسياسي؛ قيود الحركة؛ محدودية السيادة على الموارد؛ ارتفاع البطالة؛ الاعتماد على المانحين.",
        challenges_fr="Instabilité géopolitique; restrictions de mouvement; souveraineté limitée sur les ressources; chômage élevé; dépendance aux donateurs.",
        key_regulations="Palestinian Public Procurement Law; Palestinian Authority regulations; International donor procurement rules (World Bank, UN); Investment Promotion Law.",
        major_trading_partners=["Israel", "EU", "Jordan", "Turkey", "USA", "China"],
        free_trade_zones=["Jericho Agro-Industrial Park (JAIP)", "Bethlehem Industrial Zone", "Jenin Industrial Free Zone"],
        market_summary_en="The Palestinian economy faces severe challenges but has an active IT sector and strong international donor support for reconstruction and development projects.",
        market_summary_ar="يواجه الاقتصاد الفلسطيني تحديات شديدة لكن لديه قطاع تكنولوجيا معلومات نشط ودعم دولي قوي لمشاريع الإعمار والتنمية.",
        market_summary_fr="L'économie palestinienne fait face à des défis sévères mais dispose d'un secteur IT actif et d'un fort soutien international pour les projets de reconstruction.",
    )


def _sudan() -> dict:
    return _build_record(
        country_code="SD",
        year=2024,
        gdp_usd=26.0,
        gdp_growth_pct=-18.0,
        inflation_pct=73.0,
        population=48.1,
        unemployment_pct=18.0,
        fdi_inflow_usd=0.2,
        construction_output_usd=1.0,
        ease_of_business_rank=171,
        top_sectors=["agriculture", "mining", "oil_gas", "construction", "water"],
        currency_code="SDG",
        currency_name="Sudanese Pound",
        exchange_rate_usd=601.0,
        construction_spend_usd=2.0,
        business_environment="Sudan's economy has been severely impacted by the civil conflict that began in April 2023. Prior to the conflict, the country was undergoing economic reforms post-sanctions removal (2020). Massive reconstruction needs will emerge when stability is restored. Sudan has significant agricultural potential and mineral resources (gold).",
        opportunities_en="Post-conflict reconstruction (when stability returns); agricultural sector modernization; gold mining; Nile water management; renewable energy; telecommunications infrastructure.",
        opportunities_ar="إعادة الإعمار بعد النزاع؛ تحديث القطاع الزراعي؛ تعدين الذهب؛ إدارة مياه النيل؛ الطاقة المتجددة.",
        opportunities_fr="Reconstruction post-conflit; modernisation agricole; mines d'or; gestion des eaux du Nil; énergie renouvelable.",
        challenges_en="Active civil conflict; economic collapse; hyperinflation; sanctions legacy; infrastructure destruction; humanitarian crisis; displacement of millions.",
        challenges_ar="نزاع مسلح نشط؛ انهيار اقتصادي؛ تضخم مفرط؛ تراث العقوبات؛ تدمير البنية التحتية؛ أزمة إنسانية.",
        challenges_fr="Conflit civil actif; effondrement économique; hyperinflation; héritage des sanctions; destruction des infrastructures; crise humanitaire.",
        key_regulations="Government procurement regulations (limited enforcement during conflict); Central Bank of Sudan regulations; Investment Law.",
        major_trading_partners=["UAE", "China", "Saudi Arabia", "India", "Egypt", "Turkey"],
        free_trade_zones=["Port Sudan Free Zone"],
        market_summary_en="Sudan's economy has collapsed due to the civil conflict since April 2023. When stability returns, massive reconstruction and development needs will create procurement opportunities.",
        market_summary_ar="انهار الاقتصاد السوداني بسبب النزاع المسلح منذ أبريل 2023. عند عودة الاستقرار ستظهر فرص إعمار وتنمية ضخمة.",
        market_summary_fr="L'économie soudanaise s'est effondrée en raison du conflit civil depuis avril 2023. La stabilité créera d'importantes opportunités de reconstruction.",
    )


def _yemen() -> dict:
    return _build_record(
        country_code="YE",
        year=2024,
        gdp_usd=21.0,
        gdp_growth_pct=-1.0,
        inflation_pct=10.0,
        population=34.4,
        unemployment_pct=30.0,
        fdi_inflow_usd=0.05,
        construction_output_usd=0.5,
        ease_of_business_rank=187,
        top_sectors=["oil_gas", "agriculture", "construction", "water", "energy"],
        currency_code="YER",
        currency_name="Yemeni Rial",
        exchange_rate_usd=250.0,
        construction_spend_usd=1.5,
        business_environment="Yemen has been in civil conflict since 2014 and faces one of the world's worst humanitarian crises. The economy has contracted by over 50% since the conflict began. When peace is achieved, reconstruction needs will be enormous. International organizations are the primary procurement entities currently.",
        opportunities_en="Humanitarian aid procurement; post-conflict reconstruction (future); port rehabilitation (Aden, Hodeidah); power infrastructure; water and sanitation; agricultural rehabilitation.",
        opportunities_ar="مشتريات المساعدات الإنسانية؛ إعادة الإعمار بعد النزاع؛ تأهيل الموانئ؛ البنية التحتية للطاقة؛ المياه والصرف الصحي.",
        opportunities_fr="Marchés de l'aide humanitaire; reconstruction post-conflit; réhabilitation portuaire; infrastructure énergétique; eau et assainissement.",
        challenges_en="Active conflict; humanitarian crisis; divided government; infrastructure destruction; currency instability; food insecurity; limited banking system.",
        challenges_ar="نزاع نشط؛ أزمة إنسانية؛ حكومة منقسمة؛ تدمير البنية التحتية؛ عدم استقرار العملة؛ انعدام الأمن الغذائي.",
        challenges_fr="Conflit actif; crise humanitaire; gouvernement divisé; destruction d'infrastructures; instabilité monétaire; insécurité alimentaire.",
        key_regulations="Limited regulatory framework due to conflict; Central Bank regulations; International humanitarian procurement rules (UN, ICRC).",
        major_trading_partners=["China", "UAE", "Saudi Arabia", "India", "Turkey", "Oman"],
        free_trade_zones=["Aden Free Zone (limited operations)"],
        market_summary_en="Yemen's economy has been devastated by civil conflict since 2014. When peace is achieved, reconstruction needs estimated at $20B+ will create significant opportunities.",
        market_summary_ar="دمّر النزاع المسلح اقتصاد اليمن منذ 2014. عند تحقيق السلام، ستخلق احتياجات الإعمار المقدرة بأكثر من 20 مليار دولار فرصاً كبيرة.",
        market_summary_fr="L'économie yéménite a été dévastée par le conflit civil depuis 2014. La paix créera des besoins de reconstruction estimés à plus de 20 milliards de dollars.",
    )


def _mauritania() -> dict:
    return _build_record(
        country_code="MR",
        year=2024,
        gdp_usd=10.4,
        gdp_growth_pct=4.8,
        inflation_pct=5.0,
        population=4.9,
        unemployment_pct=10.5,
        fdi_inflow_usd=0.9,
        construction_output_usd=0.8,
        ease_of_business_rank=152,
        top_sectors=["mining", "agriculture", "oil_gas", "construction", "water"],
        currency_code="MRU",
        currency_name="Mauritanian Ouguiya",
        exchange_rate_usd=39.7,
        construction_spend_usd=1.5,
        business_environment="Mauritania is one of the newest hydrocarbon producers in West Africa, with the GTA (Greater Tortue Ahmeyim) LNG project expected to transform the economy. The country has significant iron ore reserves (SNIM) and rich fishing waters. Infrastructure is underdeveloped, presenting opportunities in construction, energy, and water management.",
        opportunities_en="GTA LNG project (BP/Kosmos); iron ore expansion (SNIM); Band d'Arguin fishing zone; renewable energy; infrastructure development; mining (gold, copper); Nouakchott port expansion.",
        opportunities_ar="مشروع الغاز المسال GTA؛ توسعة خام الحديد؛ الطاقة المتجددة؛ تطوير البنية التحتية؛ التعدين؛ توسعة ميناء نواكشوط.",
        opportunities_fr="Projet GNL GTA (BP/Kosmos); expansion du minerai de fer (SNIM); zone de pêche du Banc d'Arguin; énergie renouvelable; développement des infrastructures; mines (or, cuivre).",
        challenges_en="Limited infrastructure; small market size; harsh climate; limited skilled workforce; bureaucratic processes; French language requirement; underdeveloped banking system.",
        challenges_ar="محدودية البنية التحتية؛ صغر حجم السوق؛ المناخ القاسي؛ محدودية القوى العاملة الماهرة؛ العمليات البيروقراطية.",
        challenges_fr="Infrastructure limitée; petit marché; climat difficile; main-d'œuvre qualifiée limitée; processus bureaucratiques; système bancaire sous-développé.",
        key_regulations="Public Procurement Code; Mining Code (2012); Hydrocarbons Code; Investment Code; Central Bank regulations; SNIM procurement framework.",
        major_trading_partners=["China", "EU (Spain, France)", "Japan", "India", "UAE", "USA"],
        free_trade_zones=["Nouadhibou Free Zone"],
        market_summary_en="Mauritania's $10B economy is on the cusp of transformation with the GTA LNG project. Iron ore mining and fishing remain key sectors. Infrastructure development needs are significant.",
        market_summary_ar="يقف اقتصاد موريتانيا البالغ 10 مليارات دولار على أعتاب تحول مع مشروع الغاز المسال GTA. يبقى التعدين والصيد قطاعين رئيسيين.",
        market_summary_fr="L'économie mauritanienne de 10 milliards de dollars est en passe de se transformer avec le projet GNL GTA. L'exploitation minière du fer et la pêche restent des secteurs clés.",
    )


def scrape() -> list[dict]:
    """Generate curated market intelligence seed data for 18 MENA countries.

    Returns:
        list[dict]: Market data records for each country.
    """
    logger.info("Generating curated market seed data for 18 MENA countries...")

    records = [
        _saudi_arabia(),
        _uae(),
        _qatar(),
        _kuwait(),
        _bahrain(),
        _oman(),
        _egypt(),
        _morocco(),
        _jordan(),
        _tunisia(),
        _algeria(),
        _libya(),
        _iraq(),
        _lebanon(),
        _palestine(),
        _sudan(),
        _yemen(),
        _mauritania(),
    ]

    logger.info(f"Generated {len(records)} market seed records")
    return records


if __name__ == "__main__":
    data = scrape()
    save_market_data(data, "market_seed")
    print(f"\nSaved {len(data)} market seed records")
    print("=" * 80)
    print(f"{'Country':<22} | {'GDP ($B)':>10} | {'Growth':>7} | {'Pop (M)':>8} | {'Constr ($B)':>12} | {'FDI ($B)':>9}")
    print("-" * 80)
    for rec in data:
        print(
            f"{rec['country']:<22} | "
            f"${rec.get('gdp_usd', 0):>8.1f}B | "
            f"{rec.get('gdp_growth_pct', 0):>6.1f}% | "
            f"{rec.get('population', 0):>7.1f}M | "
            f"${rec.get('construction_spend_usd', 0):>10.1f}B | "
            f"${rec.get('fdi_inflow_usd', 0):>7.1f}B"
        )
    print("=" * 80)
    total_gdp = sum(r.get("gdp_usd", 0) or 0 for r in data)
    total_pop = sum(r.get("population", 0) or 0 for r in data)
    total_constr = sum(r.get("construction_spend_usd", 0) or 0 for r in data)
    print(f"{'TOTAL':<22} | ${total_gdp:>8.1f}B |         | {total_pop:>7.1f}M | ${total_constr:>10.1f}B |")
