from pydantic import BaseModel, Field
from enum import Enum

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ClassificationResult(BaseModel):
    review_id: str = Field(..., description="Reference to the original review")
    primary_category: str = Field(..., description="Primary category classification")
    sentiment: Sentiment = Field(..., description="Sentiment analysis result")
    summary: str = Field(..., description="Summary of the review")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    key_quote: str = Field(..., description="Key quote from the review")