import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Mail, Lock, LogIn, AlertCircle } from "lucide-react";
import { useAuth } from "../../lib/auth-context";
import SEOHead from "../../components/SEOHead";

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { signInWithEmail, signInWithGoogle } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const { error } = await signInWithEmail(email, password);
    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      navigate("/dashboard");
    }
  };

  const handleGoogleLogin = async () => {
    setError("");
    const { error } = await signInWithGoogle();
    if (error) setError(error.message);
  };

  return (
    <>
      <SEOHead title={t("auth.loginTitle")} />

      <div className="min-h-screen flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div className="glass-card rounded-2xl p-8">
            <div className="text-center mb-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary font-bold text-white text-xl mx-auto mb-4">
                M
              </div>
              <h1 className="text-2xl font-bold text-white">{t("auth.loginTitle")}</h1>
              <p className="text-slate-400 text-sm mt-2">{t("auth.loginSubtitle")}</p>
            </div>

            {error && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-400/10 border border-red-400/30 text-red-400 text-sm mb-6">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            {/* Google OAuth */}
            <button
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-dark-border rounded-xl text-sm font-medium text-slate-200 hover:bg-white/5 transition-colors mb-6"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              {t("auth.continueWithGoogle")}
            </button>

            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-dark-border" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-dark-card px-3 text-slate-500">{t("auth.orEmail")}</span>
              </div>
            </div>

            {/* Email login form */}
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                  <Mail className="w-4 h-4" />
                  {t("auth.email")}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t("auth.emailPlaceholder")}
                  required
                  className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
                />
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                  <Lock className="w-4 h-4" />
                  {t("auth.password")}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-primary/20 disabled:opacity-50"
              >
                <LogIn className="w-4 h-4" />
                {loading ? t("auth.signingIn") : t("auth.signIn")}
              </button>
            </form>

            <p className="text-center text-sm text-slate-400 mt-6">
              {t("auth.noAccount")}{" "}
              <Link to="/auth/signup" className="text-primary-light hover:text-primary font-medium">
                {t("auth.signUpLink")}
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </>
  );
}
