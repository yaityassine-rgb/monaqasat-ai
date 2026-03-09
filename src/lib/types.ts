export interface Tender {
  id: string;
  title: { en: string; ar: string; fr: string };
  organization: { en: string; ar: string; fr: string };
  country: string;
  countryCode: string;
  sector: string;
  budget: number;
  currency: string;
  deadline: string;
  publishDate: string;
  status: "open" | "closing-soon" | "closed";
  description: { en: string; ar: string; fr: string };
  requirements: string[];
  matchScore: number;
  saved?: boolean;
}

export type SectorKey =
  | "construction"
  | "it"
  | "healthcare"
  | "energy"
  | "education"
  | "transport"
  | "defense"
  | "water"
  | "telecom"
  | "agriculture";

export type CountryCode =
  | "MA"
  | "SA"
  | "AE"
  | "EG"
  | "KW"
  | "QA"
  | "BH"
  | "OM"
  | "JO"
  | "TN"
  | "DZ"
  | "LY";
