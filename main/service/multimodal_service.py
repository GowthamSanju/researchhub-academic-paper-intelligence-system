"""Core multi-modal service orchestrating document processing and querying."""
import logging
import uuid
from typing import List, Optional, Dict, Any
from llama_index.core import VectorStoreIndex, Document, Settings, StorageContext
from llama_index.core.schema import BaseNode
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

from .indexing import configure_llm_and_embeddings, get_file_metadata, create_vector_store
from .document_parser import load_documents, extract_tables_from_text
from .image_extraction import extract_images_from_document
from .sql_service import create_sql_query_engine
from .text_processor import TextProcessor
from .table_processor import TableProcessor
from .image_processor import ImageProcessor
from .validators import GuardrailsValidator, get_validator

logger = logging.getLogger(__name__)


class MultimodalService:
    """Core service for multi-modal document processing and querying."""
    
    def __init__(self):
        """Initialize the multi-modal service."""
        self.index: Optional[VectorStoreIndex] = None
        self.vector_store = None
        self.storage_context = None
        self.llm = None
        self.embed_model = None
        self._initialized = False
        self._index_loaded = False  # Track if we've attempted to load existing index
        self.validator: Optional[GuardrailsValidator] = None
        self._bm25_enabled = False
        self._sql_enabled = False
        self._sql_query_engine = None
        
        # Processors (will be initialized in initialize())
        self.text_processor = None
        self.table_processor = None
        self.image_processor = None
    
    def initialize(self):
        """Initialize LLM, embeddings, processors, and guardrails validators."""
        if not self._initialized:
            logger.info("Initializing LLM and embedding models...")
            self.llm, self.embed_model = configure_llm_and_embeddings()
            
            # Initialize processors
            logger.info("Initializing processors...")
            self.text_processor = TextProcessor(self.embed_model)
            self.table_processor = TableProcessor(self.llm)
            # ImageProcessor uses captioning module which handles multi-modal LLM internally
            self.image_processor = ImageProcessor(llm=self.llm)
            
            # Initialize guardrails validator
            logger.info("Initializing guardrails validators...")
            try:
                self.validator = get_validator()
                logger.info("✓ Guardrails validators initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize guardrails: {e}")
                self.validator = None
            
            self._configure_sql_support()
            
            self._initialized = True
            logger.info("Multi-modal service initialized successfully")
            # Try to load existing index after initialization
            if not self._index_loaded:
                self._load_existing_index()
    

    def _configure_sql_support(self) -> None:
        """Configure SQL query engine support for structured database retrieval."""
        try:
            self._sql_query_engine = create_sql_query_engine()
            self._sql_enabled = True
            logger.info("✓ SQL query support initialized successfully")
        except Exception as e:
            self._sql_enabled = False
            self._sql_query_engine = None
            logger.warning(f"SQL query support unavailable: {e}")


    def _build_vector_query_engine(self, similarity_top_k: int, system_prompt: str):
        """Build a pure semantic-only vector query engine."""
        logger.info("Using semantic search only")
        query_engine = self.index.as_query_engine(
            similarity_top_k=similarity_top_k,
            system_prompt=system_prompt
        )
        return query_engine, "semantic_search"

    def _extract_answer_text(self, response) -> str:
        """Extract plain answer text from a LlamaIndex response object."""
        if hasattr(response, 'response'):
            return str(response.response).strip()
        if hasattr(response, 'get_response'):
            return str(response.get_response()).strip()
        if hasattr(response, '__str__'):
            return str(response).strip()
        return str(response).strip()

    def _load_existing_index(self):
        """Load existing index from PostgreSQL if it exists."""
        if self._index_loaded:
            return  # Already attempted
        
        self._index_loaded = True
        
        try:
            logger.info("Attempting to load existing index from PostgreSQL...")
            
            # Ensure LLM/embeddings are configured
            if not self._initialized:
                self.initialize()
            
            embed_dim = getattr(self.embed_model, 'dimension', None) or 1536
            vector_store = create_vector_store(embed_dim=embed_dim)
            
            # Try to load existing index from vector store
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
            
            # If we get here, index was loaded successfully
            self.index = index
            self.vector_store = vector_store
            logger.info("Successfully loaded existing index from PostgreSQL")
        except Exception as e:
            # This is expected on first run or if table doesn't exist yet
            # Log at info level so user can see what happened
            logger.info(f"No existing index found in PostgreSQL (this is normal for first run or if table is empty): {type(e).__name__}: {e}")
            self.index = None
            self.vector_store = None
    
    def process_document(
        self,
        file_path: str,
        document_id: Optional[str] = None,
        reset_index: bool = False,
        original_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a document and add it to the multi-modal index.
        
        Supports: PDF, DOCX, TXT, MD files
        
        Args:
            file_path: Path to the document file (may be temporary)
            document_id: Optional document ID (generated if not provided)
            reset_index: If True, reset the index before adding nodes
            original_filename: Original filename to use in metadata (if different from file_path)
            
        Returns:
            Dictionary with processing results including node statistics
        """
        if not self._initialized:
            self.initialize()
        
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        logger.info(f"Processing document: {file_path} (document_id={document_id})")
        
        # Get file metadata - use original filename if provided
        metadata = get_file_metadata(file_path)
        if original_filename:
            # Override source with original filename for better metadata
            source_name = original_filename
            metadata["source"] = original_filename
        else:
            source_name = metadata.get("source", file_path)
        
        # all_nodes can contain TextNode, ImageNode, and other BaseNode types
        # ImageNode objects are created by image_processor (same approach as demo-2)
        all_nodes: List[BaseNode] = []
        
        # Step 1: Load document with LlamaParse (like demo-1)
        logger.info("Step 1: Loading and parsing document with LlamaParse...")
        full_text = load_documents(file_path)
        logger.info(f"Document loaded successfully, text length: {len(full_text)} characters")
        
        # Step 2: Process text with semantic chunking
        if full_text:
            logger.info("Step 2: Processing text content with semantic chunking...")
            text_nodes = self.text_processor.process(
                full_text,
                metadata={"source": source_name, "page": "all", **metadata},
            )
            all_nodes.extend(text_nodes)
            logger.info(f"Created {len(text_nodes)} text nodes")
        
        # Step 3: Extract and process tables (like demo-1)
        logger.info("Step 3: Extracting markdown tables from document...")
        table_strings = extract_tables_from_text(full_text)
        if table_strings:
            logger.info(f"Found {len(table_strings)} table(s) in the document")
            for idx, table_md in enumerate(table_strings):
                logger.debug(f"Processing table {idx + 1}/{len(table_strings)}")
                table_nodes = self.table_processor.process(
                    table_md,
                    metadata={
                        "source": source_name,
                        "table_index": idx,
                        **metadata,
                    },
                )
                all_nodes.extend(table_nodes)
                logger.debug(f"Table {idx + 1} processed, created {len(table_nodes)} node(s)")
        else:
            logger.info("No tables found in document")
        
        # Step 4: Extract and process images (like demo-2)
        # Note: Temporary directory is only used for initial extraction from documents.
        # The image_processor.process_from_path() copies images to permanent storage
        # (stored_images/) and ImageNode objects use the permanent path, not temp path.
        logger.info("Step 4: Extracting images from document...")
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                images = extract_images_from_document(file_path, tmpdir)
                if images:
                    logger.info(f"Extracted {len(images)} images from document")
                    
                    for img_info in images:
                        try:
                            logger.debug(f"Processing image: {img_info['path']} (page={img_info.get('page')}, index={img_info.get('image_index')})")
                            # process_from_path() receives temp path but copies to permanent storage
                            # and returns ImageNode with permanent path
                            image_nodes = self.image_processor.process_from_path(
                                img_info["path"],  # Temp path (will be copied to permanent storage)
                                metadata={
                                    "source": source_name,
                                    "page": img_info.get("page"),
                                    "image_index": img_info.get("image_index"),
                                    **metadata,
                                },
                            )
                            all_nodes.extend(image_nodes)
                            logger.debug(f"Image processed, created {len(image_nodes)} node(s) with permanent paths")
                        except Exception as e:
                            logger.error(f"Failed to process image {img_info['path']}: {e}", exc_info=True)
                else:
                    logger.info("No images found in document")
            except Exception as e:
                logger.warning(f"Image extraction encountered an error: {e}", exc_info=True)
        
        # Calculate statistics
        text_count = sum(1 for n in all_nodes if n.metadata.get('content_type') == 'text')
        table_count = sum(1 for n in all_nodes if n.metadata.get('content_type') == 'table_summary')
        image_count = sum(1 for n in all_nodes if n.metadata.get('content_type') == 'image_caption')
        
        stats = {
            "total_nodes": len(all_nodes),
            "text_nodes": text_count,
            "table_nodes": table_count,
            "image_nodes": image_count,
        }
        
        logger.info(f"Total nodes created: {len(all_nodes)} (text: {text_count}, tables: {table_count}, images: {image_count})")
        
        # Create or update index
        logger.info("Step 5: Creating PostgreSQL vector store and indexing documents...")
        embed_dim = getattr(self.embed_model, 'dimension', None) or 1536
        
        # Reuse existing vector store if available, otherwise create new one
        if self.vector_store is None:
            self.vector_store = create_vector_store(embed_dim=embed_dim)
        else:
            logger.debug("Reusing existing vector store")
        
        if reset_index:
            try:
                self.vector_store.drop()
                logger.info("Existing table dropped")
            except Exception as e:
                logger.warning(f"Could not drop existing table: {e}")
        
        if not self.storage_context:
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
        
        if reset_index or self.index is None:
            try:
                Settings.embed_model = self.embed_model
                self.index = VectorStoreIndex(
                    nodes=all_nodes,
                    storage_context=self.storage_context,
                    embed_model=self.embed_model,
                )
                logger.info("VectorStoreIndex created successfully using Settings.embed_model")
            except Exception as e:
                logger.warning(f"Could not set Settings.embed_model: {e}, trying direct parameter...")
                self.index = VectorStoreIndex(
                    nodes=all_nodes,
                    storage_context=self.storage_context,
                    embed_model=self.embed_model,
                )
                logger.info("VectorStoreIndex created successfully using direct embed_model parameter")
        else:
            logger.info(f"Adding {len(all_nodes)} nodes to existing index...")
            self.index.insert_nodes(all_nodes)
            logger.info("Nodes added to index successfully")
        
        logger.info("Document processing completed successfully")
        
        # Use original filename in response if provided, otherwise use file_path
        response_file_path = original_filename if original_filename else file_path
        
        # Cache indexed nodes for BM25 keyword retrieval
        try:
            self._cached_documents = [
                Document(text=node.text)
                for node in all_nodes
                if hasattr(node, 'text') and node.text
            ]
            logger.info(f"Cached {len(self._cached_documents)} documents for BM25 keyword retrieval")
        except Exception as e:
            logger.warning(f"Failed to cache documents for BM25 retrieval: {e}", exc_info=True)

        # Store document metadata
        self._document_store[document_id] = {
            "file_path": response_file_path,
            "status": "processed",
            "stats": stats,
        }
        
        return {
            "document_id": document_id,
            "file_path": response_file_path,
            "status": "success",
            **stats,
        }
    
    def is_initialized(self) -> bool:
        """Check if the service and index are initialized."""
        # Try to load existing index if not already loaded
        if not self._index_loaded:
            if not self._initialized:
                self.initialize()
            else:
                self._load_existing_index()
        
        return self._initialized and self.index is not None


# Global service instance
_service: Optional[MultimodalService] = None


def get_service() -> MultimodalService:
    """Get or create the global multi-modal service instance."""
    global _service
    if _service is None:
        _service = MultimodalService()
    return _service

