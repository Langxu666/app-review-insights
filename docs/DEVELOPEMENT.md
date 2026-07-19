# App Review Insights

> V1.1 Development Roadmap — Interview Demo Edition

Version: **V1.1**

Status: Planning

---

# 1. Objective

The MVP (V1.0) successfully demonstrates an end-to-end AI workflow that transforms App Store reviews into product planning artifacts. It works, but the demo experience has critical gaps.

Version **V1.1** fixes the demo-blocking issues and adds two high-impact polish items. Everything else is deferred to V2.

**Scope for V1.1:**

- **🔴 P0 — Critical Fixes**: streaming progress, conflicting_evidence schema unification, request cancellation, import_data backend integration
- **🟡 P1 — Demo Polish**: PRD export (PDF/DOCX/Markdown), interactive traceability

---

# 2. Development Strategy

## 🔴 P0 — Critical Fixes (Must Complete)

These issues block a polished interview demo or risk runtime failures during demo:

| # | Task | Source | Impact |
|---|------|--------|--------|
| P0-1 | Synchronous → SSE streaming | Code review C1 | 2-5 min blank wait is the biggest UX gap |
| P0-2 | `conflicting_evidence` schema unification | Code review C2 | LLM may output objects, schema expects strings, frontend may break |
| P0-3 | Request cancellation (AbortController) | Code review C3 | Double-submit poisons state; no way to abort stuck analysis |
| P0-4 | `import_data` backend integration | Code review C4 | Module does NOT exist — must be created AND wired |

## 🟡 P1 — Demo Polish

| # | Task | Why |
|---|------|-----|
| P1-3 | PRD export (PDF/DOCX/Markdown) | Give the interviewer a tangible deliverable to take away |
| P1-4 | Interactive traceability | Let the interviewer click Finding → Review back-and-forth; demonstrates understanding of the pipeline |

## ❌ Deferred (was in original V1.1 plan, removed from this scope)

| # | Task | Reason |
|---|------|--------|
| P1-1 | Frontend data entry (textarea + toggle) | P0-4 gives backend support; frontend entry can wait |
| P1-2 | Full review collection (scraper) | RSS ~150 reviews is sufficient for an interview demo |
| P1-5 | Prompt optimization (few-shot + goal weighting) | Nice-to-have but not demo-blocking |
| P1-6 | Deployment improvements | Local dev is fine for an interview |

---

# 3. Updated Architecture

The Artifact Pipeline remains unchanged. New layers are added for streaming, cancellation, schema consistency, import, export, and traceability.

```text
                      Data Sources
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       App Store URL   import_data   File Upload
      (apple_collector)  (P0-4)      (V2+)
              │            │            │
              └────────────┼────────────┘
                           ▼
                    Raw Reviews
                           ▼
                      Cleaned Data
                           ▼
                Classification Results
                           ▼
                        Findings  ←── conflicting_evidence now ALWAYS List[str]
                           ▼       (normalized from LLM objects at extraction time)
                       PRD Draft  ──→ Export (PDF/DOCX/Markdown) — P1-3
                           ▼
                  Test Case Drafts
                           ▼
              Interactive Traceability (P1-4)
       Review ←→ Finding ←→ Requirement ←→ Test Case
```

<aside>
⚠️ **Schema Contract (conflicting_evidence)**

After P0-2 fix, the pipeline contract is:
- **Prompt**: asks for review IDs only (plain strings), NOT objects
- **Pydantic (backend)**: `conflicting_evidence: Optional[List[str]]`
- **Frontend**: `conflicting_evidence: string[] | null` — renders by looking up review in reviewMap by ID
- **Normalization** (finding_extractor.py): if LLM still returns objects like `{review_id: "...", excerpt: "..."}`, extract `.review_id` and log a warning
</aside>

### Data Source Implementation Status

