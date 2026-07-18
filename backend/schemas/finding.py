from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional

class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EvidenceSufficiency(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

class Finding(BaseModel):
    finding_id: str = Field(..., description="Finding unique identifier")
    title: str = Field(..., description="Finding title")
    category: str = Field(..., description="Finding category")
    severity: FindingSeverity = Field(..., description="Severity level")
    description: str = Field(..., description="Detailed description")
    supporting_review_ids: List[str] = Field(..., description="List of supporting review IDs")
    supporting_excerpts: List[str] = Field(..., description="Excerpts from supporting reviews")
    support_count: int = Field(..., ge=0, description="Number of supporting reviews")
    conflicting_evidence: Optional[str] = Field(None, description="Any conflicting evidence")
    assumptions: Optional[str] = Field(None, description="Assumptions made")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    uncertainty_notes: Optional[str] = Field(None, description="Notes on uncertainty")
    evidence_sufficiency: EvidenceSufficiency = Field(..., description="Sufficiency of evidence")