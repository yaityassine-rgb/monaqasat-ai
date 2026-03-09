import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Mail, MapPin, Heart } from "lucide-react";
import { COMPANY, NAV_LINKS, LEGAL_LINKS } from "../lib/constants";

export default function Footer() {
  const { t } = useTranslation();
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-dark-border bg-dark">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {/* Company column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white">
              {t("footer.company")}
            </h3>
            <ul className="space-y-3">
              {NAV_LINKS.map((link) => (
                <li key={link.key}>
                  <Link
                    to={link.path}
                    className="text-sm text-slate-400 transition-colors hover:text-primary-light"
                  >
                    {t(`nav.${link.key}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Product column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white">
              {t("footer.product")}
            </h3>
            <ul className="space-y-3">
              <li>
                <Link
                  to="/dashboard"
                  className="text-sm text-slate-400 transition-colors hover:text-primary-light"
                >
                  {t("nav.dashboard")}
                </Link>
              </li>
              <li>
                <Link
                  to="/pricing"
                  className="text-sm text-slate-400 transition-colors hover:text-primary-light"
                >
                  {t("nav.pricing")}
                </Link>
              </li>
              <li>
                <Link
                  to="/dashboard/analytics"
                  className="text-sm text-slate-400 transition-colors hover:text-primary-light"
                >
                  {t("analytics.title")}
                </Link>
              </li>
              <li>
                <Link
                  to="/dashboard/profile"
                  className="text-sm text-slate-400 transition-colors hover:text-primary-light"
                >
                  {t("profile.title")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white">
              {t("footer.legal")}
            </h3>
            <ul className="space-y-3">
              {LEGAL_LINKS.map((link) => (
                <li key={link.key}>
                  <Link
                    to={link.path}
                    className="text-sm text-slate-400 transition-colors hover:text-primary-light"
                  >
                    {t(`footer.${link.key}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Connect column */}
          <div>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white">
              {t("footer.connect")}
            </h3>
            <ul className="space-y-3">
              <li className="flex items-center gap-2 text-sm text-slate-400">
                <Mail className="h-4 w-4 shrink-0 text-primary" />
                <a
                  href={`mailto:${COMPANY.email}`}
                  className="transition-colors hover:text-primary-light"
                >
                  {COMPANY.email}
                </a>
              </li>
              <li className="flex items-center gap-2 text-sm text-slate-400">
                <MapPin className="h-4 w-4 shrink-0 text-primary" />
                <span>{COMPANY.address}</span>
              </li>
              <li className="mt-4 text-sm text-slate-500">
                {COMPANY.parent}
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 flex flex-col items-center gap-4 border-t border-dark-border pt-8 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
              M
            </div>
            <span className="text-sm font-semibold text-white">
              Monaqasat <span className="text-primary-light">AI</span>
            </span>
          </div>

          <p className="text-center text-sm text-slate-500">
            &copy; {year} {COMPANY.parent}. {t("footer.rights")}
          </p>

          <p className="flex items-center gap-1 text-xs text-slate-600">
            {t("footer.builtIn")} <Heart className="h-3 w-3 text-danger" />
          </p>
        </div>
      </div>
    </footer>
  );
}
