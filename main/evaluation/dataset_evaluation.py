"""Evaluation utilities for scoring RAG responses with Langfuse and LLM judgment."""

import os
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from langfuse import Langfuse
from llama_index.core.settings import Settings

from .dataset import get_langfuse_client
from ..service.multimodal_service import get_service, MultimodalService

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATASET_NAME = "academic_rag_evaluation"


def _extract_score_from_text(text: str) -> float:
    """Extract a single numeric score from judgment text."""
    try:
        text = text.split(":", 1)[-1].strip()
        numbers = re.findall(r"\d+\.\d+|\d+", text)
        if not numbers:
            logger.warning(f"No numeric score found in judgment: {text}")
            return 0.0

        first_num = float(numbers[0])
        if len(numbers) >= 2:
            second_num = float(numbers[1])
            score = (first_num + second_num) / 2.0
        else:
            score = first_num

        return max(0.0, min(1.0, score))
    except Exception as exc:
        logger.warning(f"Failed to parse score from text '{text}': {exc}")
        return 0.0


async def evaluate_faithfulness_score(
    langfuse: Langfuse,
    trace_id: str,
    query: str,
    context: str,
    answer: str,
) -> float:
    """Evaluate answer faithfulness using LLM-as-a-judge."""
    judge_prompt = f"""
You are a judge evaluating whether the answer is faithful to the retrieved document context.

Question: {query}

Retrieved context:
{context}

Generated answer:
{answer}

Task: Rate faithfulness from 0.0 to 1.0.
- 1.0 = all answer claims are supported by the context.
- 0.7-0.9 = most claims are supported, with minor unsupported details.
- 0.4-0.6 = a mix of supported and unsupported claims.
- 0.1-0.3 = most claims are unsupported or fabricated.
- 0.0 = answer contradicts the context or is entirely invented.

Provide reasoning, then give a single numeric score.

Format:
Reasoning: ...
Score: 0.00
"""
    try:
        if not hasattr(Settings, "llm") or Settings.llm is None:
            raise RuntimeError("LLM is not configured in Settings for evaluation.")

        response = Settings.llm.complete(judge_prompt)
        judgment = response.text if hasattr(response, "text") else str(response)
        score = 0.0

        lines = [line for line in judgment.splitlines() if "Score:" in line]
        if lines:
            score = _extract_score_from_text(lines[0])
        else:
            score = _extract_score_from_text(judgment)

        langfuse.create_score(
            trace_id=trace_id,
            name="faithfulness",
            value=score,
            comment=judgment,
        )
        logger.info(f"Faithfulness score for trace {trace_id}: {score:.2f}")
        return score
    except Exception as exc:
        logger.error(f"Faithfulness evaluation error: {exc}", exc_info=True)
        return 0.0


async def evaluate_answer_relevance(
    langfuse: Langfuse,
    trace_id: str,
    query: str,
    answer: str,
) -> float:
    """Evaluate answer relevance using LLM-as-a-judge."""
    judge_prompt = f"""
You are a judge evaluating whether the answer addresses the user's question.

Question: {query}

Answer:
{answer}

Task: Rate relevance from 0.0 to 1.0.
- 1.0 = directly and completely answers the question.
- 0.7-0.9 = answers the question with some extra or tangential details.
- 0.4-0.6 = partially relevant, missing important points.
- 0.1-0.3 = mostly irrelevant.
- 0.0 = unrelated.

Provide reasoning, then give a single numeric score.

Format:
Reasoning: ...
Score: 0.00
"""
    try:
        if not hasattr(Settings, "llm") or Settings.llm is None:
            raise RuntimeError("LLM is not configured in Settings for evaluation.")

        response = Settings.llm.complete(judge_prompt)
        judgment = response.text if hasattr(response, "text") else str(response)
        score = 0.0

        lines = [line for line in judgment.splitlines() if "Score:" in line]
        if lines:
            score = _extract_score_from_text(lines[0])
        else:
            score = _extract_score_from_text(judgment)

        langfuse.create_score(
            trace_id=trace_id,
            name="answer_relevance",
            value=score,
            comment=judgment,
        )
        logger.info(f"Answer relevance score for trace {trace_id}: {score:.2f}")
        return score
    except Exception as exc:
        logger.error(f"Answer relevance evaluation error: {exc}", exc_info=True)
        return 0.0


async def query_with_evaluation(
    langfuse: Langfuse,
    service: MultimodalService,
    question: str,
    similarity_top_k: int = 4,
) -> Dict[str, Any]:
    """Execute a RAG query and run automatic evaluation for the result."""
    with langfuse.start_as_current_observation(
        as_type="span",
        name="rag_query",
        input={"question": question, "similarity_top_k": similarity_top_k},
        metadata={"dataset": DATASET_NAME},
    ) as span:
        trace_id = span.trace_id

        result = service.query(query=question, similarity_top_k=similarity_top_k)
        answer = result["answer"]

        context_lines: List[str] = []
        for node in result.get("source_nodes", []):
            source = node.get("source", "unknown")
            text_preview = node.get("text_preview", "")
            context_lines.append(f"Source: {source}\n{text_preview}")
        context = "\n\n".join(context_lines)

        faithfulness_task = asyncio.create_task(
            evaluate_faithfulness_score(langfuse, trace_id, question, context, answer)
        )
        relevance_task = asyncio.create_task(
            evaluate_answer_relevance(langfuse, trace_id, question, answer)
        )

        faithfulness_score, relevance_score = await asyncio.gather(faithfulness_task, relevance_task)

        span.update(output={
            "answer": answer,
            "evaluation": {
                "faithfulness": faithfulness_score,
                "answer_relevance": relevance_score,
            },
        })

    return {
        "question": question,
        "answer": answer,
        "trace_id": trace_id,
        "faithfulness": faithfulness_score,
        "answer_relevance": relevance_score,
        "source_nodes": result.get("source_nodes", []),
        "guardrails_report": result.get("guardrails_report", {}),
    }


async def run_dataset_evaluation(
    dataset_name: str = DATASET_NAME,
    similarity_top_k: int = 4,
) -> Dict[str, Any]:
    """Run evaluation over the Langfuse dataset and compute aggregate metrics."""
    service = get_service()
    service.initialize()

    langfuse = get_langfuse_client()
    dataset = langfuse.get_dataset(dataset_name)
    items = dataset.items

    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        question = item.input.get("question") if isinstance(item.input, dict) else None
        expected_output = item.expected_output
        if not question:
            continue

        logger.info(f"Evaluating item {idx}/{len(items)}: {question}")
        result = await query_with_evaluation(
            langfuse=langfuse,
            service=service,
            question=question,
            similarity_top_k=similarity_top_k,
        )
        result["expected_output"] = expected_output
        results.append(result)
        await asyncio.sleep(1)

    avg_faithfulness = sum(r["faithfulness"] for r in results) / max(len(results), 1)
    avg_relevance = sum(r["answer_relevance"] for r in results) / max(len(results), 1)

    metrics = {
        "dataset_name": dataset_name,
        "queries_executed": len(results),
        "average_faithfulness": avg_faithfulness,
        "average_answer_relevance": avg_relevance,
    }
    logger.info(f"Completed dataset evaluation: {metrics}")
    return {"metrics": metrics, "results": results}


async def main():
    """Main orchestration for dataset evaluation."""
    await run_dataset_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
