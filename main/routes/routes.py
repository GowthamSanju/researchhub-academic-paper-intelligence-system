"""FastAPI routes for the unified multi-modal retrieval API."""
import logging
import os
import tempfile
import datetime
import secrets
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks

from ..models import UploadResponse, QueryRequest, QueryResponse
from ..service.multimodal_service import get_service, MultimodalService
from ..evaluation.dataset import get_langfuse_client
from ..evaluation.dataset_evaluation import (
    evaluate_faithfulness_score,
    evaluate_answer_relevance,
)
from ..handoff.handoff_service import (
    evaluate_score,
    evaluate_confidence_score,
    evaluate_explicit_user_request,
    generate_handoff_reference_id,
    send_handoff_email,
)

from main.service.query_service import execute_hybrid_query
from main.service.validators import get_validator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Check if the API and services are running correctly"
)
async def health_check(
    service: MultimodalService = Depends(get_service),
) -> dict:
    """Health check endpoint."""
    try:
        # Try to access the service
        _ = service
        
        return {
            "status": "healthy",
            "service": "unified-multimodal-rag",
            "index_available": service.is_initialized(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload and process a document",
    description="Upload a document file (PDF, DOCX, TXT, or MD) containing text, tables, and/or images. The file will be processed and indexed."
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload and process (PDF, DOCX, TXT, or MD)"),
    service: MultimodalService = Depends(get_service),
) -> UploadResponse:
    """
    Upload and process a document.
    
    Supported formats: PDF, DOCX, TXT, MD
    
    The document will be parsed to extract:
    - Text content (semantically chunked)
    - Tables (summarized)
    - Images (extracted from PDF and DOCX files)
    
    All content is added to a unified vector index.
    """
    filename = file.filename or "uploaded_file"
    logger.info(f"Received document upload request: filename={filename}, size={file.size}")
    
    # Validate file type
    supported_extensions = {'.txt', '.pdf', '.md', '.docx'}
    file_extension = Path(filename).suffix.lower()
    if file_extension not in supported_extensions:
        logger.warning(f"Invalid file type: {filename}")
        raise HTTPException(
            status_code=400,
            detail=f"Supported file types: {', '.join(supported_extensions)}"
        )
    
    try:
        # Save uploaded file temporarily (same approach as demo-1 and demo-2)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        logger.info(f"Saved uploaded file to temporary location: {tmp_path}")
        
        try:
            # Process document (pass original filename for metadata)
            logger.info(f"Processing document: {filename}")
            result = service.process_document(tmp_path, original_filename=filename)
            
            logger.info(f"Document processed successfully: {result}")
            
            return UploadResponse(
                success=True,
                message=f"Document '{filename}' processed successfully",
                document_id=result["document_id"],
                file_path=result.get("file_path", filename),
                nodes_created=result.get("total_nodes", 0),
                text_nodes=result.get("text_nodes", 0),
                table_nodes=result.get("table_nodes", 0),
                image_nodes=result.get("image_nodes", 0),
            )
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                logger.debug(f"Cleaned up temporary file: {tmp_path}")
        
    except Exception as e:
        logger.error(f"Error processing document {filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@router.post("/query", response_model=QueryResponse)
async def query_agent(
    request: QueryRequest,
    background_tasks: BackgroundTasks, 
) -> QueryResponse:
    """
    Query the Agentic RAG system with a question.
    Decides between SQL, Vector documents, and Academic MCP tools.
    Evaluates quality, processes Guardrails checks, and manages human handoff triggers.
    """
    logger.info(f"Received agent query request: query='{request.query[:100]}...'")

    try:
        # Get the global guardrails validator instance
        validator = get_validator()
        query_text = request.query

        # ===== INPUT GUARDRAILS =====
        if validator:
            # 1. Structural Length & Input Sanitization
            is_valid, error_msg = validator.validate_input(query_text)
            if not is_valid:
                logger.warning(f"Input validation failed: {error_msg}")
                raise HTTPException(status_code=400, detail=f"Input validation failed: {error_msg}")
            
            query_text = validator.sanitize_input(query_text)

            # 2. Semantic Security & Prompt Injection Scan
            is_safe, issues = validator.check_query_safety(query_text)
            if not is_safe:
                logger.warning(f"Query security issues detected: {issues}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Query contains security risks: {', '.join(issues)}"
                )

        session_id = secrets.token_hex(8)
        conversation_flow = []

        # 1. Execute the hybrid query via the service layer (using sanitized text)
        result = await execute_hybrid_query(query_text)
        result_dict = result.to_dict()
        
        answer = result_dict.get("answer", "")
        tools_used = result_dict.get("tools_used", [])
        source_nodes = result_dict.get("source_nodes", [])

        # Format retrieved items for the handoff context validation layer
        full_chunks = [
            {
                "chunk_id": node.get("metadata", {}).get("node_id", "unknown"),
                "text": node.get("text_preview", ""),
                "source": node.get("source", "unknown"),
                "metadata": node.get("metadata", {}),
            }
            for node in source_nodes
        ]
        eval_context = "\n\n".join(chunk["text"] for chunk in full_chunks if chunk["text"])

        # ===== OUTPUT GUARDRAILS =====
        guardrails_report = {
            "input_validation": {"passed": True},
            "security_check": {"passed": True},
            "output_validation": {"passed": True, "pii_detected": False, "warnings": []},
            "retrieval_method": "agentic_hybrid_search" if tools_used else "agent_reasoning",
        }

        if validator:
            is_output_valid, sanitized_answer, output_metadata = validator.validate_output(
                answer,
                check_pii=True,
                check_length=True
            )
            answer = sanitized_answer
            guardrails_report["output_validation"] = {
                "passed": is_output_valid,
                "pii_detected": output_metadata["pii_detected"],
                "pii_entities": output_metadata["pii_entities"],
                "warnings": output_metadata["warnings"],
            }
            if output_metadata["pii_detected"]:
                logger.warning(f"PII redacted in agent output: {output_metadata['pii_entities']}")

        # 3. Setup Langfuse Tracing & Evaluation Matrix
        langfuse = None
        trace_id = "unknown"
        try:
            langfuse = get_langfuse_client()
        except Exception as exc:
            logger.warning(f"Langfuse client unavailable; skipping tracing: {exc}")

        # --- EVALUATION FLOW ---
        confidence_handoff = await evaluate_confidence_score(answer)
        confidence_score = confidence_handoff.get("confidence", 50)
        explicit_handoff = await evaluate_explicit_user_request(query_text)

        retrieval_empty = len(full_chunks) == 0
        faithfulness = None
        relevance = None

        if langfuse is not None:
            span_context = langfuse.start_as_current_observation(
                as_type="span",
                name="api_agent_query_handoff",
                input={"query": query_text},
                metadata={"dataset": "academic_agent_evaluation"},
            )
            with span_context as span:
                trace_id = getattr(span, "trace_id", "unknown")
                faithfulness = await evaluate_faithfulness_score(
                    langfuse, trace_id, query_text, eval_context, answer
                )
                relevance = await evaluate_answer_relevance(
                    langfuse, trace_id, query_text, answer
                )

        score_based_handoff = evaluate_score(
            faithfulness,
            relevance,
            query_text,
            no_chunks=retrieval_empty,
        )

        # 4. Resolve Handoff Cascades & Priorities
        if explicit_handoff["trigger"]:
            handoff = explicit_handoff
            priority = "high"
        elif confidence_handoff["trigger"] and score_based_handoff["trigger"]:
            handoff = confidence_handoff
            priority = "high"
        elif score_based_handoff["trigger"]:
            handoff = score_based_handoff
            priority = "normal"
        else:
            handoff = {"trigger": False}
            priority = None

        # 5. Build Final Response Data Object Mapping Structure
        response_data = {
            "question": query_text,  
            "answer": answer,
            "handoff_triggered": False,
            "handoff_reference_id": None,
            "handoff_reason": None,
        }

        # Handle Triggered Handoffs
        if handoff["trigger"]:
            reference_id = generate_handoff_reference_id()
            timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

            handoff_context = {
                "reference_id": reference_id,
                "trace_id": trace_id,
                "timestamp_utc": timestamp_utc,
                "session_id": session_id,
                "priority": priority,
                "trigger_reason": handoff.get("reason", "human handoff triggered"),
                "query_history": [{"role": "user", "message": query_text}],
                "generated_answer": answer,
                "evaluation_scores": {
                    "faithfulness": faithfulness,
                    "relevance": relevance,
                    "confidence": confidence_score,
                },
                "retrieved_chunks": full_chunks,
                "conversation_flow": conversation_flow,
                "guardrails_report": guardrails_report,  # Map the generated guardrails report
            }

            background_tasks.add_task(send_handoff_email, handoff_context)

            response_data["answer"] = (
                "I don't have enough reliable information to answer confidently. "
                "Your request has been escalated to a human reviewer. "
                f"Reference ID: {reference_id}"
            )
            response_data["handoff_triggered"] = True
            response_data["handoff_reference_id"] = reference_id
            response_data["handoff_reason"] = handoff.get("reason")

        return QueryResponse(**response_data)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error processing agent query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")