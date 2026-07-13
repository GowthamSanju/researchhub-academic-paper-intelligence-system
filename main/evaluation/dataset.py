"""Create Langfuse evaluation datasets for the academic RAG system."""

import os
import logging
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()
logger = logging.getLogger(__name__)


def get_langfuse_client() -> Langfuse:
    """Initialize Langfuse client using environment variables."""
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not secret_key or not public_key:
        raise RuntimeError(
            "LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY must be set in environment."
        )

    return Langfuse(
        secret_key=secret_key,
        public_key=public_key,
        host=host,
    )


def create_dataset(langfuse: Langfuse, dataset_name: str, use_logger: bool = False):
    """Create an evaluation dataset in Langfuse."""
    log_func = logger.info if use_logger else print
    log_func(f"Creating dataset '{dataset_name}' if it does not exist...")

    langfuse.create_dataset(
        name=dataset_name,
        description="Academic RAG evaluation dataset for answer quality scoring",
        metadata={
            "domain": "academic_paper_intelligence",
            "type": "rag_evaluation",
            "version": "1.0",
            "source": "evaluation_suite",
        },
    )
    log_func("✓ Dataset created (or already exists).")


def add_items(langfuse: Langfuse, dataset_name: str, use_logger: bool = False):
    """Add evaluation items to the Langfuse dataset."""
    log_func = logger.info if use_logger else print

    test_cases = [
        # Easy factual questions (3)
        {
            "input": "What is the primary goal of an academic literature review?",
            "expected_output": "The primary goal is to summarize, synthesize, and contextualize existing research on a topic.",
            "category": "literature_review",
            "difficulty": "easy",
        },
        {
            "input": "What section of a paper usually contains experiment details and results?",
            "expected_output": "The Methods and Results sections contain experiment details and outcomes.",
            "category": "paper_structure",
            "difficulty": "easy",
        },
        {
            "input": "What does the abstract of a research paper summarize?",
            "expected_output": "It summarizes the research question, methods, main findings, and conclusion in brief form.",
            "category": "paper_structure",
            "difficulty": "easy",
        },
        # Medium questions (4)
        {
            "input": "How should a student verify whether a reported claim is supported by the cited source?",
            "expected_output": "They should compare the claim to the original source text and check that the citation directly supports the statement.",
            "category": "fact_checking",
            "difficulty": "medium",
        },
        {
            "input": "What is the best way to extract a table of experimental results from a PDF?",
            "expected_output": "Use a PDF parser or table extraction tool to convert the tabular data into structured text or CSV, then verify the values against the original PDF.",
            "category": "data_extraction",
            "difficulty": "medium",
        },
        {
            "input": "Why is it important to include source metadata when indexing academic documents?",
            "expected_output": "Source metadata helps preserve provenance, enables filtering by document, and improves retrieval accuracy during question answering.",
            "category": "indexing",
            "difficulty": "medium",
        },
        {
            "input": "How can the system determine whether an answer is grounded in the retrieved document context?",
            "expected_output": "By comparing each claim in the answer to the retrieved source text and checking that the answer does not introduce unsupported facts.",
            "category": "evaluation",
            "difficulty": "medium",
        },
        # Hard edge-case questions (3)
        {
            "input": "If a figure caption and table caption differ about the same experimental result, what should the answer say?",
            "expected_output": "The answer should note the discrepancy and state that the document contains conflicting captions for the same result, recommending verification from the original source.",
            "category": "conflict_resolution",
            "difficulty": "hard",
            "edge_case": "conflicting_documentation",
        },
        {
            "input": "Can the system infer a conclusion from a paper if the conclusion section is missing?",
            "expected_output": "No, it should say the conclusion section is absent and avoid inventing a conclusion not supported by the available text.",
            "category": "hallucination_prevention",
            "difficulty": "hard",
            "edge_case": "missing_section",
        },
        {
            "input": "How should the RAG system handle a question about a paper reference that is not in the indexed documents?",
            "expected_output": "It should report that the referenced paper is not available in the indexed documents and avoid fabricating details from unknown sources.",
            "category": "source_coverage",
            "difficulty": "hard",
            "edge_case": "missing_reference",
        },
    ]

    existing_questions = set()
    try:
        dataset = langfuse.get_dataset(dataset_name)
        for item in dataset.items:
            question = item.input.get("question") if isinstance(item.input, dict) else None
            if question:
                existing_questions.add(question)
        log_func(f"Found {len(existing_questions)} existing items in dataset '{dataset_name}'")
    except Exception as exc:
        log_func(f"Could not retrieve existing dataset items: {exc}")

    new_items = [case for case in test_cases if case["input"] not in existing_questions]
    if not new_items:
        log_func(f"✓ All {len(test_cases)} items already exist. No new items to add.")
        return

    log_func(f"Adding {len(new_items)} new items to dataset '{dataset_name}'...")
    for idx, case in enumerate(new_items, start=1):
        metadata = {
            "category": case["category"],
            "difficulty": case["difficulty"],
            "source": "academic_paper_intelligence",
        }
        if "edge_case" in case:
            metadata["edge_case"] = case["edge_case"]

        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            input={"question": case["input"]},
            expected_output=case["expected_output"],
            metadata=metadata,
        )
        log_func(f"  ✓ Added item {idx}/{len(new_items)} ({case['difficulty']}): {case['input']}")

    log_func(f"✓ Added {len(new_items)} new items to dataset '{dataset_name}'.")


def main(use_logger: bool = False) -> bool:
    """Orchestrate Langfuse evaluation dataset creation."""
    DATASET_NAME = "academic_rag_evaluation"
    log_func = logger.info if use_logger else print

    try:
        langfuse = get_langfuse_client()
        create_dataset(langfuse, DATASET_NAME, use_logger=use_logger)
        add_items(langfuse, DATASET_NAME, use_logger=use_logger)

        log_func("\n" + "=" * 60)
        log_func("Evaluation dataset setup completed.")
        log_func("=" * 60)
        log_func(f"Dataset: '{DATASET_NAME}'")
        log_func("Total items: 10")
        log_func("  - Easy: 3")
        log_func("  - Medium: 4")
        log_func("  - Hard: 3")
        log_func("=" * 60)
        return True
    except RuntimeError as err:
        log_func(f"Warning: Langfuse credentials not configured, skipping dataset creation: {err}")
        return False
    except Exception as err:
        log_func(f"Error: Failed to create evaluation dataset: {err}")
        return False


if __name__ == "__main__":
    main(use_logger=False)
