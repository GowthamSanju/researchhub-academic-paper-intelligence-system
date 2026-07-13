"""Image processing module for generating text captions using ImageNode (same as demo-2)."""

import logging
import shutil
from typing import List, Optional, Any
from pathlib import Path
from llama_index.core.schema import ImageNode
from llama_index.llms.azure_openai import AzureOpenAI

from .captioning import generate_caption

logger = logging.getLogger(__name__)

# Directory for storing extracted images permanently (same as demo-2)
IMAGES_STORAGE_DIR = Path("stored_images")


class ImageProcessor:
    """Processes images by generating text captions and creating ImageNode objects."""
    
    def __init__(self, llm: Optional[AzureOpenAI] = None, multi_modal_llm: Optional[Any] = None):
        """
        Initialize image processor.
        
        Args:
            llm: LLM instance (not used for images, kept for compatibility)
            multi_modal_llm: Multi-modal LLM (not used, captioning module handles it)
        """
        # Note: We use the captioning module which handles multi-modal LLM internally
        # These parameters are kept for backward compatibility but not used
        self.llm = llm
        
        # Create images storage directory if it doesn't exist (same as demo-2)
        IMAGES_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Images will be stored in: {IMAGES_STORAGE_DIR.absolute()}")
    
    def process_from_path(self, image_path: str, metadata: dict = None) -> List[ImageNode]:
        """
        Process image from file path by generating a caption and creating ImageNode.
        
        Uses the same approach as demo-2: stores image permanently and creates ImageNode
        with both caption text (for embedding) and image_path (for reference).
        
        Args:
            image_path: Path to image file (may be temporary)
            metadata: Additional metadata to attach to the node
            
        Returns:
            List containing a single ImageNode with image caption and path
        """
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Use the captioning module to generate caption
        # This handles multi-modal LLM initialization and image processing
        caption = generate_caption(image_path)
        logger.debug(f"Generated caption: {caption[:100]}...")
        
        # Copy image to permanent storage (same as demo-2)
        source_path = Path(image_path)
        source_name = metadata.get("source", "unknown") if metadata else "unknown"
        safe_source_name = Path(source_name).stem.replace(" ", "_")
        page = metadata.get("page", 0) if metadata else 0
        image_index = metadata.get("image_index", 0) if metadata else 0
        
        # Create a unique filename based on source document and image index
        permanent_filename = f"{safe_source_name}_page{page}_img{image_index}{source_path.suffix}"
        permanent_path = IMAGES_STORAGE_DIR / permanent_filename
        
        # Copy image to permanent location
        shutil.copy2(source_path, permanent_path)
        logger.info(f"Stored image permanently at: {permanent_path}")
        permanent_path_str = str(permanent_path)
        
        # Create ImageNode directly (same as demo-2)
        node_metadata = metadata or {}
        node_metadata["content_type"] = "image_caption"
        node_metadata["image_path"] = permanent_path_str  # Store permanent path in metadata
        
        # Create ImageNode with caption text (for embedding) and image_path (for reference)
        image_node = ImageNode(
            text=caption,  # The caption for embedding/search
            image_path=permanent_path_str,  # Permanent path to the image
            metadata=node_metadata,
        )
        
        return [image_node]

