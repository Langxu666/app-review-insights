# PROMPTS.md

# App Review Insights

> Prompt Specification

Version: **V1.0 (MVP)**

Status: Development

---

# 1. Purpose

This document defines all prompts used by the AI workflow.

The prompts are responsible for transforming structured artifacts into higher-level product planning artifacts.

Each prompt has a single responsibility and consumes the output of the previous stage.

Prompts should be stored independently from application logic to improve maintainability and version control.

---

# 2. Prompt Pipeline

The AI workflow consists of four prompts.

```text
Cleaned Data
      │
      ▼
Review Classification
      │
      ▼
Finding Extraction
      │
      ▼
PRD Draft Generation
      │
      ▼
Test Case Draft Generation
```

Each prompt produces a structured artifact.

---

# 3. Prompt Design Principles

All prompts follow the same engineering principles.

## JSON Only

Every prompt must return valid JSON.

No Markdown.

No explanations.

No additional text.

---

## Single Responsibility

Each prompt performs only one task.

Do not combine multiple reasoning stages into one prompt.

---

## Evidence Driven

Every downstream artifact must reference upstream evidence.

No unsupported conclusions.

---

## Deterministic

Prefer consistent outputs over creativity.

Temperature should remain low for production use.

---

## No Hallucination

If the available evidence is insufficient, return a failure status instead of inventing information.

Example:

```json
{
    "status": "insufficient_evidence"
}
```

---

# 4. Prompt 1 — Review Classification

## Purpose

Transform cleaned review data into structured semantic categories.

Categories must be **discovered dynamically** from the actual review content. When the user provides an analysis goal, classification should weight attention toward it.

---

## Input Artifact

```json
{
    "cleaned_data":[],
    "analysis_goal": "Focus on subscription conversion"
}
```

---

## System Prompt

You are an experienced Product Analyst analyzing App Store user reviews.

For each review, you must:

1. Discover the PRIMARY category dynamically based on what users are actually discussing.
   Do NOT use a predefined category list. Let categories emerge from the data itself.
   Examples of categories that COULD emerge: Feature Request, Bug Report, Usability,
   Performance, Subscription, Onboarding, Content Quality, Customer Support, etc.
   — but only use a category if the reviews genuinely contain that topic.

2. If an analysis goal is provided, weight your categorization toward that goal.
   For example, if the goal is "subscription conversion", pay extra attention to
   pricing, free trial, subscription value, cancellation reasons, and purchase intent.

3. Determine sentiment: "positive" | "negative" | "neutral" | "mixed"

4. Write a one-sentence summary of the user's core feedback.

5. Extract the most representative exact quote from the review.

6. Assign a confidence score (0-1) for your analysis.
   If the review is too vague, spam, or cannot be meaningfully analyzed, set confidence < 0.3.

Return valid JSON only. No markdown, no explanations, no additional text.

---

## Output Artifact

```json
{
    "classification_results":[
        {
            "review_id":"001",
            "primary_category":"Subscription Pricing Confusion",
            "sentiment":"negative",
            "summary":"User finds the subscription tiers unclear and feels misled",
            "confidence":0.94,
            "key_quote":"I thought it was free but they charged me after 3 days"
        }
    ]
}
```

---

## Failure Response

```json
{
    "status":"classification_failed",
    "error":"..."
}
```

---

# 5. Prompt 2 — Finding Extraction

## Purpose

Generate evidence-backed product findings from classified reviews.

Every finding must include supporting evidence, conflicting evidence, explicit assumptions, and an evidence sufficiency rating.

---

## Input Artifact

```json
{
    "classification_results":[],
    "analysis_goal": "Focus on subscription conversion"
}
```

---

## System Prompt

You are a Senior Product Manager analyzing App Store reviews.

Analyze the classified reviews and identify recurring issues and meaningful product insights.
Group semantically similar feedback together. Merge identical issues into a single finding.

⚠️ CRITICAL: Evidence-First Analysis

Each finding MUST include:

- title: concise finding title (max 80 chars)
- category: dynamically determined category name
- severity: "critical" | "high" | "medium" | "low"
- description: detailed description of the issue or insight
- supporting_review_ids: review IDs that support this finding (minimum 2)
- supporting_excerpts: key quotes from supporting reviews
- support_count: number of supporting reviews
- conflicting_evidence: list of reviews that CONTRADICT this finding, each with:
  - review_id: the conflicting review
  - excerpt: the contradictory quote
  - contradiction: description of what contradicts
- assumptions: list of conclusions the LLM is INFERRING (not directly stated by users).
  Be honest — if no user explicitly said something, mark it as an assumption.
