import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useLocation } from "react-router-dom";
import { Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useLang, SUPPORTED_LANGS } from "../lib/use-lang";

const LANGUAGES = [
  { code: "en", label: "English", short: "EN" },
  { code: "ar", label: "العربية", short: "AR" },
  { code: "fr", label: "Français", short: "FR" },
] as const;

export default function LanguageSwitcher() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const currentLang = useLang();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = LANGUAGES.find((l) => l.code === currentLang) ?? LANGUAGES[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function switchLanguage(code: string) {
    if (!SUPPORTED_LANGS.includes(code as typeof SUPPORTED_LANGS[number])) return;
    // Replace current lang prefix in the URL path
    const rest = location.pathname.replace(/^\/[a-z]{2}/, "");
    navigate(`/${code}${rest || "/"}`);
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
        aria-label={t("common.changeLanguage")}
      >
        <Globe className="h-4 w-4" />
        <span className="font-medium">{current.short}</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="glass absolute end-0 top-full z-50 mt-2 min-w-[140px] overflow-hidden rounded-xl p-1"
          >
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => switchLanguage(lang.code)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  lang.code === currentLang
                    ? "bg-primary/20 text-primary-light"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <span className="font-medium">{lang.short}</span>
                <span className="text-slate-400">{lang.label}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
