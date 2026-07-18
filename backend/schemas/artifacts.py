from pydantic import BaseModel, Field
from typing import List, Optional
from .review import Review
from .classification import ClassificationResult
from .finding import Finding
from .prd import PRDDraft
from .test_case import TestCase

class Artifacts(BaseModel):
    raw_reviews: Optional[List[Review]] = Field(None, description="Raw reviews data")
    cleaned_data: Optional[List[Review]] = Field(None, description="Cleaned/processed reviews")
    classification_results: Optional[List[ClassificationResult]] = Field(None, description="Classification results")
    findings: Optional[List[Finding]] = Field(None, description="Analysis findings")
    prd_draft: Optional[PRDDraft] = Field(None, description="PRD draft")
    test_case_drafts: Optional[List[TestCase]] = Field(None, description="Test case drafts")