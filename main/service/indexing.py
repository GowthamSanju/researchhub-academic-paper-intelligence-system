"""LLM, embedding, and vector store configuration for Azure OpenAI and PostgreSQL."""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Tuple

from dotenv import load_dotenv
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core import Settings
from llama_index.vector_stores.postgres import PGVectorStore

logger = logging.getLogger(__name__)


def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file metadata
    """
    path = Path(file_path)
    return {
        "source": path.name,
        "file_path": str(path),
        "file_extension": path.suffix.lower(),
        "file_size": path.stat().st_size if path.exists() else 0,
    }


def configure_llm_and_embeddings() -> Tuple[AzureOpenAI, AzureOpenAIEmbedding]:
    """
    Configure LLM and embedding models from environment variables.
    
    Returns:
        Tuple of (llm, embed_model)
        
    Raises:
        EnvironmentError: If required environment variables are missing
    """
    load_dotenv()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    llm_deployment = os.environ.get("AZURE_OPENAI_LLM_DEPLOYMENT")
    embedding_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    missing = [
        name for name, val in [
            ("AZURE_OPENAI_API_KEY", api_key),
            ("AZURE_OPENAI_ENDPOINT", endpoint),
            ("AZURE_OPENAI_LLM_DEPLOYMENT", llm_deployment),
            ("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", embedding_deployment),
        ] if not val
    ]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        raise EnvironmentError(
            "Missing environment variables: " + ", ".join(missing)
        )

    logger.info(f"Configuring Azure OpenAI LLM: deployment={llm_deployment}, endpoint={endpoint}")
    llm = AzureOpenAI(
        model="gpt-4o-mini",
        deployment_name=llm_deployment,
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )

    logger.info(f"Configuring Azure OpenAI Embedding: deployment={embedding_deployment}")
    embed_model = AzureOpenAIEmbedding(
        model=embedding_deployment,
        deployment_name=embedding_deployment,
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        dimensions=1536,
    )

    try:
        Settings.llm = llm
        Settings.embed_model = embed_model
        logger.debug("Successfully configured global Settings with LLM and embedding model")
    except Exception as e:
        logger.warning(f"Could not set global Settings: {e}, models will be passed directly")
        pass

    logger.info("LLM and embedding models configured successfully")
    return llm, embed_model


def create_vector_store(
    embed_dim: int = 1536
) -> PGVectorStore:
    """
    Create a PostgreSQL vector store instance.
    
    Args:
        embed_dim: Dimension of the embeddings (default: 1536 for text-embedding-3-small)
        
    Returns:
        PGVectorStore instance
        
    Raises:
        EnvironmentError: If required environment variables are missing
    """
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "rag_db")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    
    # Always use DB_TABLE_NAME from environment variable
    # This ensures consistency and prevents hardcoded values
    table_name = os.getenv("DB_TABLE_NAME")
    
    
    if not table_name:
        logger.error("DB_TABLE_NAME environment variable is required")
        raise EnvironmentError(
            "DB_TABLE_NAME environment variable is required. Please set it in your .env file."
        )
    
    logger.info(f"Using table name from DB_TABLE_NAME environment variable: {table_name}")
    
    logger.info(f"Creating PostgreSQL vector store: table={table_name}, embed_dim={embed_dim}, host={host}, database={database}")
    
    vector_store = PGVectorStore.from_params(
        database=database,
        host=host,
        password=password,
        port=int(port),
        user=user,
        table_name=table_name,
        embed_dim=embed_dim,
    )
    
    logger.info(f"PostgreSQL vector store created successfully: {table_name}")
    return vector_store

