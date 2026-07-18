import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from collector.apple_collector import collect_reviews
from analyzer.cleaner import clean_reviews
from analyzer.classifier import classify_reviews
from analyzer.finding_extractor import extract_findings
from planner.prd_generator import generate_prd
from planner.test_generator import generate_test_cases

logger = logging.getLogger(__name__)


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="App Store URL of the app to analyze")
    goal: Optional[str] = Field(None, description="Optional analysis goal to focus the workflow")


class StageInfo(BaseModel):
    status: StageStatus = Field(StageStatus.PENDING, description="Stage status")
    started_at: Optional[datetime] = Field(None, description="Stage start time")
    completed_at: Optional[datetime] = Field(None, description="Stage completion time")
    duration_ms: Optional[float] = Field(None, description="Stage duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if stage failed")


class ArtifactsSummary(BaseModel):
    reviews_count: int = Field(0, description="Number of raw reviews collected")
    cleaned_count: int = Field(0, description="Number of reviews after cleaning")
    classified_count: int = Field(0, description="Number of reviews classified")
    findings_count: int = Field(0, description="Number of findings extracted")
    requirements_count: int = Field(0, description="Number of PRD requirements")
    test_cases_count: int = Field(0, description="Number of test cases generated")


class WorkflowResponse(BaseModel):
    status: WorkflowStatus = Field(..., description="Overall workflow status")
    stages: Dict[str, StageInfo] = Field(..., description="Per-stage status information")
    artifacts: ArtifactsSummary = Field(..., description="Artifacts summary counts")
    artifacts_data: Optional[Dict[str, Any]] = Field(None, description="Full artifacts data (reviews, findings, PRD, etc.)")
    error: Optional[str] = Field(None, description="Overall error message if workflow failed")
    started_at: Optional[datetime] = Field(None, description="Workflow start time")
    completed_at: Optional[datetime] = Field(None, description="Workflow completion time")
    duration_ms: Optional[float] = Field(None, description="Total workflow duration")


