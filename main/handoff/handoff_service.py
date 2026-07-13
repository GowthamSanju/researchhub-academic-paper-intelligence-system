"""Human handoff support service for flagging low-quality or unsafe query results."""

import datetime
import logging
import os
import re
import secrets
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from llama_index.core.settings import Settings

logger = logging.getLogger(__name__)

# Handoff thresholds
FAITHFULNESS_THRESHOLD = 0.7
RELEVANCE_THRESHOLD = 0.7
CONFIDENCE_THRESHOLD = 40  # 0-100 scale

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("APPLICATION_EMAIL")
EMAIL_TO = os.getenv("SUPPORT_EMAIL")


def generate_handoff_reference_id(now: Optional[datetime.datetime] = None) -> str:
    """Generate a unique handoff reference ID."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    token = secrets.token_hex(3).upper()
    return f"HO-{now.strftime('%Y%m%d-%H%M%S')}-{token}"


def evaluate_score(
    faithfulness: Optional[float],
    relevance: Optional[float],
    user_question: str,
    no_chunks: bool,
) -> Dict[str, Any]:
    """Decide whether the retrieved answer quality should trigger a human handoff."""
    # CHANGED: Allow the agent to answer using internal tools/reasoning even if zero vector chunks are returned
    if no_chunks:
        return {"trigger": False, "reason": "retrieval returned no context chunks; relying on agent logic"}

    if faithfulness is None or relevance is None:
        return {"trigger": False, "reason": "evaluation scores unavailable"}

    if faithfulness < FAITHFULNESS_THRESHOLD:
        return {
            "trigger": True,
            "reason": f"faithfulness below threshold ({faithfulness:.2f} < {FAITHFULNESS_THRESHOLD})",
        }

    if relevance < RELEVANCE_THRESHOLD:
        return {
            "trigger": True,
            "reason": f"relevance below threshold ({relevance:.2f} < {RELEVANCE_THRESHOLD})",
        }

    if any(keyword in user_question.lower() for keyword in ["human", "agent", "support", "escalate", "help"]):
        return {"trigger": True, "reason": "explicit user language indicates human assistance"}

    return {"trigger": False, "reason": "quality thresholds satisfied"}


async def evaluate_confidence_score(answer: str) -> Dict[str, Any]:
    """Ask the LLM to rate confidence for the generated answer."""
    llm = Settings.llm
    if llm is None:
        raise ValueError("LLM is not initialized for confidence evaluation")

    prompt = (
        "Please rate the confidence of the following answer on a scale from 0 to 100, "
        "where 100 means the answer is fully supported by the retrieved context and 0 means the answer is likely incorrect or invented."
        f"\n\nAnswer:\n{answer}\n\nRespond with a single integer."
    )

    try:
        if hasattr(llm, "acomplete"):
            response = await llm.acomplete(prompt)
        else:
            response = llm.complete(prompt)
    except Exception as exc:
        logger.warning(f"Confidence evaluation failed: {exc}")
        return {
            "trigger": False,
            "reason": "confidence evaluation failed",
            "confidence": 50,
        }

    text = getattr(response, "text", str(response))
    numbers = re.findall(r"\d+", text)
    confidence = int(numbers[0]) if numbers else 50
    confidence = max(0, min(100, confidence))

    trigger = confidence < CONFIDENCE_THRESHOLD
    reason = (
        f"LLM confidence below threshold ({confidence} < {CONFIDENCE_THRESHOLD})"
        if trigger
        else "confidence is sufficient"
    )

    return {
        "trigger": trigger,
        "reason": reason,
        "confidence": confidence,
    }


async def evaluate_explicit_user_request(message: str) -> Dict[str, Any]:
    """Classify whether the user explicitly asked for a human reviewer."""
    llm = Settings.llm
    if llm is None:
        raise ValueError("LLM is not initialized for explicit request evaluation")

    prompt = (
        "Determine whether the user explicitly requests human assistance. "
        "Respond with ONLY YES or NO.\n\n"
        f"User message: \"{message}\"\n"
    )

    try:
        if hasattr(llm, "acomplete"):
            response = await llm.acomplete(prompt)
        else:
            response = llm.complete(prompt)
    except Exception as exc:
        logger.warning(f"Explicit user request evaluation failed: {exc}")
        return {"trigger": False, "reason": "explicit request evaluation failed"}

    text = getattr(response, "text", str(response)).strip().upper()
    is_explicit = "YES" in text

    return {
        "trigger": is_explicit,
        "reason": "LLM classified explicit handoff request" if is_explicit else "no explicit human request detected",
    }


def send_handoff_email(context: Dict[str, Any]):
    """Send a human handoff notification email with full handoff context."""
    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.warning("Email settings missing. Cannot send handoff email.")
        return

    subject = f"[HUMAN HANDOFF] Ref {context.get('reference_id', 'UNKNOWN')} - {context.get('trigger_reason', 'handoff')}"

    retrieved_chunks = context.get("retrieved_chunks", [])
    chunk_text = "\n\n".join(
        [
            f"Source: {chunk.get('source', 'unknown')}\nScore: {chunk.get('score', 'n/a')}\nText:\n{chunk.get('text', '')}"
            for chunk in retrieved_chunks
        ]
    ) or "No retrieved chunks available."

    body = f"""
A human handoff has been triggered.

Reference ID: {context.get('reference_id')}
Trace ID: {context.get('trace_id')}
Timestamp: {context.get('timestamp_utc')}
Priority: {context.get('priority')}
Trigger Reason: {context.get('trigger_reason')}

User Email: {context.get('user_metadata', {}).get('email', 'N/A')}
Session ID: {context.get('session_id')}

User Query History:
{context.get('query_history')}

Generated Answer:
{context.get('generated_answer')}

Evaluation Scores:
Faithfulness: {context.get('evaluation_scores', {}).get('faithfulness')}
Relevance: {context.get('evaluation_scores', {}).get('relevance')}
LLM Confidence: {context.get('evaluation_scores', {}).get('confidence')}

Retrieved Chunks:
{chunk_text}

Conversation Flow:
{context.get('conversation_flow')}

Guardrails Report:
{context.get('guardrails_report')}
"""

    msg = MIMEText(body)
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        logger.info("Human handoff email sent successfully.")
    except Exception as exc:
        logger.error(f"Failed to send handoff email: {exc}")
