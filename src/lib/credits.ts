/**
 * AI Credit System
 * Credits are consumed by AI-powered features:
 * - Tender analysis: 1 credit
 * - Proposal generation: 5 credits
 * - Competitor insights: 2 credits
 * - BOQ analysis: 3 credits
 * - Win probability: 1 credit
 * - Grant matching: 1 credit
 * - PPP analysis: 2 credits
 * - Partner compatibility: 1 credit
 */

export interface CreditBalance {
  total: number;
  used: number;
  remaining: number;
  plan: string;
  monthlyAllowance: number;
  bonusCredits: number;
  resetDate: string;
}

export interface CreditCost {
  feature: string;
  cost: number;
  key: string;
}

export const CREDIT_COSTS: CreditCost[] = [
  { key: "tenderAnalysis", feature: "AI Tender Analysis", cost: 1 },
  { key: "proposalGeneration", feature: "Proposal Generation", cost: 5 },
  { key: "competitorInsights", feature: "Competitor Insights", cost: 2 },
  { key: "boqAnalysis", feature: "BOQ Analysis", cost: 3 },
  { key: "winProbability", feature: "Win Probability", cost: 1 },
  { key: "grantMatching", feature: "Grant Matching", cost: 1 },
  { key: "pppAnalysis", feature: "PPP Analysis", cost: 2 },
  { key: "partnerCompatibility", feature: "Partner Compatibility", cost: 1 },
  { key: "preQualCheck", feature: "Pre-Qualification Check", cost: 2 },
];

export const PLAN_CREDITS: Record<string, number> = {
  explorer: 10,
  starter: 100,
  professional: 500,
  business: 2000,
  enterprise: 999999, // effectively unlimited
};

const STORAGE_KEY = "monaqasat_credits";

function getStoredCredits(): CreditBalance {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch { /* ignore */ }

  // Default for new/free users
  const now = new Date();
  const resetDate = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return {
    total: 10,
    used: 0,
    remaining: 10,
    plan: "explorer",
    monthlyAllowance: 10,
    bonusCredits: 0,
    resetDate: resetDate.toISOString().split("T")[0],
  };
}

function saveCredits(balance: CreditBalance) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(balance));
}

export function getCreditBalance(): CreditBalance {
  return getStoredCredits();
}

export function consumeCredits(featureKey: string): { success: boolean; balance: CreditBalance } {
  const cost = CREDIT_COSTS.find((c) => c.key === featureKey);
  if (!cost) return { success: false, balance: getStoredCredits() };

  const balance = getStoredCredits();
  if (balance.remaining < cost.cost) {
    return { success: false, balance };
  }

  balance.used += cost.cost;
  balance.remaining = balance.total - balance.used;
  saveCredits(balance);
  return { success: true, balance };
}

export function addCredits(amount: number): CreditBalance {
  const balance = getStoredCredits();
  balance.total += amount;
  balance.bonusCredits += amount;
  balance.remaining = balance.total - balance.used;
  saveCredits(balance);
  return balance;
}

export function setPlanCredits(plan: string): CreditBalance {
  const allowance = PLAN_CREDITS[plan] || 10;
  const balance = getStoredCredits();
  const now = new Date();
  const resetDate = new Date(now.getFullYear(), now.getMonth() + 1, 1);

  balance.plan = plan;
  balance.monthlyAllowance = allowance;
  balance.total = allowance + balance.bonusCredits;
  balance.used = 0;
  balance.remaining = balance.total;
  balance.resetDate = resetDate.toISOString().split("T")[0];

  saveCredits(balance);
  return balance;
}

export function getCreditCost(featureKey: string): number {
  return CREDIT_COSTS.find((c) => c.key === featureKey)?.cost ?? 0;
}

export function hasEnoughCredits(featureKey: string): boolean {
  const cost = getCreditCost(featureKey);
  const balance = getCreditBalance();
  return balance.remaining >= cost;
}
