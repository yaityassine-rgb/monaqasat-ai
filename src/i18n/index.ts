import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./en.json";
import ar from "./ar.json";
import fr from "./fr.json";

const SUPPORTED = ["en", "ar", "fr"];

/** Custom detector: reads language from URL path prefix first */
const pathDetector = {
  name: "path",
  lookup() {
    const match = window.location.pathname.match(/^\/([a-z]{2})(\/|$)/);
    if (match && SUPPORTED.includes(match[1])) return match[1];
    return undefined;
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ar: { translation: ar },
      fr: { translation: fr },
    },
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    detection: {
      order: ["path", "localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

// Register custom path detector
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(i18n.services.languageDetector as any).addDetector(pathDetector);

// Re-detect now that path detector is registered
const pathLang = pathDetector.lookup();
if (pathLang && i18n.language !== pathLang) {
  i18n.changeLanguage(pathLang);
}

i18n.on("languageChanged", (lng) => {
  const dir = lng === "ar" ? "rtl" : "ltr";
  document.documentElement.dir = dir;
  document.documentElement.lang = lng;
});

const dir = i18n.language === "ar" ? "rtl" : "ltr";
document.documentElement.dir = dir;
document.documentElement.lang = i18n.language;

export default i18n;
