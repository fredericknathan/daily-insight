"""
LLM inference layer with robust failover.
Primary: OpenAI (LLM_API_KEY)
Fallback: Groq (GROQ_API_KEY)
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

    # Try Primary (OpenAI or user's custom base URL)
    primary_token = os.environ.get("LLM_API_KEY")
    if primary_token:
        try:
            base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
            model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            
            client = OpenAI(base_url=base_url, api_key=primary_token)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Primary LLM generation failed: %s", e)
    else:
        logger.warning("LLM_API_KEY not set, attempting fallback...")

    # Try Fallback (Groq)
    groq_token = os.environ.get("GROQ_API_KEY")
    if groq_token:
        try:
            logger.info("Using Groq fallback...")
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_token)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Groq fallback generation failed: %s", e)
    
    # Mock fallback if nothing works locally
    if not primary_token and not groq_token:
        logger.warning("No API keys found. Returning MOCK data.")
        lines = prompt.split("\n")
        country = lines[0].split(": ")[1]
        return f"A dummy macro narrative summary for {country}. The news headlines indicated a generally cautious market sentiment today, heavily influenced by global rate hikes."

    raise RuntimeError("All LLM generation attempts failed.")
