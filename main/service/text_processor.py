"""Text processing module using SemanticSplitterNodeParser."""

from typing import List
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import TextNode, BaseNode
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding


class TextProcessor:
    """Processes text content using semantic chunking."""
    
    def __init__(self, embed_model: AzureOpenAIEmbedding):
        """
        Initialize text processor.
        
        Args:
            embed_model: Embedding model for semantic splitting
        """
        self.embed_model = embed_model
        self.parser = SemanticSplitterNodeParser(
            buffer_size=1,
            breakpoint_percentile_threshold=95,
            embed_model=embed_model,
        )
    
    def process(self, text: str, metadata: dict = None) -> List[TextNode]:
        """
        Process text into semantically chunked nodes.
        
        Args:
            text: Raw text content to process
            metadata: Additional metadata to attach to nodes
            
        Returns:
            List of TextNode objects with semantic chunks
        """
        if not text or not text.strip():
            return []
        
        # Create a temporary document node
        from llama_index.core.schema import Document
        doc = Document(text=text, metadata=metadata or {})
        
        # Parse into nodes
        nodes = self.parser.get_nodes_from_documents([doc])
        
        # Add content_type metadata to all nodes
        for node in nodes:
            node.metadata = node.metadata or {}
            node.metadata["content_type"] = "text"
            if metadata:
                node.metadata.update(metadata)
        
        return nodes

