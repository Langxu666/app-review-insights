# PROJECT_SPEC.md

# App Review Insights

> AI-powered Product Discovery & Planning Workflow

Version: **V1.0 (MVP)**

Status: Development

---

# 1. Project Overview

## Background

Mobile applications receive thousands of App Store reviews every month.

These reviews contain valuable user feedback, bug reports, feature requests, and usability issues. However, manually converting these reviews into actionable product planning documents is time-consuming and inconsistent.

This project automates that workflow using Large Language Models.

Instead of building a traditional review analytics dashboard, the system transforms unstructured user feedback into structured product planning artifacts while exposing every intermediate step of the AI workflow.

---

# 2. Problem Statement

Most review analysis tools only provide:

- Sentiment analysis
- Keyword statistics
- Word clouds
- Basic dashboards

They rarely answer questions such as:

- What are users actually asking for?
- Which issues matter the most?
- Which reviews support each conclusion?
- What should be included in the next PRD?
- How should the proposed features be tested?

This project addresses those questions through a transparent AI workflow.

---

# 3. Project Goal

Build an AI-powered workflow capable of transforming an Apple App Store URL into structured product planning artifacts.

The application should automatically:

- Collect raw reviews
- Clean and normalize review data
- Classify reviews into semantic categories
- Extract evidence-backed findings
- Generate a PRD Draft
- Generate QA Test Case Drafts
- Maintain traceability across every artifact

The user only needs to provide:

- An Apple App Store URL
- (Optional) An analysis objective

---

# 4. MVP Scope (V1)

## Objective

Deliver a complete interview-ready MVP within **2 days**.

The MVP focuses exclusively on the core workflow.

---

## Included Features

### Review Collection

- Accept Apple App Store URL
- Retrieve raw reviews
- Preserve original review metadata

---

### Review Cleaning

Normalize collected reviews.

Tasks include:

- Remove duplicate reviews
- Normalize fields
- Standardize review format

---

### Review Classification

Use an LLM to classify reviews into semantic categories.

The LLM must discover categories dynamically based on the actual review content and the user's analysis goal. Do NOT rely on a fixed predefined category taxonomy.

Categories should emerge from what users are actually discussing in each specific app. When the user provides an analysis goal, classification should weight attention toward that goal.

---

### Findings Extraction

Summarize meaningful product insights from classified reviews.

Each finding must include:

- Summary
- Related category
- Supporting evidence (review IDs and excerpts)
- Confidence score
- Conflicting evidence (reviews that contradict this finding)
- Explicit assumptions (LLM-inferred conclusions not directly stated by users)
- Evidence sufficiency rating (sufficient / limited / insufficient)

---

### PRD Draft Generation

Generate a structured Product Requirements Document (PRD) Draft.

The draft should include:

- Background
- Problem Statement
- Supporting Findings
- User Stories
- Functional Requirements
- Acceptance Criteria
- Priority
- Target Version (grouping requirements into releases, e.g., v1.1 / v1.2 / v2.0)
- Assumption flags (marking requirements based on inferred rather than direct evidence)

---

### Test Case Draft Generation

Generate QA Test Case Drafts based on the generated PRD Draft.

Each test case should reference the corresponding functional requirement.

---

### Traceability

Maintain complete traceability across all workflow artifacts.

```text
Raw Review
      │
      ▼
Cleaned Data
      │
      ▼
Classification Result
      │
      ▼
Finding
      │
      ▼
PRD Draft
      │
      ▼
Test Case Draft
```

---

### Frontend

Display every workflow stage transparently.

The application should emphasize explainability instead of dashboard visualizations.

---

## Excluded Features

The following features are intentionally excluded from the MVP.

- User authentication
- Database persistence
- Redis
- Docker
- Background task queue
- Google Play support
- Embedding retrieval
- Historical trend analysis
- Competitor analysis
- Multi-user collaboration

These features should not delay MVP delivery.

---

# 5. User Workflow

