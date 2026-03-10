import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Coins, Zap } from "lucide-react";
import { getCreditBalance, type CreditBalance as CreditBalanceType } from "../lib/credits";
import { useLang, localizedPath } from "../lib/use-lang";

export default function CreditBalance() {
  const { t } = useTranslation();
  const lang = useLang();
  const [balance, setBalance] = useState<CreditBalanceType>(getCreditBalance);

  useEffect(() => {
    // Re-check on focus (user may have used credits in another tab)
    const refresh = () => setBalance(getCreditBalance());
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, []);

  const pct = balance.total > 0 ? Math.round((balance.remaining / balance.total) * 100) : 0;
  const barColor = pct > 50 ? "bg-emerald-400" : pct > 20 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Coins className="w-4 h-4 text-accent" />
          <span className="text-xs font-semibold text-slate-200">{t("credits.title")}</span>
        </div>
        <Link
          to={localizedPath(lang, "/pricing")}
          className="flex items-center gap-1 text-[10px] text-accent hover:text-accent/80 transition-colors"
        >
          <Zap className="w-3 h-3" />
          {t("credits.buyMore")}
        </Link>
      </div>

      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-2xl font-bold text-white">{balance.remaining}</span>
        <span className="text-xs text-slate-500">/ {balance.total}</span>
      </div>

      <div className="w-full h-1.5 rounded-full bg-dark-border overflow-hidden mb-2">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <p className="text-[10px] text-slate-500">
        {t("credits.resets")} {balance.resetDate}
      </p>
    </div>
  );
}
