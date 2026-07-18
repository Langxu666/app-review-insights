from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional
from datetime import datetime

class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class Requirement(BaseModel):
    req_id: str = Field(..., description="Requirement unique identifier")
    title: str = Field(..., description="Requirement title")
    description: str = Field(..., description="Detailed description")
    user_problem: str = Field(..., description="User problem being solved")
    business_value: str = Field(..., description="Business value")
    priority: Priority = Field(..., description="Priority level")
    target_version: Optional[str] = Field(None, description="Target version for implementation")
    acceptance_criteria: List[str] = Field(..., description="Acceptance criteria")
    source_finding_ids: List[str] = Field(..., description="Finding IDs that support this requirement")
    source_review_ids: List[str] = Field(..., description="Review IDs that support this requirement")
    effort_estimate: Optional[str] = Field(None, description="Effort estimate")
    is_assumption: bool = Field(False, description="Whether this is an assumption")

class VersionPlan(BaseModel):
    version: str = Field(..., description="Version identifier")
    theme: str = Field(..., description="Version theme")
    release_goal: str = Field(..., description="Release goal")
    requirement_ids: List[str] = Field(..., description="Requirements in this version")
    rationale: str = Field(..., description="Rationale for this plan")

class UserStory(BaseModel):
    id: str = Field(..., description="User story ID")
    role: str = Field(..., description="User role")
    goal: str = Field(..., description="User goal")
    benefit: str = Field(..., description="Expected benefit")

class PRDDraft(BaseModel):
    title: str = Field(..., description="PRD title")
    app_name: str = Field(..., description="App name")
    analysis_goal: str = Field(..., description="Analysis goal")
    generated_at: datetime = Field(..., description="Generation timestamp")
    background: str = Field(..., description="Background context")
    problem_statement: str = Field(..., description="Problem statement")
    supporting_findings: List[str] = Field(..., description="Finding IDs supporting this PRD")
    user_stories: List[UserStory] = Field(..., description="User stories")
    requirements: List[Requirement] = Field(..., description="Requirements")
    version_plan: List[VersionPlan] = Field(..., description="Version plan")