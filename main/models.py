"""Pydantic models for API requests and responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Response model for file upload endpoint."""
    
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Status message")
    document_id: Optional[str] = Field(None, description="Unique document identifier")
    file_path: str = Field(..., description="Original filename of the processed document")
    nodes_created: int = Field(0, description="Number of nodes created")
    text_nodes: int = Field(0, description="Number of text nodes")
    table_nodes: int = Field(0, description="Number of table nodes")
    image_nodes: int = Field(0, description="Number of image nodes")


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    
    query: str = Field(..., description="The query string to search for", min_length=1)


class SourceNode(BaseModel):
    """Model for source node information."""
    
    content_type: str = Field(..., description="Type of content (text, table_summary, image_caption)")
    source: str = Field(..., description="Source document path")
    text_preview: str = Field(..., description="Preview of node text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class OutputValidation(BaseModel):
    """Model for output validation results."""
    
    passed: bool = Field(..., description="Whether output validation passed")
    pii_detected: bool = Field(False, description="Whether PII was detected")
    pii_entities: List[str] = Field(default_factory=list, description="Types of PII detected")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class GuardrailsReport(BaseModel):
    """Model for guardrails validation report."""
    
    input_validation: Dict[str, Any] = Field(default_factory=dict, description="Input validation results")
    security_check: Dict[str, Any] = Field(default_factory=dict, description="Security check results")
    output_validation: OutputValidation = Field(..., description="Output validation results")
    retrieval_method: str = Field("semantic_search", description="Retrieval method used (semantic_search, fusion_retrieval, sql_search, hybrid_search)")


class EvaluationReport(BaseModel):
    """Model for automatic evaluation scores."""

    trace_id: str = Field(..., description="Langfuse trace ID for the evaluation span")
    faithfulness: Optional[float] = Field(None, description="Faithfulness score from 0.0 to 1.0")
    answer_relevance: Optional[float] = Field(None, description="Answer relevance score from 0.0 to 1.0")
    confidence: Optional[int] = Field(None, description="LLM confidence score from 0 to 100")


class QueryResponse(BaseModel):
    """Response model for query results including optional handoff metadata."""

    question: str  # Or 'question', ensure this matches what you send in to_dict()
    answer: str
    
    handoff_triggered: Optional[bool] = False
    handoff_reference_id: Optional[str] = None
    handoff_reason: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")

