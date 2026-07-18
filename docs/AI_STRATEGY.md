# AI_STRATEGY.md

# App Review Insights

> AI Model Configuration, Prompt Strategy & Failure Handling

Version: **V1.0 (MVP)**

Status: Development

---

# 1. Purpose

This document records the complete AI strategy for the MVP:

- Model and provider used
- Model configuration
- Prompt design rationale
- Failure-handling strategy
- Anti-hallucination measures
- Token management for long inputs

This satisfies the README requirement:

> "The submission must document the model and provider used, the main prompts or tool definitions, model configuration, failure-handling strategy, and measures used to reduce hallucinations and unsupported conclusions."

---

# 2. Model & Provider

## Primary Configuration

| Field | Value |
|-------|-------|
| **Provider** | OpenAI-compatible API |
| **Default Model** | `gpt-4o-mini` |
| **API Endpoint** | `https://api.openai.com/v1` (configurable via `OPENAI_BASE_URL`) |
| **Authentication** | API Key via `OPENAI_API_KEY` environment variable |

## Alternative Providers

The system uses the OpenAI-compatible API format. Switching providers requires only changing `OPENAI_BASE_URL` and `LLM_MODEL`:

| Provider | Base URL | Model | Cost |
|----------|----------|-------|------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | $0.15/1M input |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` | $0.14/1M input |
| Qwen (Alibaba) | Configurable | `qwen-turbo` | Varies |

## Why gpt-4o-mini?

1. **Cost**: For the MVP demo analyzing ~300 reviews × 4 LLM calls, total cost is < $0.10
2. **JSON Mode**: Native support for `response_format: { type: "json_object" }`
3. **Speed**: Sub-second response for batch classification
4. **Availability**: Widely accessible via free API credits

We recommend using gpt-4o-mini for the interview demo. Upgrade to gpt-4o or claude-3.5-sonnet for production-quality PRDs.

---

# 3. Model Configuration

```python
# Every LLM call uses these defaults
config = {
    "temperature": 0.3,        # Low temperature for deterministic JSON output
    "max_tokens": 4096,        # Sufficient for structured JSON arrays
    "response_format": {       # Enforce JSON output (OpenAI-specific)
        "type": "json_object"
    },
    "timeout": 60,             # Seconds before timeout
}
```

## Why temperature = 0.3?

- Standard JSON classification: need consistent output, not creative
- Reduces hallucination risk compared to higher temperatures
- Still allows slight variation for dynamic category discovery

## Why max_tokens = 4096?

- Single prompt call handles up to 50 reviews at once
- Output is large JSON arrays of classification results
- Findings/PRD/Test Case generation outputs are also large structured objects

---

# 4. Prompt Design Rationale

## Why 4 Separate Prompts Instead of 1 Monolithic Prompt?

| Reason | Detail |
|--------|--------|
| **Debuggability** | Each stage can be inspected and fixed independently |
| **Traceability** | Clear artifact boundaries → easier to validate the chain |
| **Iterability** | Modify one prompt without risking side effects on others |
| **Token Efficiency** | Each prompt only receives relevant input, not the full pipeline state |
| **Failure Isolation** | If PRD generation fails, classification results are preserved |

## Prompt to Stage Mapping

| Prompt | Stage | Input Artifact | Output Artifact |
|--------|-------|---------------|-----------------|
| `review_classification.md` | Stage 3 | Cleaned Data | Classification Results |
| `finding_extraction.md` | Stage 4 | Classification Results | Findings |
| `prd_generation.md` | Stage 5-6 | Findings | PRD Draft + Version Plan |
| `test_case_generation.md` | Stage 7 | PRD Draft | Test Case Drafts |

---

# 5. Failure-Handling Strategy

## Retry Policy

```python
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds

