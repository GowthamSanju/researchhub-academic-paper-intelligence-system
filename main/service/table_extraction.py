"""Table extraction utilities from markdown text."""
import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


def find_markdown_tables(md_text: str) -> List[Tuple[int, int, str]]:
    """
    Extract markdown table blocks from text.

    Returns a list of tuples: (start_index, end_index, table_string)
    
    Args:
        md_text: Markdown text to search for tables
        
    Returns:
        List of tuples containing (start_char_index, end_char_index, table_markdown)
    """
    logger.debug(f"Searching for markdown tables in text ({len(md_text)} characters)")
    lines = md_text.splitlines()
    tables: List[Tuple[int, int, str]] = []

    i = 0
    while i < len(lines):
        # find a line that looks like a header row starting with |
        if lines[i].strip().startswith("|") and "|" in lines[i].strip()[1:]:
            header_idx = i
            # next line should be a separator like |---|---|
            if i + 1 < len(lines):
                sep = lines[i + 1].strip()
                if sep.startswith("|") and re.fullmatch(r"\|[\-:\s\|]+\|", sep):
                    # collect following rows that also start with |
                    j = i + 2
                    while j < len(lines) and lines[j].strip().startswith("|"):
                        j += 1
                    # capture table block
                    table_block = "\n".join(lines[header_idx:j]).strip()
                    start_char = len("\n".join(lines[:header_idx])) + (1 if header_idx > 0 else 0)
                    end_char = start_char + len(table_block)
                    tables.append((start_char, end_char, table_block))
                    logger.debug(f"Found table at lines {header_idx+1}-{j}, length: {len(table_block)} characters")
                    i = j
                    continue
        i += 1

    logger.info(f"Extracted {len(tables)} markdown table(s) from document")
    return tables

