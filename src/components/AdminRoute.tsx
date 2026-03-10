import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../lib/auth-context";
import { useAdmin } from "../lib/use-admin";
import { isSupabaseConfigured } from "../lib/supabase";
import { useLang, localizedPath } from "../lib/use-lang";

export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const { isAdmin, loading: adminLoading } = useAdmin();
  const lang = useLang();

  if (!isSupabaseConfigured) return <>{children}</>;

  if (authLoading || adminLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-dark">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to={localizedPath(lang, "/auth/login")} replace />;
  }

  if (!isAdmin) {
    return <Navigate to={localizedPath(lang, "/dashboard")} replace />;
  }

  return <>{children}</>;
}
