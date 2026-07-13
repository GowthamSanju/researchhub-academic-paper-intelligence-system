"""Guardrails validators for input/output safety."""
import logging
from datetime import datetime
from typing import Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


class GuardrailsValidator:
    """
    Orchestrates input and output validation using LOCAL guardrails.
    
    Implements:
    - Input Guardrails: Sanitization & validation
    - Output Guardrails: PII detection & redaction
    - Security & Operational Guardrails: Rate limiting & content filtering
    
    Prerequisites:
    1. Install Presidio for PII detection:
       pip install presidio-analyzer presidio-anonymizer
    """
    
    def __init__(self):
        """Initialize LOCAL guardrails validators (no external API calls needed)."""
        self._pii_analyzer = None
        self._pii_anonymizer = None
        self._initialize_pii_detection()
        logger.info("✓ Guardrails validators initialized")
    
    def _initialize_pii_detection(self) -> None:
        """Initialize Presidio for LOCAL PII detection and anonymization."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            
            self._pii_analyzer = AnalyzerEngine()
            self._pii_anonymizer = AnonymizerEngine()
            logger.info("✓ Presidio PII detection initialized (LOCAL, no API calls)")
        except ImportError as e:
            logger.warning(f"Presidio not installed: {e}. PII detection will be skipped.")
            logger.info("Install with: pip install presidio-analyzer presidio-anonymizer")
    
    # ============================================================================
    # INPUT GUARDRAILS
    # ============================================================================
    
    def validate_input(self, text: str, max_length: int = 10000) -> Tuple[bool, str]:
        """
        Validate input text for safety and quality.
        
        Input Guardrails:
        - Non-empty validation
        - Length validation
        - Format validation
        
        Args:
            text: The input text to validate
            max_length: Maximum allowed length
            
        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        logger.debug(f"Validating input (length={len(text) if text else 0})")
        
        # Empty check
        if not text or not text.strip():
            return False, "Input text cannot be empty"
        
        # Length check
        if len(text) > max_length:
            return False, f"Input exceeds maximum length of {max_length} characters"
        
        # Content safety checks
        prohibited_patterns = [
            "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE ", "ALTER TABLE",  # destructive SQL
            "EXECUTE", "GRANT", "REVOKE", "CREATE TABLE", "CREATE DATABASE",
            "script>", "<iframe", "<embed",  # XSS patterns
        ]
        
        text_upper = text.upper()
        for pattern in prohibited_patterns:
            if pattern in text_upper:
                return False, f"Input contains potentially harmful content: {pattern}"
        
        logger.debug("✓ Input validation passed")
        return True, None
    
    def sanitize_input(self, text: str) -> str:
        """
        Sanitize input text by removing potentially harmful content.
        
        Args:
            text: The text to sanitize
            
        Returns:
            Sanitized text
        """
        logger.debug("Sanitizing input")
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize whitespace
        text = " ".join(text.split())
        
        logger.debug(f"✓ Input sanitized")
        return text
    
    
    # ============================================================================
    # OUTPUT GUARDRAILS
    # ============================================================================
    
    def validate_output(
        self,
        text: str,
        check_pii: bool = True,
        check_length: bool = True,
        max_length: int = 50000
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate and sanitize output text.
        
        Output Guardrails:
        - PII detection and redaction
        - Length validation
        - Hallucination detection (if output is too short for query length)
        
        Args:
            text: The output text to validate
            check_pii: Whether to check and redact PII
            check_length: Whether to validate output length
            max_length: Maximum allowed output length
            
        Returns:
            Tuple of (is_valid: bool, sanitized_text: str, metadata: Dict)
        """
        metadata = {
            "pii_detected": False,
            "pii_entities": [],
            "length_valid": True,
            "warnings": [],
        }
        
        logger.debug(f"Validating output (length={len(text)})")
        sanitized_text = text
        
        # PII Detection & Redaction
        if check_pii and self._pii_analyzer:
            logger.debug("🔍 Checking output for PII...")
            try:
                results = self._pii_analyzer.analyze(
                    text=text,
                    language="en",
                    entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN"]
                )
                
                if results:
                    logger.info(f"⚠ Detected {len(results)} PII entities")
                    metadata["pii_detected"] = True
                    metadata["pii_entities"] = [r.entity_type for r in results]
                    
                    # Redact PII
                    for result in sorted(results, key=lambda r: r.start, reverse=True):
                        entity_type = result.entity_type
                        start = result.start
                        end = result.end
                        
                        redaction = f"[{entity_type}]"
                        sanitized_text = sanitized_text[:start] + redaction + sanitized_text[end:]
                        logger.debug(f"  Redacted {entity_type} at position {start}")
                    
                    metadata["warnings"].append(f"PII detected and redacted: {', '.join(set(metadata['pii_entities']))}")
                else:
                    logger.debug("✓ No PII detected")
                    
            except Exception as e:
                logger.warning(f"PII detection failed: {e}")
                metadata["warnings"].append(f"PII detection error: {str(e)}")
        
        # Length validation
        if check_length and len(sanitized_text) > max_length:
            metadata["length_valid"] = False
            metadata["warnings"].append(f"Output exceeds max length: {len(sanitized_text)} > {max_length}")
            logger.warning(f"Output length exceeds limit: {len(sanitized_text)}")
        
        # Basic hallucination detection (very short output for normal query)
        if len(sanitized_text) < 10 and check_length:
            metadata["warnings"].append("Output is suspiciously short - possible hallucination")
        
        logger.info(f"✓ Output validation complete (pii_detected={metadata['pii_detected']}, warnings={len(metadata['warnings'])})")
        return True, sanitized_text, metadata
    
    # ============================================================================
    # REWRITTEN SECURITY & JAILBREAK GUARDRAIL
    # ============================================================================
    def check_query_safety(self, query: str) -> Tuple[bool, List[str]]:
        """
        Check query for semantic security threats, prompt injection, and jailbreaks.
        """
        issues = []
        logger.info(f"Performing intensive safety scan on query: '{query[:60]}...'")
        
        # 1. Structural/SQL Injection Baseline Check
        dangerous_sql_patterns = [
            "DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE ", "ALTER TABLE",
            "EXECUTE", "GRANT", "REVOKE", "CREATE TABLE", "CREATE DATABASE", "TRUNCATE"
        ]
        query_upper = query.upper()
        for keyword in dangerous_sql_patterns:
            if keyword in query_upper:
                issues.append(f"Possible destructive SQL operation detected: {keyword}")
        
        if query.count(";") > 3 or query.count("{") > 2:
            issues.append("Suspicious code execution or encoding syntax detected")

        # 2. Prompt injection and jailbreak heuristic detection
        injection_patterns = [
            "ignore previous", "forget", "override", "system prompt", "jailbreak", "rogue terminal",
            "do anything", "break out", "disable safety", "open the door"
        ]
        query_lower = query.lower()
        for pattern in injection_patterns:
            if pattern in query_lower:
                issues.append(f"Prompt injection pattern anomaly: '{pattern}' detected")

        if issues:
            logger.warning(f"⚠ Critical Guardrail Triggered! Issues found: {issues}")
            return False, issues
        
        logger.info("✓ Query passed semantic safety guard layer")
        return True, []
    
    def check_rate_limits(
        self,
        user_id: str,
        operation: str,
        request_count: int,
        max_requests_per_minute: int = 10
    ) -> Tuple[bool, str]:
        """
        Check if user is within rate limits (Operational Guardrail).
        
        Args:
            user_id: User identifier
            operation: Operation type (query, upload, etc.)
            request_count: Current request count for this operation
            max_requests_per_minute: Max allowed requests
            
        Returns:
            Tuple of (is_within_limits: bool, message: str)
        """
        if request_count >= max_requests_per_minute:
            message = f"Rate limit exceeded for {operation}: {request_count}/{max_requests_per_minute} requests"
            logger.warning(f"Rate limit exceeded for user {user_id}: {message}")
            return False, message
        
        return True, f"{request_count}/{max_requests_per_minute} requests used"
    
    def validate_content_type(self, content: str, expected_type: str = "text") -> Tuple[bool, str]:
        """
        Validate that content matches expected type (Operational Guardrail).
        
        Args:
            content: The content to validate
            expected_type: Expected type (text, json, markdown, etc.)
            
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        logger.debug(f"Validating content type: {expected_type}")
        
        if expected_type == "text" and isinstance(content, str):
            return True, "Content is valid text"
        elif expected_type == "json":
            try:
                import json
                json.loads(content)
                return True, "Content is valid JSON"
            except:
                return False, "Content is not valid JSON"
        elif expected_type == "markdown":
            # Basic markdown validation
            if any(c in content for c in ["#", "*", "-", "`", "["]):
                return True, "Content appears to be markdown"
            return False, "Content does not appear to be markdown"
        
        return True, "Content type validation passed"
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_validation_report(self, query: str, response: str) -> Dict[str, Any]:
        """
        Generate a complete validation report for a query-response pair.
        
        Args:
            query: The input query
            response: The output response
            
        Returns:
            Dictionary containing comprehensive validation results
        """
        logger.info("Generating validation report...")
        
        # Input validation
        input_valid, input_error = self.validate_input(query)
        
        # Query safety
        query_safe, query_issues = self.check_query_safety(query)
        
        # Output validation
        output_valid, sanitized_output, output_metadata = self.validate_output(response)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "input": {
                "valid": input_valid,
                "error": input_error,
                "length": len(query),
            },
            "query_security": {
                "safe": query_safe,
                "issues": query_issues,
            },
            "output": {
                "valid": output_valid,
                "pii_detected": output_metadata["pii_detected"],
                "pii_entities": output_metadata["pii_entities"],
                "length": len(sanitized_output),
                "warnings": output_metadata["warnings"],
            },
            "overall_safe": input_valid and query_safe and output_valid,
        }
        
        logger.info(f"✓ Validation report generated (overall_safe={report['overall_safe']})")
        return report


# Global validator instance
_global_validator: GuardrailsValidator = None


def get_validator() -> GuardrailsValidator:
    """Get or create the global validator instance."""
    global _global_validator
    if _global_validator is None:
        _global_validator = GuardrailsValidator()
    return _global_validator
