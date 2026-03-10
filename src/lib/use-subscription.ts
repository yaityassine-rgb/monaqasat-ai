import { useState, useEffect } from "react";
import { supabase, isSupabaseConfigured } from "./supabase";
import { useAuth } from "./auth-context";

export type Tier = "free" | "starter" | "professional" | "business" | "enterprise";

export interface TierLimits {
  tenderViewsPerDay: number;
  aiCreditsPerMonth: number;
  aiMatching: boolean;
  emailAlerts: boolean;
  competitorInsights: boolean;
  proposalGeneration: boolean;
  grantsIntelligence: boolean;
  pppIntelligence: boolean;
  jvMatchmaking: boolean;
  preQualification: boolean;
  marketConsulting: boolean;
  apiAccess: boolean;
  teamSeats: number;
}

export const TIER_LIMITS: Record<Tier, TierLimits> = {
  free: {
    tenderViewsPerDay: 10,
    aiCreditsPerMonth: 10,
    aiMatching: false,
    emailAlerts: false,
    competitorInsights: false,
    proposalGeneration: false,
    grantsIntelligence: false,
    pppIntelligence: false,
    jvMatchmaking: false,
    preQualification: false,
    marketConsulting: false,
    apiAccess: false,
    teamSeats: 1,
  },
  starter: {
    tenderViewsPerDay: Infinity,
    aiCreditsPerMonth: 100,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: false,
    proposalGeneration: false,
    grantsIntelligence: false,
    pppIntelligence: false,
    jvMatchmaking: false,
    preQualification: false,
    marketConsulting: false,
    apiAccess: false,
    teamSeats: 1,
  },
  professional: {
    tenderViewsPerDay: Infinity,
    aiCreditsPerMonth: 500,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: true,
    proposalGeneration: true,
    grantsIntelligence: true,
    pppIntelligence: false,
    jvMatchmaking: false,
    preQualification: false,
    marketConsulting: false,
    apiAccess: false,
    teamSeats: 1,
  },
  business: {
    tenderViewsPerDay: Infinity,
    aiCreditsPerMonth: 2000,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: true,
    proposalGeneration: true,
    grantsIntelligence: true,
    pppIntelligence: true,
    jvMatchmaking: true,
    preQualification: true,
    marketConsulting: false,
    apiAccess: true,
    teamSeats: 5,
  },
  enterprise: {
    tenderViewsPerDay: Infinity,
    aiCreditsPerMonth: 999999,
    aiMatching: true,
    emailAlerts: true,
    competitorInsights: true,
    proposalGeneration: true,
    grantsIntelligence: true,
    pppIntelligence: true,
    jvMatchmaking: true,
    preQualification: true,
    marketConsulting: true,
    apiAccess: true,
    teamSeats: Infinity,
  },
};

export const TIER_PRICES = {
  free: { monthly: 0, yearly: 0 },
  starter: { monthly: 49, yearly: 470 },
  professional: { monthly: 149, yearly: 1430 },
  business: { monthly: 399, yearly: 3830 },
  enterprise: { monthly: 999, yearly: 9990 },
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
