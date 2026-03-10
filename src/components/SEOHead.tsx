import { Helmet } from "react-helmet-async";
import { useLang, canonicalUrl, SUPPORTED_LANGS, SITE_URL } from "../lib/use-lang";

const OG_LOCALE: Record<string, string> = {
  en: "en_US",
  ar: "ar_SA",
  fr: "fr_FR",
};

interface SEOHeadProps {
  title: string;
  description?: string;
  /** Page path without lang prefix, e.g. "/about". Used for canonical + hreflang. */
  path?: string;
  noindex?: boolean;
  ogImage?: string;
  jsonLd?: object | object[];
}

export default function SEOHead({
  title,
  description,
  path,
  noindex,
  ogImage,
  jsonLd,
}: SEOHeadProps) {
  const lang = useLang();
  const siteName = "Monaqasat AI";
  const fullTitle = title === siteName ? title : `${title} | ${siteName}`;

  const canonical = path !== undefined ? canonicalUrl(lang, path) : undefined;
  const ogImg = ogImage ?? `${SITE_URL}/og/og-${lang}.svg`;

  const jsonLdArray = jsonLd
    ? Array.isArray(jsonLd)
      ? jsonLd
      : [jsonLd]
    : [];

  return (
    <Helmet>
      <title>{fullTitle}</title>

      {description && <meta name="description" content={description} />}

      {/* Canonical */}
      {canonical && <link rel="canonical" href={canonical} />}

      {/* Hreflang alternates */}
      {path !== undefined &&
        SUPPORTED_LANGS.map((l) => (
          <link
            key={l}
            rel="alternate"
            hrefLang={l}
            href={canonicalUrl(l, path)}
          />
        ))}
      {path !== undefined && (
        <link
          rel="alternate"
          hrefLang="x-default"
          href={canonicalUrl("en", path)}
        />
      )}

      {/* Robots */}
      {noindex && <meta name="robots" content="noindex,nofollow" />}

      {/* Open Graph */}
      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content={siteName} />
      <meta property="og:locale" content={OG_LOCALE[lang] ?? "en_US"} />
      {SUPPORTED_LANGS.filter((l) => l !== lang).map((l) => (
        <meta
          key={l}
          property="og:locale:alternate"
          content={OG_LOCALE[l]}
        />
      ))}
      {canonical && <meta property="og:url" content={canonical} />}
      <meta property="og:image" content={ogImg} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      {description && <meta name="twitter:description" content={description} />}
      <meta name="twitter:image" content={ogImg} />

      {/* Structured Data */}
      {jsonLdArray.map((data, i) => (
        <script key={i} type="application/ld+json">
          {JSON.stringify(data)}
        </script>
      ))}
    </Helmet>
  );
}
