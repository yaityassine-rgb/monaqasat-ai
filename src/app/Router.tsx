import { Routes, Route } from "react-router-dom";
import Layout from "../components/Layout";

import HomePage from "../pages/HomePage";
import AboutPage from "../pages/AboutPage";
import PricingPage from "../pages/PricingPage";
import ContactPage from "../pages/ContactPage";
import TermsPage from "../pages/TermsPage";
import PrivacyPage from "../pages/PrivacyPage";
import RefundPage from "../pages/RefundPage";
import NotFoundPage from "../pages/NotFoundPage";

import DashboardPage from "../pages/dashboard/DashboardPage";
import TenderDetailPage from "../pages/dashboard/TenderDetailPage";
import SavedTendersPage from "../pages/dashboard/SavedTendersPage";
import ProfilePage from "../pages/dashboard/ProfilePage";
import AnalyticsPage from "../pages/dashboard/AnalyticsPage";

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

        {/* Dashboard pages */}
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="dashboard/tender/:id" element={<TenderDetailPage />} />
        <Route path="dashboard/saved" element={<SavedTendersPage />} />
        <Route path="dashboard/profile" element={<ProfilePage />} />
        <Route path="dashboard/analytics" element={<AnalyticsPage />} />

        {/* Catch-all */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
