import { useState, useEffect } from "react";
import { supabase, isSupabaseConfigured } from "./supabase";
import { useAuth } from "./auth-context";
import type { AdminRole } from "./admin-types";

interface AdminState {
  isAdmin: boolean;
  isSuperAdmin: boolean;
  role: AdminRole;
  loading: boolean;
}

export function useAdmin(): AdminState {
  const { user } = useAuth();
  const [role, setRole] = useState<AdminRole>("user");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !isSupabaseConfigured) {
      setRole("user");
      setLoading(false);
      return;
    }

    // Check sessionStorage cache first
    const cached = sessionStorage.getItem(`admin_role_${user.id}`);
    if (cached) {
      setRole(cached as AdminRole);
      setLoading(false);
      return;
    }

    supabase
      .from("user_roles")
      .select("role")
      .eq("user_id", user.id)
      .maybeSingle()
      .then(({ data }) => {
        const r = (data?.role as AdminRole) || "user";
        setRole(r);
        sessionStorage.setItem(`admin_role_${user.id}`, r);
        setLoading(false);
      });
  }, [user]);

  return {
    isAdmin: role === "admin" || role === "superadmin",
    isSuperAdmin: role === "superadmin",
    role,
    loading,
  };
}
