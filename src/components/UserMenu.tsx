import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { User, LogOut, Settings, CreditCard, ChevronDown } from "lucide-react";
import { useAuth } from "../lib/auth-context";

export default function UserMenu() {
  const { t } = useTranslation();
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!user) return null;

  const email = user.email || "";
  const initial = email.charAt(0).toUpperCase();

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-primary-light text-xs font-bold">
          {initial}
        </div>
        <span className="hidden sm:inline max-w-[120px] truncate">{email}</span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute end-0 top-full mt-2 w-56 rounded-xl glass-card border border-dark-border shadow-xl shadow-black/30 py-1 z-50">
          <div className="px-4 py-3 border-b border-dark-border">
            <p className="text-sm font-medium text-slate-200 truncate">{email}</p>
            <p className="text-xs text-slate-500 mt-0.5">{t("auth.freeAccount")}</p>
          </div>

          <Link
            to="/dashboard/profile"
            onClick={() => setOpen(false)}
            className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 transition-colors"
          >
            <User className="w-4 h-4" />
            {t("auth.profile")}
          </Link>

          <Link
            to="/dashboard/subscription"
            onClick={() => setOpen(false)}
            className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 transition-colors"
          >
            <CreditCard className="w-4 h-4" />
            {t("auth.subscription")}
          </Link>

          <Link
            to="/dashboard/profile"
            onClick={() => setOpen(false)}
            className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 transition-colors"
          >
            <Settings className="w-4 h-4" />
            {t("auth.settings")}
          </Link>

          <div className="border-t border-dark-border mt-1 pt-1">
            <button
              onClick={() => { signOut(); setOpen(false); }}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-400/5 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              {t("auth.signOut")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
