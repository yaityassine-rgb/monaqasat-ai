import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../lib/auth-context";
import { isSupabaseConfigured } from "../lib/supabase";
import { useLang, localizedPath } from "../lib/use-lang";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  const lang = useLang();

  // If Supabase is not configured, allow access (dev/preview mode)
  if (!isSupabaseConfigured) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to={localizedPath(lang, "/auth/login")} state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
