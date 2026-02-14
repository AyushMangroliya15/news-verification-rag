"""
OpenAI embedding wrapper for RAG. Single interface: embed(text) -> list[list[float]].
"""

import logging
from typing import List, Union

from openai import OpenAI

from backend.config import OPENAI_API_KEY, RAG_EMBEDDING_MODEL

logger = logging.getLogger(__name__)


def embed(text: Union[str, List[str]]) -> List[List[float]]:
    """
    Embed one or more texts using the configured OpenAI embedding model.
    Returns list of embedding vectors (each a list of floats).
    """
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set; embeddings will fail.")
    client = OpenAI(api_key=OPENAI_API_KEY or "")
    inputs = [text] if isinstance(text, str) else text
    if not inputs:
        return []
    try:
        response = client.embeddings.create(
            model=RAG_EMBEDDING_MODEL,
            input=inputs,
        )
        # Preserve order by index
        by_index = {e.index: e.embedding for e in response.data}
        return [by_index[i] for i in range(len(inputs))]
    except Exception as e:
        logger.exception("Embedding request failed: %s", e)
        raise