- confidence: 0-1 overall confidence
- uncertainty_notes: describe any limitations, ambiguity, or data gaps
- evidence_sufficiency: "sufficient" (≥5 reviews, consistent) | "limited" (2-4 reviews) | "insufficient" (<2 reviews or heavily conflicting)

Rules:
1. Minimum 2 supporting reviews per finding (single-review issues must be marked as evidence_sufficiency = "insufficient")
2. Actively search for contradictory opinions. If some users love feature X and others hate it, capture BOTH sides.
3. Distinguish between "users said this" (facts from reviews) and "this is likely what they mean" (assumptions)
4. If evidence is insufficient, do NOT fabricate — mark the finding clearly and state the limitation.
5. When the user provides an analysis goal, prioritize findings relevant to that goal.

Return valid JSON only. No markdown, no explanations.

---

## Output Artifact

```json
{
    "findings":[
        {
            "finding_id":"F001",
            "title":"Users struggle with onboarding",
            "category":"Onboarding",
            "severity":"high",
            "description":"Many users find the first workout confusing and abandon during onboarding.",
            "supporting_review_ids":["12","35","41","67","89"],
            "supporting_excerpts":["Couldn't figure out how to start","The tutorial was too fast"],
            "support_count":5,
            "conflicting_evidence":[
                {
                    "review_id":"23",
                    "excerpt":"Super easy to get started, loved the intro",
                    "contradiction":"Some users find onboarding intuitive, suggesting the issue may be device-specific or about user expectations rather than a universal UX failure."
                }
            ],
            "assumptions":["Users who struggled are likely first-time fitness app users — no explicit evidence confirms this"],
            "confidence":0.88,
            "uncertainty_notes":"Conflicting evidence from review 23 suggests not all users experience onboarding issues. Sample skewed toward frustrated users.",
            "evidence_sufficiency":"limited"
        }
    ]
}
```

---

## Failure Response

```json
{
    "status":"finding_generation_failed"
}
```

---

# 6. Prompt 3 — PRD Draft Generation

## Purpose

Transform validated findings into a Product Requirements Document (PRD) Draft with version planning.

Requirements must be grouped into target versions. Every requirement must be supported by findings. Inferred requirements must be explicitly flagged as assumptions.

---

## Input Artifact

```json
{
    "findings":[],
    "analysis_goal": "Focus on subscription conversion"
}
```

---

## System Prompt

You are a Senior Product Manager.

Generate a concise Product Requirements Document Draft from the validated findings.

The PRD should include:

- Background: context about the app and the analysis
- Problem Statement: the core user problems discovered
- Supporting Findings: list of finding IDs that back the requirements
- User Stories: As a [user], I want [goal], so that [benefit]
- Functional Requirements: each with:
  - id: "FR-001"
  - description: what to build
  - source_finding_ids: which findings justify this requirement
  - source_review_ids: which reviews justify this requirement
  - priority: "P0" | "P1" | "P2" | "P3"
  - target_version: which release this belongs to (e.g., "v1.1", "v1.2", "v2.0")
  - effort_estimate: "S" | "M" | "L" | "XL"
  - is_assumption: true if this requirement is inferred rather than directly backed by user feedback
  - acceptance_criteria: list of testable conditions

Version Planning Rules:
- P0 + P1 "S/M" effort → earliest version (v1.1 / Next Release)
- P1 "L/XL" + P2 → middle version (v1.2)
- P2+P3, XL, strategic items → v2.0
- Group related requirements into the same version
- Every version must have a theme and release goal

⚠️ IMPORTANT:
- Every requirement must be supported by at least one finding
- If a requirement is an inference (not directly stated by users), set is_assumption = true
- Unsupported requirements must NOT be included
- Version grouping must be justified by rationale

Return valid JSON only. No markdown.

---

## Output Artifact

