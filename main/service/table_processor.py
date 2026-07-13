"""Table processing module for generating text summaries."""

import logging
from typing import List, Optional
from llama_index.core.schema import TextNode
from llama_index.llms.azure_openai import AzureOpenAI
from openai import BadRequestError

logger = logging.getLogger(__name__)


class TableProcessor:
    """Processes tables by generating text summaries."""
    
    def __init__(self, llm: AzureOpenAI):
        """
        Initialize table processor.
        
        Args:
            llm: LLM instance for generating summaries
        """
        self.llm = llm
    
    def process(self, table_text: str, metadata: dict = None) -> List[TextNode]:
        """
        Process table by generating a text summary.
        
        Args:
            table_text: Table content as text (markdown or structured format)
            metadata: Additional metadata to attach to the node
            
        Returns:
            List containing a single TextNode with table summary
        """
        if not table_text or not table_text.strip():
            return []
        
        # Truncate very long table data to avoid token limits and content filter issues
        max_table_length = 5000  # characters
        truncated_table = table_text[:max_table_length]
        if len(table_text) > max_table_length:
            truncated_table += "\n[... table truncated ...]"
            logger.warning(f"Table data truncated from {len(table_text)} to {max_table_length} characters")
        
        # Use a more structured prompt that's less likely to trigger content filters
        # Be explicit and direct to avoid jailbreak detection
        prompt = f"""You are a data analyst. Analyze the following table and provide a clear, factual summary.

Focus on:
- Key numerical values and figures
- Important trends or patterns
- Significant data points

Table data:
{truncated_table}

Provide a concise summary of the key information in this table."""
        
        try:
            response = self.llm.complete(prompt)
            summary = str(response).strip()
        except BadRequestError as e:
            # Handle content filter errors
            error_message = str(e)
            if "content_filter" in error_message or "ResponsibleAIPolicyViolation" in error_message:
                logger.warning(f"Content filter triggered for table summary. Using fallback summary.")
                # Create a basic summary from the table structure
                summary = self._create_fallback_summary(truncated_table)
            else:
                # Re-raise if it's a different error
                logger.error(f"Error generating table summary: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error generating table summary: {e}")
            # Use fallback summary
            summary = self._create_fallback_summary(truncated_table)
        
        # Create a single node with the summary
        node_metadata = metadata or {}
        node_metadata["content_type"] = "table_summary"
        #node_metadata["original_table"] = table_text  # Keep original for reference
        
        node = TextNode(
            text=summary,
            metadata=node_metadata,
        )
        
        return [node]
    
    def _create_fallback_summary(self, table_text: str) -> str:
        """
        Create a fallback summary when LLM call fails due to content filter.
        
        Args:
            table_text: The table text to summarize
            
        Returns:
            A basic summary string
        """
        # Extract basic information from table structure
        lines = table_text.split('\n')
        # Count rows (non-empty lines that look like table rows)
        row_count = sum(1 for line in lines if line.strip() and '|' in line)
        
        # Try to extract header if it exists
        header = ""
        for line in lines[:3]:
            if '|' in line and not all(c in '|-: ' for c in line.strip()):
                header = line.strip()
                break
        
        summary = f"Table containing {row_count} rows"
        if header:
            summary += f" with columns: {header[:200]}"
        
        summary += ". Table data available in original format."
        return summary

