"""Agent orchestration module for academic RAG queries with SQL, vector, and MCP tools."""

import logging
import os
from dotenv import load_dotenv
from llama_index.core.agent.workflow.multi_agent_workflow import AgentWorkflow
from llama_index.core import Settings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from main.service.tools import get_sql_tool, get_vector_tool
from .mcp_client import AcademicMCPService

load_dotenv()

_agent = None

async def get_agent():
    """Get or create the OpenAI agent with SQL, Vector, and Academic MCP tools."""
    global _agent
    if _agent is None:
        # Initialize LLM
        llm = AzureOpenAI(
            model=os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT"),
            deployment_name=os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
        Settings.llm = llm

        # Initialize Embeddings
        embed_model = AzureOpenAIEmbedding(
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            deployment_name=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
        Settings.embed_model = embed_model

        # Build local workspace tools
        sql_tool = get_sql_tool()
        vector_tool = get_vector_tool()
        
        # Load the new Academic Engine
        mcp_service = AcademicMCPService()
        mcp_tools = await mcp_service.load_tools(allowed_tools=None)
        if not isinstance(mcp_tools, list):
            mcp_tools = [mcp_tools]
        
        tools = [sql_tool, vector_tool, *mcp_tools]
        logger = logging.getLogger(__name__)
        logger.info(f"Creating academic coordinator workflow with {len(tools)} tools.")

        _agent = AgentWorkflow.from_tools_or_functions(
            tools,
            llm=llm,
            verbose=True,
            system_prompt="""
            You are an advanced Academic Intelligence System designed for comprehensive research orchestration.
            You have access to three tool domains:
            1) Academic_database: Best for querying our internal structural SQL database grids (metrics, citation counts, tracking records, specific paper tracking indices).
            2) Academic_papers: Best for semantic search inside our internal vector document store (qualitative analysis, extracted markdown tables, internal goals/theses).
            3) Academic MCP Tools: External global lookup endpoints (e.g., paper_search, paper_download). 

            CRITICAL GROUNDING DIRECTIVES:
            - Always try to resolve queries using internal resources ('Academic_database' or 'Academic_papers') first.
            - Only invoke external Academic MCP tools when the user explicitly requests live literature research, broad external cross-referencing, or information completely absent from the local vector/SQL repository.
            - Never use your own internal pre-trained weights to answer general knowledge or trivia queries. If all tools lack the required context, explain that the context is unavailable.

            EXAMPLE OF CORRECT FAILURE HANDLING:
            User Query: "Can you give me a step-by-step financial trading strategy for buying cryptocurrency options based on quantum physics formulas?"
            Agent Action: [Queries Academic_database and Academic_papers -> Returns empty]
            Correct Response: "I am unable to answer this request because the necessary context regarding cryptocurrency trading and quantum physics is completely unavailable in the internal repositories."
            """,
        )
    return _agent