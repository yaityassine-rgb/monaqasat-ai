import { useEffect } from "react";

type ShortcutHandler = () => void;

const shortcuts = new Map<string, ShortcutHandler>();

export function useKeyboardShortcut(keys: string, handler: ShortcutHandler) {
  useEffect(() => {
    shortcuts.set(keys, handler);
    return () => { shortcuts.delete(keys); };
  }, [keys, handler]);
}

// Sequence-based shortcuts (e.g., "g o" for go to overview)
let sequence = "";
let sequenceTimer: ReturnType<typeof setTimeout>;

export function useAdminShortcuts(navigate: (path: string) => void, onCommandPalette: () => void) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Skip if focused on input
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if ((e.target as HTMLElement).isContentEditable) return;

      // Cmd+K or Ctrl+K → command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onCommandPalette();
        return;
      }

      // Sequence shortcuts
      clearTimeout(sequenceTimer);
      sequence += e.key;
      sequenceTimer = setTimeout(() => { sequence = ""; }, 800);

      const routes: Record<string, string> = {
        go: "admin",
        gs: "admin/scrapers",
        gu: "admin/users",
        gd: "admin/data",
        gl: "admin/logs",
      };

      if (routes[sequence]) {
        navigate(routes[sequence]);
        sequence = "";
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [navigate, onCommandPalette]);
}
