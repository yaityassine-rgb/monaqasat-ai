import type { Lang } from "./use-lang";
import { SITE_URL, canonicalUrl } from "./use-lang";

const ORG_NAME: Record<Lang, string> = {
  en: "Monaqasat AI",
  ar: "مناقصات AI",
  fr: "Monaqasat AI",
};

const ORG_DESC: Record<Lang, string> = {
  en: "AI-powered government tender intelligence for the MENA region",
  ar: "ذكاء اصطناعي لمناقصات الحكومة في منطقة الشرق الأوسط وشمال أفريقيا",
  fr: "Intelligence artificielle pour les appels d'offres gouvernementaux dans la région MENA",
};

export function buildOrganizationJsonLd(lang: Lang) {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: ORG_NAME[lang],
    url: SITE_URL,
    logo: `${SITE_URL}/favicon.svg`,
    description: ORG_DESC[lang],
    email: "contact@monaqasat.ai",
    address: {
      "@type": "PostalAddress",
      addressLocality: "Casablanca",
      addressCountry: "MA",
    },
    parentOrganization: {
      "@type": "Organization",
      name: "Holoul AI SARL",
    },
    inLanguage: [
      { "@type": "Language", name: "English", alternateName: "en" },
      { "@type": "Language", name: "Arabic", alternateName: "ar" },
      { "@type": "Language", name: "French", alternateName: "fr" },
    ],
  };
}

export function buildWebApplicationJsonLd(lang: Lang) {
  return {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    name: ORG_NAME[lang],
    url: canonicalUrl(lang, ""),
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description: ORG_DESC[lang],
    offers: {
      "@type": "AggregateOffer",
      lowPrice: "0",
      highPrice: "499",
      priceCurrency: "USD",
      offerCount: "4",
    },
    creator: {
      "@type": "Organization",
      name: "Holoul AI SARL",
    },
  };
}

export function buildBreadcrumbJsonLd(
  lang: Lang,
  items: { name: string; path: string }[]
) {
  const homeLabel = lang === "ar" ? "الرئيسية" : lang === "fr" ? "Accueil" : "Home";

  const listItems = [
    {
      "@type": "ListItem",
      position: 1,
      name: homeLabel,
      item: canonicalUrl(lang, ""),
    },
    ...items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 2,
      name: item.name,
      item: canonicalUrl(lang, item.path),
    })),
  ];

  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: listItems,
  };
}

export function buildFaqJsonLd(
  faqs: { question: string; answer: string }[]
) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };
}