| Source | Module | Status |
|--------|--------|--------|
| Apple App Store URL | `collector/apple_collector.py` | ✅ Existing |
| JSON/CSV text import | `collector/data_importer.py` | 🔴 Module does NOT exist — P0-4 creates it from scratch |
| File upload (multipart) | Not yet implemented | 🔴 P2 — deferred to V2 |

---

# 4. P0-1 — Streaming Workflow Progress (CRITICAL)

## Current State

`POST /api/analyze` returns a synchronous `WorkflowResponse`. The entire workflow runs server-side before any data reaches the frontend. The user sees a static spinner for 2-5 minutes with no visibility into which stage is running.

## Decision: content-negotiation (single endpoint)

**Decision**: Modify `POST /api/analyze` to support both synchronous JSON response AND SSE streaming via the `Accept` header, rather than adding a separate endpoint.

**Rationale**:
- Single endpoint = simpler API surface
- `Accept: application/json` → synchronous (backward-compatible)
- `Accept: text/event-stream` → SSE streaming (new behavior)
- No breaking change for existing callers

## Backend Architecture

```text
POST /api/analyze
    │
    ├── Accept: application/json
    │       └── WorkflowEngine.run() → WorkflowResponse (existing behavior)
    │
    └── Accept: text/event-stream
            └── WorkflowEngine.run_streaming() → SSE stream
```

## Tasks

### Task P0-1.1 — Add SSE streaming to workflow

Modify `api/workflow.py`:

```python
import asyncio
from fastapi.responses import StreamingResponse

class WorkflowEngine:
    async def run_streaming(self, url: str, goal: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Execute workflow and yield SSE events for each stage transition."""
        yield f"data: {json.dumps({'event': 'start', 'stages': list(self.STAGE_ORDER)})}\n\n"

        reviews = await self._run_stage_async("collect", lambda: collect_reviews(url))
        yield f"data: {json.dumps({'stage': 'collect', 'status': 'completed', 'count': len(reviews) if reviews else 0})}\n\n"

        # ... repeat for each stage ...

        yield f"data: {json.dumps({'event': 'complete', 'artifacts_data': self._build_artifacts_data()})}\n\n"
```

### Task P0-1.2 — Add content-negotiation to routes

Modify `api/routes.py`:

```python
from fastapi import Header

@router.post("/api/analyze")
def analyze_reviews(request: AnalyzeRequest, accept: str = Header(default="application/json")):
    _validate_app_store_url(request.url)
    engine = WorkflowEngine()

    if "text/event-stream" in accept:
        return StreamingResponse(
            engine.run_streaming(request.url, request.goal),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
    else:
        return engine.run(url=request.url, goal=request.goal)
```

### Task P0-1.3 — Frontend: EventSource integration

Modify `frontend/services/api.ts`:

```typescript
export function analyzeReviewsStreaming(
  url: string,
  goal?: string,
  signal?: AbortSignal,
): {
  eventSource: EventSource;
  promise: Promise<AnalyzeResponse>;
} {
  // Build body, open EventSource with POST
  // (fetch + ReadableStream reader for SSE parsing)
}
```

Modify `frontend/app/page.tsx`:
- Replace `analyzeReviews()` with the streaming variant
- Update stage states in real time as SSE events arrive
- Use `AbortController` (P0-3) to cancel the EventSource on unmount or re-submit

---

# 5. P0-2 — conflicting_evidence Schema Unification (CRITICAL)

## Current State (BROKEN)

Three components disagree on what `conflicting_evidence` is:

| Component | Expected Type | Location |
|-----------|--------------|----------|
| Prompt | Field description is ambiguous — says "list of reviews" without specifying format; example shows empty array `[]` | `prompts/finding_extraction.md` |
| Pydantic Schema | `Optional[List[str]]` (string IDs) | `schemas/finding.py:26` |
| Frontend | `string[]` — rendered via `reviewMap.get(evidenceId)` | `FindingsList.tsx:117` |
| Normalizer | Converts objects → strings at runtime (silent, no log warning) | `finding_extractor.py:138-147` |

