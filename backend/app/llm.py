"""
LLM Integration Module — Supports both Ollama (local) and Groq (cloud).

Toggle via environment variable:
    GROQ_ENABLED=yes  → Uses Groq Cloud API (free, fast, needs internet)
    GROQ_ENABLED=no   → Uses Ollama (local, offline, needs GPU)

Required env vars for Groq mode:
    GROQ_API_KEY=gsk_xxxxx
"""
import requests
import os
import logging
from typing import List
from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger("aml.llm")

# ─── Configuration ─────────────────────────────────────────────
GROQ_ENABLED = os.getenv("GROQ_ENABLED", "no").lower() in ("yes", "true", "1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = "mistral:7b-instruct-q4_K_M"

if GROQ_ENABLED:
    logger.info(f"🌐 LLM Provider: GROQ (model: {GROQ_MODEL})")
else:
    logger.info(f"🖥️  LLM Provider: OLLAMA (model: {OLLAMA_MODEL})")


# ─── Text Generation ───────────────────────────────────────────

def generate_text(prompt: str, model: str = None) -> str:
    """
    Generate text using either Groq or Ollama based on GROQ_ENABLED env var.

    Args:
        prompt: The prompt to send to the model
        model: Optional model override

    Returns:
        Generated text response
    """
    if GROQ_ENABLED:
        return _generate_text_groq(prompt)
    else:
        return _generate_text_ollama(prompt, model or OLLAMA_MODEL)


def _generate_text_groq(prompt: str) -> str:
    """Generate text via Groq Cloud API (OpenAI-compatible)."""
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert AML compliance analyst."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1024
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return f"Error generating text via Groq: {str(e)}"


def _generate_text_ollama(prompt: str, model: str) -> str:
    """Generate text via local Ollama instance."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"Error generating text via Ollama: {str(e)}"


# ─── Embedding Generation ─────────────────────────────────────

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector.

    - Groq mode: Uses a lightweight local approach (hash-based 768-dim vector)
      since Groq doesn't offer an embedding endpoint on free tier.
      For production, swap this with a dedicated embedding API.
    - Ollama mode: Uses nomic-embed-text (768-dim).

    Returns:
        768-dimensional embedding vector
    """
   
    return _generate_embedding_ollama(text)


def _generate_embedding_local(text: str) -> List[float]:
    """
    Generate a deterministic 768-dim embedding from text using hashing.
    This is a lightweight fallback when Ollama is not available.
    Good enough for RAG similarity when documents are seeded consistently.
    """
    import hashlib
    import struct

    # Create a deterministic hash-based vector
    vectors = []
    for i in range(768):
        hash_input = f"{text}_{i}".encode("utf-8")
        h = hashlib.sha256(hash_input).digest()
        val = struct.unpack("f", h[:4])[0]
        # Normalize to [-1, 1] range
        val = (val % 2.0) - 1.0
        vectors.append(round(val, 6))

    # Normalize the vector (unit length)
    magnitude = sum(v * v for v in vectors) ** 0.5
    if magnitude > 0:
        vectors = [v / magnitude for v in vectors]

    return vectors


def _generate_embedding_ollama(text: str) -> List[float]:
    """Generate embedding using Ollama's nomic-embed-text model."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return [0.0] * 768  # Return zero vector on error

