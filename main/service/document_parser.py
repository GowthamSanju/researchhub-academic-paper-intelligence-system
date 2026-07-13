"""Document parsing using LlamaParse for text and tables, PyMuPDF for images."""
import logging
import os
from typing import Dict, List, Optional
from pathlib import Path
from llama_parse import LlamaParse

from .table_extraction import find_markdown_tables

logger = logging.getLogger(__name__)


def load_documents(file_path: str) -> str:
    """
    Load and parse document to markdown using LlamaParse.
    
    Supports: PDF, DOCX, TXT, MD formats
    
    Args:
        file_path: Path to the document file (PDF, DOCX, TXT, or MD)
        
    Returns:
        Full markdown text from the document
        
    Raises:
        SystemExit: If LLAMA_CLOUD_API_KEY is missing or LlamaParse fails
    """
    logger.info(f"Loading document: {file_path}")
    llama_parse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not llama_parse_api_key:
        logger.error("Missing LLAMA_CLOUD_API_KEY in environment")
        raise SystemExit("Missing LLAMA_CLOUD_API_KEY in environment. Get one from https://cloud.llamaindex.ai/")

    logger.info("Initializing LlamaParse parser...")
    
    parser_lp = LlamaParse(result_type="markdown", verbose=True)
    
    logger.info(f"Parsing document with LlamaParse: {file_path}")
    documents = parser_lp.load_data(file_path)
    
    if not documents or not documents[0].text:
        logger.error("No content returned by LlamaParse")
        raise SystemExit("No content returned by LlamaParse.")
    
    logger.info(f"LlamaParse returned {len(documents)} document(s)")
    
    # Combine all document text
    full_text = "\n\n".join([doc.text for doc in documents])
    logger.info(f"Combined text length: {len(full_text)} characters")
    
    return full_text


def extract_tables_from_text(text: str) -> List[str]:
    """
    Extract markdown tables from text.
    
    Args:
        text: Markdown text to search for tables
        
    Returns:
        List of markdown table strings
    """
    logger.info("Extracting markdown tables from text...")
    tables = find_markdown_tables(text)
    if not tables:
        logger.info("No markdown tables found in text")
        return []
    
    # Extract just the table strings (third element of each tuple)
    table_strings = [tb[2] for tb in tables]
    logger.info(f"Extracted {len(table_strings)} table(s) from document")
    return table_strings