The normalizer in `finding_extractor.py` currently salvages mismatches, but it's a silent band-aid. When the LLM outputs objects like `{review_id: "123", excerpt: "..."}`, the normalizer extracts the ID without any warning — making it impossible to detect that the prompt needs fixing.

## Decision: Unify to `List[str]` (review IDs only)

**Rationale**:
- `List[str]` is simpler to validate and transmit
- Frontend already renders by looking up review IDs → full review content is available client-side
- The `FindingCard` expanded view already shows full review content from `reviewMap`, so passing structured objects to the frontend is redundant

## Tasks

### Task P0-2.1 — Update prompt to explicitly request string IDs

Modify `backend/prompts/finding_extraction.md`.

Update the field description (current is vague):
```markdown
- conflicting_evidence: list of review IDs (strings) that CONTRADICT this finding.
  Example: ["14308859067", "14307471563"]
  Do NOT include full review content — just the review ID string.
```

Update the Output Format example (current shows empty `[]`, which provides no format guidance):
```json
{
    "findings": [{
        ...
        "conflicting_evidence": ["14308859067", "14307471563"],
        ...
    }]
}
```

### Task P0-2.2 — Add explicit log warning in normalizer

Modify `backend/analyzer/finding_extractor.py` in the normalizer block (L138-147). When an object is detected, upgrade from silent conversion to a logged warning:

```python
if isinstance(item, dict):
    rid = item.get("review_id") or item.get("id", "")
    logger.warning(
        f"conflicting_evidence contained object instead of string ID. "
        f"Extracted review_id={rid}. Prompt may need updating."
    )
    if rid:
        normalized_ce.append(str(rid))
```

### Task P0-2.3 — No frontend changes needed

The frontend already handles `string[]` correctly. After P0-2.1, LLM output should match. The normalizer (P0-2.2) is defense-in-depth.

---

# 6. P0-3 — Request Cancellation (CRITICAL)

## Current State

- **Frontend**: `handleAnalyze` has no `AbortController`. If the user clicks "分析" twice, two in-flight requests race and the earlier response can overwrite the later one's state.
- **Backend**: `WorkflowEngine.run()` has no client disconnect detection. If the user closes the tab, the workflow keeps running and consuming LLM tokens.

## Tasks

### Task P0-3.1 — Frontend: AbortController

Modify `frontend/app/page.tsx`:

```typescript
const abortRef = useRef<AbortController | null>(null);

const handleAnalyze = useCallback(async () => {
  // Cancel previous request if any
  if (abortRef.current) {
    abortRef.current.abort();
  }
  const controller = new AbortController();
  abortRef.current = controller;

  setIsAnalyzing(true);
  setResponse(null);
  setError(null);

  try {
    const result = await analyzeReviews(url.trim(), goal?.trim() || undefined, controller.signal);
    setResponse(result);
    // ...
  } catch (err) {
    if (controller.signal.aborted) return; // Silently ignore cancellations
    // ... existing error handling
  } finally {
    setIsAnalyzing(false);
    abortRef.current = null;
  }
}, [url, goal]);
```

### Task P0-3.2 — API layer: signal passthrough

Modify `frontend/services/api.ts`:

```typescript
export async function analyzeReviews(
  url: string,
  goal?: string,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const { data } = await api.post<AnalyzeResponse>("/api/analyze", { url, goal }, { signal });
  return data;
}
```

### Task P0-3.3 — Backend: client disconnect detection

Modify `backend/api/workflow.py`. After SSE streaming is implemented (P0-1), FastAPI's `StreamingResponse` automatically detects client disconnects via `asyncio.CancelledError`. For the synchronous path, add a `Request` parameter and check `await request.is_disconnected()` between stages:

