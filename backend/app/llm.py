import requests
import os
from typing import List

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

def generate_text(prompt: str, model: str = "mistral:7b-instruct-q4_K_M") -> str:
    """
    Generate text using Ollama.
    
    Args:
        prompt: The prompt to send to the model
        model: The model to use (default: mistral 7B)
        
    Returns:
        Generated text response
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        return f"Error generating text: {str(e)}"

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding using Nomic.
    
    Args:
        text: The text to embed
        
    Returns:
        768-dimensional embedding vector
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return [0.0] * 768  # Return zero vector on error
