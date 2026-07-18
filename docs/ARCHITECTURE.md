# ARCHITECTURE.md

# App Review Insights

> Technical Architecture Design

Version: **V1.0 (MVP)**

Status: Development

---

# 1. Architecture Overview

## Objective

This document describes the technical architecture of the MVP.

The system is designed as a transparent AI workflow that transforms App Store reviews into structured product planning artifacts.

Unlike traditional review analytics tools, every intermediate artifact is preserved and displayed to the user.

---

## Design Principles

The architecture follows five principles.

- Workflow First
- Artifact Driven
- Explainability
- Modularity
- MVP First

---

# 2. MVP Architecture (V1)

The MVP consists of three layers.

```text
                    User
                      │
                      ▼
              Next.js Frontend
                      │
                  REST API
                      │
                      ▼
              FastAPI Backend
                      │
        ┌────────┬─────────┬─────────┐
        ▼        ▼         ▼
   Collector  Analyzer   Planner
                      │
                      ▼
               Structured Artifacts
                      │
                      ▼
              React User Interface
```

---

## Layer Responsibilities

### Frontend

Responsible for

- User interaction
- Workflow visualization
- Artifact presentation

---

### Backend

Responsible for

- Review collection
- Review transformation
- AI reasoning
- Artifact generation

---

### OpenAI API

Responsible for

- Semantic understanding
- Classification
- Findings extraction
- PRD Draft generation
- Test Case Draft generation

---

# 3. Artifact Pipeline

The entire application is an artifact generation workflow.

```text
Raw Reviews
      │
      ▼
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

Each artifact becomes the input of the next stage.

No artifact should be discarded.

---

# 4. Workflow Pipeline

The application executes as a sequential pipeline.

```text
Apple App URL
      │
      ▼
Review Collection
      │
      ▼
Review Cleaning
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
      │
      ▼
Presentation
```

The workflow runs automatically after the user clicks **Analyze**.

---

## Workflow State

Every stage reports its execution state.

```text
Pending
      │
      ▼
Running
      │
      ├────────► Failed
      │
      ▼
Completed
```

The frontend visualizes every stage in real time.

---

# 5. Backend Architecture

```text
backend/

├── api/
├── collector/
├── analyzer/
├── planner/
├── services/
├── prompts/
├── schemas/
└── main.py
```

---

## api/

Expose REST APIs.

Responsibilities

- Validate requests
- Trigger workflow
- Return artifacts

---

## collector/

Responsibilities

- Parse Apple URL
- Retrieve reviews
- Normalize review metadata

Output

Raw Reviews

---

## analyzer/

Responsibilities

- Clean review data
- Classify reviews
- Extract findings
- Validate evidence

Outputs

- Cleaned Data
- Classification Results
- Findings

---

## planner/

Responsibilities

Generate

- PRD Draft
- Test Case Drafts

Maintain traceability.

---

## prompts/

Contains all LLM prompts.

Each workflow stage owns one prompt.

---

## schemas/

Pydantic models.

Examples

- Review
- Finding
- PRD
- TestCase

---

## services/

Shared services.

Examples

- OpenAI Client
- Logger
- Config

---

# 6. Frontend Architecture

```text
frontend/

app/

components/

services/

types/

hooks/
```

---

## Main Interface

The application contains one primary workspace.

```text
----------------------------------------------------

Apple URL

Analysis Goal

Analyze

----------------------------------------------------

Workflow Progress

----------------------------------------------------

Artifact Tabs

Raw Reviews

Cleaned Data

Classification Results

Findings

PRD Draft

Test Case Drafts

