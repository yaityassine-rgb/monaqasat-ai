import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, LayoutDashboard, Shield } from "lucide-react";
import { NAV_LINKS } from "../lib/constants";
import { useAuth } from "../lib/auth-context";
import { useAdmin } from "../lib/use-admin";
import { useLang, localizedPath } from "../lib/use-lang";
import LanguageSwitcher from "./LanguageSwitcher";
import UserMenu from "./UserMenu";

export default function Navbar() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { user, loading } = useAuth();
  const { isAdmin } = useAdmin();
  const lang = useLang();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 20);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? "glass shadow-lg shadow-black/20" : "bg-transparent"
      }`}
    >
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link to={localizedPath(lang, "/")} className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary font-bold text-white">
            M
          </div>
          <span className="text-lg font-bold text-white">
            Monaqasat <span className="text-primary-light">AI</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => {
            const to = localizedPath(lang, link.path);
            const isActive = pathname === to;
            return (
              <Link
                key={link.key}
                to={to}
                className={`relative rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "text-white"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-lg bg-white/10"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                  />
                )}
                <span className="relative">{t(`nav.${link.key}`)}</span>
              </Link>
            );
          })}

          <Link
            to={localizedPath(lang, "/dashboard")}
            className={`ms-2 flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              pathname.includes("/dashboard")
                ? "bg-primary/20 text-primary-light"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <LayoutDashboard className="h-4 w-4" />
            {t("nav.dashboard")}
          </Link>

          {isAdmin && (
            <Link
              to={localizedPath(lang, "/admin")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                pathname.includes("/admin")
                  ? "bg-accent/20 text-accent-light"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Shield className="h-4 w-4" />
              {t("nav.admin", "Admin")}
            </Link>
          )}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2">
          <LanguageSwitcher />

          {!loading && (
            user ? (
              <UserMenu />
            ) : (
              <Link
                to={localizedPath(lang, "/auth/login")}
                className="hidden rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-all hover:bg-primary-dark hover:shadow-lg hover:shadow-primary/25 md:block"
              >
                {t("nav.signIn")}
              </Link>
            )
          )}

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen((prev) => !prev)}
            className="rounded-lg p-2 text-slate-300 transition-colors hover:bg-white/5 hover:text-white md:hidden"
            aria-label={t("common.toggleMenu")}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="glass overflow-hidden border-t border-dark-border md:hidden"
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-4 sm:px-6">
              {NAV_LINKS.map((link) => {
                const to = localizedPath(lang, link.path);
                const isActive = pathname === to;
                return (
                  <Link
                    key={link.key}
                    to={to}
                    className={`rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary/10 text-primary-light"
                        : "text-slate-300 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    {t(`nav.${link.key}`)}
                  </Link>
                );
              })}

              <Link
                to={localizedPath(lang, "/dashboard")}
                className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                  pathname.includes("/dashboard")
                    ? "bg-primary/10 text-primary-light"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <LayoutDashboard className="h-4 w-4" />
                {t("nav.dashboard")}
              </Link>

              {user ? (
                <Link
                  to={localizedPath(lang, "/dashboard/profile")}
                  className="mt-2 rounded-lg bg-primary/20 px-4 py-3 text-center text-sm font-semibold text-primary-light transition-all hover:bg-primary/30"
                >
                  {t("auth.profile")}
                </Link>
              ) : (
                <Link
                  to={localizedPath(lang, "/auth/login")}
                  className="mt-2 rounded-lg bg-primary px-4 py-3 text-center text-sm font-semibold text-white transition-all hover:bg-primary-dark"
                >
                  {t("nav.signIn")}
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
