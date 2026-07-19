import re
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.workflow import (
    WorkflowEngine,
    AnalyzeRequest,
    WorkflowResponse,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Matches: idXXXXXXXXX (9-10 digits) in an App Store URL
_APP_ID_PATTERN = re.compile(r"id(\d{9,10})")


def _validate_app_store_url(url: str) -> str:
    """Validate that the URL is a well-formed App Store URL and extract the app ID.

    Returns:
        The extracted app ID string.

    Raises:
        HTTPException(400): If the URL is invalid or doesn't contain an app ID.
    """
    url = url.strip()

    if not url:
        raise HTTPException(status_code=400, detail="URL must not be empty")

    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://",
        )

    if "apps.apple.com" not in url and "itunes.apple.com" not in url:
        raise HTTPException(
            status_code=400,
            detail="URL must be an App Store URL (apps.apple.com or itunes.apple.com)",
        )

    match = _APP_ID_PATTERN.search(url)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Could not extract app ID from URL. Expected format: .../idXXXXXXXXX/...",
        )

    return url


@router.get("/api/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/api/analyze", response_model=WorkflowResponse)
def analyze_reviews(
    request_body: AnalyzeRequest,
    request: Request,
) -> WorkflowResponse | StreamingResponse:
    """Execute the full review analysis workflow.

    Accepts either an App Store URL or raw import data (JSON/CSV).
    If import_data is provided, it takes precedence over url.

    Content negotiation:
      - Accept: text/event-stream  → SSE streaming response (real-time progress)
      - Otherwise                   → synchronous WorkflowResponse (backward compatible)

    Args:
        request_body: Contains url, import_data, and an optional analysis goal.

    Returns:
        WorkflowResponse or StreamingResponse.
    """
    url = request_body.url.strip() if request_body.url else None
    import_data = request_body.import_data.strip() if request_body.import_data else None
    goal = request_body.goal.strip() if request_body.goal else None

    # Validation: only enforce URL format when it's the sole input
    if import_data:
        pass
    elif url:
        _validate_app_store_url(url)

    accept_header = request.headers.get("accept", "")

    # ── SSE streaming path ──
    if "text/event-stream" in accept_header:
        logger.info(
            "Starting streaming analysis: url=%s, has_import_data=%s, goal=%s",
            url, bool(import_data), goal,
        )

        async def sse_generator():
            try:
                engine = WorkflowEngine()
                async for event in engine.run_streaming(
                    url=url, goal=goal, import_data=import_data
                ):
                    yield event
            except Exception as e:
                logger.error("SSE streaming error: %s", e, exc_info=True)

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )

    # ── Synchronous path (backward compatible) ──
    logger.info(
        "Starting analysis: url=%s, has_import_data=%s, goal=%s",
        url, bool(import_data), goal,
    )

    try:
        engine = WorkflowEngine()
        result = engine.run(url=url, goal=goal, import_data=import_data)
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Invalid data: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/api/analyze/import", response_model=WorkflowResponse)
def analyze_imported_reviews(
    request_body: AnalyzeRequest,
    request: Request,
) -> WorkflowResponse | StreamingResponse:
    """Execute the analysis workflow starting from imported review data.

    Convenience endpoint — delegates to the same logic as /api/analyze
    but expects import_data to be provided.
    """
    return analyze_reviews(request_body, request)