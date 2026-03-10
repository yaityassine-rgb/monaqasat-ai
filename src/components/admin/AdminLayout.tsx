import { useState, useCallback } from "react";
import { Outlet } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import AdminSidebar from "./AdminSidebar";
import AdminHeader from "./AdminHeader";
import CommandPalette from "./CommandPalette";
import { useAdminShortcuts } from "../../lib/keyboard-shortcuts";
import { useLang, localizedPath } from "../../lib/use-lang";

export default function AdminLayout() {
  const [cmdOpen, setCmdOpen] = useState(false);
  const navigate = useNavigate();
  const lang = useLang();

  const navTo = useCallback((path: string) => {
    navigate(localizedPath(lang, `/${path}`));
  }, [navigate, lang]);

  const toggleCmd = useCallback(() => setCmdOpen((o) => !o), []);

  useAdminShortcuts(navTo, toggleCmd);

  return (
    <div className="flex min-h-screen bg-dark">
      <AdminSidebar />
      <div className="flex flex-1 flex-col admin-main">
        <AdminHeader onCommandPalette={toggleCmd} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          className: "!glass-card !border-dark-border !text-white",
        }}
      />
    </div>
  );
}
