"""
OpenRouter LLM Integration.
Uses native OpenAI client for Nemotron model via OpenRouter.
"""

import os
from openai import OpenAI


# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "nvidia/nemotron-3-nano-30b-a3b:free"


def get_openai_client() -> OpenAI:
    """Get OpenAI client configured for OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
    )


def generate_answer(prompt: str, enable_reasoning: bool = True) -> str:
    """
    Generate an answer using Nemotron model via OpenRouter.
    
    Args:
        prompt: The prompt to send to the model
        enable_reasoning: Whether to enable reasoning mode
        
    Returns:
        Generated text response
    """
    client = get_openai_client()
    
    try:
        extra_body = {}
        if enable_reasoning:
            extra_body["reasoning"] = {"enabled": True}
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            extra_body=extra_body if extra_body else None,
            max_tokens=4096,  # Increased for comprehensive code explanations
            temperature=0.1,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        raise


def get_available_models() -> dict:
    """Return available model options for frontend display."""
    return {
        "nemotron": {
            "name": "Nemotron 30B (Free)",
            "description": "NVIDIA Nemotron with reasoning capabilities"
        }
    }
