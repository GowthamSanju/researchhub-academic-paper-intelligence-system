"""Core RAG service orchestrating multi-modal document processing and querying."""
import logging
import os
import tempfile
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.schema import TextNode
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.vector_stores.postgres import PGVectorStore

from .metadata import get_file_metadata, extract_legal_metadata_from_filename
from .semantic_chunking import SemanticChunker
from .table_extraction import find_markdown_tables
from .table_processing import build_nodes_from_tables
from .image_extraction import extract_images_from_pdf
from .captioning import generate_caption

logger = logging.getLogger(__name__)


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
        name
        for name, val in [
            ("AZURE_OPENAI_API_KEY", api_key),
            ("AZURE_OPENAI_ENDPOINT", endpoint),
            ("AZURE_OPENAI_LLM_DEPLOYMENT", llm_deployment),
            ("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", embedding_deployment),
        ]
        if not val
    ]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        raise EnvironmentError("Missing environment variables: " + ", ".join(missing))

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
    )

    try:
        Settings.llm = llm
        Settings.embed_model = embed_model
    except Exception as e:
        logger.warning(f"Could not set global Settings: {e}, models will be passed directly")

    logger.info("LLM and embedding models configured successfully")
    return llm, embed_model


def load_documents(pdf_path: str) -> str:
    """
    Load and parse PDF document to markdown using LlamaParse.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Full markdown text from the document
    """
    logger.info(f"Loading PDF document: {pdf_path}")
    llama_parse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not llama_parse_api_key:
        logger.error("Missing LLAMA_CLOUD_API_KEY in environment")
        raise SystemExit(
            "Missing LLAMA_CLOUD_API_KEY in environment. Get one from https://cloud.llamaindex.ai/"
        )

    logger.info("Initializing LlamaParse parser...")
    parser_lp = LlamaParse(result_type="markdown", verbose=True)
    documents = parser_lp.load_data(pdf_path)

    if not documents:
        logger.error("No content returned by LlamaParse")
        raise SystemExit("No content returned by LlamaParse.")

    full_text = "\n\n".join(doc.text for doc in documents if getattr(doc, "text", ""))
    if not full_text.strip():
        logger.error("Parsed document appears empty")
        raise SystemExit("Parsed document appears empty.")

    logger.info(f"Document parsed successfully, extracted {len(full_text)} characters of text")
    return full_text


def create_vector_store(embed_dim: int = 1536) -> PGVectorStore:
    """
    Create a PostgreSQL vector store instance.

    Args:
        embed_dim: Dimension of the embeddings

    Returns:
        PGVectorStore instance
    """
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "rag_db")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    table_name = os.getenv("DB_TABLE_NAME")


    if not table_name:
        logger.error("DB_TABLE_NAME environment variable is required")
        raise EnvironmentError(
            "DB_TABLE_NAME environment variable is required. Please set it in your .env file."
        )

    logger.info(f"Using table name from DB_TABLE_NAME environment variable: {table_name}")
    return PGVectorStore.from_params(
        database=database,
        host=host,
        password=password,
        port=int(port),
        user=user,
        table_name=table_name,
        embed_dim=embed_dim,
    )


