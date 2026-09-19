"""
GitHub Models — free, OpenAI-compatible inference authenticated by the
GITHUB_TOKEN already present in every Actions run. No separate API key.

KNOWN GOTCHA from research: org-owned repos can return 403 on inference
even with `models: read` granted in the workflow, while personal-account
repos work fine. This repo must live under a personal account, not an
org, or this whole layer silently breaks.
"""

from __future__ import annotations
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-4.1-mini"  # small, fast, cheap on rate limits — plenty for 9 short paragraphs
BASE_URL = "https://models.github.ai/inference"


def get_client() -> OpenAI | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning("GITHUB_TOKEN not set. Running in MOCK mode for local testing.")
        return None
    return OpenAI(base_url=BASE_URL, api_key=token)


def generate(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    client = get_client()
    if client is None:
        # Mock mode
        lines = prompt.split("\n")
        country = lines[0].split(": ")[1]
        return f"A dummy macro narrative summary for {country}. The news headlines indicated a generally cautious market sentiment today, heavily influenced by global rate hikes."

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()