```python
from fastapi import Request

def run(self, url: str, goal: Optional[str] = None, request: Optional[Request] = None) -> WorkflowResponse:
    for stage_name in self.STAGE_ORDER:
        if request:
            # Check if client disconnected between stages
            # (sync path — check before each LLM call to avoid wasting tokens)
            pass
        # ... run stage ...
```

For the streaming path (P0-1), FastAPI handles this automatically.

---

# 7. P0-4 — import_data Backend Integration (CRITICAL)

## Current State (BROKEN)

The `import_data` feature has zero implementation:

- `collector/data_importer.py` **does NOT exist** — the entire module needs to be created from scratch
- `AnalyzeRequest` in `api/workflow.py` has NO `import_data` field — `url` is required (`Field(...)`)
- `WorkflowEngine.run()` accepts only `url` and `goal` — no `import_data` parameter
- `routes.py` validation requires an App Store URL — no branch for raw data

This blocks the ability to paste review data (JSON/CSV) directly, which is valuable for demos where the App Store endpoint may be slow or unreachable.

## Tasks

### Task P0-4.0 — Create data_importer module

Create `backend/collector/data_importer.py` with a function that parses JSON and CSV review data strings into `List[Review]`:

```python
# Expected signature
def import_reviews(data: str) -> List[Review]:
    """
    Parse JSON or CSV review data string.

    JSON formats accepted:
      - Array of review objects: [{"id": ..., "rating": ..., ...}, ...]
      - Object with reviews key: {"reviews": [...]}

    CSV: first row is header, maps columns by name (id, rating, title, content, author, date, version, app_id).
    """
```

The module must:
- Auto-detect format (JSON vs CSV) by first non-whitespace character
- Map raw fields to the `Review` schema
- Validate required fields (`content` at minimum)
- Log and skip malformed rows rather than failing the entire import

### Task P0-4.1 — Add `import_data` to AnalyzeRequest

Modify `backend/api/workflow.py`:

```python
class AnalyzeRequest(BaseModel):
    url: Optional[str] = Field(None, description="App Store URL (optional if import_data provided)")
    goal: Optional[str] = Field(None, description="Optional analysis goal")
    import_data: Optional[str] = Field(None, description="JSON/CSV review data string (optional if url provided)")
```

Add a model validator to ensure at least one of `url` or `import_data` is provided.

### Task P0-4.2 — Wire into WorkflowEngine.run()

Modify `backend/api/workflow.py` `WorkflowEngine.run()`:

```python
def run(self, url: Optional[str] = None, goal: Optional[str] = None,
        import_data: Optional[str] = None) -> WorkflowResponse:

    if import_data:
        # Skip App Store collection: use imported data
        from collector.data_importer import import_reviews
        reviews = self._run_stage("collect", lambda: import_reviews(import_data), "reviews")
    elif url:
        reviews = self._run_stage("collect", lambda: collect_reviews(url), "reviews")
    else:
        return self._finish(WorkflowStatus.FAILED, "Either url or import_data must be provided")
```

### Task P0-4.3 — Update routes validation

Modify `backend/api/routes.py`:

```python
@router.post("/api/analyze", response_model=WorkflowResponse)
def analyze_reviews(request: AnalyzeRequest) -> WorkflowResponse:
    if not request.url and not request.import_data:
        raise HTTPException(status_code=400, detail="Either url or import_data must be provided")
    if request.url:
        _validate_app_store_url(request.url)
    engine = WorkflowEngine()
    result = engine.run(url=request.url, goal=request.goal, import_data=request.import_data)
    return result
```

---

# 8. Milestone P1-3 — PRD Export (P1)

## Objective

Allow users to export the generated PRD Draft as a tangible deliverable. This is a high-impact demo feature — the interviewer walks away with a PDF they can reference.

## Target

```text
PRD Draft
    ↓
PDF / DOCX / Markdown
```

## Tasks

