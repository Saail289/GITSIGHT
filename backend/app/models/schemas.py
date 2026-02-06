"""
Pydantic models for request/response validation.
These define the structure of data sent to/from the API.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal


class IngestRequest(BaseModel):
    """Request model for repository ingestion"""
    repo_url: str = Field(..., description="GitHub repository URL")
    user_id: Optional[str] = Field(default="default", description="User ID for RLS")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repo_url": "https://github.com/anthropics/anthropic-sdk-python",
                "user_id": "user123"
            }
        }
    )


class IngestResponse(BaseModel):
    """Response model for repository ingestion"""
    status: str
    message: str
    documents_processed: int
    repo_url: str


class QueryRequest(BaseModel):
    """Request model for asking questions"""
    repo_url: str = Field(..., description="GitHub repository URL to query")
    question: str = Field(..., description="Question about the repository")
    llm_model: Optional[str] = Field(
        default="nemotron",
        description="LLM model to use (currently only nemotron)"
    )
    
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "repo_url": "https://github.com/anthropics/anthropic-sdk-python",
                "question": "How do I install this library?",
                "llm_model": "nemotron"
            }
        }
    )


class SourceDocument(BaseModel):
    """Source document information"""
    file_path: str
    similarity: float
    preview: str
    file_type: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for questions"""
    answer: str
    sources: List[SourceDocument]
    repo_url: str
    llm_used: str
    
    model_config = ConfigDict(protected_namespaces=())


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


class ModelsResponse(BaseModel):
    """Available models response"""
    models: dict