class RAGService:
    """Core service for multi-modal RAG system."""
    
    def __init__(self):
        """Initialize the RAG service."""
        self.index: Optional[VectorStoreIndex] = None
        self.llm = None
        self.embed_model = None
        self.semantic_chunker = None
        self._initialized = False
        self._index_loaded = False
    
    def initialize(self):
        """Initialize LLM, embeddings, and processors."""
        if not self._initialized:
            logger.info("Initializing LLM and embedding models...")
            self.llm, self.embed_model = configure_llm_and_embeddings()
            
            # Initialize semantic chunker
            self.semantic_chunker = SemanticChunker(self.embed_model)
            
            self._initialized = True
            logger.info("RAG service initialized successfully")
            
            # Try to load existing index after initialization
            if not self._index_loaded:
                self._load_existing_index()
    
    def _load_existing_index(self):
        """Load existing index from PostgreSQL if it exists."""
        if self._index_loaded:
            return
        
        self._index_loaded = True
        
        try:
            logger.info("Attempting to load existing index from PostgreSQL...")
            
            if not self._initialized:
                self.initialize()
            
            vector_store = create_vector_store(embed_dim=1536)
            
            try:
                Settings.embed_model = self.embed_model
                index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            except Exception as e1:
                logger.debug(f"First attempt to load index failed: {e1}, trying with explicit embed_model...")
                try:
                    index = VectorStoreIndex.from_vector_store(
                        vector_store=vector_store,
                        embed_model=self.embed_model
                    )
                except Exception as e2:
                    logger.debug(f"Second attempt to load index failed: {e2}")
                    raise e2
            
            self.index = index
            logger.info("Successfully loaded existing index from PostgreSQL")
        except Exception as e:
            logger.info(f"No existing index found in PostgreSQL (this is normal for first run): {type(e).__name__}: {e}")
            self.index = None
    
    def process_document(
        self,
        pdf_path: str,
        original_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF document and add it to the multi-modal index.
        
        Processes text (with semantic chunking), tables, and images.
        
        Args:
            pdf_path: Path to the PDF file (may be temporary)
            original_filename: Original filename to use in metadata
            
        Returns:
            Dictionary with processing results including node statistics
        """
        logger.info("Processing document (boilerplate): %s", pdf_path)
        logger.info(f"Processing document: {pdf_path}")
        try:
            self.initialize()
    
            metadata = get_file_metadata(pdf_path)
            if original_filename :
                metadata["source"] = original_filename
                metadata["file_path"] = original_filename
                legal_metadata = extract_legal_metadata_from_filename(original_filename)
                metadata.update(legal_metadata)
            logger.info(f"Extracted metadata: {metadata}")
            
            markdown_text = load_documents(pdf_path)
            tables = find_markdown_tables(markdown_text)
            image_infos = []

            if Path(pdf_path).suffix.lower() == ".pdf":
                image_output_dir = Path(tempfile.gettempdir()) / "legal_doc_images"

                image_infos = extract_images_from_pdf(
                    pdf_path,
                    str(image_output_dir)
                )
            
            all_nodes = []
            
            
            text_nodes = self.semantic_chunker.process(
                text=markdown_text,
                metadata=metadata
            )
            
            for node in text_nodes:
                node.metadata.update(metadata)
                node.metadata["content_type"] = "text"
            all_nodes.extend(text_nodes)
            
            table_nodes = build_nodes_from_tables(
                source_name=metadata["source"],
                table_markdowns=[t[2] for t in tables],
                llm=self.llm,
                additional_metadata=metadata
            )
            for idx, node in enumerate(table_nodes):
                node.metadata["table_chunk_id"] = idx
            
            all_nodes.extend(table_nodes)
            
            image_nodes = []
            
            for image_info in image_infos:
                try:
                    caption = generate_caption(image_info["path"])
                except Exception as e:
                    logger.error(f"Failed to caption image {image_info["path"]}: {e}")
                    caption = (
                        f"Image extracted from page "
                        f"{image_info.get('page', 'unknown')}"
                    )
                
                image_node = TextNode(
                    text = caption,
                    metadata={
                        **metadata,
                        "content_type": "image_caption",
                        "image_path": str(image_info["path"]),
                        "page": image_info["page"],
                        "image_index": image_info["image_index"],
                    }
                )
                image_nodes.append(image_node)
                
            all_nodes.extend(image_nodes)
                
            logger.info("Created nodes -> total: %d | text: %d | tables: %d | images: %d", len(all_nodes), len(text_nodes), len(table_nodes), len(image_nodes))
                
            vector_store = create_vector_store(embed_dim=1536)
                
            if self.index is None:
                logger.info("Creating/loading VectorStoreIndex...")

                try:
                    self.index = VectorStoreIndex.from_vector_store(
                        vector_store=vector_store,
                        embed_model=self.embed_model
                    )

                    logger.info("Loaded existing index from vector store")

                except Exception as e:
                    logger.warning(
                        f"Failed to load existing index: {e}. "
                        "Creating a new index instead."
                    )

                    try:
                        self.index = VectorStoreIndex(
                            nodes=all_nodes,
                            vector_store=vector_store,
                            embed_model=self.embed_model
                        )

                        logger.info("Created new index from nodes")

                    except Exception as inner_e:
                        logger.error(
                            f"Failed to create new index: {inner_e}"
                        )
                        raise
            else:
                self.index.insert_nodes(all_nodes)
            logger.info("Successfully indexed %d nodes", len(all_nodes))
                
            return {
                "message": "Document processed successfully",
                "documents_indexed": 1,
                "total_nodes": len(all_nodes),
                "text_nodes": len(text_nodes),
                "table_nodes": len(table_nodes),
                "image_nodes": len(image_nodes),
                "file_path": metadata.get("file_path"),
                "source": metadata.get("source"),
            }
        except Exception as e:

            logger.exception("Failed to process document")

            return {
                "message": f"Failed to process document: {str(e)}",
                "documents_indexed": 0,
                "total_nodes": 0,
                "text_nodes": 0,
                "table_nodes": 0,
                "image_nodes": 0,
                "file_path": pdf_path,
                "error": str(e),
            }
    
    def is_initialized(self) -> bool:
        """Check if the service has been initialized with a document."""
        if not self.index and not self._index_loaded:
            try:
                self._load_existing_index()
            except Exception:
                pass
        return self.index is not None


# Global singleton instance for use in tools and other modules
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get or create the global RAGService singleton instance.
    
    Returns:
        RAGService instance
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
