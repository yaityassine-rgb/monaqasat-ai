import { Outlet, Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu, X } from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "../lib/auth-context";
import { useLang, localizedPath } from "../lib/use-lang";
import DashboardSidebar from "./DashboardSidebar";
import LanguageSwitcher from "./LanguageSwitcher";
import ScrollToTop from "./ScrollToTop";

export default function DashboardLayout() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const lang = useLang();
  const [mobileOpen, setMobileOpen] = useState(false);

  const { pathname } = useLocation();

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const email = user?.email || "";
  const initial = email.charAt(0).toUpperCase();

  return (
    <div className="flex min-h-screen bg-dark">
      <ScrollToTop />

      {/* Desktop sidebar */}
      <DashboardSidebar />

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-50 bg-black/60 md:hidden" onClick={() => setMobileOpen(false)} />
          <div className="fixed inset-y-0 start-0 z-50 w-60 md:hidden">
            <DashboardSidebar mobile onClose={() => setMobileOpen(false)} />
          </div>
        </>
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col dashboard-main">
        {/* Header */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-dark-border bg-[#06060a]/80 backdrop-blur-sm px-4 sm:px-6">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="rounded-lg p-2 text-slate-300 hover:bg-white/5 hover:text-white md:hidden"
              aria-label={t("common.toggleMenu")}
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            {/* Mobile logo */}
            <Link to={localizedPath(lang, "/")} className="flex items-center gap-2 md:hidden">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary font-bold text-white text-xs">
                M
              </div>
              <span className="text-sm font-bold text-white">
                Monaqasat <span className="text-primary-light">AI</span>
              </span>
            </Link>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <Link
              to={localizedPath(lang, "/dashboard/profile")}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary-light"
              title={email}
            >
              {initial}
            </Link>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
