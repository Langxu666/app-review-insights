import asyncio
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

from collector.apple_collector import collect_reviews
from collector.data_importer import import_reviews
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
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalyzeRequest(BaseModel):
    url: Optional[str] = Field(None, description="App Store URL (optional if import_data provided)")
    goal: Optional[str] = Field(None, description="Optional analysis goal to focus the workflow")
    import_data: Optional[str] = Field(None, description="JSON/CSV review data string (optional if url provided)")

    @model_validator(mode="after")
    def check_at_least_one_input(self) -> "AnalyzeRequest":
        if not self.url and not self.import_data:
            raise ValueError("At least one of 'url' or 'import_data' must be provided")
        return self


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

    When import_data is provided, the collect stage is skipped and reviews
    are obtained via :func:`collector.data_importer.import_reviews` instead.
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

    def run(
        self,
        url: Optional[str] = None,
        goal: Optional[str] = None,
        import_data: Optional[str] = None,
    ) -> WorkflowResponse:
        """Execute the full analysis workflow.

        Accepts either an App Store URL or raw import data (JSON/CSV).
        If import_data is provided, the collect stage is skipped.

        Args:
            url: App Store URL of the app to analyze.
            goal: Optional analysis goal to focus classification and finding extraction.
            import_data: Raw review data in JSON or CSV format.

        Returns:
            WorkflowResponse with status, stage info, and artifact counts.
        """
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()

        # ── Stage 1: Collect (or Import) ──
        if import_data:
            logger.info("Workflow started with import_data, goal: %s", goal)
            reviews = import_reviews(import_data)
            self.stages["collect"].status = StageStatus.SKIPPED
            self.stages["collect"].completed_at = datetime.now()
            self.artifacts["reviews"] = _serialize(reviews)
            self.artifacts["reviews_count"] = len(reviews)
            logger.info(
                "Imported %d review(s), collect stage skipped", len(reviews)
            )
        elif url:
            logger.info("Workflow started for URL: %s, goal: %s", url, goal)
            reviews = self._run_stage(
                "collect",
                lambda: collect_reviews(url),
                "reviews",
            )
            if reviews is None:
                return self._finish(WorkflowStatus.FAILED, "Collect stage failed")
            if len(reviews) == 0:
                return self._finish(WorkflowStatus.FAILED, "未采集到任何评论（该 App 的 RSS feed 可能无数据，请尝试导入数据或更换 App Store 链接）")
        else:
            return self._finish(WorkflowStatus.FAILED, "No input provided (url or import_data required)")

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

    async def run_streaming(
        self,
        url: Optional[str] = None,
        goal: Optional[str] = None,
        import_data: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Execute the analysis workflow with SSE streaming progress.

        Yields SSE-formatted JSON events for each stage transition.
        Use ``asyncio.to_thread`` for synchronous stage code.

        Args:
            url: App Store URL of the app to analyze.
            goal: Optional analysis goal.
            import_data: Raw review data in JSON or CSV format.
        """
        try:
            self.status = WorkflowStatus.RUNNING
            self.started_at = datetime.now()

            # ── Start event ──
            stages_snapshot = {
                name: {"status": s.status.value, "started_at": None, "completed_at": None}
                for name, s in self.stages.items()
            }
            yield self._sse_event("start", status="running", stages=stages_snapshot)
            await asyncio.sleep(0.1)

            # ── Stage 1: Collect (or Import) ──
            if import_data:
                logger.info("Streaming workflow with import_data, goal: %s", goal)
                reviews = await asyncio.to_thread(import_reviews, import_data)
                self.stages["collect"].status = StageStatus.SKIPPED
                self.stages["collect"].completed_at = datetime.now()
                self.artifacts["reviews"] = _serialize(reviews)
                self.artifacts["reviews_count"] = len(reviews)
                yield self._sse_event("stage_update",
                    stage="collect", status="skipped",
                    reviews_count=len(reviews))
            elif url:
                logger.info("Streaming workflow for URL: %s, goal: %s", url, goal)
                yield self._sse_event("stage_update", stage="collect", status="running")
                try:
                    reviews = await asyncio.to_thread(collect_reviews, url)
                    self.stages["collect"].status = StageStatus.COMPLETED
                    self.stages["collect"].completed_at = datetime.now()
                    self.artifacts["reviews"] = _serialize(reviews)
                    self.artifacts["reviews_count"] = len(reviews)
                    yield self._sse_event("stage_update",
                        stage="collect", status="completed",
                        reviews_count=len(reviews))
                except Exception as e:
                    self.stages["collect"].status = StageStatus.FAILED
                    self.stages["collect"].error = str(e)
                    yield self._sse_event("stage_update",
                        stage="collect", status="failed", error=str(e))
                    yield self._sse_event("complete", status="failed",
                        error="Collect stage failed")
                    return

                if len(reviews) == 0:
                    yield self._sse_event("complete", status="failed",
                        error="未采集到任何评论（该 App 的 RSS feed 可能无数据，请尝试导入数据或更换 App Store 链接）")
                    return
            else:
                yield self._sse_event("complete", status="failed",
                    error="No input provided (url or import_data required)")
                return

            await asyncio.sleep(0.1)

            # ── Shared analysis pipeline ──
            for stage_name, stage_func, artifact_key, extra_args in [
                ("clean", clean_reviews, "cleaned", [reviews]),
                ("classify", classify_reviews, "classified", [None, {"analysis_goal": goal}]),
                ("extract_findings", extract_findings, "findings", [None, {"analysis_goal": goal}]),
                ("generate_prd", generate_prd, "prd", [[], {"analysis_goal": goal}]),
                ("generate_tests", generate_test_cases, "tests", []),
            ]:
                yield self._sse_event("stage_update", stage=stage_name, status="running")
                try:
                    if stage_name == "classify":
                        output = await asyncio.to_thread(stage_func, cleaned_data, analysis_goal=goal)
                    elif stage_name == "extract_findings":
                        output = await asyncio.to_thread(stage_func, classification_results, analysis_goal=goal)
                    elif stage_name == "generate_prd":
                        output = await asyncio.to_thread(stage_func, findings_list, analysis_goal=goal)
                    elif stage_name == "generate_tests":
                        output = await asyncio.to_thread(stage_func, prd_result)
                    else:
                        output = await asyncio.to_thread(stage_func, reviews)

                    self.stages[stage_name].status = StageStatus.COMPLETED
                    self.stages[stage_name].completed_at = datetime.now()
                    self.artifacts[artifact_key] = _serialize(output)
                    self._extract_counts(stage_name, output)

                    # Prepare data for stage_update event
                    yield self._sse_event("stage_update",
                        stage=stage_name, status="completed",
                        **self._stage_summary(stage_name, output))

                except Exception as e:
                    self.stages[stage_name].status = StageStatus.FAILED
                    self.stages[stage_name].error = str(e)
                    yield self._sse_event("stage_update",
                        stage=stage_name, status="failed", error=str(e))
                    yield self._sse_event("complete", status="failed",
                        error=f"{stage_name} stage failed: {e}")
                    return

                # Update pipeline state for next stages
                if stage_name == "clean":
                    cleaned_data = output.get("cleaned_data", [])
                    if not cleaned_data:
                        removed_dup = output.get("removed_duplicates", 0)
                        removed_empty = output.get("removed_empty", 0)
                        total = self.artifacts.get("reviews_count", 0)
                        yield self._sse_event("complete", status="failed",
                            error=(
                                f"清洗后无有效评论（共采集 {total} 条，"
                                f"去重移除 {removed_dup} 条，无效内容移除 {removed_empty} 条）"
                            ))
                        return
                elif stage_name == "classify":
                    if isinstance(output, dict) and "classification_results" in output:
                        classification_results = output["classification_results"]
                    else:
                        classification_results = output
                    if not classification_results:
                        yield self._sse_event("complete", status="failed",
                            error="No classification results")
                        return
                elif stage_name == "extract_findings":
                    findings_list = output.get("findings", [])
                    if not findings_list:
                        logger.warning("No findings extracted, continuing with empty findings")
                elif stage_name == "generate_prd":
                    if isinstance(output, dict) and "error" in output:
                        yield self._sse_event("stage_update",
                            stage="generate_prd", status="failed",
                            error=f"PRD generation error: {output['error']}")
                        yield self._sse_event("complete", status="failed",
                            error=output["error"])
                        return
                    prd_result = output

                await asyncio.sleep(0.1)

            # ── Complete ──
            self.status = WorkflowStatus.COMPLETED
            self.completed_at = datetime.now()
            duration = (self.completed_at - self.started_at).total_seconds() * 1000 if self.started_at else 0

            artifacts_data = self._build_artifacts_data()
            summary = {
                "reviews_count": self.artifacts.get("reviews_count", 0),
                "cleaned_count": self.artifacts.get("cleaned_count", 0),
                "classified_count": self.artifacts.get("classified_count", 0),
                "findings_count": self.artifacts.get("findings_count", 0),
                "requirements_count": self.artifacts.get("requirements_count", 0),
                "test_cases_count": self.artifacts.get("test_cases_count", 0),
            }
            stages_snapshot = {
                name: {"status": s.status.value, "started_at": _serialize(s.started_at),
                       "completed_at": _serialize(s.completed_at), "error": s.error}
                for name, s in self.stages.items()
            }

            yield self._sse_event("complete", status="completed",
                stages=stages_snapshot, artifacts=summary,
                artifacts_data=artifacts_data, duration_ms=duration)

        except asyncio.CancelledError:
            logger.info("Streaming workflow cancelled by client disconnect")
            self.status = WorkflowStatus.FAILED
            self.error = "Client disconnected"
            yield self._sse_event("complete", status="failed",
                error="Client disconnected")
        except Exception as e:
            logger.error("Streaming workflow error: %s", e, exc_info=True)
            self.status = WorkflowStatus.FAILED
            self.error = str(e)
            yield self._sse_event("complete", status="failed", error=str(e))

    def _sse_event(self, event: str, **data: Any) -> str:
        """Format a dict as an SSE data line.

        For 'complete' events, automatically includes the current stages snapshot
        so the frontend always has stage data regardless of success/failure path.
        """
        payload: Dict[str, Any] = {"event": event, **data}
        if event == "complete" and "stages" not in payload:
            payload["stages"] = {
                name: {"status": s.status.value, "started_at": _serialize(s.started_at),
                       "completed_at": _serialize(s.completed_at), "error": s.error}
                for name, s in self.stages.items()
            }
        return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

    def _stage_summary(self, stage_name: str, output: Any) -> Dict[str, Any]:
        """Build a summary dict for a completed stage."""
        summary: Dict[str, Any] = {}
        if stage_name == "collect" or stage_name == "clean":
            if isinstance(output, list):
                summary["count"] = len(output)
            elif isinstance(output, dict) and "cleaned_data" in output:
                summary["count"] = len(output["cleaned_data"])
        elif stage_name == "classify":
            if isinstance(output, dict) and "classification_results" in output:
                summary["count"] = len(output["classification_results"])
            elif isinstance(output, list):
                summary["count"] = len(output)
        elif stage_name == "extract_findings":
            summary["count"] = len(output.get("findings", [])) if isinstance(output, dict) else 0
        elif stage_name == "generate_prd":
            if isinstance(output, dict):
                summary["count"] = output.get("requirements_count", 0)
        elif stage_name == "generate_tests":
            summary["count"] = len(output) if isinstance(output, list) else 0
        return summary

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
                # Unwrap: generate_prd returns {"prd_draft": PRDDraft, ...}
                # Frontend expects the PRDDraft directly, not the wrapper dict
                if isinstance(prd, dict) and "prd_draft" in prd:
                    data["prd_draft"] = prd["prd_draft"]
                else:
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