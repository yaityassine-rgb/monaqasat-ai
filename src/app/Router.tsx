import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { Loader2 } from "lucide-react";
import Layout from "../components/Layout";
import DashboardLayout from "../components/DashboardLayout";
import ProtectedRoute from "../components/ProtectedRoute";
import AdminRoute from "../components/AdminRoute";
import { LanguageLayout, RootRedirect } from "../lib/use-lang";

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
import DocumentsPage from "../pages/dashboard/DocumentsPage";
import ProposalPage from "../pages/dashboard/ProposalPage";
import TeamPage from "../pages/dashboard/TeamPage";
import GrantsPage from "../pages/dashboard/GrantsPage";
import GrantDetailPage from "../pages/dashboard/GrantDetailPage";
import PPPPage from "../pages/dashboard/PPPPage";
import PartnersPage from "../pages/dashboard/PartnersPage";
import PreQualificationPage from "../pages/dashboard/PreQualificationPage";
import ConsultingPage from "../pages/dashboard/ConsultingPage";

// Admin pages (lazy-loaded — non-admin users never download this code)
const AdminLayout = lazy(() => import("../components/admin/AdminLayout"));
const AdminOverviewPage = lazy(() => import("../pages/admin/AdminOverviewPage"));
const ScraperManagementPage = lazy(() => import("../pages/admin/ScraperManagementPage"));
const UserManagementPage = lazy(() => import("../pages/admin/UserManagementPage"));
const DataExplorerPage = lazy(() => import("../pages/admin/DataExplorerPage"));
const AdminSubscriptionsPage = lazy(() => import("../pages/admin/SubscriptionsPage"));
const CreditsPage = lazy(() => import("../pages/admin/CreditsPage"));
const ContentManagementPage = lazy(() => import("../pages/admin/ContentManagementPage"));
const SystemLogsPage = lazy(() => import("../pages/admin/SystemLogsPage"));
const AdminSettingsPage = lazy(() => import("../pages/admin/AdminSettingsPage"));

function AdminFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-dark">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

export default function Router() {
  return (
    <Routes>
      {/* Root redirect: / → /en (or detected language) */}
      <Route index element={<RootRedirect />} />

      {/* All routes nested under /:lang */}
      <Route path=":lang" element={<LanguageLayout />}>
        {/* Dashboard pages — own layout with sidebar */}
        <Route path="dashboard" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="tender/:id" element={<TenderDetailPage />} />
          <Route path="saved" element={<SavedTendersPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="subscription" element={<SubscriptionPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="proposals" element={<ProposalPage />} />
          <Route path="proposals/:id" element={<ProposalPage />} />
          <Route path="team" element={<TeamPage />} />
          <Route path="grants" element={<GrantsPage />} />
          <Route path="grants/:id" element={<GrantDetailPage />} />
          <Route path="ppp" element={<PPPPage />} />
          <Route path="partners" element={<PartnersPage />} />
          <Route path="prequalification" element={<PreQualificationPage />} />
          <Route path="consulting" element={<ConsultingPage />} />
        </Route>

        {/* Admin pages (separate layout, no Navbar/Footer) */}
        <Route
          path="admin"
          element={
            <AdminRoute>
              <Suspense fallback={<AdminFallback />}>
                <AdminLayout />
              </Suspense>
            </AdminRoute>
          }
        >
          <Route index element={<Suspense fallback={<AdminFallback />}><AdminOverviewPage /></Suspense>} />
          <Route path="scrapers" element={<Suspense fallback={<AdminFallback />}><ScraperManagementPage /></Suspense>} />
          <Route path="users" element={<Suspense fallback={<AdminFallback />}><UserManagementPage /></Suspense>} />
          <Route path="data" element={<Suspense fallback={<AdminFallback />}><DataExplorerPage /></Suspense>} />
          <Route path="data/:type" element={<Suspense fallback={<AdminFallback />}><DataExplorerPage /></Suspense>} />
          <Route path="subscriptions" element={<Suspense fallback={<AdminFallback />}><AdminSubscriptionsPage /></Suspense>} />
          <Route path="credits" element={<Suspense fallback={<AdminFallback />}><CreditsPage /></Suspense>} />
          <Route path="content" element={<Suspense fallback={<AdminFallback />}><ContentManagementPage /></Suspense>} />
          <Route path="logs" element={<Suspense fallback={<AdminFallback />}><SystemLogsPage /></Suspense>} />
          <Route path="settings" element={<Suspense fallback={<AdminFallback />}><AdminSettingsPage /></Suspense>} />
        </Route>

        {/* Public pages (Layout with Navbar/Footer) */}
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="pricing" element={<PricingPage />} />
          <Route path="contact" element={<ContactPage />} />
          <Route path="terms" element={<TermsPage />} />
          <Route path="privacy" element={<PrivacyPage />} />
          <Route path="refund" element={<RefundPage />} />
          <Route path="auth/login" element={<LoginPage />} />
          <Route path="auth/signup" element={<SignupPage />} />
          <Route path="auth/callback" element={<AuthCallbackPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
