import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useNavigate } from "react-router-dom";
import { useLang, localizedPath } from "../../lib/use-lang";
import {
  LayoutDashboard, Database, Users, BarChart3, CreditCard, Coins,
  FileText, ScrollText, Settings, Search, Play, Upload, Download,
} from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const lang = useLang();
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  function go(path: string) {
    navigate(localizedPath(lang, path));
    onOpenChange(false);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[20vh] bg-black/60 backdrop-blur-sm" onClick={() => onOpenChange(false)}>
      <div className="w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <Command className="glass-card overflow-hidden rounded-xl border border-dark-border shadow-2xl" shouldFilter={true}>
          <div className="flex items-center gap-2 border-b border-dark-border px-4">
            <Search className="h-4 w-4 text-slate-500" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent py-3.5 text-sm text-white placeholder:text-slate-600 focus:outline-none"
            />
            <kbd className="rounded border border-dark-border px-1.5 py-0.5 text-[10px] text-slate-600">ESC</kbd>
          </div>
          <Command.List className="max-h-72 overflow-y-auto p-2">
            <Command.Empty className="px-4 py-8 text-center text-sm text-slate-600">No results found</Command.Empty>

            <Command.Group heading="Navigate" className="text-xs font-medium uppercase text-slate-600 px-2 py-1.5">
              <Item icon={LayoutDashboard} label="Overview" onSelect={() => go("/admin")} />
              <Item icon={Database} label="Scrapers" onSelect={() => go("/admin/scrapers")} />
              <Item icon={Users} label="Users" onSelect={() => go("/admin/users")} />
              <Item icon={BarChart3} label="Data Explorer" onSelect={() => go("/admin/data")} />
              <Item icon={CreditCard} label="Subscriptions" onSelect={() => go("/admin/subscriptions")} />
              <Item icon={Coins} label="Credits" onSelect={() => go("/admin/credits")} />
              <Item icon={FileText} label="Content" onSelect={() => go("/admin/content")} />
              <Item icon={ScrollText} label="System Logs" onSelect={() => go("/admin/logs")} />
              <Item icon={Settings} label="Settings" onSelect={() => go("/admin/settings")} />
            </Command.Group>

            <Command.Separator className="my-1 h-px bg-dark-border" />

            <Command.Group heading="Quick Actions" className="text-xs font-medium uppercase text-slate-600 px-2 py-1.5">
              <Item icon={Play} label="Run All Scrapers" onSelect={() => go("/admin/scrapers")} />
              <Item icon={Upload} label="Upload Data" onSelect={() => go("/admin/scrapers")} />
              <Item icon={Download} label="Export Users" onSelect={() => go("/admin/users")} />
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}

function Item({ icon: Icon, label, onSelect }: { icon: typeof Search; label: string; onSelect: () => void }) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-300 transition-colors data-[selected=true]:bg-primary/10 data-[selected=true]:text-white"
    >
      <Icon className="h-4 w-4 text-slate-500" />
      {label}
    </Command.Item>
  );
}
