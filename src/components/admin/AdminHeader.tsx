import { useLocation, Link } from "react-router-dom";
import { Search, Command } from "lucide-react";
import { useAuth } from "../../lib/auth-context";
import { useLang, localizedPath } from "../../lib/use-lang";

interface AdminHeaderProps {
  onCommandPalette: () => void;
}

const breadcrumbLabels: Record<string, string> = {
  admin: "Dashboard",
  scrapers: "Scrapers",
  users: "Users",
  data: "Data Explorer",
  subscriptions: "Subscriptions",
  credits: "Credits",
  content: "Content",
  logs: "System Logs",
  settings: "Settings",
};

export default function AdminHeader({ onCommandPalette }: AdminHeaderProps) {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const lang = useLang();

  // Build breadcrumbs from path
  const segments = pathname.replace(`/${lang}/`, "").split("/").filter(Boolean);
  const crumbs = segments.map((seg, i) => ({
    label: breadcrumbLabels[seg] || seg,
    path: localizedPath(lang, "/" + segments.slice(0, i + 1).join("/")),
    isLast: i === segments.length - 1,
  }));

  const email = user?.email || "";
  const initial = email.charAt(0).toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-dark-border bg-[#06060a]/80 backdrop-blur-sm px-6">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1.5 text-sm">
        {crumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-slate-700">/</span>}
            {crumb.isLast ? (
              <span className="font-medium text-white">{crumb.label}</span>
            ) : (
              <Link to={crumb.path} className="text-slate-500 hover:text-slate-300">
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Cmd+K button */}
        <button
          onClick={onCommandPalette}
          className="flex items-center gap-2 rounded-lg border border-dark-border bg-dark-card px-3 py-1.5 text-sm text-slate-500 hover:border-primary/30 hover:text-slate-300"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search...</span>
          <kbd className="hidden items-center gap-0.5 rounded border border-dark-border px-1 py-0.5 text-[10px] sm:flex">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>

        {/* Avatar */}
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary-light">
          {initial}
        </div>
      </div>
    </header>
  );
}
