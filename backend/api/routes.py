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

    Accepts either an App Store URL or raw import data (JSON/CSV).
    If import_data is provided, it takes precedence over url.

    Validation logic:
      - Only import_data  → skip URL validation
      - Only url          → validate as Apple App Store URL
      - Both provided     → import_data takes precedence, skip URL validation

    Args:
        request: Contains url, import_data, and an optional analysis goal.

    Returns:
        WorkflowResponse with per-stage status and artifact counts.

    Raises:
        HTTPException(400): Invalid request (no input provided or invalid URL).
        HTTPException(500): Workflow execution failed.
    """
    url = request.url.strip() if request.url else None
    import_data = request.import_data.strip() if request.import_data else None
    goal = request.goal.strip() if request.goal else None

    # Validation: only enforce URL format when it's the sole input
    if import_data:
        # import_data takes precedence — skip URL validation
        pass
    elif url:
        _validate_app_store_url(url)
    # else: Pydantic model_validator already guarantees at least one is provided

    logger.info(
        "Starting analysis: url=%s, has_import_data=%s, goal=%s",
        url,
        bool(import_data),
        goal,
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
def analyze_imported_reviews(request: AnalyzeRequest) -> WorkflowResponse:
    """Execute the analysis workflow starting from imported review data.

    Convenience endpoint — delegates to the same logic as /api/analyze
    but expects import_data to be provided.

    Args:
        request: Contains the raw review data and an optional analysis goal.

    Returns:
        WorkflowResponse with per-stage status and artifact counts.

    Raises:
        HTTPException(400): Empty or invalid data.
        HTTPException(500): Workflow execution failed.
    """
    return analyze_reviews(request)