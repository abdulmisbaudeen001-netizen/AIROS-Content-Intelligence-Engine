"""
AIROS Content Intelligence Engine
LLM Service — single gateway for all agent LLM calls.

Agents call:  llm_service.generate(prompt, system, ...)
They never know which model responded.

Routing:
  1. openrouter/auto  (free router — picks best available free model)
  2. DeepSeek V4 Flash free
  3. Tencent Hy3 free
  4. Qwen free (emergency)
"""

import time
from typing import Optional
import httpx

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    LLM_PRIMARY_MODEL,
    LLM_FALLBACK_CHAIN,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    LLM_MAX_RETRIES,
)
from logger import get_logger

logger = get_logger("llm_service")

_MODEL_CHAIN = [LLM_PRIMARY_MODEL] + LLM_FALLBACK_CHAIN


class LLMError(Exception):
    """Raised when all models in the chain are exhausted."""


def generate(
    prompt: str,
    system: str = "You are AIROS, an autonomous AI content engine. Be precise, factual, and human in your writing.",
    temperature: float = LLM_TEMPERATURE,
    max_tokens: int = LLM_MAX_TOKENS,
    json_mode: bool = False,
) -> str:
    """
    Send a prompt through the model chain.
    Returns the text content of the first successful response.

    Args:
        prompt:      User message / task description.
        system:      System-level instruction for the model.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        max_tokens:  Maximum response length.
        json_mode:   If True, instructs the model to return only valid JSON.

    Returns:
        str: Model response text.

    Raises:
        LLMError: If every model in the chain fails.
    """
    if not OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY is not set.")

    if json_mode:
        system += "\n\nRESPOND ONLY WITH VALID JSON. No preamble. No markdown fences."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://airos.news",
        "X-Title": "AIROS Content Intelligence Engine",
    }

    last_error: Optional[Exception] = None

    for model in _MODEL_CHAIN:
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            try:
                logger.debug(f"LLM call | model={model} | attempt={attempt}")

                payload = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                }

                with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
                    response = client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                response.raise_for_status()
                data = response.json()

                text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"LLM success | model={model} | chars={len(text)}")
                return text

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                logger.warning(f"LLM HTTP error | model={model} | status={status} | attempt={attempt}")
                last_error = e

                # Rate limit — back off before retry
                if status == 429:
                    time.sleep(5 * attempt)
                else:
                    break  # Non-rate-limit HTTP errors → try next model immediately

            except Exception as e:
                logger.warning(f"LLM error | model={model} | error={e} | attempt={attempt}")
                last_error = e
                time.sleep(2 * attempt)

        logger.warning(f"Model exhausted, moving to next | model={model}")

    raise LLMError(f"All models in chain failed. Last error: {last_error}")
