"""
Metadata Service Module

Handles:
- File metadata extraction
- Legal document metadata extraction from filenames
- Optional path-based metadata extraction

Missing metadata fields are omitted automatically.
"""

import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Legal document categories
DOCUMENT_TYPES = [
    "contract",
    "agreement",
    "nda",
    "lease",
    "policy",
    "judgment",
    "petition",
    "notice",
    "affidavit",
    "invoice",
]

PRACTICE_AREAS = [
    "employment",
    "corporate",
    "compliance",
    "tax",
    "property",
    "intellectual-property",
    "litigation",
]

DOCUMENT_STATUS = [
    "draft",
    "review",
    "approved",
    "executed",
    "final",
]


def _find_match(text: str, keywords: list[str]) -> str | None:
    """
    Find the first matching keyword in text.

    Supports:
    - hyphenated values
    - underscored values
    """

    text = text.lower()

    for keyword in keywords:
        variations = [
            keyword,
            keyword.replace("-", "_"),
            keyword.replace("-", " "),
        ]

        if any(variation in text for variation in variations):
            return keyword

    return None


def extract_legal_metadata_from_filename(
    filename: str,
) -> Dict[str, Any]:
    """
    Extract legal metadata from filename.

    Example:
        employment_contract_final.pdf

    Returns:
        {
            "document_type": "contract",
            "practice_area": "employment",
            "document_status": "final"
        }
    """

    filename_lower = filename.lower()
    metadata: Dict[str, Any] = {}

    document_type = _find_match(
        filename_lower,
        DOCUMENT_TYPES,
    )
    if document_type:
        metadata["document_type"] = document_type

    practice_area = _find_match(
        filename_lower,
        PRACTICE_AREAS,
    )
    if practice_area:
        metadata["practice_area"] = practice_area

    document_status = _find_match(
        filename_lower,
        DOCUMENT_STATUS,
    )
    if document_status:
        metadata["document_status"] = document_status

    logger.debug(
        "Extracted metadata from '%s': %s",
        filename,
        metadata,
    )

    return metadata


def extract_path_metadata(
    file_path: str,
) -> Dict[str, Any]:
    """
    Extract metadata from folder structure.

    Example:
        legal/contracts/employment_contract.pdf

    Returns:
        {
            "department": "legal",
            "document_category": "contracts"
        }
    """

    path = Path(file_path)
    parts = [part.lower() for part in path.parts]

    metadata: Dict[str, Any] = {}

    if "legal" in parts:
        metadata["department"] = "legal"

    if "contracts" in parts:
        metadata["document_category"] = "contracts"

    if "litigation" in parts:
        metadata["practice_area"] = "litigation"

    return metadata


def get_file_metadata(
    file_path: str,
) -> Dict[str, Any]:
    """
    Extract complete metadata for a legal document.

    Always returns:
    - source
    - file_path
    - file_extension
    - file_size

    Optionally returns:
    - document_type
    - practice_area
    - document_status
    - department
    - document_category
    """

    path = Path(file_path)

    metadata: Dict[str, Any] = {
        "source": path.name,
        "file_path": str(path),
        "file_extension": path.suffix.lower(),
        "file_size": path.stat().st_size if path.exists() else 0,
    }

    metadata.update(
        extract_legal_metadata_from_filename(path.name)
    )

    metadata.update(
        extract_path_metadata(file_path)
    )

    return metadata