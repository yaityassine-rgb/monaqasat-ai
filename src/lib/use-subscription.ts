import { useState, useEffect } from "react";
import { supabase, isSupabaseConfigured } from "./supabase";
import { useAuth } from "./auth-context";

export type Tier = "free" | "starter" | "professional" | "business";

export interface TierLimits {
  tenderViewsPerDay: number;
  analysesPerMonth: number;
  proposalsPerMonth: number;
  aiMatching: boolean;
  emailAlerts: boolean;
  competitorInsights: boolean;
  apiAccess: boolean;
  teamSeats: number;
}

export const TIER_LIMITS: Record<Tier, TierLimits> = {
  free: {
    tenderViewsPerDay: 10,
    analysesPerMonth: 0,
    proposalsPerMonth: 0,
    aiMatching: false,
    emailAlerts: false,
    competitorInsights: false,
    apiAccess: false,
    teamSeats: 1,
  },
  starter: {
    tenderViewsPerDay: Infinity,
    analysesPerMonth: 20,
    proposalsPerMonth: 0,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: false,
    apiAccess: false,
    teamSeats: 1,
  },
  professional: {
    tenderViewsPerDay: Infinity,
    analysesPerMonth: Infinity,
    proposalsPerMonth: 10,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: true,
    apiAccess: false,
    teamSeats: 1,
  },
  business: {
    tenderViewsPerDay: Infinity,
    analysesPerMonth: Infinity,
    proposalsPerMonth: Infinity,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: true,
    apiAccess: true,
    teamSeats: 5,
  },
};

export const TIER_PRICES = {
  free: { monthly: 0, yearly: 0 },
  starter: { monthly: 79, yearly: 790 },
  professional: { monthly: 199, yearly: 1990 },
  business: { monthly: 499, yearly: 4990 },
};

interface SubscriptionState {
  tier: Tier;
  limits: TierLimits;
  loading: boolean;
  subscriptionId: string | null;
  currentPeriodEnd: string | null;
  canUseFeature: (feature: keyof TierLimits) => boolean;
}

export function useSubscription(): SubscriptionState {
  const { user } = useAuth();
  const [tier, setTier] = useState<Tier>("free");
  const [loading, setLoading] = useState(true);
  const [subscriptionId, setSubscriptionId] = useState<string | null>(null);
  const [currentPeriodEnd, setCurrentPeriodEnd] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !isSupabaseConfigured) {
      setTier("free");
      setLoading(false);
      return;
    }

    async function fetchSubscription() {
      const { data } = await supabase
        .from("subscriptions")
        .select("*")
        .eq("user_id", user!.id)
        .eq("status", "active")
        .order("created_at", { ascending: false })
        .limit(1)
        .single();

      if (data) {
        setTier(data.tier as Tier);
        setSubscriptionId(data.id);
        setCurrentPeriodEnd(data.current_period_end);
      }
      setLoading(false);
    }

    fetchSubscription();
  }, [user]);

  const limits = TIER_LIMITS[tier];

  const canUseFeature = (feature: keyof TierLimits): boolean => {
    const value = limits[feature];
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value > 0;
    return false;
  };

  return { tier, limits, loading, subscriptionId, currentPeriodEnd, canUseFeature };
}
