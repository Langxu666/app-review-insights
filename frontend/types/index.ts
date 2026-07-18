// ──────────────── Enums ────────────────

export type StageStatus = "pending" | "running" | "completed" | "failed";

export type WorkflowStatus = "pending" | "running" | "completed" | "failed";

export type Sentiment = "positive" | "negative" | "neutral" | "mixed";

export type FindingSeverity = "critical" | "high" | "medium" | "low";

export type EvidenceSufficiency = "sufficient" | "limited" | "insufficient";

export type Priority = "P0" | "P1" | "P2" | "P3";

// ──────────────── Core Models ────────────────

export interface Review {
  id: string;
  app_id: string;
  rating: number;
  title: string | null;
  content: string;
  author: string;
  date: string;
  version: string | null;
}

export interface ClassificationResult {
  review_id: string;
  primary_category: string;
  sentiment: Sentiment;
  summary: string;
  confidence: number;
  key_quote: string;
}

export interface Finding {
  finding_id: string;
  title: string;
  category: string;
  severity: FindingSeverity;
  description: string;
  supporting_review_ids: string[];
  supporting_excerpts: string[];
  support_count: number;
  conflicting_evidence: string[] | null;
  assumptions: string[] | null;
  confidence: number;
  uncertainty_notes: string | null;
  evidence_sufficiency: EvidenceSufficiency;
}

export interface UserStory {
  id: string;
  role: string;
  goal: string;
  benefit: string;
  role_en?: string | null;
  goal_en?: string | null;
  benefit_en?: string | null;
}

export interface Requirement {
  req_id: string;
  title: string;
  description: string;
  user_problem: string;
  business_value: string;
  priority: Priority;
  target_version: string | null;
  acceptance_criteria: string[];
  source_finding_ids: string[];
  source_review_ids: string[];
  effort_estimate: string | null;
  is_assumption: boolean;
}

export interface VersionPlan {
  version: string;
  theme: string;
  release_goal: string;
  requirement_ids: string[];
  rationale: string;
}

export interface PRDDraft {
  title: string;
  app_name: string;
  analysis_goal: string;
  generated_at: string;
  background: string;
  problem_statement: string;
  supporting_findings: string[];
  user_stories: UserStory[];
  requirements: Requirement[];
  version_plan: VersionPlan[];
}

export interface TestCase {
  id: string;
  title: string;
  related_requirement: string | null;
  preconditions: string[];
  steps: string[];
  expected_result: string;
}

// ──────────────── Workflow / API Response ────────────────

export interface StageInfo {
  status: StageStatus;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error: string | null;
}

export interface ArtifactsSummary {
  reviews_count: number;
  cleaned_count: number;
  classified_count: number;
  findings_count: number;
  requirements_count: number;
  test_cases_count: number;
}

export interface AnalyzeResponse {
  status: WorkflowStatus;
  stages: Record<string, StageInfo>;
  artifacts: ArtifactsSummary;
  artifacts_data: Artifacts | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
}

// ──────────────── Full Artifacts (from backend schemas) ────────────────

export interface Artifacts {
  raw_reviews: Review[] | null;
  cleaned_data: Review[] | null;
  classification_results: ClassificationResult[] | null;
  findings: Finding[] | null;
  prd_draft: PRDDraft | null;
  test_case_drafts: TestCase[] | null;
}