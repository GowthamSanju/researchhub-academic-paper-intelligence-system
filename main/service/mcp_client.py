"""Academic MCP service wrapper to load external research tools as LlamaIndex functions."""

import logging
import sys
from typing import List
from llama_index.core.tools import BaseTool

try:
    from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
except ImportError as exc:
    logging.error(
        "llama-index-tools-mcp not found. Install 'llama-index-tools-mcp' to use MCP capabilities."
    )
    BasicMCPClient = None
    McpToolSpec = None

logger = logging.getLogger(__name__)

class AcademicMCPService:
    """
    Service to spin up and orchestrate a local Academic Research MCP Engine.
    Provides deep extraction/search across ArXiv, PubMed, and Semantic Scholar.
    """
    def __init__(self) -> None:
        """Prepare the academic MCP subprocess command and local tool orchestration settings."""
        # We leverage standard stdio transport by invoking the server command line package
        # Alternate option: ["uvx", "google-scholar-search-mcp"]
        self.command = "uvx"
        self.args = ["academic-mcp"]
        self.headers = {}

    async def load_tools(
        self, allowed_tools: List[str] | None = None
    ) -> List[BaseTool]:
        """
        Spins up the sub-process academic MCP server and returns executable tools.
        """
        logger.info("Initializing Academic Research MCP Server Subprocess...")
        if BasicMCPClient is None or McpToolSpec is None:
            logger.warning("MCP package not installed; skipping academic tools.")
            return []
            
        try:
            # Initialize Client via local command/stdio pipeline instead of remote URL
            client = BasicMCPClient(
                command_or_url=self.command,
                args=self.args
            )
            
            # Wrap discovered capabilities as native LlamaIndex Tools
            tool_spec = McpToolSpec(client=client)
            tools = await tool_spec.to_tool_list_async()
            
            if allowed_tools:
                filtered_tools = [t for t in tools if t.metadata.name in allowed_tools]
                logger.info(f"Filtered to {len(filtered_tools)} academic tools out of {len(tools)} available.")
                return filtered_tools
                
            logger.info(f"Successfully loaded academic tools: {[t.metadata.name for t in tools]}")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to spawn/load Academic MCP engine: {str(e)}")
            # Fallback cleanly so your local text and SQL engines don't crash
            return []