def _serialize(obj: Any) -> Any:
    """Serialize Pydantic models and other objects to JSON-compatible dicts."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class WorkflowEngine:
    """Orchestrates the full review analysis workflow.

    Stages: collect -> clean -> classify -> extract_findings -> generate_prd -> generate_tests
    """

    STAGE_ORDER = [
        "collect",
        "clean",
        "classify",
        "extract_findings",
        "generate_prd",
        "generate_tests",
    ]

    def __init__(self):
        self.stages: Dict[str, StageInfo] = {
            name: StageInfo(status=StageStatus.PENDING) for name in self.STAGE_ORDER
        }
        self.artifacts: Dict[str, Any] = {}
        self.status = WorkflowStatus.PENDING
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def run(self, url: str, goal: Optional[str] = None) -> WorkflowResponse:
        """Execute the full analysis workflow.

        Args:
            url: App Store URL of the app to analyze.
            goal: Optional analysis goal to focus classification and finding extraction.

        Returns:
            WorkflowResponse with status, stage info, and artifact counts.
        """
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()
        logger.info(f"Workflow started for URL: {url}, goal: {goal}")

        # ── Stage 1: Collect ──
        reviews = self._run_stage(
            "collect",
            lambda: collect_reviews(url),
            "reviews",
        )
        if reviews is None:
            return self._finish(WorkflowStatus.FAILED, "Collect stage failed")

        # ── Stage 2: Clean ──
        cleaned_result = self._run_stage(
            "clean",
            lambda: clean_reviews(reviews),
            "cleaned",
        )
        if cleaned_result is None:
            return self._finish(WorkflowStatus.FAILED, "Clean stage failed")

        cleaned_data = cleaned_result.get("cleaned_data", [])
        if not cleaned_data:
            return self._finish(WorkflowStatus.FAILED, "No reviews after cleaning")

        # ── Stage 3: Classify ──
        classified_result = self._run_stage(
            "classify",
            lambda: classify_reviews(cleaned_data, analysis_goal=goal),
            "classified",
        )
        if classified_result is None:
            return self._finish(WorkflowStatus.FAILED, "Classify stage failed")

        # classify_reviews returns a dict with classification_results key
        if isinstance(classified_result, dict) and "classification_results" in classified_result:
            classification_results = classified_result["classification_results"]
        else:
            classification_results = classified_result

        if not classification_results:
            return self._finish(WorkflowStatus.FAILED, "No classification results")

        # ── Stage 4: Extract Findings ──
        findings_result = self._run_stage(
            "extract_findings",
            lambda: extract_findings(classification_results, analysis_goal=goal),
            "findings",
        )
        if findings_result is None:
            return self._finish(WorkflowStatus.FAILED, "Extract findings stage failed")

        findings_list = findings_result.get("findings", [])
        if not findings_list:
            logger.warning("No findings extracted, continuing with empty findings")

        # ── Stage 5: Generate PRD ──
        prd_result = self._run_stage(
            "generate_prd",
            lambda: generate_prd(findings_list, analysis_goal=goal),
            "prd",
        )
        if prd_result is None:
            return self._finish(WorkflowStatus.FAILED, "Generate PRD stage failed")

        if "error" in prd_result:
            return self._finish(WorkflowStatus.FAILED, f"PRD generation error: {prd_result['error']}")

        # ── Stage 6: Generate Tests ──
        test_cases = self._run_stage(
            "generate_tests",
            lambda: generate_test_cases(prd_result),
            "tests",
        )
        if test_cases is None:
            return self._finish(WorkflowStatus.FAILED, "Generate tests stage failed")

        return self._finish(WorkflowStatus.COMPLETED)

    def _run_stage(self, stage_name: str, func, artifact_key: str) -> Optional[Any]:
        """Execute a single workflow stage with timing and error handling.

        Args:
            stage_name: Name of the stage (must match a key in self.stages).
            func: Callable that executes the stage logic.
            artifact_key: Key under which to store the serialized output in self.artifacts.

        Returns:
            The raw output of func, or None if the stage failed.
        """
        stage = self.stages[stage_name]
        stage.status = StageStatus.RUNNING
        stage.started_at = datetime.now()
        logger.info(f"[{stage_name}] Starting...")

        try:
            output = func()
            stage.status = StageStatus.COMPLETED
            stage.completed_at = datetime.now()
            stage.duration_ms = (stage.completed_at - stage.started_at).total_seconds() * 1000

            # Store serialized artifacts
            self.artifacts[artifact_key] = _serialize(output)

            # Extract counts for summary
            self._extract_counts(stage_name, output)

            logger.info(
                f"[{stage_name}] Completed in {stage.duration_ms:.0f}ms"
            )
            return output

        except Exception as e:
            stage.status = StageStatus.FAILED
            stage.completed_at = datetime.now()
            stage.duration_ms = (stage.completed_at - stage.started_at).total_seconds() * 1000
            stage.error = str(e)
            logger.error(f"[{stage_name}] Failed: {e}", exc_info=True)
            return None

    def _extract_counts(self, stage_name: str, output: Any) -> None:
        """Extract count metrics from stage output for the artifacts summary."""
        try:
            if stage_name == "collect":
                self.artifacts["reviews_count"] = len(output) if isinstance(output, list) else 0
            elif stage_name == "clean":
                self.artifacts["cleaned_count"] = len(output.get("cleaned_data", [])) if isinstance(output, dict) else 0
            elif stage_name == "classify":
                if isinstance(output, dict) and "classification_results" in output:
                    self.artifacts["classified_count"] = len(output["classification_results"])
                elif isinstance(output, list):
                    self.artifacts["classified_count"] = len(output)
            elif stage_name == "extract_findings":
                self.artifacts["findings_count"] = len(output.get("findings", [])) if isinstance(output, dict) else 0
            elif stage_name == "generate_prd":
                self.artifacts["requirements_count"] = output.get("requirements_count", 0) if isinstance(output, dict) else 0
            elif stage_name == "generate_tests":
                self.artifacts["test_cases_count"] = len(output) if isinstance(output, list) else 0
        except Exception as e:
            logger.warning(f"Failed to extract counts for stage '{stage_name}': {e}")

    def _build_artifacts_data(self) -> Optional[Dict[str, Any]]:
        """Build the artifacts data dict in the shape the frontend expects.

        Maps internal artifact keys to frontend-friendly keys:
          reviews → raw_reviews
          cleaned → cleaned_data
          classified → classification_results
          findings → findings
          prd → prd_draft
          tests → test_case_drafts
        """
        try:
            data: Dict[str, Any] = {}

            raw = self.artifacts.get("reviews")
            if raw is not None:
                data["raw_reviews"] = raw

            cleaned = self.artifacts.get("cleaned")
            if cleaned is not None:
                if isinstance(cleaned, dict) and "cleaned_data" in cleaned:
                    data["cleaned_data"] = cleaned["cleaned_data"]
                else:
                    data["cleaned_data"] = cleaned

            classified = self.artifacts.get("classified")
            if classified is not None:
                if isinstance(classified, dict) and "classification_results" in classified:
                    data["classification_results"] = classified["classification_results"]
                elif isinstance(classified, list):
                    data["classification_results"] = classified
                else:
                    data["classification_results"] = classified

            findings = self.artifacts.get("findings")
            if findings is not None:
                if isinstance(findings, dict) and "findings" in findings:
                    data["findings"] = findings["findings"]
                else:
                    data["findings"] = findings

            prd = self.artifacts.get("prd")
            if prd is not None:
                data["prd_draft"] = prd

            tests = self.artifacts.get("tests")
            if tests is not None:
                data["test_case_drafts"] = tests

            return data if data else None
        except Exception as e:
            logger.warning(f"Failed to build artifacts_data: {e}")
            return None

    def _finish(self, status: WorkflowStatus, error: Optional[str] = None) -> WorkflowResponse:
        """Finalize the workflow and build the response."""
        self.status = status
        self.completed_at = datetime.now()
        self.error = error

        if self.started_at:
            total_duration = (self.completed_at - self.started_at).total_seconds() * 1000
        else:
            total_duration = 0

        logger.info(
            f"Workflow finished: status={status.value}, duration={total_duration:.0f}ms"
            + (f", error={error}" if error else "")
        )

        # Build artifacts_data in the shape the frontend expects
        artifacts_data = self._build_artifacts_data()

        return WorkflowResponse(
            status=status,
            stages=self.stages,
            artifacts=ArtifactsSummary(
                reviews_count=self.artifacts.get("reviews_count", 0),
                cleaned_count=self.artifacts.get("cleaned_count", 0),
                classified_count=self.artifacts.get("classified_count", 0),
                findings_count=self.artifacts.get("findings_count", 0),
                requirements_count=self.artifacts.get("requirements_count", 0),
                test_cases_count=self.artifacts.get("test_cases_count", 0),
            ),
            artifacts_data=artifacts_data,
            error=error,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=total_duration,
        )