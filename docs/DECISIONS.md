# DECISIONS.md

# App Review Insights

> Architecture & Product Decision Log

Version: **V1.0 (MVP)**

Status: Development

---

# Purpose

This document records the major architectural and product decisions made during the development of the MVP.

Each decision explains:

- The problem
- The chosen solution
- Alternatives considered
- Why the final decision was made

This document serves as an Architecture Decision Record (ADR).

---

# Decision 001

## Title

Support Apple App Store URL and local file import as dual inputs

### Status

Accepted (Revised — V1.1)

### Context

The interview task requires the system to analyze an existing application.

The README explicitly mandates:

> "The application must also support importing review data from a documented JSON or CSV format."

This ensures interviewers can evaluate the pipeline even without network access, with previously unseen datasets, or when review collection is constrained.

### Decision

The application accepts:

- Apple App Store URL (primary path — automatic collection via RSS Feed)
- Local JSON/CSV file import (secondary path — for offline evaluation or custom datasets)
- Optional analysis goal

The backend prioritizes imported data when both URL and file are provided.

### Alternatives

- URL only (rejected — fails README mandatory requirement)
- File only (rejected — reduces the demo impact of the automated workflow)

### Reason

Dual input satisfies the README requirement while preserving the automated collection workflow as the primary and most impressive user experience. The import path also serves as a fallback when network conditions or rate limits prevent live collection.

---

# Decision 002

## Title

Use an Artifact Pipeline instead of isolated AI features

### Status

Accepted

### Context

Many review analysis tools only output dashboards or isolated reports.

The interview task explicitly requires displaying both intermediate and final deliverables.

### Decision

The application is designed as a sequential artifact pipeline.

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

### Reason

Every artifact becomes the input to the next stage and remains visible in the UI.

This improves transparency and explainability.

---

# Decision 003

## Title

Preserve every intermediate artifact

### Status

Accepted

### Context

Most AI applications only display the final output.

The interview task requires displaying interim deliverables.

### Decision

No intermediate artifact is discarded.

The frontend displays:

- Raw Reviews
- Cleaned Data
- Classification Results
- Findings
- PRD Draft
- Test Case Drafts

### Reason

Users should understand how the AI reaches its conclusions.

---

# Decision 004

## Title

Use LLM-based semantic classification

### Status

Accepted

### Context

Traditional review analysis often relies on keyword rules.

Rule-based systems are difficult to maintain and adapt.

### Decision

Review classification is performed by an LLM.

Categories are generated semantically rather than through handcrafted rules.

### Alternatives

- Keyword matching
- Regular expressions
- Rule engine

### Reason

LLMs generalize better across different applications and domains.

---

# Decision 005

## Title

Generate Findings before generating the PRD Draft

### Status

Accepted

### Context

Generating a PRD directly from reviews reduces explainability.

### Decision

Introduce a Finding Extraction stage.

```text
Reviews

↓

Classification

↓

Findings

↓

PRD Draft
```

### Reason

Findings act as an interpretable bridge between raw user feedback and product planning.

---

# Decision 006

## Title

Generate a PRD Draft instead of a complete PRD

### Status

Accepted

### Context

The README specifies **PRD drafts**, not full production-ready PRDs.

The project is limited to two days.

### Decision

Generate a structured PRD Draft containing:

- Background
- Problem Statement
- Supporting Findings
- User Stories
- Functional Requirements
- Acceptance Criteria
- Priority

### Reason

This satisfies the interview requirement while remaining achievable within the MVP scope.

---

# Decision 007

## Title

Generate Test Case Drafts from the PRD Draft

### Status

Accepted

### Context

QA activities should validate product requirements rather than raw reviews.

### Decision

Test cases are generated from the PRD Draft.

```text
PRD Draft

↓

Test Case Drafts
```

### Reason

This mirrors a realistic software development lifecycle and maintains traceability.

---

# Decision 008

## Title

Maintain end-to-end traceability

### Status

Accepted

### Context

Users should understand why every artifact exists.

### Decision

Every downstream artifact references its upstream source.

```text
Raw Review

↓

Classification Result

↓

Finding

↓

PRD Draft

↓

Test Case Draft
```

### Reason

Traceability improves explainability, debugging, and confidence in AI-generated outputs.

---

# Decision 009

## Title

Use independent prompts for each AI stage

### Status

Accepted

### Context

Large prompts that perform multiple tasks are difficult to maintain and debug.

### Decision

Use one prompt per workflow stage.

Current prompts:

- Review Classification
- Finding Extraction
- PRD Draft Generation
- Test Case Draft Generation

### Reason

Single-responsibility prompts are easier to iterate, evaluate, and replace.

---

# Decision 010

## Title

Keep the MVP stateless

### Status

Accepted

### Context

Persistent storage is unnecessary for the interview MVP.

### Decision

Do not include:

- Database
- Redis
- Authentication
- Background queues

All artifacts remain in memory during execution.

### Reason

This minimizes implementation complexity and maximizes development speed.

---

# Decision 011

## Title

Prioritize workflow completion over feature richness

### Status

Accepted

### Context

Development time is limited to two days.

### Decision

Complete the entire workflow before adding enhancements.

Priority order:

1. Workflow execution
2. Artifact generation
3. UI presentation
4. Additional features

### Reason

A complete working pipeline demonstrates the project vision better than many unfinished features.

---

# Decision 012

## Title

Keep the architecture modular

### Status

Accepted

### Context

Future enhancements should not require major refactoring.

### Decision

Separate the project into:

- Collector
- Analyzer
- Planner
- Presentation

Each module owns a single responsibility.

### Reason

Improves maintainability and future extensibility.

---

# Deferred Decisions (V2)

The following topics are intentionally postponed until after the MVP.

- Google Play review support
- PDF / Markdown export
- Workflow streaming
- Prompt version management
- Retry mechanism
- Historical trend analysis
- Multi-language support

---

# Future Decisions (V3)

Potential future architectural decisions include:

- Multi-Agent orchestration
- LangGraph workflow engine
- RAG-based knowledge retrieval
- Competitor analysis
- Autonomous product planning
- Prompt evaluation framework

These are intentionally excluded from the MVP.

---

# Decision Summary

| ID | Decision |
|----|----------|
| ADR-001 | Apple App URL as the only input |
| ADR-002 | Artifact Pipeline architecture |
| ADR-003 | Preserve all intermediate artifacts |
| ADR-004 | LLM-based semantic classification |
| ADR-005 | Findings before PRD Draft |
| ADR-006 | Generate PRD Draft instead of full PRD |
| ADR-007 | Test Case Drafts from PRD Draft |
| ADR-008 | End-to-end traceability |
| ADR-009 | One prompt per AI stage |
| ADR-010 | Stateless MVP |
| ADR-011 | Workflow first, features second |
| ADR-012 | Modular architecture |

---

# End of Document