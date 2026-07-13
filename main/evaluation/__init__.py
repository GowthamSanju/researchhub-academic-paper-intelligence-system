"""Evaluation package."""

from .dataset import get_langfuse_client, create_dataset, add_items, main as setup_evaluation_dataset
from .dataset_evaluation import (
    evaluate_faithfulness_score,
    evaluate_answer_relevance,
    query_with_evaluation,
    run_dataset_evaluation,
)

__all__ = [
    "get_langfuse_client",
    "create_dataset",
    "add_items",
    "setup_evaluation_dataset",
    "evaluate_faithfulness_score",
    "evaluate_answer_relevance",
    "query_with_evaluation",
    "run_dataset_evaluation",
]
