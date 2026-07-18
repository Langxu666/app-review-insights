export interface Review {
  id: string;
  appId: string;
  appName: string;
  rating: number;
  title: string;
  content: string;
  author: string;
  date: string;
  version: string;
}

export interface AnalysisResult {
  sentiment: "positive" | "negative" | "neutral";
  keywords: string[];
  summary: string;
}

export interface Insight {
  id: string;
  type: "bug" | "feature" | "improvement" | "praise";
  description: string;
  confidence: number;
  reviews: Review[];
}