----------------------------------------------------
```

Every artifact remains visible after generation.

---

# 7. Data Models

The workflow continuously transforms one structured artifact into another.

---

## Review

```json
{
  "review_id":"001",
  "rating":5,
  "content":"Great app."
}
```

---

## Classification Result

```json
{
  "review_id":"001",
  "primary_category":"Subscription Pricing Confusion",
  "sentiment":"negative",
  "summary":"User finds subscription tiers unclear",
  "confidence":0.94,
  "key_quote":"I thought it was free but they charged me"
}
```

Categories are discovered dynamically by the LLM — no fixed taxonomy.

---

## Finding

```json
{
  "finding_id":"F001",
  "title":"Users struggle with onboarding",
  "category":"Onboarding",
  "severity":"high",
  "description":"Many users find the first workout confusing and abandon during onboarding.",
  "supporting_review_ids":["12","35","41"],
  "supporting_excerpts":["Couldn't figure out how to start"],
  "support_count":3,
  "conflicting_evidence":[
    {
      "review_id":"23",
      "excerpt":"Super easy to get started",
      "contradiction":"Some users find onboarding intuitive"
    }
  ],
  "assumptions":["Users who struggled are likely first-time fitness app users"],
  "confidence":0.88,
  "uncertainty_notes":"Conflicting evidence from review 23",
  "evidence_sufficiency":"limited"
}
```

---

## PRD Draft

```json
{
  "title":"App Review Insights — PRD Draft",
  "app_name":"Workout for Women",
  "analysis_goal":"Focus on subscription conversion",
  "generated_at":"2025-07-18T10:00:00Z",
  "requirements":[
    {
      "req_id":"REQ-001",
      "title":"Simplify Subscription Pricing Display",
      "description":"Redesign the subscription page to show all tiers clearly.",
      "user_problem":"Users cannot understand pricing before subscribing",
      "business_value":"Improve subscription conversion rate",
      "priority":"P0",
      "target_version":"v1.1",
      "acceptance_criteria":["All subscription tiers visible on one page"],
      "source_finding_ids":["F001"],
      "source_review_ids":["12","35"],
      "effort_estimate":"M",
      "is_assumption":false
    }
  ],
  "version_plan":[
    {
      "version":"v1.1",
      "theme":"Fix Conversion Blockers",
      "release_goal":"Reduce subscription page abandonment",
      "requirement_ids":["REQ-001"],
      "rationale":"P0 items directly addressing top user complaints"
    }
  ]
}
```

---

## Test Case Draft

```json
{
  "title":"Verify onboarding",

  "related_requirement":"FR-001",

  "steps":[],

  "expected_result":"..."
}
```

---

# 8. API Design

The MVP exposes only two APIs.

---

## POST /api/analyze

Input

```json
{
    "url":"https://apps.apple.com/...",
    "goal":"Focus on onboarding",
    "import_data": {
        "reviews": []
    }
}
```

- `url`: App Store URL (optional if `import_data` is provided)
- `import_data`: pre-collected reviews in JSON format (optional if `url` is provided)
- `goal`: analysis objective (optional)
- At least one of `url` or `import_data` must be provided

Output (SSE Stream)

```text
data: {"stage":"collect","status":"done","data":{"total_collected":320}}
data: {"stage":"clean","status":"done","data":{"final_count":298}}
data: {"stage":"classify","status":"done","data":{"classification_results":[]}}
data: {"stage":"findings","status":"done","data":{"findings":[]}}
data: {"stage":"prd","status":"done","data":{"prd_draft":{}}}
data: {"stage":"tests","status":"done","data":{"test_case_drafts":[]}}
data: {"stage":"traceability","status":"done","data":{"traceability_report":{}}}
data: {"stage":"complete","status":"done","data":{"all_artifacts":{}}}
```

---

## GET /api/health

```json
{
    "status":"ok"
}
```

---

# 9. Project Structure

```text
app-review-insights/

frontend/
│
├── app/
├── components/
├── services/
└── types/

backend/
│
├── api/
├── collector/
├── analyzer/
├── planner/
├── prompts/
├── schemas/
├── services/
└── main.py

docs/
│
├── PROJECT_SPEC.md
├── ARCHITECTURE.md
├── TASKS.md
├── PROMPTS.md
└── DECISIONS.md
```

---

# 10. Development Principles

## Workflow First

The workflow defines the architecture.

---

## Artifact Driven

Every stage produces a reusable artifact.

---

## Explainability

Intermediate artifacts remain visible.

---

## Traceability

Every artifact references its upstream source.

---

## Simplicity

Avoid unnecessary infrastructure.

---

## MVP First

Complete the entire workflow before introducing advanced features.

---

# 11. V2 Architecture

Only after the MVP is complete.

Possible enhancements

- Workflow Streaming
- Markdown Export
- PDF Export
- Google Play Support
- Prompt Version Management
- Better Error Recovery

---

# 12. V3 Architecture

Potential future evolution.

```text
Workflow Engine

        │

        ▼

Agent Orchestrator

├── Collection Agent

├── Analysis Agent

├── Planning Agent

├── QA Agent

└── Validation Agent

        │

        ▼

Artifact Repository
```

Possible technologies

- LangGraph
- OpenAI Agents SDK
- CrewAI
- AutoGen

These technologies are intentionally excluded from the MVP.

---

# Architecture Summary

## V1 (Must Have)

✅ Apple Review Collection

✅ Review Cleaning

✅ Review Classification

✅ Findings Extraction

✅ PRD Draft Generation

✅ Test Case Draft Generation

✅ Workflow UI

---

## V2 (Enhancement)

- Export
- Streaming
- Google Play
- Prompt Management

---

## V3 (Future)

- Multi-Agent Workflow
- Embedding Retrieval
- Competitor Analysis
- Autonomous Product Planning

---

# End of Document