// Shared utility functions used across dashboard pages

export const SAVED_TENDERS_KEY = "monaqasat-saved-tenders";

export function getSavedIds(): string[] {
  try {
    const raw = localStorage.getItem(SAVED_TENDERS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function setSavedIds(ids: string[]) {
  localStorage.setItem(SAVED_TENDERS_KEY, JSON.stringify(ids));
}

export function formatBudget(
  amount: number,
  currency: string,
  notDisclosedLabel = "Not disclosed",
): string {
  if (!amount || amount <= 0) return notDisclosedLabel;
  if (amount >= 1_000_000_000) {
    return `${(amount / 1_000_000_000).toFixed(1)}B ${currency}`;
  }
  if (amount >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(1)}M ${currency}`;
  }
  if (amount >= 1_000) {
    return `${(amount / 1_000).toFixed(0)}K ${currency}`;
  }
  return `${amount.toLocaleString()} ${currency}`;
}

export function formatValue(amount: number): string {
  if (amount >= 1_000_000_000_000) {
    return `${(amount / 1_000_000_000_000).toFixed(1)}T`;
  }
  if (amount >= 1_000_000_000) {
    return `${(amount / 1_000_000_000).toFixed(1)}B`;
  }
  if (amount >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `${(amount / 1_000).toFixed(0)}K`;
  }
  return amount.toLocaleString();
}

export function getMatchColor(score: number): string {
  if (score >= 80)
    return "text-emerald-400 bg-emerald-400/10 border-emerald-400/30";
  if (score >= 60)
    return "text-amber-400 bg-amber-400/10 border-amber-400/30";
  return "text-red-400 bg-red-400/10 border-red-400/30";
}

export function getMatchTextColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

export function getStatusStyle(status: string): string {
  switch (status) {
    case "open":
      return "text-emerald-400 bg-emerald-400/10 border-emerald-400/30";
    case "closing-soon":
      return "text-amber-400 bg-amber-400/10 border-amber-400/30";
    case "closed":
      return "text-red-400 bg-red-400/10 border-red-400/30";
    default:
      return "text-slate-400 bg-slate-400/10 border-slate-400/30";
  }
}
