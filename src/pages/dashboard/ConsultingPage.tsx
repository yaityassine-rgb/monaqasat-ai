import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  Briefcase,
  Check,
  Clock,
  ArrowRight,
  Phone,
  FileSearch,
  Rocket,
  Users,
  Star,
  Globe,
  MessageSquareQuote,
  ChevronRight,
} from "lucide-react";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

interface ConsultingPackage {
  key: string;
  name: string;
  price: number;
  icon: typeof FileSearch;
  color: string;
  bgColor: string;
  borderColor: string;
  deliveryDays: number;
  features: string[];
  popular?: boolean;
}

const PACKAGES: ConsultingPackage[] = [
  {
    key: "scanner",
    name: "Market Scanner",
    price: 499,
    icon: FileSearch,
    color: "text-blue-400",
    bgColor: "bg-blue-400/10",
    borderColor: "border-blue-400/30",
    deliveryDays: 5,
    features: [
      "Comprehensive market overview report",
      "Competitor landscape analysis",
      "Regulatory environment snapshot",
      "Key opportunity identification",
      "Market size & growth data",
    ],
  },
  {
    key: "entry",
    name: "Market Entry",
    price: 2499,
    icon: Rocket,
    color: "text-primary-light",
    bgColor: "bg-primary/10",
    borderColor: "border-primary/40",
    deliveryDays: 15,
    popular: true,
    features: [
      "Full market analysis & sizing",
      "Go-to-market entry strategy",
      "Potential partner shortlist (10+)",
      "Regulatory & compliance guide",
      "Risk assessment matrix",
      "Pricing strategy recommendations",
      "Quarterly market update (3 months)",
    ],
  },
  {
    key: "launch",
    name: "Full Launch",
    price: 9999,
    icon: Users,
    color: "text-emerald-400",
    bgColor: "bg-emerald-400/10",
    borderColor: "border-emerald-400/30",
    deliveryDays: 45,
    features: [
      "Everything in Market Entry package",
      "On-ground partner introductions",
      "Local entity setup support",
      "First 3 tender submissions assisted",
      "Dedicated account manager",
      "Government relationship facilitation",
      "12-month strategic advisory calls",
      "Translated document preparation",
    ],
  },
];

interface HowItWorksStep {
  icon: typeof Phone;
  titleKey: string;
  descKey: string;
  color: string;
}

const HOW_IT_WORKS: HowItWorksStep[] = [
  {
    icon: FileSearch,
    titleKey: "selectPackage",
    descKey: "selectPackageDesc",
    color: "text-blue-400",
  },
  {
    icon: Phone,
    titleKey: "briefCall",
    descKey: "briefCallDesc",
    color: "text-amber-400",
  },
  {
    icon: Rocket,
    titleKey: "weDeliver",
    descKey: "weDeliverDesc",
    color: "text-primary-light",
  },
  {
    icon: Check,
    titleKey: "youExecute",
    descKey: "youExecuteDesc",
    color: "text-emerald-400",
  },
];

const MENA_COUNTRIES = [
  { flag: "\u{1F1F8}\u{1F1E6}", name: "Saudi Arabia" },
  { flag: "\u{1F1E6}\u{1F1EA}", name: "UAE" },
  { flag: "\u{1F1F0}\u{1F1FC}", name: "Kuwait" },
  { flag: "\u{1F1F6}\u{1F1E6}", name: "Qatar" },
  { flag: "\u{1F1E7}\u{1F1ED}", name: "Bahrain" },
  { flag: "\u{1F1F4}\u{1F1F2}", name: "Oman" },
  { flag: "\u{1F1EA}\u{1F1EC}", name: "Egypt" },
  { flag: "\u{1F1EF}\u{1F1F4}", name: "Jordan" },
  { flag: "\u{1F1F2}\u{1F1E6}", name: "Morocco" },
  { flag: "\u{1F1F9}\u{1F1F3}", name: "Tunisia" },
  { flag: "\u{1F1EE}\u{1F1F6}", name: "Iraq" },
  { flag: "\u{1F1F1}\u{1F1E7}", name: "Lebanon" },
];

interface Testimonial {
  quote: string;
  author: string;
  role: string;
  company: string;
}

const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      "Monaqasat's Market Entry package gave us the confidence to bid on Saudi government contracts. Within 3 months we had our first awarded tender worth $1.2M.",
    author: "Sarah K.",
    role: "Business Development Director",
    company: "TechBridge Solutions, UK",
  },
  {
    quote:
      "The Full Launch package was a game-changer. From entity setup to our first successful tender submission, the team guided us every step of the way in the UAE market.",
    author: "Marc D.",
    role: "CEO",
    company: "InfraServe Group, France",
  },
];

