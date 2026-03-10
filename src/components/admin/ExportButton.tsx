import { useState, useRef, useEffect } from "react";
import { Download, ChevronDown } from "lucide-react";

interface ExportButtonProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
  filename?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toCsv(data: any[]): string {
  if (!data.length) return "";
  const headers = Object.keys(data[0]);
  const rows = data.map((row) =>
    headers.map((h) => {
      const val = row[h];
      const str = val === null || val === undefined ? "" : String(val);
      return str.includes(",") || str.includes('"') || str.includes("\n")
        ? `"${str.replace(/"/g, '""')}"`
        : str;
    }).join(",")
  );
  return [headers.join(","), ...rows].join("\n");
}

function download(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ExportButton({ data, filename = "export" }: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg border border-dark-border px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5"
      >
        <Download className="h-4 w-4" />
        Export
        <ChevronDown className="h-3 w-3" />
      </button>
      {open && (
        <div className="absolute end-0 top-full mt-1 z-50 w-32 rounded-lg glass-card border border-dark-border py-1 shadow-xl">
          <button
            onClick={() => { download(toCsv(data), `${filename}.csv`, "text/csv"); setOpen(false); }}
            className="w-full px-3 py-2 text-start text-sm text-slate-300 hover:bg-white/5"
          >
            CSV
          </button>
          <button
            onClick={() => { download(JSON.stringify(data, null, 2), `${filename}.json`, "application/json"); setOpen(false); }}
            className="w-full px-3 py-2 text-start text-sm text-slate-300 hover:bg-white/5"
          >
            JSON
          </button>
        </div>
      )}
    </div>
  );
}