```text
Paste Apple App URL
        │
        ▼
(Optional)
Enter Analysis Goal
        │
        ▼
Start Analysis
        │
        ▼
Collect Raw Reviews
        │
        ▼
Clean Reviews
        │
        ▼
Classify Reviews
        │
        ▼
Extract Findings
        │
        ▼
Generate PRD Draft
        │
        ▼
Generate Test Case Drafts
        │
        ▼
View Results
```

The workflow executes automatically from beginning to end.

---

# 6. Functional Requirements

The application consists of four logical modules.

## Module A — Review Collection

Responsibilities

- Parse Apple App Store URL
- Retrieve raw reviews
- Normalize review structure

---

## Module B — AI Analysis

Responsibilities

- Clean review data
- Classify reviews
- Extract findings
- Generate supporting evidence

---

## Module C — Planning Engine

Responsibilities

Generate:

- Classification Results
- Findings
- PRD Draft
- Test Case Drafts

Maintain traceability across every artifact.

---

## Module D — Presentation Layer

Responsibilities

Display:

- Raw Reviews
- Cleaned Data
- Classification Results
- Findings
- PRD Draft
- Test Case Drafts

---

# 7. Non-functional Requirements

## Explainability

Every finding must reference supporting review evidence.

---

## Traceability

Every downstream artifact must be traceable back to the original reviews.

---

## Generalization

The workflow should support any Apple App Store application.

No app-specific logic should exist.

---

## Modularity

Each workflow stage should have a single responsibility.

---

## Extensibility

Future workflow stages should be added without modifying existing ones.

---

# 8. Workflow Stages

```text
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
Result Presentation
```

Each stage consumes structured outputs from the previous stage.

---

# 9. User Interface

The interface should resemble an AI workspace rather than a BI dashboard.

```text
----------------------------------------------------

Apple App URL

[________________________________________]

Analysis Goal

[________________________________________]

                Analyze

----------------------------------------------------

Workflow

✓ Collect Reviews

✓ Clean Reviews

✓ Classify Reviews

✓ Extract Findings

✓ Generate PRD Draft

✓ Generate Test Case Drafts

----------------------------------------------------

Tabs

Raw Reviews

Cleaned Data

Classification Results

Findings

PRD Draft

Test Case Drafts

----------------------------------------------------
```

Users should always understand:

- What the AI is doing
- Which workflow stage is currently running
- Which evidence supports each conclusion

---

# 10. Artifact Pipeline

The application produces a sequence of intermediate and final artifacts.

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

Each artifact remains visible in the UI and serves as the input for the next stage.

---

# 11. Deliverables

The completed MVP should produce:

- ✅ Raw Reviews
- ✅ Cleaned Data
- ✅ Classification Results
- ✅ Findings
- ✅ PRD Draft
- ✅ Test Case Drafts
- ✅ Traceability Links

Each artifact should be independently viewable.

---

# 12. Development Constraints

## Time

Maximum development time:

**2 Days**

---

## Priority

Complete the end-to-end workflow before adding new features.

---

## Development Principle

Prefer simple, maintainable implementations.

Avoid premature optimization.

---

## AI-first

Leverage LLM semantic reasoning whenever practical instead of handcrafted rules.

---

# 13. Success Criteria

The MVP is considered complete when a user can:

1. Paste an Apple App Store URL.
2. Optionally specify an analysis goal.
3. Start the workflow.
4. Observe workflow progress.
5. View Raw Reviews.
6. View Cleaned Data.
7. View Classification Results.
8. Inspect Findings.
9. Review the generated PRD Draft.
10. Review the generated Test Case Drafts.
11. Understand traceability between all generated artifacts.

No manual preprocessing should be required.

---

# 14. V2 Enhancements

Only begin after the MVP is complete.

Potential enhancements include:

- Google Play support
- Streaming workflow execution
- Markdown / PDF export
- Prompt version management
- Multi-language support
- Historical trend analysis
- Release note generation
- Jira integration
- Notion export

---

# 15. V3 Future Vision

Potential future evolution:

- Multi-agent orchestration
- Competitor analysis
- Embedding-based semantic retrieval
- Product roadmap optimization
- Autonomous product planning assistant
- Risk assessment
- Cost estimation

These ideas are intentionally excluded from the interview MVP.

---

# End of Document