Retry triggers:
- HTTP error (5xx, 429 rate limit)
- JSON parse failure (LLM returned non-JSON)
- Timeout
```

## Per-Stage Failure Strategy

| Stage | Failure Impact | Recovery Strategy |
|-------|---------------|-------------------|
| Collect | Pipeline can still proceed if import_data is available | Fall back to import_data; if none, abort with clear message |
| Clean | Deterministic logic, rarely fails | Mark problematic records, proceed with valid ones |
| Classify (LLM) | Batch failure | Retry 3 times; fall back to basic keyword heuristic for that batch; mark low confidence |
| Findings (LLM) | Full failure | Mark all findings with `evidence_sufficiency: "insufficient"`; return partial results |
| PRD (LLM) | Full failure | Return empty PRD structure with `status: "prd_generation_failed"` + error |
| Tests (LLM) | Full failure | Return empty test case list with error |
| Traceability | Deterministic logic, never fails | N/A — always runs successfully |

## Partial Failure Handling

If 3 of 5 batches succeed during classification:
- ✅ Return results for the 3 successful batches
- ⚠️ Mark the 2 failed batches in warnings
- 🏷️ Classify the failed reviews with a basic keyword heuristic (fallback strategy)
- 📊 Show `completion_rate: 60%` in the UI

This ensures the pipeline NEVER silently discards data.

---

# 6. Anti-Hallucination Measures

## Structural Safeguards

| Measure | Implementation |
|---------|---------------|
| **Low Temperature** | 0.3 reduces creative fabrication |
| **JSON Structured Output** | `response_format: json_object` constrains output format |
| **Explicit Source Links** | Every finding/requirement/test case must include `source_review_ids` |
| **Confidence Scores** | LLM must self-assess 0-1 confidence; low-confidence items are flagged |
| **Assumptions Field** | LLM must explicitly list what it INFERRED vs what users SAID |
| **Conflicting Evidence** | LLM must search for contradictions within the data |
| **Evidence Sufficiency** | Each finding rated as sufficient/limited/insufficient |

## Validation Safeguards (Stage 8 — Traceability)

| Check | What it catches |
|-------|----------------|
| Finding → Review link validation | LLM hallucinated supporting review IDs that don't exist |
| Requirement → Finding link validation | PRD requirements not backed by any finding |
| Test Case → Requirement link validation | Orphan test cases |
| Cross-reference count check | Single-review "consensus" presented as fact |

## Human-Reviewable Design

- Every artifact is visible in the UI
- Evidence excerpts are shown alongside conclusions
- Assumptions are color-coded (yellow) vs evidence-backed (green)
- Low-confidence items show a ⚠️ indicator

---

# 7. Token Management

## Batch Processing Strategy

```python
BATCH_SIZE = 50  # Reviews per LLM call

# For ~300 reviews:
# - 6 batches for classification
# - Each batch: ~3K input tokens (reviews) + ~2K output tokens (classification)
# - Total classification: ~30K tokens ($0.005 with gpt-4o-mini)

# Findings extraction: 1 call, ~4K input (classified summaries) + ~3K output
# PRD generation: 1 call, ~3K input + ~4K output
# Test case generation: 1 call, ~2K input + ~3K output

# Total per analysis: ~46K tokens ($0.007 with gpt-4o-mini)
```

## Token Limits

| Component | Max Input Tokens | Max Output Tokens |
|-----------|-----------------|-------------------|
| Classification (per batch) | ~6,000 (50 reviews × 120 chars avg) | 4,096 |
| Finding Extraction | ~8,000 (classification results) | 4,096 |
| PRD Generation | ~6,000 (findings) | 4,096 |
| Test Case Generation | ~6,000 (PRD) | 4,096 |

If input exceeds token limits, the system will truncate the oldest/lowest-rated reviews first (preserving most recent and extreme-rating reviews as highest-signal).

---

# 8. Prompt Storage & Versioning

All prompts are stored as Markdown files in `backend/prompts/`:

```text
backend/prompts/
├── review_classification.md    # v1.0 — Stage 3
├── finding_extraction.md        # v1.0 — Stage 4
├── prd_generation.md            # v1.0 — Stage 5-6
└── test_case_generation.md      # v1.0 — Stage 7
```

Each prompt file contains:
- System prompt (the actual prompt sent to the LLM)
- Input artifact format
- Expected output artifact format
- Failure response format
- Version number and change log

Prompt files are loaded at runtime, enabling prompt iteration without code changes.

---

# 9. Cost Estimate for Interview Demo

| Operation | Reviews | LLM Calls | Est. Tokens | Est. Cost (gpt-4o-mini) |
|-----------|---------|-----------|-------------|--------------------------|
| Classification | 300 | 6 | 30K | $0.0045 |
| Findings | — | 1 | 7K | $0.0011 |
| PRD | — | 1 | 7K | $0.0011 |
| Test Cases | — | 1 | 5K | $0.0008 |
| **Total** | | **9** | **49K** | **$0.0075** |

One full analysis costs less than 1 cent. This is negligible for the interview demo.

---

# 10. Secrets Management

```bash
# backend/.env.example — do NOT commit real values
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1   # Optional: change for other providers
LLM_MODEL=gpt-4o-mini                       # Optional: change model

# The .env file is in .gitignore
# Interviewers: copy .env.example to .env and fill in your API key
```

Secrets must NOT be committed to the repository. The `.env.example` file provides a template without real values.

---

# End of Document
