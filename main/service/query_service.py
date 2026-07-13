"""Hybrid query execution utilities for agent-driven academic search workflows."""

import logging
from typing import Optional, List, Dict, Any
from main.service.agent import get_agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class QueryResult:
    """Result of a hybrid query with tool tracking and node parsing."""
    def __init__(
        self, 
        question: str, 
        answer: str, 
        tools_used: Optional[List[str]] = None, 
        source_nodes: Optional[List[Dict[str, Any]]] = None,
        guardrails_report: Optional[Dict[str, Any]] = None
    ):
        """Initialize the query result with answer, tool history, and source context."""
        self.question = question
        self.answer = answer
        self.tools_used = tools_used or []
        self.source_nodes = source_nodes or []
        self.guardrails_report = guardrails_report or {"input_validation": {"passed": True}}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        if self.tools_used:
            sources_description = f"Agent used: {', '.join(self.tools_used)}"
        else:
            sources_description = "Agent reasoning without external tools"
            
        return {
            "question": self.question,
            "answer": self.answer,
            "tools_used": self.tools_used if self.tools_used else None,
            "sources_used": sources_description,
            "source_nodes": self.source_nodes,  # Now correctly returns structured metadata maps
            "guardrails_report": self.guardrails_report
        }

async def execute_hybrid_query(question: str) -> QueryResult:
    """
    Execute a hybrid agentic query that can use SQL database, vector store, or MCP tools.
    """
    logger.info(f"Executing hybrid query: {question}")
    agent = await get_agent()
    
    try:
        handler = agent.run(question, max_iterations=40)
        response = await handler
        
        # 1. Safely pull executed tools and map them dynamically
        tools_used = _extract_tools_used(agent, response)
        logger.info(f"Query completed. Tools used: {tools_used}")
        
        # 2. Extract context nodes populated during tool operations
        source_nodes = _extract_source_nodes(response)
        
        return QueryResult(
            question=question,
            answer=str(response),
            tools_used=tools_used,
            source_nodes=source_nodes
        )
        
    except Exception as run_error:
        error_msg = str(run_error)
        if "Max iterations" in error_msg:
            logger.warning(f"Agent trapped in infinite loop execution: {error_msg}")
            
            loop_guardrail_report = {
                "input_validation": {"passed": True},
                "security_check": {"passed": True},
                "output_validation": {"passed": False, "warnings": ["Agent loop execution timeout exceeded"]},
                "retrieval_method": "agentic_hybrid_search"
            }
            
            return QueryResult(
                question=question,
                answer="I was unable to compile the research results safely within a secure runtime execution window.",
                tools_used=["Workflow_Iteration_Timeout"],
                guardrails_report=loop_guardrail_report
            )
        raise run_error

def _extract_tools_used(agent, response) -> List[str]:
    """
    Robust extraction of internal and dynamic external MCP tool calls from AgentWorkflow response streams.
    """
    tools_used = []
    
    # Check directly inside the response history steps
    if hasattr(response, "sources") and response.sources:
        for source in response.sources:
            tool_name = getattr(source, "tool_name", None)
            if not tool_name and isinstance(source, dict):
                tool_name = source.get("tool_name")
            
            if tool_name:
                friendly_name = _map_tool_name(tool_name)
                if friendly_name not in tools_used:
                    tools_used.append(friendly_name)

    # Backup extraction from raw event message payload strings
    if not tools_used and hasattr(response, "response") and hasattr(response.response, "sources"):
        for source in response.response.sources:
            tool_name = getattr(source, "tool_name", None)
            if tool_name:
                friendly_name = _map_tool_name(tool_name)
                if friendly_name not in tools_used:
                    tools_used.append(friendly_name)
                    
    return tools_used

def _extract_source_nodes(response) -> List[Dict[str, Any]]:
    """
    Extracts raw or unstructured reference items emitted by underlying agent tools.
    """
    extracted_nodes = []
    
    # Safely pull the nodes returned from vector tool engine responses nested in the agent payload
    if hasattr(response, "sources") and response.sources:
        for source in response.sources:
            raw_output = getattr(source, "raw_output", None)
            # If the raw tool output context contains standard node schemas, unpack them
            if hasattr(raw_output, "source_nodes") and raw_output.source_nodes:
                for node_with_score in raw_output.source_nodes:
                    node = getattr(node_with_score, "node", node_with_score)
                    extracted_nodes.append({
                        "content_type": node.metadata.get("content_type", "text") if hasattr(node, "metadata") else "text",
                        "source": node.metadata.get("source", "local_file") if hasattr(node, "metadata") else "local_file",
                        "text_preview": node.text[:200] + "..." if hasattr(node, "text") and len(node.text) > 200 else getattr(node, "text", ""),
                        "metadata": node.metadata if hasattr(node, "metadata") else {}
                    })
    return extracted_nodes

def _map_tool_name(internal_name: str) -> str:
    """
    Standardizes internal tool tracking signatures while letting dynamic MCP tools pass safely.
    """
    if not internal_name:
        return "Unknown Tool"
              
    name_lower = internal_name.lower()
    if "sql" in name_lower or "database" in name_lower or "academic_database" in name_lower:
        return "SQL Database (Academic_database)"
    elif "vector" in name_lower or "papers" in name_lower or "academic_papers" in name_lower:
        return "Vector Store (Academic_papers)"
    
    # DYNAMIC DEDUCTION: If it's an academic-mcp subprocess tool, format cleanly
    return f"Academic MCP Tool ({internal_name})"