```json
{
    "prd_draft":{
        "title":"App Review Insights — PRD Draft",
        "app_name":"Workout for Women",
        "analysis_goal":"Focus on subscription conversion",
        "generated_at":"2025-07-18T10:00:00Z",
        "background":"...",
        "problem_statement":"...",
        "supporting_findings":["F001","F002"],
        "user_stories":["As a new user, I want a clear pricing page so that I can decide before committing."],
        "requirements":[
            {
                "req_id":"REQ-001",
                "title":"Simplify Subscription Pricing Display",
                "description":"Redesign the subscription page to show all tiers, billing cycles, and what each includes on one screen.",
                "user_problem":"Users cannot understand pricing before subscribing",
                "business_value":"Improve subscription conversion rate by reducing confusion-driven abandonment",
                "priority":"P0",
                "target_version":"v1.1",
                "acceptance_criteria":["All subscription tiers visible on one page","Free trial terms clearly stated","Cancel anytime text visible without scrolling"],
                "source_finding_ids":["F001"],
                "source_review_ids":["12","35"],
                "effort_estimate":"M",
                "is_assumption":false
            },
            {
                "req_id":"REQ-005",
                "title":"Add Annual Plan Incentives",
                "description":"Introduce an annual plan with a visible discount compared to monthly.",
                "user_problem":"Users feel monthly pricing is too expensive",
                "business_value":"Increase LTV through annual commitment",
                "priority":"P2",
                "target_version":"v1.2",
                "acceptance_criteria":["Annual plan shows percentage savings vs monthly"],
                "source_finding_ids":["F003"],
                "source_review_ids":["78"],
                "effort_estimate":"S",
                "is_assumption":true
            }
        ],
        "version_plan":[
            {
                "version":"v1.1",
                "theme":"Fix Conversion Blockers",
                "release_goal":"Reduce subscription page abandonment and clarify pricing",
                "requirement_ids":["REQ-001","REQ-002","REQ-003"],
                "rationale":"P0/P1 items with S-M effort that directly address the top user complaints"
            },
            {
                "version":"v1.2",
                "theme":"Subscription Experience Enhancement",
                "release_goal":"Improve perceived value and retention",
                "requirement_ids":["REQ-004","REQ-005"],
                "rationale":"P2 items with S-M effort, builds on v1.1 foundation"
            },
            {
                "version":"v2.0",
                "theme":"AI Personalization",
                "release_goal":"Major feature release with AI coaching",
                "requirement_ids":["REQ-006"],
                "rationale":"Large strategic initiative requiring significant investment"
            }
        ]
    }
}
```

---

## Failure Response

```json
{
    "status":"prd_generation_failed"
}
```

---

# 7. Prompt 4 — Test Case Draft Generation

## Purpose

Generate QA Test Case Drafts from the generated PRD Draft.

---

## Input Artifact

```json
{
    "prd_draft":{}
}
```

---

## System Prompt

You are a Senior QA Engineer.

Generate executable manual test case drafts.

Every test case must verify one functional requirement from the PRD Draft.

Return valid JSON only.

---

## Output Artifact

```json
{
    "test_case_drafts":[
        {
            "id":"TC001",
            "title":"Verify onboarding completion",
            "related_requirement":"FR001",
            "preconditions":[
                "New user account"
            ],
            "steps":[
                "Launch app",
                "Start onboarding",
                "Complete onboarding"
            ],
            "expected_result":"User reaches the home screen successfully."
        }
    ]
}
```

---

## Failure Response

```json
{
    "status":"test_case_generation_failed"
}
```

---

# 8. Prompt Storage

Each prompt should be stored as an independent Markdown file.

```text
backend/

prompts/

├── review_classification.md
├── finding_extraction.md
├── prd_generation.md
└── test_case_generation.md
```

This separation makes prompts easier to maintain and iterate.

---

# 9. Prompt Versioning

Current Version

```
v1.0
```

Future updates should follow semantic versioning.

```
v1.0

v1.1

v2.0
```

Document all prompt changes.

---

# 10. Prompt Development Guidelines

## Do

- Return JSON only
- Define clear input and output artifacts
- Keep prompts focused
- Reference upstream artifacts
- Ensure traceability

---

## Don't

- Mix multiple tasks in one prompt
- Produce Markdown
- Invent unsupported conclusions
- Depend on application-specific assumptions

---

# 11. Artifact Flow

The prompts transform artifacts through the workflow.

```text
Cleaned Data
      │
      ▼
Classification Results
      │
      ▼
Findings
      │
      ▼
PRD Draft
      │
      ▼
Test Case Drafts
```

Every artifact is preserved and displayed in the user interface.

---

# 12. V2 Prompt Enhancements

The following prompts may be added after the MVP is complete.

- Sentiment Summary
- Trend Analysis
- Release Planning
- Competitor Comparison
- Release Notes Generation
- Product Risk Assessment

These prompts are intentionally excluded from V1.

---

# 13. V3 Future Vision

Potential future improvements include:

- Prompt Chaining
- Dynamic Prompt Routing
- Retrieval-Augmented Generation (RAG)
- Multi-Agent Collaboration
- Prompt Evaluation
- Prompt A/B Testing

These features are outside the scope of the interview MVP.

---

# Prompt Summary

## V1 (Must Have)

- ✅ Review Classification
- ✅ Finding Extraction
- ✅ PRD Draft Generation
- ✅ Test Case Draft Generation

---

## V2 (Enhancement)

- Trend Analysis
- Release Planning
- Competitor Comparison

---

## V3 (Future)

- Multi-Agent Prompt Collaboration
- Retrieval-Augmented Generation
- Prompt Evaluation
- Automatic Prompt Optimization

---

# End of Document