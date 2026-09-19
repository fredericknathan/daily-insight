"""
LLM inference layer with robust failover.
Primary: OpenAI
Fallback 1: Groq
Fallback 2: GitHub Models
"""

from __future__ import annotations
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def generate(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Try Primary (Groq)
    groq_token = os.environ.get("GROQ_API_KEY")
    if groq_token:
        try:
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_token)
            resp = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=temperature,
                timeout=15.0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Primary Groq generation failed: %s", e)
    else:
        logger.warning("GROQ_API_KEY not set, attempting fallback...")

    # Try Fallback 1 (OpenRouter)
    openrouter_token = os.environ.get("LLM_API_KEY")
    if openrouter_token:
        try:
            logger.info("Using OpenRouter fallback...")
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_token)
            resp = client.chat.completions.create(
                model="nvidia/nemotron-3-ultra-550b-a55b:free",
                messages=messages,
                temperature=temperature,
                timeout=15.0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("OpenRouter fallback generation failed: %s", e)

    # Try Fallback 2 (GitHub Models)
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        try:
            logger.info("Using GitHub Models fallback...")
            client = OpenAI(base_url="https://models.github.ai/inference", api_key=github_token)
            resp = client.chat.completions.create(
                model="openai/gpt-4.1-mini",
                messages=messages,
                temperature=temperature,
                timeout=15.0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("GitHub Models fallback generation failed: %s", e)
    
    raise RuntimeError("All LLM generation attempts failed.")
