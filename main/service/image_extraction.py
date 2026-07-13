"""Image extraction from documents (PDF, DOCX, TXT, MD)."""
import logging
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    Extract images from a PDF document.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        
    Returns:
        List of dictionaries containing image information:
        - path: Path to the extracted image file
        - page: Page number (0-indexed)
        - image_index: Index of the image on the page
        
    Raises:
        RuntimeError: If no images are found in the PDF
    """
    logger.info(f"Opening PDF file: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    logger.info(f"PDF opened successfully, total pages: {total_pages}")
    
    results = []
    try:
        for page_index in range(total_pages):
            logger.debug(f"Processing page {page_index + 1}/{total_pages}")
            page = doc.load_page(page_index)
            images = page.get_images(full=True)
            
            if not images:
                logger.debug(f"No images found on page {page_index + 1}")
                continue
            
            logger.info(f"Found {len(images)} image(s) on page {page_index + 1}")
            
            for img_index, img in enumerate(images):
                xref = img[0]
                logger.debug(f"Extracting image {img_index + 1} from page {page_index + 1} (xref: {xref})")
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                out_path = Path(output_dir) / f"extracted_image_page{page_index}_img{img_index}.{ext}"
                
                with open(out_path, "wb") as f:
                    f.write(image_bytes)
                
                image_size = len(image_bytes)
                logger.debug(f"Saved image to {out_path} (size: {image_size} bytes)")
                
                results.append({
                    "path": str(out_path),
                    "page": page_index,
                    "image_index": img_index,
                })
        
        if not results:
            logger.error("No images found in the PDF")
            raise RuntimeError("No images found in the PDF")
        
        logger.info(f"Image extraction completed: {len(results)} images extracted from {total_pages} pages")
        return results
    finally:
        doc.close()
        logger.debug("PDF document closed")


def extract_images_from_docx(docx_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    Extract images from a DOCX document.
    
    Args:
        docx_path: Path to the DOCX file
        output_dir: Directory to save extracted images
        
    Returns:
        List of dictionaries containing image information:
        - path: Path to the extracted image file
        - page: Page information (DOCX doesn't have traditional pages, so 0)
        - image_index: Index of the image in the document
        
    Raises:
        RuntimeError: If no images are found or error during extraction
    """
    try:
        from docx import Document
        from docx.oxml import parse_xml
    except ImportError:
        logger.error("python-docx is not installed. Install it with: pip install python-docx")
        raise RuntimeError("python-docx library is required to extract images from DOCX files")
    
    logger.info(f"Opening DOCX file: {docx_path}")
    try:
        doc = Document(docx_path)
    except Exception as e:
        logger.error(f"Failed to open DOCX file: {e}")
        raise RuntimeError(f"Failed to open DOCX file: {e}")
    
    results = []
    image_index = 0
    
    try:
        # Extract inline shapes (images embedded directly in the document)
        logger.info("Extracting images from document...")
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    image = rel.target_part
                    image_bytes = image.blob
                    
                    # Determine image format from content type
                    content_type = image.content_type
                    ext_map = {
                        "image/jpeg": "jpg",
                        "image/png": "png",
                        "image/gif": "gif",
                        "image/bmp": "bmp",
                        "image/webp": "webp",
                    }
                    ext = ext_map.get(content_type, "png")
                    
                    out_path = Path(output_dir) / f"extracted_image_docx_{image_index}.{ext}"
                    
                    with open(out_path, "wb") as f:
                        f.write(image_bytes)
                    
                    image_size = len(image_bytes)
                    logger.debug(f"Saved DOCX image to {out_path} (size: {image_size} bytes)")
                    
                    results.append({
                        "path": str(out_path),
                        "page": 0,  # DOCX doesn't have traditional pages
                        "image_index": image_index,
                    })
                    image_index += 1
                except Exception as e:
                    logger.warning(f"Failed to extract image {image_index}: {e}")
                    continue
        
        if not results:
            logger.info("No images found in the DOCX document")
            raise RuntimeError("No images found in the DOCX document")
        
        logger.info(f"Image extraction completed: {len(results)} images extracted from DOCX")
        return results
        
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Error extracting images from DOCX: {e}", exc_info=True)
        raise RuntimeError(f"Error extracting images from DOCX: {e}")


def extract_images_from_document(file_path: str, output_dir: str) -> List[Dict[str, Any]]:
    """
    Extract images from a document based on its file type.
    
    Supports: PDF, DOCX
    Note: TXT and MD files typically don't contain embedded images, so they return empty list.
    
    Args:
        file_path: Path to the document file
        output_dir: Directory to save extracted images
        
    Returns:
        List of dictionaries containing image information
        Empty list if no images are found or file type doesn't support images
    """
    file_extension = Path(file_path).suffix.lower()
    
    logger.info(f"Extracting images from {file_extension} file: {file_path}")
    
    try:
        if file_extension == ".pdf":
            return extract_images_from_pdf(file_path, output_dir)
        elif file_extension == ".docx":
            return extract_images_from_docx(file_path, output_dir)
        elif file_extension in {".txt", ".md"}:
            logger.info(f"File type {file_extension} typically doesn't contain embedded images")
            return []
        else:
            logger.warning(f"Unsupported file type for image extraction: {file_extension}")
            return []
    except RuntimeError as e:
        # If extraction fails, log and return empty list to allow processing to continue
        logger.info(f"Image extraction returned no results for {file_extension}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error during image extraction: {e}", exc_info=True)
        return []

