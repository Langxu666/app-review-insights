import re
import logging
from fastapi import APIRouter, HTTPException

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
def analyze_reviews(request: AnalyzeRequest) -> WorkflowResponse:
    """Execute the full review analysis workflow.

    Stages: collect → clean → classify → extract_findings → generate_prd → generate_tests

    Args:
        request: Contains the App Store URL and an optional analysis goal.

    Returns:
        WorkflowResponse with per-stage status and artifact counts.

    Raises:
        HTTPException(400): Invalid App Store URL.
        HTTPException(500): Workflow execution failed.
    """
    # Validate the URL
    _validate_app_store_url(request.url)

    goal = request.goal.strip() if request.goal else None

    logger.info(f"Starting analysis for URL: {request.url}, goal: {goal}")

    try:
        engine = WorkflowEngine()
        result = engine.run(url=request.url, goal=goal)

        # Return the full WorkflowResponse even on failure — the client
        # can inspect result.status and result.stages for diagnostics.
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )