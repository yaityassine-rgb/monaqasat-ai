export const COMPANY = {
  name: "Monaqasat AI",
  nameAr: "مناقصات AI",
  parent: "Holoul AI SARL",
  address: "Casablanca, Morocco",
  email: "contact@monaqasat.ai",
  website: "https://monaqasat.ai",
};

export const NAV_LINKS = [
  { key: "home", path: "/" },
  { key: "about", path: "/about" },
  { key: "pricing", path: "/pricing" },
  { key: "contact", path: "/contact" },
] as const;

export const LEGAL_LINKS = [
  { key: "terms", path: "/terms" },
  { key: "privacy", path: "/privacy" },
  { key: "refund", path: "/refund" },
] as const;

export const COUNTRIES = [
  { code: "MA", name: { en: "Morocco", ar: "المغرب", fr: "Maroc" }, flag: "🇲🇦" },
  { code: "SA", name: { en: "Saudi Arabia", ar: "السعودية", fr: "Arabie saoudite" }, flag: "🇸🇦" },
  { code: "AE", name: { en: "UAE", ar: "الإمارات", fr: "EAU" }, flag: "🇦🇪" },
  { code: "EG", name: { en: "Egypt", ar: "مصر", fr: "Égypte" }, flag: "🇪🇬" },
  { code: "KW", name: { en: "Kuwait", ar: "الكويت", fr: "Koweït" }, flag: "🇰🇼" },
  { code: "QA", name: { en: "Qatar", ar: "قطر", fr: "Qatar" }, flag: "🇶🇦" },
  { code: "BH", name: { en: "Bahrain", ar: "البحرين", fr: "Bahreïn" }, flag: "🇧🇭" },
  { code: "OM", name: { en: "Oman", ar: "عمان", fr: "Oman" }, flag: "🇴🇲" },
  { code: "JO", name: { en: "Jordan", ar: "الأردن", fr: "Jordanie" }, flag: "🇯🇴" },
  { code: "TN", name: { en: "Tunisia", ar: "تونس", fr: "Tunisie" }, flag: "🇹🇳" },
  { code: "DZ", name: { en: "Algeria", ar: "الجزائر", fr: "Algérie" }, flag: "🇩🇿" },
  { code: "LY", name: { en: "Libya", ar: "ليبيا", fr: "Libye" }, flag: "🇱🇾" },
  { code: "IQ", name: { en: "Iraq", ar: "العراق", fr: "Irak" }, flag: "🇮🇶" },
  { code: "LB", name: { en: "Lebanon", ar: "لبنان", fr: "Liban" }, flag: "🇱🇧" },
  { code: "PS", name: { en: "Palestine", ar: "فلسطين", fr: "Palestine" }, flag: "🇵🇸" },
  { code: "SD", name: { en: "Sudan", ar: "السودان", fr: "Soudan" }, flag: "🇸🇩" },
  { code: "YE", name: { en: "Yemen", ar: "اليمن", fr: "Yémen" }, flag: "🇾🇪" },
  { code: "MR", name: { en: "Mauritania", ar: "موريتانيا", fr: "Mauritanie" }, flag: "🇲🇷" },
] as const;

export const SECTORS: { key: string; icon: string }[] = [
  { key: "construction", icon: "HardHat" },
  { key: "it", icon: "Monitor" },
  { key: "healthcare", icon: "Heart" },
  { key: "energy", icon: "Zap" },
  { key: "education", icon: "GraduationCap" },
  { key: "transport", icon: "Truck" },
  { key: "defense", icon: "Shield" },
  { key: "water", icon: "Droplets" },
  { key: "telecom", icon: "Radio" },
  { key: "agriculture", icon: "Wheat" },
];
