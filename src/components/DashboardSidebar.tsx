import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard, Bookmark, BarChart3, CreditCard,
  Bell, FileText, FolderOpen, Users, Globe, Handshake,
  ShieldCheck, Briefcase, User,
  PanelLeftClose, PanelLeftOpen, ChevronRight, LogOut, Shield,
} from "lucide-react";
import { useAuth } from "../lib/auth-context";
import { useAdmin } from "../lib/use-admin";
import { useLang, localizedPath } from "../lib/use-lang";

interface NavItem {
  key: string;
  labelKey: string;
  icon: typeof LayoutDashboard;
  path: string;
}

interface NavSection {
  labelKey: string;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    labelKey: "sidebar.main",
    items: [
      { key: "dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard, path: "/dashboard" },
      { key: "saved", labelKey: "sidebar.saved", icon: Bookmark, path: "/dashboard/saved" },
      { key: "analytics", labelKey: "sidebar.analytics", icon: BarChart3, path: "/dashboard/analytics" },
    ],
  },
  {
    labelKey: "sidebar.workspace",
    items: [
      { key: "proposals", labelKey: "auth.proposals", icon: FileText, path: "/dashboard/proposals" },
      { key: "documents", labelKey: "auth.documents", icon: FolderOpen, path: "/dashboard/documents" },
      { key: "alerts", labelKey: "auth.alerts", icon: Bell, path: "/dashboard/alerts" },
      { key: "team", labelKey: "auth.team", icon: Users, path: "/dashboard/team" },
    ],
  },
  {
    labelKey: "sidebar.opportunities",
    items: [
      { key: "grants", labelKey: "auth.grants", icon: Globe, path: "/dashboard/grants" },
      { key: "ppp", labelKey: "auth.ppp", icon: Handshake, path: "/dashboard/ppp" },
      { key: "partners", labelKey: "auth.partners", icon: Users, path: "/dashboard/partners" },
      { key: "prequalification", labelKey: "auth.preQual", icon: ShieldCheck, path: "/dashboard/prequalification" },
      { key: "consulting", labelKey: "auth.consulting", icon: Briefcase, path: "/dashboard/consulting" },
    ],
  },
  {
    labelKey: "sidebar.account",
    items: [
      { key: "profile", labelKey: "auth.profile", icon: User, path: "/dashboard/profile" },
      { key: "subscription", labelKey: "auth.subscription", icon: CreditCard, path: "/dashboard/subscription" },
    ],
  },
];

interface DashboardSidebarProps {
  mobile?: boolean;
  onClose?: () => void;
}

export default function DashboardSidebar({ mobile, onClose }: DashboardSidebarProps = {}) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { signOut } = useAuth();
  const { isAdmin } = useAdmin();
  const lang = useLang();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("dashboard_sidebar") === "collapsed"
  );
  const isCollapsed = mobile ? false : collapsed;

  useEffect(() => {
    localStorage.setItem("dashboard_sidebar", collapsed ? "collapsed" : "expanded");
  }, [collapsed]);

  function isActive(path: string) {
    const full = localizedPath(lang, path);
    if (path === "/dashboard") return pathname === full;
    return pathname.startsWith(full);
  }

  const handleClick = mobile ? onClose : undefined;

  return (
    <aside
      data-sidebar={isCollapsed ? "collapsed" : "expanded"}
      data-sidebar-type="dashboard"
      className={`flex flex-col border-e border-dark-border bg-[#06060a] transition-all duration-200 ${
        mobile ? "w-60 h-full" : `fixed inset-y-0 start-0 z-40 h-screen max-md:hidden ${isCollapsed ? "w-16" : "w-60"}`
      }`}
    >
      {/* Logo */}
      <div className={`flex h-14 items-center border-b border-dark-border ${isCollapsed ? "justify-center px-2" : "px-4"}`}>
        <Link to={localizedPath(lang, "/")} className="flex items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary font-bold text-white text-sm">
            M
          </div>
          {!isCollapsed && (
            <span className="text-sm font-bold text-white">
              Monaqasat <span className="text-primary-light">AI</span>
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3">
        {isAdmin && (
          <div className="mb-3">
            {!isCollapsed && (
              <p className="mb-1 px-4 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                Admin
              </p>
            )}
            <Link
              to={localizedPath(lang, "/admin")}
              onClick={handleClick}
              title={isCollapsed ? t("nav.adminPanel", "Admin Panel") : undefined}
              className={`mx-2 mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-accent transition-colors hover:bg-accent/5 ${
                isCollapsed ? "justify-center" : ""
              }`}
            >
              <Shield className="h-4 w-4 shrink-0" />
              {!isCollapsed && <span className="font-medium">{t("nav.adminPanel", "Admin Panel")}</span>}
            </Link>
          </div>
        )}

        {sections.map((section) => (
          <div key={section.labelKey} className="mb-3">
            {!isCollapsed && (
              <p className="mb-1 px-4 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                {t(section.labelKey, section.labelKey.split(".").pop() ?? section.labelKey)}
              </p>
            )}
            {section.items.map((item) => {
              const active = isActive(item.path);
              return (
                <Link
                  key={item.key}
                  to={localizedPath(lang, item.path)}
                  onClick={handleClick}
                  title={isCollapsed ? t(item.labelKey, item.key) : undefined}
                  className={`mx-2 mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-primary/10 text-primary-light font-medium"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  } ${isCollapsed ? "justify-center" : ""}`}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!isCollapsed && <span>{t(item.labelKey, item.key)}</span>}
                  {!isCollapsed && active && <ChevronRight className="ms-auto h-3 w-3 text-primary/50" />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom actions */}
      <div className="border-t border-dark-border p-2 space-y-0.5">
        {!mobile && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-white ${
              isCollapsed ? "justify-center" : ""
            }`}
          >
            {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            {!isCollapsed && t("sidebar.collapse", "Collapse")}
          </button>
        )}
        <button
          onClick={() => signOut()}
          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-red-400 hover:bg-red-400/5 ${
            isCollapsed ? "justify-center" : ""
          }`}
        >
          <LogOut className="h-4 w-4" />
          {!isCollapsed && t("auth.signOut")}
        </button>
      </div>
    </aside>
  );
}
