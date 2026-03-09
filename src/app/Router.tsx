import { Routes, Route } from "react-router-dom";
import Layout from "../components/Layout";
import ProtectedRoute from "../components/ProtectedRoute";

import HomePage from "../pages/HomePage";
import AboutPage from "../pages/AboutPage";
import PricingPage from "../pages/PricingPage";
import ContactPage from "../pages/ContactPage";
import TermsPage from "../pages/TermsPage";
import PrivacyPage from "../pages/PrivacyPage";
import RefundPage from "../pages/RefundPage";
import NotFoundPage from "../pages/NotFoundPage";

import LoginPage from "../pages/auth/LoginPage";
import SignupPage from "../pages/auth/SignupPage";
import AuthCallbackPage from "../pages/auth/AuthCallbackPage";

import DashboardPage from "../pages/dashboard/DashboardPage";
import TenderDetailPage from "../pages/dashboard/TenderDetailPage";
import SavedTendersPage from "../pages/dashboard/SavedTendersPage";
import ProfilePage from "../pages/dashboard/ProfilePage";
import AnalyticsPage from "../pages/dashboard/AnalyticsPage";
import SubscriptionPage from "../pages/dashboard/SubscriptionPage";
import AlertsPage from "../pages/dashboard/AlertsPage";

export default function Router() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Public pages */}
        <Route index element={<HomePage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="pricing" element={<PricingPage />} />
        <Route path="contact" element={<ContactPage />} />

        {/* Legal pages */}
        <Route path="terms" element={<TermsPage />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="refund" element={<RefundPage />} />

        {/* Auth pages */}
        <Route path="auth/login" element={<LoginPage />} />
        <Route path="auth/signup" element={<SignupPage />} />
        <Route path="auth/callback" element={<AuthCallbackPage />} />

        {/* Dashboard pages (protected) */}
        <Route path="dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="dashboard/tender/:id" element={<ProtectedRoute><TenderDetailPage /></ProtectedRoute>} />
        <Route path="dashboard/saved" element={<ProtectedRoute><SavedTendersPage /></ProtectedRoute>} />
        <Route path="dashboard/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="dashboard/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
        <Route path="dashboard/subscription" element={<ProtectedRoute><SubscriptionPage /></ProtectedRoute>} />
        <Route path="dashboard/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />

        {/* Catch-all */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