export default function ConsultingPage() {
  const { t } = useTranslation();
  const [selectedPackage, setSelectedPackage] = useState<string | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-6xl mx-auto"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <div className="flex items-center gap-3 mb-1">
          <Briefcase className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("consulting.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("consulting.subtitle")}</p>
      </motion.div>

      {/* Consulting Packages */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5 mb-10">
        {PACKAGES.map((pkg, idx) => {
          const Icon = pkg.icon;
          const isSelected = selectedPackage === pkg.key;

          return (
            <motion.div
              key={pkg.key}
              {...fadeUp}
              transition={{ delay: 0.15 + idx * 0.08 }}
              className={`glass-card rounded-xl p-5 md:p-6 border transition-all relative ${
                pkg.popular
                  ? "border-primary/40 shadow-lg shadow-primary/10"
                  : isSelected
                  ? "border-primary/30"
                  : "border-dark-border hover:border-slate-600"
              }`}
            >
              {/* Popular badge */}
              {pkg.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 rounded-full bg-primary text-white text-[10px] font-bold uppercase tracking-wider shadow-lg shadow-primary/30">
                    {t("consulting.mostPopular")}
                  </span>
                </div>
              )}

              {/* Icon + Name */}
              <div className="flex items-center gap-3 mb-4 mt-1">
                <div
                  className={`w-11 h-11 rounded-lg ${pkg.bgColor} flex items-center justify-center`}
                >
                  <Icon className={`w-5 h-5 ${pkg.color}`} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">
                    {pkg.name}
                  </h3>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>
                      {t("consulting.deliveryDays", { days: pkg.deliveryDays })}
                    </span>
                  </div>
                </div>
              </div>

              {/* Price */}
              <div className="mb-5">
                <span className="text-3xl font-bold text-white">
                  ${pkg.price.toLocaleString()}
                </span>
                <span className="text-sm text-slate-500 ml-1">
                  {t("consulting.oneTime")}
                </span>
              </div>

              {/* Features List */}
              <ul className="space-y-2.5 mb-6">
                {pkg.features.map((feature, fIdx) => (
                  <li
                    key={fIdx}
                    className="flex items-start gap-2.5 text-sm text-slate-300"
                  >
                    <Check
                      className={`w-4 h-4 shrink-0 mt-0.5 ${pkg.color}`}
                    />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA Button */}
              <button
                onClick={() => setSelectedPackage(pkg.key)}
                className={`w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold rounded-xl transition-all ${
                  pkg.popular
                    ? "bg-primary hover:bg-primary-dark text-white shadow-lg shadow-primary/20"
                    : "bg-primary/10 hover:bg-primary/20 border border-primary/30 hover:border-primary/50 text-primary-light"
                }`}
              >
                {t("consulting.getStarted")}
                <ArrowRight className="w-4 h-4" />
              </button>
            </motion.div>
          );
        })}
      </div>

      {/* How It Works */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.4 }}
        className="glass-card rounded-xl p-5 md:p-6 mb-8"
      >
        <h2 className="text-base font-semibold text-slate-100 mb-6 flex items-center gap-2">
          <Rocket className="w-4 h-4 text-primary-light" />
          {t("consulting.howItWorks")}
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {HOW_IT_WORKS.map((step, idx) => {
            const StepIcon = step.icon;

            return (
              <motion.div
                key={step.titleKey}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45 + idx * 0.08 }}
                className="relative"
              >
                <div className="flex flex-col items-center text-center p-4">
                  {/* Step Number */}
                  <div className="w-8 h-8 rounded-full bg-dark/80 border border-dark-border flex items-center justify-center mb-3">
                    <span className="text-xs font-bold text-slate-300">
                      {idx + 1}
                    </span>
                  </div>

                  {/* Icon */}
                  <div className="w-12 h-12 rounded-xl bg-dark/60 border border-dark-border flex items-center justify-center mb-3">
                    <StepIcon className={`w-5 h-5 ${step.color}`} />
                  </div>

                  <h4 className="text-sm font-semibold text-slate-200 mb-1">
                    {t(`consulting.hiw.${step.titleKey}`)}
                  </h4>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    {t(`consulting.hiw.${step.descKey}`)}
                  </p>
                </div>

                {/* Arrow connector (hidden on last item) */}
                {idx < HOW_IT_WORKS.length - 1 && (
                  <div className="hidden lg:block absolute top-1/2 -right-2 -translate-y-1/2">
                    <ChevronRight className="w-4 h-4 text-slate-600" />
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Covered Regions */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.5 }}
        className="glass-card rounded-xl p-5 md:p-6 mb-8"
      >
        <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
          <Globe className="w-4 h-4 text-primary-light" />
          {t("consulting.coveredRegions")}
        </h2>

        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
          {MENA_COUNTRIES.map((country, idx) => (
            <motion.div
              key={country.name}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.55 + idx * 0.03 }}
              className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-dark/40 border border-dark-border hover:border-primary/20 transition-colors"
            >
              <span className="text-2xl">{country.flag}</span>
              <span className="text-[10px] md:text-xs text-slate-400 text-center leading-tight">
                {country.name}
              </span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Testimonials / Social Proof */}
      <motion.div {...fadeUp} transition={{ delay: 0.6 }} className="mb-8">
        <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
          <MessageSquareQuote className="w-4 h-4 text-primary-light" />
          {t("consulting.clientSuccess")}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {TESTIMONIALS.map((testimonial, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.65 + idx * 0.08 }}
              className="glass-card rounded-xl p-5 md:p-6 border border-dark-border"
            >
              {/* Stars */}
              <div className="flex items-center gap-0.5 mb-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className="w-4 h-4 text-amber-400 fill-amber-400"
                  />
                ))}
              </div>

              {/* Quote */}
              <p className="text-sm text-slate-300 leading-relaxed mb-4 italic">
                "{testimonial.quote}"
              </p>

              {/* Author */}
              <div className="flex items-center gap-3 pt-3 border-t border-dark-border">
                <div className="w-9 h-9 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                  <span className="text-xs font-bold text-primary-light">
                    {testimonial.author
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                  </span>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    {testimonial.author}
                  </p>
                  <p className="text-xs text-slate-500">
                    {testimonial.role} · {testimonial.company}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Bottom CTA */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.75 }}
        className="glass-card rounded-xl p-6 md:p-8 text-center border border-primary/20"
      >
        <h3 className="text-lg md:text-xl font-bold text-slate-100 mb-2">
          {t("consulting.readyToExpand")}
        </h3>
        <p className="text-sm text-slate-400 mb-5 max-w-lg mx-auto">
          {t("consulting.readyToExpandDesc")}
        </p>
        <button className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-primary/20">
          {t("consulting.scheduleCall")}
          <Phone className="w-4 h-4" />
        </button>
      </motion.div>
    </motion.div>
  );
}
