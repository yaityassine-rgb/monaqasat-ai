import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Database, FileText, Users, CreditCard, Coins,
  BarChart3, ScrollText, PanelLeftClose, PanelLeftOpen,
  ArrowLeft, LogOut, ChevronRight,
} from "lucide-react";
import { useLang, localizedPath } from "../../lib/use-lang";
import { useAuth } from "../../lib/auth-context";

interface NavItem {
  key: string;
  label: string;
  icon: typeof LayoutDashboard;
  path: string;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    label: "Overview",
    items: [
      { key: "overview", label: "Dashboard", icon: LayoutDashboard, path: "/admin" },
    ],
  },
  {
    label: "Operations",
    items: [
      { key: "scrapers", label: "Scrapers", icon: Database, path: "/admin/scrapers" },
      { key: "content", label: "Content", icon: FileText, path: "/admin/content" },
    ],
  },
  {
    label: "Users",
    items: [
      { key: "users", label: "User Management", icon: Users, path: "/admin/users" },
      { key: "subscriptions", label: "Subscriptions", icon: CreditCard, path: "/admin/subscriptions" },
      { key: "credits", label: "Credits", icon: Coins, path: "/admin/credits" },
    ],
  },
  {
    label: "Data",
    items: [
      { key: "data", label: "Data Explorer", icon: BarChart3, path: "/admin/data" },
      { key: "logs", label: "System Logs", icon: ScrollText, path: "/admin/logs" },
    ],
  },
];

export default function AdminSidebar() {
  const { pathname } = useLocation();
  const lang = useLang();
  const { signOut } = useAuth();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("admin_sidebar") === "collapsed");

  useEffect(() => {
    localStorage.setItem("admin_sidebar", collapsed ? "collapsed" : "expanded");
  }, [collapsed]);

  function isActive(path: string) {
    const full = localizedPath(lang, path);
    if (path === "/admin") return pathname === full;
    return pathname.startsWith(full);
  }

  return (
    <aside className={`fixed inset-y-0 start-0 z-40 flex flex-col border-e border-dark-border bg-[#06060a] transition-all duration-200 ${collapsed ? "w-16" : "w-60"}`}>
      {/* Logo */}
      <div className={`flex h-14 items-center border-b border-dark-border ${collapsed ? "justify-center px-2" : "px-4"}`}>
        <Link to={localizedPath(lang, "/admin")} className="flex items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary font-bold text-white text-sm">
            M
          </div>
          {!collapsed && (
            <span className="text-sm font-bold text-white">
              Admin <span className="text-primary-light">Panel</span>
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3">
        {sections.map((section) => (
          <div key={section.label} className="mb-3">
            {!collapsed && (
              <p className="mb-1 px-4 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                {section.label}
              </p>
            )}
            {section.items.map((item) => {
              const active = isActive(item.path);
              return (
                <Link
                  key={item.key}
                  to={localizedPath(lang, item.path)}
                  title={collapsed ? item.label : undefined}
                  className={`mx-2 mb-0.5 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-primary/10 text-primary-light font-medium"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  } ${collapsed ? "justify-center" : ""}`}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                  {!collapsed && active && <ChevronRight className="ms-auto h-3 w-3 text-primary/50" />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom actions */}
      <div className="border-t border-dark-border p-2 space-y-0.5">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-white ${collapsed ? "justify-center" : ""}`}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          {!collapsed && "Collapse"}
        </button>
        <Link
          to={localizedPath(lang, "/dashboard")}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-white ${collapsed ? "justify-center" : ""}`}
        >
          <ArrowLeft className="h-4 w-4" />
          {!collapsed && "Back to App"}
        </Link>
        <button
          onClick={() => signOut()}
          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-red-400 hover:bg-red-400/5 ${collapsed ? "justify-center" : ""}`}
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && "Sign Out"}
        </button>
      </div>
    </aside>
  );
}

export function useSidebarWidth() {
  const [collapsed] = useState(() => localStorage.getItem("admin_sidebar") === "collapsed");
  return collapsed ? "4rem" : "15rem";
}
