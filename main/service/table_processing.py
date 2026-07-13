"""Table Processing Service Module
Handles table summarization and node creation from extracted tables.

This module provides:
- Table summarization interface
- Node creation interface for table summaries
"""
import logging
from typing import List, Dict, Any

from llama_index.core.schema import TextNode
from llama_index.llms.azure_openai import AzureOpenAI

logger = logging.getLogger(__name__)


def summarize_table(llm: AzureOpenAI, table_md: str) -> str:
    """
    Summarize a markdown table into a natural language description.
    
    Args:
        llm: The language model instance
        table_md: Markdown table string
        
    Returns:
        Single-sentence summary of the table
    """
    logger.info("Summarizing table (boilerplate)")

    prompt = (
        "Summarize the following markdown table in a single sentence. "
        "Include key figures and relationships. Be concise and factual. \n\n"
        f"Table:\n{table_md}\n\n"
        "Summary:"
    )
    try:
        resp = llm.complete(prompt)
        summary =  resp.text.strip()
        logger.info(f"Generated summary (length: {len(summary)} characters): {summary[:100]}.....")
        return summary
    except Exception as e:
        error_msg = str(e)
        if "content_filter" in error_msg or "content management policy" in error_msg:
            logger.info(f"content filter triggered. using fallback summary based on table structure.")
            lines = table_md.strip().split("\n")
            if len(lines) > 1:
                headers = lines[0] if lines else "table"
                summary = f"Table containing data with columns: {headers[:100]}"
            else:
                summary = "Table with structured data"
            return summary
        raise

def build_nodes_from_tables(
    source_name: str, 
    table_markdowns: List[str], 
    llm: AzureOpenAI,
    additional_metadata: Dict[str, Any] = None
) -> List[TextNode]:
    """
    Build TextNode objects from table markdowns with summaries.
    
    Args:
        source_name: Name of the source document
        table_markdowns: List of markdown table strings
        llm: Language model instance for summarization
        additional_metadata: Optional additional metadata to include
        
    Returns:
        List of TextNode objects with table summaries
    """
    logger.info("Building nodes from tables (boilerplate)")

    nodes: List[TextNode] = []
    base_metadata = additional_metadata or {}
    
    for idx, tbl in enumerate(table_markdowns, 1):
        logger.info(f"Processing table {idx}/{len(table_markdowns)}")
        summary = summarize_table(llm, tbl)
        node = TextNode(
            text = summary,
            metadata = {
                **base_metadata,
                "source": source_name,
                "content_type": "table_summary",
                "table_index": idx - 1,
            },
        )
        nodes.append(node)
        
    logger.info(f"Created {len(nodes)} textNode(s) with table summaries")
    return nodes
