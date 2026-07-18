from pydantic import BaseModel, Field
from typing import List, Optional

class TestCase(BaseModel):
    id: str = Field(..., description="Test case unique identifier")
    title: str = Field(..., description="Test case title")
    related_requirement: Optional[str] = Field(None, description="Related requirement ID")
    preconditions: List[str] = Field(..., description="Preconditions")
    steps: List[str] = Field(..., description="Test steps")
    expected_result: str = Field(..., description="Expected result")