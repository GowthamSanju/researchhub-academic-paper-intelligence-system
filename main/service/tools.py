"""
Tools Module - Provides SQL and Vector tools for the agentic RAG system
"""

import os
import logging

from llama_index.core import Settings
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.core.tools import FunctionTool # <-- Import FunctionTool
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

from .rag_service import get_rag_service
from .sql_service import get_sql_database

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# ----- Public API: Tool Creation -----


def get_vector_tool():
    """
    Create a FunctionTool for querying company documents stored in pgvector.

    Returns:
        FunctionTool configured for vector document search
    """
    logger.info("Creating vector tool...")

    # Initialize Azure embeddings if not already set
    if Settings._embed_model is None:
        logger.info("Initializing Azure OpenAI embeddings...")
        embed_model = AzureOpenAIEmbedding(
            model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            deployment_name=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
        Settings.embed_model = embed_model

    rag_service = get_rag_service()
    if not rag_service._index_loaded:
        rag_service._load_existing_index()

    vector_index = rag_service.index

    if vector_index is None:
        raise RuntimeError(
            "No vector index found in the RAG service. Please upload documents first via /api/upload"
        )

    query_engine = vector_index.as_query_engine()

    # Wrap the query engine's string-based query method into a FunctionTool
    def query_academic_papers(query: str) -> str:
        response = query_engine.query(query)
        return str(response)

    return FunctionTool.from_defaults(
        fn=query_academic_papers,
        name="Academic_papers",
        description=(
            "Contains unstructured academic papers, including full text, tables, and discussions. "
            "Use this tool to search through the textual content of papers or find specific written arguments."
        ),
    )


def get_sql_tool():
    """
    Create a FunctionTool for querying the SQL business database.

    Returns:
        FunctionTool configured for SQL database queries
    """
    logger.info("Creating SQL tool...")

    # Get SQL database and create query engine
    sql_database = get_sql_database()
    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_database,
        tables=[
            "papers",
            "authors",
            "paper_authors",
            "keywords",
            "paper_keywords",
            "citations",
        ],
        verbose=True,
    )

    # Wrap the SQL engine's string-based query method into a FunctionTool
    def query_academic_database(query: str) -> str:
        response = query_engine.query(query)
        return str(response)

    return FunctionTool.from_defaults(
        fn=query_academic_database,
        name="Academic_database",
        description=(
            "Contains structured metadata information about academic papers, authors, keywords, and citations. "
            "Use this tool to find papers written by specific authors, match keys, check metrics, counting, or relational data facts."
        ),
    )