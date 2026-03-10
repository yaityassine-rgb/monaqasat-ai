import { useParams, useLocation, Navigate, Outlet } from "react-router-dom";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export const SUPPORTED_LANGS = ["en", "ar", "fr"] as const;
export type Lang = (typeof SUPPORTED_LANGS)[number];

export const SITE_URL = "https://monaqasat.ai";

/** Returns /:lang prefix from URL params, falling back to "en" */
export function useLang(): Lang {
  const { lang } = useParams<{ lang: string }>();
  if (lang && SUPPORTED_LANGS.includes(lang as Lang)) return lang as Lang;
  return "en";
}

/** Prepends current lang prefix to a path: useLocalizedPath("/about") => "/en/about" */
export function useLocalizedPath(path: string): string {
  const lang = useLang();
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `/${lang}${clean}`;
}

/** Builds a localized path without hooks (for constants / static contexts) */
export function localizedPath(lang: Lang, path: string): string {
  const clean = path === "/" ? "" : path.startsWith("/") ? path : `/${path}`;
  return `/${lang}${clean}`;
}

/** Builds the full canonical URL for a given lang + path */
export function canonicalUrl(lang: Lang, path: string): string {
  const clean = path === "/" ? "" : path.startsWith("/") ? path : `/${path}`;
  return `${SITE_URL}/${lang}${clean}`;
}

/**
 * Layout component that reads :lang param, validates it,
 * syncs i18n language, and sets document dir/lang.
 */
export function LanguageLayout() {
  const { lang } = useParams<{ lang: string }>();
  const { i18n } = useTranslation();
  const location = useLocation();

  const isValid = lang && SUPPORTED_LANGS.includes(lang as Lang);

  useEffect(() => {
    if (isValid && i18n.language !== lang) {
      i18n.changeLanguage(lang);
    }
  }, [lang, isValid, i18n]);

  if (!isValid) {
    // Redirect invalid lang prefixes to /en + same path
    const rest = location.pathname.replace(/^\/[^/]*/, "");
    return <Navigate to={`/en${rest}`} replace />;
  }

  return <Outlet />;
}

/**
 * Component for the root "/" path — redirects to /{detectedLang}/
 */
export function RootRedirect() {
  const { i18n } = useTranslation();
  const detected = SUPPORTED_LANGS.includes(i18n.language as Lang)
    ? (i18n.language as Lang)
    : "en";
  return <Navigate to={`/${detected}`} replace />;
}
