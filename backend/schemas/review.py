from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Review(BaseModel):
    id: str = Field(..., description="Review unique identifier")
    app_id: str = Field(..., description="App identifier")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    title: Optional[str] = Field(None, description="Review title")
    content: str = Field(..., description="Review content")
    author: str = Field(..., description="Review author")
    date: datetime = Field(..., description="Review date")
    version: Optional[str] = Field(None, description="App version at review time")