import logging
import re
import os
from pathlib import Path
from nemoguardrails import LLMRails, RailsConfig

logger = logging.getLogger(__name__)

# Locate the guardrails configuration directory
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "guardrails"

# Load the configuration and initialize NeMo once.
config = RailsConfig.from_path(str(CONFIG_DIR))

# Configure NeMo to use the Ollama endpoint from the environment.
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
config.models[0].parameters["base_url"] = f"{ollama_base_url}/v1"

rails = LLMRails(config, verbose=False)

BLOCKED_MESSAGE = "I'm sorry, I can't respond to that."

# Transformation requests must begin with an explicit task.
SAFE_ANALYSIS_PATTERN = re.compile(
    r"^\s*(translate|summari[sz]e|analy[sz]e|explain|classify)\b",
    re.IGNORECASE
)

# Recognize quoted content.
QUOTED_TEXT_PATTERN = re.compile(
    r""" "[^"]*"|'[^']*' """,
    re.DOTALL | re.VERBOSE
)

# Recognize explicitly labelled untrusted content.
UNTRUSTED_TEXT_MARKER_PATTERN = re.compile(
    r"\b(?:text|content|passage|input)\s*:",
    re.IGNORECASE
)

# Patterns for clearly identifiable direct attacks.
ATTACK_PATTERNS = [
    re.compile(
        r"\bignore\b.{0,80}\b(previous|all|prior|above|original)\b"
        r".{0,80}\b(instructions|rules|task|prompt)\b",
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r"\b(reveal|print|show|repeat|disclose|expose)\b"
        r".{0,100}\b(system prompt|hidden instructions|developer instructions|"
        r"api keys?|passwords?|credentials|secrets)\b",
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r"\b(developer mode|unrestricted mode)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(disable|bypass|override|remove)\b.{0,80}"
        r"\b(safety|guardrails|restrictions|policies)\b",
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r"\bunrestricted\b.{0,50}\b(ai|assistant|model)\b",
        re.IGNORECASE
    ),
]

def is_malicious_input(message: str) -> bool:
    """
    Detect identifiable direct instruction attacks.

    For explicit transformation requests, inspect the task
    instructions separately from the supplied content.
    """

    inspected_message = message

    if SAFE_ANALYSIS_PATTERN.search(message):

        marker = UNTRUSTED_TEXT_MARKER_PATTERN.search(message)

        if marker:
            # Inspect the task instructions before the data marker.
            inspected_message = message[:marker.start()]

        else:
            # Remove quoted data before inspecting the instructions.
            inspected_message = QUOTED_TEXT_PATTERN.sub("", message)

    return any(
        pattern.search(inspected_message)
        for pattern in ATTACK_PATTERNS
    )



async def generate_guardrailed_response(message: str) -> dict:
    """Check input, generate a response, and inspect the output."""

    if is_malicious_input(message):
        logger.warning("Input blocked by deterministic security check")

        return {
            "response": BLOCKED_MESSAGE,
            "security_decision": "INPUT_BLOCKED"
        }

    logger.info("Input allowed by deterministic security check")

    result = await rails.generate_async(
        messages=[
            {
                "role": "user",
                "content": message
            }
        ],
        options={
            "log": {
                "activated_rails": True
            }
        }
    )

    if not isinstance(result, dict) and not hasattr(result, "response"):
        raise ValueError("Unexpected response format from NeMo Guardrails")

    output_blocked = was_output_blocked(result)

    content = result.response[0].get("content")

    if not isinstance(content, str):
        raise ValueError("NeMo Guardrails returned an invalid response")

    return {
        "response": content,
        "security_decision": (
            "OUTPUT_BLOCKED" if output_blocked else "ALLOWED"
        )
    }

    
def was_output_blocked(result) -> bool:
    """Return True when NeMo's self-check output rail blocks a response."""

    generation_log = getattr(result, "log", None)

    if generation_log is None:
        return False

    activated_rails = getattr(generation_log, "activated_rails", [])

    for rail in activated_rails:
        for action in getattr(rail, "executed_actions", []):
            if action.action_name != "self_check_output":
                continue

            outcome = action.return_value
            decision = getattr(outcome, "decision", None)

            if getattr(decision, "value", decision) == "block":
                return True
    return False