import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { supabase } from "../../lib/supabase";
import { useLang, localizedPath } from "../../lib/use-lang";

export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const lang = useLang();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        navigate(localizedPath(lang, "/dashboard/profile"), { replace: true });
      } else {
        navigate(localizedPath(lang, "/auth/login"), { replace: true });
      }
    });
  }, [navigate, lang]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-8 h-8 text-primary animate-spin" />
    </div>
  );
}