| Task | Description | Est. |
|------|-------------|------|
| P1-3.1 | Design export template — layout, branding, section ordering | 30min |
| P1-3.2 | Generate PDF via `xhtml2pdf` or `weasyprint` — HTML template → PDF | 45min |
| P1-3.3 | Generate DOCX via `python-docx` — structured document with headings, tables | 45min |
| P1-3.4 | Generate Markdown — simple template rendering (fastest path) | 20min |
| P1-3.5 | Add export buttons to frontend PRD tab — dropdown with 3 format options | 30min |

Backend adds a new endpoint:

```python
@router.get("/api/export/prd/{format}")
def export_prd(format: str = "pdf") -> FileResponse:
    """Export the last generated PRD as PDF, DOCX, or Markdown."""
```

---

# 9. Milestone P1-4 — Interactive Traceability (P1)

## Objective

Improve artifact navigation so users can drill down through the analysis chain. This demonstrates a deep understanding of the pipeline to the interviewer.

## Navigation Flow

```text
PRD Draft → Requirement → Finding → Review
```

## Behavior

- Clicking a `source_finding_ids` link in a Requirement navigates to the Findings tab with that finding scrolled into view and highlighted
- Clicking a `source_review_ids` / `supporting_review_ids` link navigates to the Reviews tab with that review selected
- Back-navigation: clicking a highlighted item's "upstream" link goes back to where you came from

## Tasks

| Task | Description | Est. |
|------|-------------|------|
| P1-4.1 | Add `activeTab` / `highlightedItemId` state management to `page.tsx` | 30min |
| P1-4.2 | Make Finding IDs, Review IDs, and Requirement IDs clickable links across all tab components | 45min |
| P1-4.3 | Implement scroll-to-item + highlight animation when navigating to another tab | 30min |

---

# 10. Development Priority & Time Budget

## 🔴 P0 — Must Fix (before any demo)

| # | Task | Est. Effort |
|---|------|-------------|
| P0-1 | SSE streaming workflow progress | ~3h |
| P0-2 | conflicting_evidence schema unification | ~30min |
| P0-3 | Request cancellation (AbortController) | ~1h |
| P0-4 | import_data backend integration (create module + wire) | ~2h |
| **P0 Total** | | **~6.5h** |

## 🟡 P1 — Demo Polish

| # | Task | Est. Effort |
|---|------|-------------|
| P1-3 | PRD export (PDF/DOCX/Markdown) | ~2h |
| P1-4 | Interactive traceability | ~1.5h |
| **P1 Total** | | **~3.5h** |

## Grand Total

| Level | Hours |
|-------|-------|
| P0 | ~6.5h |
| P1 | ~3.5h |
| **Total** | **~10h** |

---

# 11. Success Criteria

Version V1.1 is complete when an interviewer can:

- ✅ Paste an Apple App Store URL and trigger analysis
- ✅ **See real-time streaming workflow progress (P0-1)** — no blank 5-minute wait
- ✅ **Cancel an in-flight analysis (P0-3)** — no stuck state on re-submit
- ✅ **Results are consistent** — `conflicting_evidence` is always `List[str]` (P0-2)
- ✅ **Import review data directly** — paste JSON/CSV instead of App Store URL (P0-4)
- ✅ View every intermediate artifact (reviews, cleaned data, classifications, findings, PRD, test cases)
- ✅ **Export the PRD as PDF, DOCX, or Markdown (P1-3)** — walk away with a deliverable
- ✅ **Click through traceability (P1-4)** — Requirement → Finding → Review back-and-forth

---

# 12. Future Enhancements (V2)

Potential future improvements outside V1.1 scope:

- Frontend data entry textarea + file upload (partially enabled by P0-4 backend)
- Full review collection via App Store internal API scraper
- Prompt optimization (few-shot examples, goal weighting)
- Deployment improvements (Docker, health checks)
- Google Play support
- Historical review analysis
- Competitor comparison
- Multi-language review analysis
- Release note generation
- Jira / Notion integration
- Multi-agent orchestration

---

# End of Document
